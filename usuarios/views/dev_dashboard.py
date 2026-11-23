from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q, Count, Prefetch, Value, FloatField
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from ..forms import PerfilDesarrolladorForm
from ..models import PerfilDesarrollador, Usuario
from logs.models import LogAuditoria
from ..decorators import requiere_usuario_activo
from ..utils import get_admin_id
from proyectos.models import Proyecto, Valoracion, Entregable, CategoriaSolucion
from postulaciones.models import Postulacion
from contrataciones.models import Contratacion, ContratoDigital
from disputas.services import datos_dashboard_disputas
from favoritos.models import Favorito
from mensajes.models import Mensaje
from ._helpers import get_notificaciones_context

# Secciones navegables del dashboard (usadas para ?seccion= y el estado inicial).
SECCIONES_DASHBOARD = {
    'inicio', 'centro-chat', 'explorar', 'postulaciones', 'activos',
    'completados', 'contratos', 'favoritos', 'disputas', 'perfil',
}


@login_required
@requiere_usuario_activo
def dashboard_desarrollador(request):
    if request.user.rol != 'desarrollador': return redirect('inicio')

    promedio = Valoracion.objects.filter(desarrollador=request.user, rol_evaluador='empresa').aggregate(Avg('puntuacion'))['puntuacion__avg'] or 0
    p_comp = Contratacion.objects.filter(desarrollador=request.user, estado='finalizada').count()
    p_act = Contratacion.objects.filter(desarrollador=request.user, estado='activa').count()
    p_fav = Favorito.objects.filter(desarrollador=request.user).count()

    mis_postulaciones = Postulacion.objects.filter(
        desarrollador=request.user
    ).select_related('proyecto', 'proyecto__empresa', 'proyecto__empresa__perfil_empresa', 'contrato_digital')
    mis_proyectos_activos_q = Contratacion.objects.filter(desarrollador=request.user, estado='activa').select_related('proyecto', 'empresa', 'empresa__perfil_empresa')

    # SCRUM-227 (RF 1.2.3): separación vigentes vs historial (contexto aditivo)
    postulaciones_vigentes = mis_postulaciones.filter(
        estado__in=['pendiente', 'en_negociacion']
    ).exclude(
        proyecto__estado__in=['finalizado', 'inactivo', 'rechazado']
    ).order_by('-fecha')
    postulaciones_en_evaluacion = mis_postulaciones.filter(
        estado='pendiente'
    ).exclude(
        proyecto__estado__in=['finalizado', 'inactivo', 'rechazado']
    ).order_by('-fecha')
    postulaciones_historial = mis_postulaciones.filter(
        estado='rechazada'
    ).order_by('-fecha')

    contratos_vigentes = Contratacion.objects.filter(
        desarrollador=request.user, estado__in=['activa', 'en_disputa']
    ).select_related('proyecto', 'empresa', 'empresa__perfil_empresa').order_by('-fecha_inicio')

    contratos_historial = Contratacion.objects.filter(
        Q(desarrollador=request.user) & (
            Q(estado__in=['finalizada', 'cancelada']) |
            Q(proyecto__estado__in=['finalizado', 'inactivo', 'rechazado'])
        )
    ).select_related('proyecto', 'empresa', 'empresa__perfil_empresa', 'contrato_digital').order_by('-fecha_inicio').distinct()

    from contrataciones.models import SolicitudCancelacion
    solicitudes_cancelacion_dev = SolicitudCancelacion.objects.filter(
        contratacion__desarrollador=request.user,
    ).select_related(
        'contratacion__proyecto', 'contratacion__empresa',
        'solicitante', 'resuelto_por',
    ).order_by('-fecha_creacion')
    contratos_cancelables_dev = Contratacion.objects.filter(
        desarrollador=request.user, estado='activa',
    ).exclude(
        proyecto__estado='en_disputa',
    ).exclude(
        solicitudes_cancelacion__estado__in=['pendiente_acuerdo', 'pendiente_revision'],
    ).select_related('proyecto', 'empresa').order_by('-fecha_inicio', '-id')
    cancelaciones_pendientes_dev = [
        s for s in solicitudes_cancelacion_dev
        if s.estado in ('pendiente_acuerdo', 'pendiente_revision')
    ]
    
    mis_proyectos_finalizados = Contratacion.objects.filter(
        Q(desarrollador=request.user) & 
        (Q(estado='finalizada') | Q(proyecto__estado='finalizado'))
    ).select_related('proyecto', 'empresa', 'empresa__perfil_empresa').annotate(
        num_desarrolladores=Count('proyecto__contrataciones')
    ).distinct()
    
    proyectos_con_accion = set(mis_postulaciones.values_list('proyecto_id', flat=True))
    proyectos_con_accion.update(mis_proyectos_activos_q.values_list('proyecto_id', flat=True))
    proyectos_con_accion.update(mis_proyectos_finalizados.values_list('proyecto_id', flat=True))

    mis_favoritos = Favorito.objects.filter(
        desarrollador=request.user, 
        proyecto__estado='publicado'
    ).exclude(proyecto_id__in=proyectos_con_accion).select_related(
        'proyecto',
        'proyecto__categoria',
        'proyecto__empresa',
        'proyecto__empresa__perfil_empresa',
    ).order_by('-fecha')

    valoraciones_queryset = Valoracion.objects.filter(desarrollador=request.user, rol_evaluador='empresa')
    mis_proyectos_finalizados = mis_proyectos_finalizados.prefetch_related(
        Prefetch('proyecto__valoraciones', queryset=valoraciones_queryset, to_attr='valoracion_empresa')
    )

    valoraciones_dev_qs = Valoracion.objects.filter(desarrollador=request.user, rol_evaluador='desarrollador')
    proyectos_calificados_por_dev = set(
        valoraciones_dev_qs.values_list('proyecto_id', flat=True)
    )

    for contrato in mis_proyectos_finalizados:
        contrato.valoracion = contrato.proyecto.valoracion_empresa[0] if contrato.proyecto.valoracion_empresa else None
        contrato.ya_califico_empresa = contrato.proyecto_id in proyectos_calificados_por_dev

    contrataciones_pendientes_calificar = [
        c for c in mis_proyectos_finalizados if not c.ya_califico_empresa
    ]

    mis_proyectos_qs = Proyecto.objects.filter(
        equipos__miembros=request.user, estado='en_desarrollo'
    ).select_related('empresa', 'empresa__perfil_empresa').annotate(
        hitos_completados=Count('entregables', filter=Q(entregables__estado='completado')),
        hitos_totales=Count('entregables'),
    ).prefetch_related(
        Prefetch('contrataciones',
            queryset=Contratacion.objects.filter(estado='activa').select_related('desarrollador'),
            to_attr='contratos_activos'),
    ).distinct()

    mis_proyectos_v = []
    proyectos_ids = list(mis_proyectos_qs.values_list('id', flat=True))

    if proyectos_ids:
        hitos_todos = Entregable.objects.filter(
            Q(proyecto_id__in=proyectos_ids) & 
            (
                Q(desarrollador=request.user) |
                Q(desarrollador__isnull=True, equipo__miembros=request.user) |
                Q(desarrollador__isnull=True, equipo__isnull=True)
            )
        ).distinct().values('proyecto_id', 'titulo', 'estado', 'descripcion')

        hitos_por_proyecto = {}
        for h in hitos_todos:
            p_id = h['proyecto_id']
            if p_id not in hitos_por_proyecto:
                hitos_por_proyecto[p_id] = []
            hitos_por_proyecto[p_id].append(h)

        for p in mis_proyectos_qs:
            perfil_empresa = getattr(p.empresa, 'perfil_empresa', None)
            dev_ids = [c.desarrollador_id for c in p.contratos_activos]
            hitos_del_proy = hitos_por_proyecto.get(p.id, [])
            hitos_pendientes_dev = sum(1 for h in hitos_del_proy if h.get('estado') == 'pendiente')
            porcentaje = int((p.hitos_completados / p.hitos_totales * 100)) if p.hitos_totales > 0 else 0
            proximo_hito = next((h for h in hitos_del_proy if h.get('estado') == 'pendiente'), None)
            mis_proyectos_v.append({
                'proyecto_id': p.id,
                'titulo': p.titulo,
                'empresa_nombre': p.empresa.nombre,
                'empresa_verificada': perfil_empresa.es_verificada if perfil_empresa else False,
                'empresa_badge': perfil_empresa.badge_info if perfil_empresa else None,
                'empresa_estado_verificacion': perfil_empresa.estado_verificacion if perfil_empresa else 'sin_verificar',
                'empresa_logo': perfil_empresa.logo.url if (perfil_empresa and getattr(perfil_empresa, 'logo', None)) else None,
                'hitos_completados': p.hitos_completados,
                'hitos_totales': p.hitos_totales,
                'hitos_pendientes': hitos_pendientes_dev,
                'porcentaje_avance': porcentaje,
                'proximo_hito': proximo_hito,
                'ultimo_avance': None,
                'fecha_fin': p.fecha_limite,
                'estado': p.estado,
                'empresa_id': p.empresa_id,
                'num_desarrolladores': len(dev_ids),
                'hitos': hitos_del_proy,
            })

    # Incluir en el Centro de Mensajes ÚNICAMENTE conversaciones activas (en desarrollo o negociación activa)
    # Los proyectos finalizados, inactivos o con contratos concluidos se eliminan automáticamente de las conversaciones.
    conversaciones_chat = []
    proyectos_v_ids = set()

    for p in mis_proyectos_v:
        if p.get('estado') == 'en_desarrollo':
            conversaciones_chat.append(p)
            proyectos_v_ids.add(p['proyecto_id'])

    # Solo postulaciones en negociación de proyectos activos publicados (excluye finalizados, inactivos y aceptadas concluidas)
    postulaciones_chat_qs = mis_postulaciones.filter(
        estado='en_negociacion',
        proyecto__estado__in=['publicado', 'en_desarrollo']
    ).select_related('proyecto__empresa__perfil_empresa')

    for post in postulaciones_chat_qs:
        if post.proyecto_id not in proyectos_v_ids:
            p_emp = getattr(post.proyecto.empresa, 'perfil_empresa', None)
            emp_logo = p_emp.logo.url if (p_emp and getattr(p_emp, 'logo', None)) else None
            conversaciones_chat.append({
                'proyecto_id': post.proyecto.id,
                'titulo': post.proyecto.titulo,
                'empresa_nombre': post.proyecto.empresa.nombre or post.proyecto.empresa.username,
                'empresa_id': post.proyecto.empresa_id,
                'empresa_logo': emp_logo,
                'estado_postulacion': post.estado,
                'es_negociacion': True,
            })
            proyectos_v_ids.add(post.proyecto_id)

    # Asegurar que cualquier postulación en negociación tenga su contrato digital asociado
    for post_nego in mis_postulaciones.filter(estado='en_negociacion').exclude(proyecto__estado__in=['finalizado', 'inactivo', 'rechazado']):
        if not hasattr(post_nego, 'contrato_digital'):
            ContratoDigital.objects.get_or_create(postulacion=post_nego)

    mis_contratos_digitales_todos = ContratoDigital.objects.filter(
        postulacion__desarrollador=request.user
    ).select_related(
        'postulacion__proyecto__empresa__perfil_empresa',
        'postulacion__proyecto',
        'contratacion',
    ).order_by('-fecha_actualizacion')

    mis_contratos_digitales_qs = mis_contratos_digitales_todos.exclude(
        Q(postulacion__proyecto__estado__in=['finalizado', 'inactivo', 'rechazado']) |
        Q(contratacion__estado__in=['finalizada', 'cancelada'])
    )

    contratos_pendientes_firma_count = mis_contratos_digitales_qs.filter(
        firmado_desarrollador=False,
        estado__in=['borrador', 'pendiente_firma'],
        postulacion__estado='en_negociacion',
    ).count()

    contratos_formalizados_count = mis_contratos_digitales_qs.filter(
        firmado_desarrollador=True
    ).count()

    total_contratos_digitales = mis_contratos_digitales_qs.count()

    # Paginación de contratos (8 por página -> 4 filas en grid de 2 columnas)
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator_contratos = Paginator(mis_contratos_digitales_qs, 8)
    page_contratos_num = request.GET.get('page_contratos', 1)
    try:
        contratos_digitales_page = paginator_contratos.page(page_contratos_num)
    except PageNotAnInteger:
        contratos_digitales_page = paginator_contratos.page(1)
    except EmptyPage:
        contratos_digitales_page = paginator_contratos.page(paginator_contratos.num_pages)

    mis_contratos_digitales = contratos_digitales_page.object_list

    admin_id = get_admin_id()
    notificaciones_recientes, notificaciones_pendientes_count = get_notificaciones_context(request.user.id)

    # Proyectos para la sección integrada de Explorar (RF 3.1.1)
    proyectos_explorar_qs = Proyecto.objects.filter(
        (Q(estado='publicado') | Q(estado='en_desarrollo')),
        (Q(fecha_limite__isnull=True) | Q(fecha_limite__gte=timezone.now().date()))
    ).exclude(
        id__in=proyectos_con_accion
    ).select_related('empresa', 'empresa__perfil_empresa', 'categoria').annotate(
        num_postulaciones=Count('postulaciones', distinct=True),
        empresa_reputacion=Coalesce(Avg('empresa__valoraciones_como_empresa__puntuacion',
            filter=Q(empresa__valoraciones_como_empresa__rol_evaluador='desarrollador')),
            Value(0.0), output_field=FloatField())
    ).order_by('-fecha_publicacion')

    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    proyectos_explorar_todos = [
        p for p in proyectos_explorar_qs
        if p.vacantes_disponibles > 0
    ]

    paginator_explorar = Paginator(proyectos_explorar_todos, 15)
    page_explorar_num = request.GET.get('page') or request.GET.get('page_explorar', 1)

    try:
        proyectos_explorar_page = paginator_explorar.page(page_explorar_num)
    except PageNotAnInteger:
        proyectos_explorar_page = paginator_explorar.page(1)
    except EmptyPage:
        proyectos_explorar_page = paginator_explorar.page(paginator_explorar.num_pages)

    proyectos_explorar = list(proyectos_explorar_page.object_list)

    favoritos_ids = list(Favorito.objects.filter(desarrollador=request.user).values_list('proyecto_id', flat=True))
    categorias_solucion = list(CategoriaSolucion.objects.filter(activo=True).order_by('nombre'))

    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=request.user)

    # --- Mi Perfil integrado en el dashboard (sin abrir otra página) ---
    perfil_form = PerfilDesarrolladorForm(instance=perfil)
    seccion_activa = request.GET.get('seccion', 'inicio')
    if seccion_activa not in SECCIONES_DASHBOARD:
        seccion_activa = 'inicio'
    if request.method == 'POST' and request.POST.get('accion') == 'perfil':
        es_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
        perfil_form = PerfilDesarrolladorForm(
            request.POST, request.FILES, instance=perfil
        )
        if perfil_form.is_valid():
            perfil_form.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                accion=f"Actualizó su perfil de {request.user.rol}",
                tabla_afectada=f"perfil_{request.user.rol}",
                registro_id=request.user.id,
            )
            if es_ajax:
                from django.http import JsonResponse
                foto_url = perfil.foto_perfil.url if perfil.foto_perfil else ''
                return JsonResponse({
                    'ok': True,
                    'mensaje': 'Perfil actualizado correctamente',
                    'nombre': request.user.nombre or request.user.username,
                    'foto_url': foto_url,
                })
            messages.success(request, 'Perfil actualizado')
            return redirect(reverse('dashboard_desarrollador'))

        if es_ajax:
            from django.http import JsonResponse
            return JsonResponse({
                'ok': False,
                'errores': {field: [str(e) for e in errs] for field, errs in perfil_form.errors.items()},
                'mensaje': 'Por favor corrige los errores del formulario.',
            }, status=400)
        seccion_activa = 'perfil'

    valores_verificacion = {
        'ficha': perfil.ficha or '',
        'programa_formacion': perfil.programa_formacion or '',
        'condicion_sena': perfil.condicion_sena or 'aprendiz',
        'metodo': 'automatica',
    }

    # Serie de actividad para la gráfica de evolución del dev (últimos 6 meses)
    import json
    from avances.models import Avance
    hoy_grafica = timezone.now().date()
    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    serie_puntos = []
    total_hitos_6m = 0
    total_posts_6m = 0

    for i in range(5, -1, -1):
        m = (hoy_grafica.month - i - 1) % 12 + 1
        y = hoy_grafica.year - ((hoy_grafica.month - i - 1) // 12 * -1 if (hoy_grafica.month - i - 1) < 0 else 0)
        c_avances = Avance.objects.filter(
            desarrollador=request.user,
            fecha_hora__year=y,
            fecha_hora__month=m
        ).count()
        c_posts = mis_postulaciones.filter(
            fecha__year=y,
            fecha__month=m
        ).count()

        v_mes = Valoracion.objects.filter(
            desarrollador=request.user,
            rol_evaluador='empresa',
            fecha__year=y,
            fecha__month=m
        ).aggregate(Avg('puntuacion'))['puntuacion__avg']
        calif_num = round(float(v_mes), 1) if v_mes else 0.0

        serie_puntos.append({
            'etiqueta': meses_nombres[m - 1],
            'hitos': c_avances,
            'postulaciones': c_posts,
            'calificacion': calif_num,
            'fecha': f"{meses_nombres[m - 1]} {y}",
        })
        total_hitos_6m += c_avances
        total_posts_6m += c_posts

    # Presupuesto total acordado en contratos vigentes del desarrollador
    from django.db.models import Sum
    presupuesto_total_dev = mis_contratos_digitales_qs.aggregate(Sum('monto'))['monto__sum'] or 0
    presupuesto_total_dev_formateado = f"{int(presupuesto_total_dev):,}".replace(",", ".")

    proxima_entrega = None
    proximo_proyecto = None
    if mis_proyectos_v:
        con_fecha = [p for p in mis_proyectos_v if p.get('fecha_fin')]
        if con_fecha:
            con_fecha.sort(key=lambda x: str(x['fecha_fin']))
            proximo_proyecto = con_fecha[0]
            proxima_entrega = proximo_proyecto['fecha_fin']
        else:
            proximo_proyecto = mis_proyectos_v[0]

    context = {
        'serie_actividad_json': json.dumps(serie_puntos),
        'total_hitos_6m': total_hitos_6m,
        'total_posts_6m': total_posts_6m,
        'presupuesto_total_dev': presupuesto_total_dev,
        'presupuesto_total_dev_formateado': presupuesto_total_dev_formateado,
        'proximo_proyecto': proximo_proyecto,
        'proxima_entrega': proxima_entrega,
        'proyectos_explorar': proyectos_explorar,
        'proyectos_explorar_page': proyectos_explorar_page,
        'proyectos_explorar_total': paginator_explorar.count,
        'categorias_solucion': categorias_solucion,
        'favoritos_ids': favoritos_ids,
        'proyectos_activos_count': p_act,
        'proyectos_completados': p_comp,
        'calificacion_promedio': round(float(promedio), 1) if promedio else 0,
        'favoritos_count': p_fav,
        'nuevos_proyectos': Proyecto.objects.filter(estado='publicado').count(),
        'notificaciones': notificaciones_recientes,
        'notificaciones_pendientes_count': notificaciones_pendientes_count,
        'mensajes_no_leidos': Mensaje.objects.filter(receptor=request.user, leido=False).count(),
        'mis_proyectos_activos_v': mis_proyectos_v,
        'conversaciones_chat': conversaciones_chat,
        'mis_proyectos_finalizados': mis_proyectos_finalizados,
        'contrataciones_pendientes_calificar': contrataciones_pendientes_calificar,
        'pendientes_calificar_empresa_count': len(contrataciones_pendientes_calificar),
        'mis_postulaciones': mis_postulaciones,
        'postulaciones_vigentes': postulaciones_vigentes,
        'postulaciones_en_evaluacion': postulaciones_en_evaluacion,
        'postulaciones_historial': postulaciones_historial,
        'postulaciones_vigentes_count': postulaciones_vigentes.count(),
        'postulaciones_historial_count': postulaciones_historial.count(),
        'postulaciones_revision_count': postulaciones_en_evaluacion.count(),
        'contratos_vigentes': contratos_vigentes,
        'contratos_historial': contratos_historial,
        'mis_contratos_digitales': mis_contratos_digitales,
        'contratos_digitales_page': contratos_digitales_page,
        'total_contratos_digitales': total_contratos_digitales,
        'contratos_pendientes_firma_count': contratos_pendientes_firma_count,
        'contratos_formalizados_count': contratos_formalizados_count,
        'contratos_vigentes_count': total_contratos_digitales,
        'solicitudes_cancelacion_dev': solicitudes_cancelacion_dev,
        'contratos_cancelables_dev': contratos_cancelables_dev,
        'cancelaciones_pendientes_dev_count': len(cancelaciones_pendientes_dev),
        'hitos_pendientes_count': sum(p.get('hitos_pendientes', 0) for p in mis_proyectos_v),
        'postulaciones_negociacion_count': postulaciones_vigentes.filter(estado='en_negociacion').count(),
        'favoritos': mis_favoritos,
        'perfil': perfil,
        'perfil_form': perfil_form,
        'seccion_activa': seccion_activa,
        'valores': valores_verificacion,
        'errores': {},
        'abrir_verificacion': request.GET.get('verificacion') == '1',
        'admin_id': admin_id
    }
    context.update(datos_dashboard_disputas(request.user, estado=request.GET.get('estado')))
    context['disputas_activas_count'] = len(context['disputas_activas'])
    return render(request, 'Desarrollador/Desarrollador.html', context)


@login_required
@requiere_usuario_activo
def detalle_desarrollador(request, desarrollador_id):
    """
    Vista de perfil público y reputación del desarrollador (RF 5.3.1 / SCRUM-222).
    Permite consultar:
    - Identidad profesional: nombre, foto, insignia SENA, programa de formación, ficha.
    - Habilidades técnicas destacadas y enlace al portafolio.
    - Métricas de trayectoria: reputación promedio, reseñas recibidas y proyectos finalizados.
    - Testimonios y valoraciones dejados por las empresas contratantes.
    """
    desarrollador = get_object_or_404(Usuario, id=desarrollador_id, rol='desarrollador')
    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=desarrollador)

    # Reseñas que las empresas dejaron a este desarrollador
    resenas = list(
        Valoracion.objects.filter(desarrollador=desarrollador, rol_evaluador='empresa')
        .select_related('empresa', 'empresa__perfil_empresa', 'proyecto')
        .order_by('-fecha')
    )

    total_resenas = len(resenas)
    promedio = (
        Valoracion.objects.filter(desarrollador=desarrollador, rol_evaluador='empresa')
        .aggregate(Avg('puntuacion'))['puntuacion__avg']
        or 0.0
    )

    # Desglose de estrellas (1 a 5) para la barra de distribución
    conteo_estrellas = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in resenas:
        if r.puntuacion in conteo_estrellas:
            conteo_estrellas[r.puntuacion] += 1

    proyectos_finalizados_count = Contratacion.objects.filter(
        desarrollador=desarrollador, estado='finalizada'
    ).count()
    proyectos_activos_count = Contratacion.objects.filter(
        desarrollador=desarrollador, estado='activa'
    ).count()

    habilidades_lista = [
        h.strip() for h in (perfil.habilidades or '').split(',') if h.strip()
    ]

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
        foto_url = None
        if perfil.foto_perfil:
            try:
                foto_url = perfil.foto_perfil.url
            except Exception:
                foto_url = None

        resenas_data = [
            {
                'empresa': (
                    (r.empresa.perfil_empresa.nombre_empresa if hasattr(r.empresa, 'perfil_empresa') and r.empresa.perfil_empresa.nombre_empresa else None)
                    or r.empresa.nombre
                    or r.empresa.username
                ),
                'puntuacion': r.puntuacion,
                'comentario': r.comentario,
                'fecha': r.fecha.strftime('%d/%m/%Y'),
                'proyecto_titulo': r.proyecto.titulo,
            }
            for r in resenas[:5]
        ]

        return JsonResponse({
            'ok': True,
            'desarrollador': {
                'id': desarrollador.id,
                'nombre': desarrollador.nombre or desarrollador.username,
                'username': desarrollador.username,
                'programa_formacion': perfil.programa_formacion or 'No especificado',
                'ficha': perfil.ficha or 'Sin registrar',
                'condicion_sena': perfil.get_condicion_sena_display() if hasattr(perfil, 'get_condicion_sena_display') else 'Aprendiz',
                'portafolio_url': perfil.portafolio_url or '',
                'habilidades': habilidades_lista,
                'es_verificado_sena': perfil.es_verificado_sena,
                'badge_label': perfil.badge_info['label'] if perfil.badge_info else 'Sin verificar',
                'reputacion': round(float(promedio), 1),
                'total_resenas': total_resenas,
                'proyectos_activos': proyectos_activos_count,
                'proyectos_finalizados': proyectos_finalizados_count,
                'foto_url': foto_url,
                'resenas': resenas_data,
            }
        })

    context = {
        'desarrollador': desarrollador,
        'perfil': perfil,
        'resenas': resenas,
        'total_resenas': total_resenas,
        'promedio_reputacion': round(float(promedio), 1),
        'conteo_estrellas': conteo_estrellas,
        'proyectos_finalizados_count': proyectos_finalizados_count,
        'habilidades_lista': habilidades_lista,
    }
    return render(request, 'desarrollador/detalle_publico.html', context)
