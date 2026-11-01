from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q, Count, Prefetch
from django.utils import timezone
from ..models import Usuario, PerfilEmpresa
from ..decorators import requiere_usuario_activo
from ..utils import get_admin_id
from proyectos.models import Proyecto, Valoracion, CategoriaSolucion
from postulaciones.models import Postulacion
from contrataciones.models import Contratacion, ContratoDigital
from disputas.services import datos_dashboard_disputas
from mensajes.models import Mensaje
from ._helpers import get_notificaciones_context


# SCRUM-228 (RF 2.2.1): estados que representan proyectos fuera del ciclo activo.
ESTADOS_HISTORIAL = ('finalizado', 'rechazado', 'inactivo', 'en_disputa')


@login_required
@requiere_usuario_activo
def dashboard_empresa(request):
    if request.user.rol != 'empresa': return redirect('inicio')
    
    p_pub = Proyecto.objects.filter(empresa=request.user, estado='publicado').count()
    p_act = Proyecto.objects.filter(empresa=request.user, estado='en_desarrollo').count()
    dev_con = Contratacion.objects.filter(empresa=request.user, estado='activa').count()

    en_desarrollo_qs = Proyecto.objects.filter(
        empresa=request.user, estado__in=['en_desarrollo', 'en_revision']
    ).select_related('categoria').annotate(
        hitos_completados=Count('entregables', filter=Q(entregables__estado='completado')),
        hitos_totales=Count('entregables'),
    ).prefetch_related(
        Prefetch('contrataciones',
            queryset=Contratacion.objects.filter(estado='activa').select_related('desarrollador'),
            to_attr='contratos_activos')
    )
    # RNF-10: precarga los conteos de postulaciones 'en_negociacion' en una
    # sola query en lugar de una consulta por proyecto (evita N+1).
    en_desarrollo_list = list(en_desarrollo_qs)
    negociacion_counts = dict(
        Postulacion.objects.filter(
            proyecto_id__in=[p.id for p in en_desarrollo_list],
            estado='en_negociacion',
        ).values('proyecto_id').annotate(c=Count('id')).values_list('proyecto_id', 'c')
    )
    en_desarrollo_v = []
    for p in en_desarrollo_list:
        dev_ids = [c.desarrollador_id for c in p.contratos_activos]
        dev_nombres = ', '.join([c.desarrollador.nombre for c in p.contratos_activos])
        cupos_comprometidos = len(dev_ids) + negociacion_counts.get(p.id, 0)
        vacantes_disponibles = max(0, p.vacantes - cupos_comprometidos) if p.estado == 'en_desarrollo' else 0
        en_desarrollo_v.append({
            'proyecto_id': p.id,
            'titulo': p.titulo,
            'desarrolladores': dev_nombres,
            'hitos_completados': p.hitos_completados,
            'hitos_totales': p.hitos_totales,
            'ultimo_avance': None,
            'fecha_fin': p.fecha_limite,
            'estado': p.estado,
            'ids': ','.join(map(str, dev_ids)),
            'primer_dev_id': dev_ids[0] if dev_ids else None,
            'num_desarrolladores': len(dev_ids),
            'vacantes_totales': p.vacantes,
            'vacantes_disponibles': vacantes_disponibles,
        })
    perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=request.user)
    mis_ofertas = list(
        Proyecto.objects.filter(empresa=request.user, estado='publicado')
        .select_related('categoria')
        .annotate(
            num_candidatos=Count(
                'postulaciones',
                filter=Q(postulaciones__estado__in=['pendiente', 'en_negociacion']),
                distinct=True
            )
        )
        .order_by('-fecha_publicacion')
    )
    total_vacantes_ofertas = sum(p.vacantes for p in mis_ofertas)

    # RF 2.2.1: marca las convocatorias que cierran en las próximas 48 horas.
    hoy = timezone.now().date()
    limite_48h = hoy + timedelta(days=2)
    for proyecto in mis_ofertas:
        proyecto.cierra_pronto = bool(
            proyecto.fecha_limite and hoy <= proyecto.fecha_limite <= limite_48h
        )

    # Onboarding: 4 pasos iniciales para que la empresa active su cuenta.
    pasos_onboarding = [
        {
            'clave': 'perfil',
            'titulo': 'Completa el perfil de tu empresa',
            'descripcion': 'Añade el logo y una descripción que genere confianza en el talento.',
            'completado': bool(perfil.logo and (perfil.descripcion or '').strip()),
            'en_revision': False,
        },
        {
            'clave': 'verificacion',
            'titulo': 'Verifica tu NIT',
            'descripcion': 'Obtén el sello de empresa verificada y publica con mayor respaldo.',
            'completado': perfil.estado_verificacion == 'verificada',
            'en_revision': perfil.estado_verificacion == 'en_revision',
        },
        {
            'clave': 'publicar',
            'titulo': 'Publica tu primera convocatoria',
            'descripcion': 'Describe tu proyecto y encuentra el talento que necesitas.',
            'completado': p_pub > 0,
            'en_revision': False,
        },
        {
            'clave': 'contratar',
            'titulo': 'Contrata tu primer talento',
            'descripcion': 'Inicia un contrato activo con un desarrollador de la plataforma.',
            'completado': dev_con > 0,
            'en_revision': False,
        },
    ]
    onboarding_completados = sum(1 for paso in pasos_onboarding if paso['completado'])
    total_pasos_onboarding = len(pasos_onboarding)
    onboarding_porcentaje = round((onboarding_completados / total_pasos_onboarding) * 100)
    
    postulaciones_pendientes_obj = Postulacion.objects.filter(
        proyecto__empresa=request.user, 
        estado='pendiente',
        proyecto__estado__in=['publicado', 'en_desarrollo']
    )
    post_pen = postulaciones_pendientes_obj.count()
    admin_id = get_admin_id()

    valoraciones_dev = list(
        Valoracion.objects.filter(empresa=request.user, rol_evaluador='desarrollador')
        .select_related('desarrollador', 'desarrollador__perfil_desarrollador', 'proyecto')
        .order_by('-fecha')
    )
    total_valoraciones = len(valoraciones_dev)
    promedio_empresa = (
        sum(v.puntuacion for v in valoraciones_dev) / total_valoraciones
        if total_valoraciones > 0 else 0.0
    )

    conteo_estrellas = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for val in valoraciones_dev:
        if val.puntuacion in conteo_estrellas:
            conteo_estrellas[val.puntuacion] += 1
    porcentaje_estrellas = {
        k: round((conteo_estrellas[k] / total_valoraciones) * 100) if total_valoraciones > 0 else 0
        for k in conteo_estrellas
    }

    notificaciones_recientes, notificaciones_pendientes_count = get_notificaciones_context(request.user.id)

    colaboradores_activos = Contratacion.objects.filter(
        empresa=request.user, 
        estado='activa',
        proyecto__estado='en_desarrollo'
    ).select_related('desarrollador__perfil_desarrollador', 'proyecto')

    # Módulo 8 / SCRUM-204: contratos digitales gestionados 100% in-situ desde el panel.
    mis_contratos_digitales = ContratoDigital.objects.filter(
        postulacion__proyecto__empresa=request.user
    ).select_related(
        'postulacion__proyecto',
        'postulacion__desarrollador',
        'postulacion__desarrollador__perfil_desarrollador',
        'contratacion',
    ).order_by('-fecha_actualizacion')
    contratos_pendientes_firma_count = sum(
        1 for c in mis_contratos_digitales
        if not c.firmado_empresa and c.estado in ('borrador', 'pendiente_firma')
    )

    historial_v = Proyecto.objects.filter(
        empresa=request.user, 
        estado='finalizado'
    ).select_related('categoria').annotate(num_desarrolladores=Count('contrataciones')).prefetch_related('contrataciones__desarrollador').order_by('-fecha_publicacion')

    # SCRUM-228 (RF 2.2.1): historial completo (finalizado, rechazado, inactivo,
    # en_disputa) con filtro opcional por estado vía GET 'historial_estado'.
    historial_estado_actual = request.GET.get('historial_estado', '')
    historial_inactivos_qs = Proyecto.objects.filter(
        empresa=request.user, estado__in=ESTADOS_HISTORIAL
    )
    if historial_estado_actual in ESTADOS_HISTORIAL:
        historial_inactivos_qs = historial_inactivos_qs.filter(estado=historial_estado_actual)
    else:
        historial_estado_actual = ''

    historial_inactivos = historial_inactivos_qs.select_related('categoria').annotate(
        num_desarrolladores=Count('contrataciones', distinct=True),
        hitos_completados=Count('entregables', filter=Q(entregables__estado='completado'), distinct=True),
        hitos_totales=Count('entregables', distinct=True),
    ).prefetch_related('contrataciones__desarrollador', 'contrataciones__desarrollador__perfil_desarrollador').order_by('-fecha_publicacion')
    historial_inactivos_count = historial_inactivos.count()

    conteos_historial = dict(
        Proyecto.objects.filter(empresa=request.user, estado__in=ESTADOS_HISTORIAL)
        .values('estado')
        .annotate(c=Count('id'))
        .values_list('estado', 'c')
    )
    historial_por_estado = {estado: conteos_historial.get(estado, 0) for estado in ESTADOS_HISTORIAL}

    context = {
        'total_proyectos': p_pub,
        'proyectos_activos': p_act,
        'total_postulaciones': post_pen,
        'total_contratados': dev_con,
        'mis_ofertas': mis_ofertas,
        'total_vacantes_ofertas': total_vacantes_ofertas,
        'pasos_onboarding': pasos_onboarding,
        'onboarding_completados': onboarding_completados,
        'onboarding_porcentaje': onboarding_porcentaje,
        'en_desarrollo_v': en_desarrollo_v,
        'colaboradores_activos': colaboradores_activos,
        'mis_contratos_digitales': mis_contratos_digitales,
        'contratos_pendientes_firma_count': contratos_pendientes_firma_count,
        'historial': historial_v,
        'historial_inactivos': historial_inactivos,
        'historial_inactivos_count': historial_inactivos_count,
        'historial_por_estado': historial_por_estado,
        'historial_estado_actual': historial_estado_actual,
        'valoraciones_recibidas': valoraciones_dev,
        'total_valoraciones': total_valoraciones,
        'conteo_estrellas': conteo_estrellas,
        'porcentaje_estrellas': porcentaje_estrellas,
        'promedio_empresa': round(float(promedio_empresa), 1),
        'postulaciones_pendientes': postulaciones_pendientes_obj,
        'notificaciones': notificaciones_recientes,
        'notificaciones_pendientes_count': notificaciones_pendientes_count,
        'mensajes_no_leidos': Mensaje.objects.filter(receptor=request.user, leido=False).count(),
        'perfil': perfil,
        'admin_id': admin_id,
        'categorias_solucion': CategoriaSolucion.objects.filter(activo=True),
    }
    context.update(datos_dashboard_disputas(request.user, estado=request.GET.get('estado')))
    context['disputas_activas_count'] = len(context['disputas_activas'])
    return render(request, 'empresa/empresa.html', context)


