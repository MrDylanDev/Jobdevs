from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q, Count, Prefetch
from ..models import PerfilDesarrollador, Usuario
from ..decorators import requiere_usuario_activo
from ..utils import get_admin_id
from proyectos.models import Proyecto, Valoracion, Entregable
from postulaciones.models import Postulacion
from contrataciones.models import Contratacion, ContratoDigital
from disputas.services import datos_dashboard_disputas
from favoritos.models import Favorito
from mensajes.models import Mensaje
from ._helpers import get_notificaciones_context


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
        estado__in=['pendiente', 'en_negociacion', 'aceptada']
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
    ).select_related('proyecto', 'empresa', 'empresa__perfil_empresa').order_by('-fecha_inicio').distinct()
    
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
    ).exclude(proyecto_id__in=proyectos_con_accion).select_related('proyecto', 'proyecto__categoria')

    valoraciones_queryset = Valoracion.objects.filter(desarrollador=request.user, rol_evaluador='empresa')
    mis_proyectos_finalizados = mis_proyectos_finalizados.prefetch_related(
        Prefetch('proyecto__valoraciones', queryset=valoraciones_queryset, to_attr='valoracion_empresa')
    )

    for contrato in mis_proyectos_finalizados:
        contrato.valoracion = contrato.proyecto.valoracion_empresa[0] if contrato.proyecto.valoracion_empresa else None

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
            mis_proyectos_v.append({
                'proyecto_id': p.id,
                'titulo': p.titulo,
                'empresa_nombre': p.empresa.nombre,
                'empresa_verificada': perfil_empresa.es_verificada if perfil_empresa else False,
                'empresa_badge': perfil_empresa.badge_info if perfil_empresa else None,
                'empresa_estado_verificacion': perfil_empresa.estado_verificacion if perfil_empresa else 'sin_verificar',
                'hitos_completados': p.hitos_completados,
                'hitos_totales': p.hitos_totales,
                'hitos_pendientes': hitos_pendientes_dev,
                'ultimo_avance': None,
                'fecha_fin': p.fecha_limite,
                'estado': p.estado,
                'empresa_id': p.empresa_id,
                'num_desarrolladores': len(dev_ids),
                'hitos': hitos_del_proy,
            })

    # Incluir también conversaciones de postulaciones activas o en negociación en el Centro de Mensajes
    conversaciones_chat = list(mis_proyectos_v)
    proyectos_v_ids = {p['proyecto_id'] for p in mis_proyectos_v}

    for post in mis_postulaciones.filter(estado__in=['pendiente', 'en_negociacion', 'aceptada']):
        if post.proyecto_id not in proyectos_v_ids:
            conversaciones_chat.append({
                'proyecto_id': post.proyecto.id,
                'titulo': post.proyecto.titulo,
                'empresa_nombre': post.proyecto.empresa.nombre or post.proyecto.empresa.username,
                'empresa_id': post.proyecto.empresa_id,
                'estado_postulacion': post.estado,
                'es_negociacion': post.estado == 'en_negociacion',
            })
            proyectos_v_ids.add(post.proyecto_id)

    mis_contratos_digitales = ContratoDigital.objects.filter(
        postulacion__desarrollador=request.user
    ).select_related(
        'postulacion__proyecto__empresa__perfil_empresa',
        'postulacion__proyecto',
        'contratacion',
    ).order_by('-fecha_actualizacion')

    contratos_pendientes_firma_count = mis_contratos_digitales.filter(
        firmado_desarrollador=False,
        estado__in=['borrador', 'pendiente_firma'],
        postulacion__estado='en_negociacion',
    ).count()

    admin_id = get_admin_id()
    notificaciones_recientes, notificaciones_pendientes_count = get_notificaciones_context(request.user.id)

    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=request.user)
    context = {
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
        'mis_postulaciones': mis_postulaciones,
        'postulaciones_vigentes': postulaciones_vigentes,
        'postulaciones_historial': postulaciones_historial,
        'postulaciones_vigentes_count': postulaciones_vigentes.count(),
        'postulaciones_historial_count': postulaciones_historial.count(),
        'contratos_vigentes': contratos_vigentes,
        'contratos_historial': contratos_historial,
        'mis_contratos_digitales': mis_contratos_digitales,
        'contratos_pendientes_firma_count': contratos_pendientes_firma_count,
        'favoritos': mis_favoritos,
        'perfil': perfil,
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

    habilidades_lista = [
        h.strip() for h in (perfil.habilidades or '').split(',') if h.strip()
    ]

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