@login_required
@requiere_usuario_activo
def detalle_empresa(request, empresa_id):
    """
    Vista de perfil público institucional y reputación de la empresa (RF 3.1.2 / SCRUM-56).
    Permite a desarrolladores y usuarios consultar:
    - Información corporativa (razón social / nombre, sector, ciudad, descripción, logo).
    - Estado e insignia de verificación oficial (Empresa Verificada / Negocio Verificado / Sin Verificar).
    - Métricas de proyectos (publicados disponibles, en desarrollo, finalizados).
    - Resumen y desglose de reputación por estrellas.
    - Historial de comentarios previos y valoraciones realizadas por desarrolladores.
    - Proyectos abiertos actualmente disponibles para postulación.
    """
    empresa = get_object_or_404(Usuario, id=empresa_id, rol='empresa')
    perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=empresa)

    # Reseñas dejadas por desarrolladores a esta empresa
    resenas = list(
        Valoracion.objects.filter(empresa=empresa, rol_evaluador='desarrollador')
        .select_related('desarrollador', 'desarrollador__perfil_desarrollador', 'proyecto')
        .order_by('-fecha')
    )

    total_resenas = len(resenas)
    promedio = (
        Valoracion.objects.filter(empresa=empresa, rol_evaluador='desarrollador')
        .aggregate(Avg('puntuacion'))['puntuacion__avg']
        or 0.0
    )

    # Desglose de estrellas para barra de distribución
    conteo_estrellas = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in resenas:
        if r.puntuacion in conteo_estrellas:
            conteo_estrellas[r.puntuacion] += 1

    # Proyectos publicados abiertos de esta empresa
    proyectos_abiertos = list(
        Proyecto.objects.filter(empresa=empresa, estado='publicado')
        .select_related('categoria')
        .order_by('-fecha_publicacion')
    )
    proyectos_finalizados_count = Proyecto.objects.filter(empresa=empresa, estado='finalizado').count()
    proyectos_activos_count = Proyecto.objects.filter(empresa=empresa, estado='en_desarrollo').count()

    context = {
        'empresa': empresa,
        'perfil': perfil,
        'resenas': resenas,
        'total_resenas': total_resenas,
        'promedio_reputacion': round(float(promedio), 1),
        'conteo_estrellas': conteo_estrellas,
        'proyectos_abiertos': proyectos_abiertos,
        'total_proyectos_abiertos': len(proyectos_abiertos),
        'proyectos_finalizados_count': proyectos_finalizados_count,
        'proyectos_activos_count': proyectos_activos_count,
    }
    return render(request, 'empresa/detalle_publico.html', context)

