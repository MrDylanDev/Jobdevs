import json
import os
import re
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import (
    Avg,
    Count,
    F,
    FloatField,
    Max,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce, TruncMonth
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_POST

from contrataciones.models import Contratacion, SolicitudCancelacion
from disputas.models import Disputa
from logs.models import LogAuditoria
from mensajes.models import Mensaje
from notificaciones.models import Notificacion
from notificaciones.services import depurar_notificaciones
from postulaciones import services as postulaciones_services
from postulaciones.models import Postulacion
from proyectos.models import (
    CategoriaSolucion,
    Proyecto,
    RegularizacionCierreProyecto,
    Valoracion,
)
from proyectos.services import regularizar_cierre_historico

from ..decorators import requiere_usuario_activo
from ..models import (
    ExcepcionFichaSena,
    FichaSena,
    PerfilDesarrollador,
    PerfilEmpresa,
    Usuario,
)
from ..services_sena import normalizar_numero_ficha
from ..utils import get_admin_ids, invalidar_sesiones_activas_usuario
from ._helpers import cached_or_compute, get_notificaciones_context


def _es_htmx_request(request):
    return (
        request.headers.get('HX-Request') == 'true'
        and request.GET.get('format') != 'json'
        and 'application/json' not in request.headers.get('Accept', '')
    )


def _htmx_admin_section_response(request, template_name, context, toast_tipo, toast_mensaje):
    response = render(request, template_name, context)
    response['HX-Trigger'] = json.dumps({
        'jobdevs:toast': {
            'tipo': toast_tipo,
            'mensaje': toast_mensaje,
        }
    })
    return response


def _contexto_sec_verificaciones(active_section=None):
    disputas_activas = list(
        Disputa.objects.filter(estado__in=('abierta', 'en_mediacion'))
        .select_related('proyecto__empresa', 'iniciado_por', 'mediador')
        .order_by('-fecha_creacion')
    )

    # SCRUM-232 (RF 10.1.2): conteos por estado para el panel de mediación.
    disputas_por_estado = {clave: 0 for clave, _ in Disputa.ESTADO}
    for fila in Disputa.objects.values('estado').annotate(total=Count('id')):
        disputas_por_estado[fila['estado']] = fila['total']

    solicitudes_cancelacion_admin = list(
        SolicitudCancelacion.objects.select_related(
            'contratacion__proyecto', 'contratacion__desarrollador',
            'contratacion__proyecto__empresa', 'solicitante',
        ).order_by('-fecha_creacion')[:50]
    )
    solicitudes_cancelacion_pendientes_count = sum(
        1 for s in solicitudes_cancelacion_admin if s.estado == 'pendiente_revision'
    )
    solicitudes_cancelacion_resueltas_count = sum(
        1 for s in solicitudes_cancelacion_admin if s.estado in ('aprobada', 'rechazada')
    )

    total_empresas_en_revision = PerfilEmpresa.objects.filter(
        estado_verificacion='en_revision'
    ).count()
    empresas_en_revision = list(
        PerfilEmpresa.objects.filter(estado_verificacion='en_revision')
        .select_related('usuario')
        .order_by('fecha_solicitud_verificacion')[:50]
    )

    total_desarrolladores_en_revision = PerfilDesarrollador.objects.filter(
        estado_verificacion='en_revision'
    ).count()
    desarrolladores_en_revision = list(
        PerfilDesarrollador.objects.filter(estado_verificacion='en_revision')
        .select_related('usuario')
        .order_by('fecha_solicitud_verificacion')[:50]
    )

    total_fichas_sena = FichaSena.objects.count()
    fichas_sena = list(FichaSena.objects.all().order_by('-fecha_creacion')[:100])

    # SCRUM-225 (RF 9.1.2): excepciones individuales justificadas a la lista blanca.
    total_excepciones_fichas_sena = ExcepcionFichaSena.objects.count()
    excepciones_fichas_sena = list(
        ExcepcionFichaSena.objects.select_related(
            'desarrollador__usuario', 'autorizado_por'
        ).order_by('-fecha_creacion')[:100]
    )
    desarrolladores_para_excepcion = list(
        PerfilDesarrollador.objects.order_by('usuario__nombre').values_list(
            'id', 'usuario__nombre', 'usuario__username'
        )
    )

    # SCRUM-311: mecanismo oficial de verificación SENA. No existe API pública de
    # SOFIA Plus, así que el padrón institucional SENA (lista blanca local) es el
    # mecanismo primario y SENA_API_URL queda como pasarela institucional opcional.
    sena_api_url = getattr(settings, 'SENA_API_URL', os.environ.get('SENA_API_URL', ''))
    sena_modo_verificacion = 'pasarela_externa' if sena_api_url else 'padron_oficial'

    return {
        'disputas_activas': disputas_activas,
        'total_disputas_activas': len(disputas_activas),
        'disputas_por_estado': disputas_por_estado,
        'solicitudes_cancelacion_admin': solicitudes_cancelacion_admin,
        'solicitudes_cancelacion_pendientes_count': solicitudes_cancelacion_pendientes_count,
        'solicitudes_cancelacion_resueltas_count': solicitudes_cancelacion_resueltas_count,
        'empresas_en_revision': empresas_en_revision,
        'total_empresas_en_revision': total_empresas_en_revision,
        'desarrolladores_en_revision': desarrolladores_en_revision,
        'total_desarrolladores_en_revision': total_desarrolladores_en_revision,
        'fichas_sena': fichas_sena,
        'total_fichas_sena': total_fichas_sena,
        'excepciones_fichas_sena': excepciones_fichas_sena,
        'total_excepciones_fichas_sena': total_excepciones_fichas_sena,
        'desarrolladores_para_excepcion': desarrolladores_para_excepcion,
        'sena_modo_verificacion': sena_modo_verificacion,
        'sena_api_url': sena_api_url,
        'active_section': active_section,
    }


def _contexto_sec_proyectos(request=None, proy_stats=None, p_ret=None, active_section=None):
    if proy_stats is None:
        proy_stats = Proyecto.objects.aggregate(
            p_pub=Count('id', filter=Q(estado='publicado')),
            p_des=Count('id', filter=Q(estado='en_desarrollo')),
            p_fin=Count('id', filter=Q(estado='finalizado')),
        )
    if p_ret is None:
        p_ret = Proyecto.objects.filter(
            estado__in=('en_desarrollo', 'en_revision'),
            fecha_cumplimiento__lt=timezone.localdate(),
        ).count()

    p_pub = proy_stats['p_pub']
    p_des = proy_stats['p_des']
    p_fin = proy_stats['p_fin']
    total_proyectos = p_pub + p_des + p_fin

    proy_q = request.GET.get('proy_q', '').strip() if request is not None else ''
    proy_estado = request.GET.get('proy_estado', '').strip() if request is not None else ''
    proy_page = request.GET.get('proy_page', 1) if request is not None else 1

    proyectos_qs = Proyecto.objects.all()
    if proy_q:
        proyectos_qs = proyectos_qs.filter(
            Q(titulo__icontains=proy_q) |
            Q(empresa__nombre__icontains=proy_q) |
            Q(empresa__username__icontains=proy_q)
        )
    if proy_estado:
        proyectos_qs = proyectos_qs.filter(estado=proy_estado)

    proy_paginator = Paginator(
        proyectos_qs.select_related('empresa').prefetch_related(
            Prefetch(
                'contrataciones',
                queryset=Contratacion.objects.filter(estado='activa').select_related('desarrollador').annotate(
                    hitos_completados=Count('proyecto__entregables', filter=Q(proyecto__entregables__estado='completado')),
                    total_hitos=Count('proyecto__entregables')
                ),
                to_attr='contratos_activos'
            )
        ).order_by('-fecha_publicacion'),
        25
    )
    proyectos_lista = proy_paginator.get_page(proy_page)

    proyectos_pendientes_regularizacion = list(
        Proyecto.objects.filter(estado='finalizado')
        .exclude(historial_estados__estado_nuevo='finalizado')
        .exclude(pk__in=RegularizacionCierreProyecto.objects.values('proyecto_id'))
        .select_related('empresa').order_by('-fecha_publicacion')[:25]
    )

    proyectos_cumplimiento_vencido = Proyecto.objects.filter(
        estado__in=('en_desarrollo', 'en_revision'),
        fecha_cumplimiento__lt=timezone.localdate(),
    ).select_related('empresa').order_by('fecha_cumplimiento')[:50]

    # SCRUM-315 (HU-A07): el umbral de inactividad es configurable (15 días por defecto).
    dias_alerta = getattr(settings, 'PROYECTO_DIAS_ALERTA_RETRASO', 15)
    fecha_alerta = timezone.now() - timedelta(days=dias_alerta)
    proyectos_alerta = Proyecto.objects.filter(
        estado='en_desarrollo'
    ).annotate(
        ultimo_avance=Max('entregables__fecha_creacion'),
    ).filter(
        Q(ultimo_avance__lt=fecha_alerta) | Q(ultimo_avance__isnull=True)
    ).select_related('empresa').prefetch_related(
        Prefetch('contrataciones',
            queryset=Contratacion.objects.filter(estado='activa').select_related('desarrollador'),
            to_attr='contratos_activos')
    ).distinct()

    alertas_retraso = []
    for p in proyectos_alerta:
        dev_nombre = p.contratos_activos[0].desarrollador.nombre if p.contratos_activos else ''
        dias = 0
        if p.ultimo_avance:
            dias = (timezone.now() - p.ultimo_avance).days
        elif p.contratos_activos:
            dias = (timezone.now().date() - p.contratos_activos[0].fecha_inicio).days
        alertas_retraso.append((p.titulo, p.empresa.nombre, dev_nombre, dias, p.empresa_id))

    categorias_solucion = CategoriaSolucion.objects.annotate(
        proyectos_count=Count('proyectos')
    ).order_by('nombre')

    return {
        'total_proyectos': total_proyectos,
        'p_pub': p_pub,
        'p_des': p_des,
        'p_fin': p_fin,
        'p_ret': p_ret,
        'proyectos_todos': proyectos_lista,
        'proy_q': proy_q,
        'proy_estado': proy_estado,
        'proyectos_pendientes_regularizacion': proyectos_pendientes_regularizacion,
        'proyectos_cumplimiento_vencido': proyectos_cumplimiento_vencido,
        'alertas_retraso': alertas_retraso,
        'dias_alerta_retraso': dias_alerta,
        'categorias_solucion': categorias_solucion,
        'active_section': active_section,
    }


def _contexto_sec_chat_config(incluir_catalogo_y_chat=False, admin_ids=None, active_section=None):
    ctx = {
        'plazo_negociacion_dias': postulaciones_services.obtener_plazo_negociacion_dias(),
        'active_section': active_section,
    }
    if not incluir_catalogo_y_chat:
        ctx['proyectos_catalogo'] = []
        ctx['conversaciones'] = []
        return ctx

    # Catálogo completo para la sección integrada Explorar en Admin
    proyectos_catalogo = list(Proyecto.objects.select_related(
        'empresa', 'empresa__perfil_empresa', 'categoria'
    ).annotate(
        num_postulaciones=Count('postulaciones', distinct=True),
        empresa_reputacion=Coalesce(Avg('empresa__valoraciones_como_empresa__puntuacion',
            filter=Q(empresa__valoraciones_como_empresa__rol_evaluador='desarrollador')),
            Value(0.0), output_field=FloatField())
    ).order_by('-fecha_publicacion')[:60])

    if admin_ids is None:
        admin_ids = get_admin_ids()
    mensajes_no_leidos_admin = Mensaje.objects.filter(receptor_id__in=admin_ids, leido=False).count()

    mensajes_soporte = Mensaje.objects.filter(
        Q(remitente_id__in=admin_ids) | Q(receptor_id__in=admin_ids)
    ).values_list('remitente_id', 'receptor_id')
    u_ids = set()
    for r, s in mensajes_soporte:
        if r not in admin_ids:
            u_ids.add(r)
        if s not in admin_ids:
            u_ids.add(s)

    ultimo_mensaje_sq = Mensaje.objects.filter(
        Q(remitente=OuterRef('pk'), receptor_id__in=admin_ids) |
         Q(remitente_id__in=admin_ids, receptor=OuterRef('pk'))
    ).order_by('-fecha_envio').values('id')[:1]

    contactos = Usuario.objects.filter(id__in=u_ids).select_related(
        'perfil_empresa', 'perfil_desarrollador'
    ).annotate(
        ultimo_mensaje_id=Subquery(ultimo_mensaje_sq)
    )

    conversaciones = []
    mensajes_ids = [c.ultimo_mensaje_id for c in contactos if c.ultimo_mensaje_id]
    ultimos_mensajes = {
        m.id: m for m in Mensaje.objects.filter(id__in=mensajes_ids).select_related('remitente')
    }

    for contacto in contactos:
        ultimo_m = ultimos_mensajes.get(contacto.ultimo_mensaje_id)
        if ultimo_m:
            tiene_pendientes = (ultimo_m.remitente_id == contacto.id and not ultimo_m.leido)
            foto_url = ''
            if contacto.rol == 'empresa':
                perfil = getattr(contacto, 'perfil_empresa', None)
                if perfil and perfil.logo:
                    foto_url = perfil.logo.url
            elif contacto.rol == 'desarrollador':
                perfil = getattr(contacto, 'perfil_desarrollador', None)
                if perfil and perfil.foto_perfil:
                    foto_url = perfil.foto_perfil.url
            conversaciones.append({
                'usuario': contacto,
                'ultimo_mensaje': ultimo_m,
                'pendiente': tiene_pendientes,
                'foto_url': foto_url,
            })
    conversaciones.sort(key=lambda x: x['ultimo_mensaje'].fecha_envio, reverse=True)

    ctx.update({
        'proyectos_catalogo': proyectos_catalogo,
        'conversaciones': conversaciones,
        'mensajes_no_leidos_admin': mensajes_no_leidos_admin,
    })
    return ctx


@login_required
@requiere_usuario_activo
def dashboard_admin(request):
    if request.user.rol != 'administrador': return redirect('inicio')
    
    # RNF-10: agregados globales cacheados (TTL 60s) — son consultas de solo
    # lectura sobre tablas completas, las más costosas con +10.000 registros.
    def _global_stats():
        user_stats = Usuario.objects.aggregate(
            total_empresas=Count('id', filter=Q(rol='empresa', is_active=True)),
            total_devs=Count('id', filter=Q(rol='desarrollador', is_active=True)),
        )
        # SCRUM-226 (RF 1.3.1): métricas de cuentas inactivas y suspendidas.
        user_stats['inactivos'] = Usuario.objects.filter(estado='inactivo').count()
        user_stats['suspendidos'] = Usuario.objects.filter(estado='suspendido').count()
        proy_stats = Proyecto.objects.aggregate(
            p_pub=Count('id', filter=Q(estado='publicado')),
            p_des=Count('id', filter=Q(estado='en_desarrollo')),
            p_fin=Count('id', filter=Q(estado='finalizado')),
        )
        post_pen = Postulacion.objects.filter(estado='pendiente').count()
        promedio_global = Valoracion.objects.aggregate(avg=Avg('puntuacion'))['avg'] or 0
        p_ret = Proyecto.objects.filter(
            estado__in=('en_desarrollo', 'en_revision'),
            fecha_cumplimiento__lt=timezone.localdate(),
        ).count()
        return user_stats, proy_stats, post_pen, promedio_global, p_ret

    user_stats, proy_stats, post_pen, promedio_global, p_ret = cached_or_compute(
        'admin:global_stats', 60, _global_stats
    )

    total_empresas = user_stats['total_empresas']
    total_devs = user_stats['total_devs']
    usuarios_inactivos = user_stats['inactivos']
    usuarios_suspendidos = user_stats['suspendidos']
    total_usuarios = total_empresas + total_devs
    
    user_q = request.GET.get('user_q', '').strip()
    user_rol = request.GET.get('user_rol', '').strip()
    user_estado = request.GET.get('user_estado', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

    usuarios_qs = Usuario.objects.all()
    if user_q:
        usuarios_qs = usuarios_qs.filter(
            Q(username__icontains=user_q) |
            Q(nombre__icontains=user_q) |
            Q(email__icontains=user_q) |
            Q(identificacion__icontains=user_q)
        )
    if user_rol:
        usuarios_qs = usuarios_qs.filter(rol=user_rol)
    if user_estado:
        usuarios_qs = usuarios_qs.filter(estado=user_estado)

    # SCRUM-226 (RF 1.3.3): filtro por rango de fecha de registro.
    fecha_desde_parsed = parse_date(fecha_desde) if fecha_desde else None
    fecha_hasta_parsed = parse_date(fecha_hasta) if fecha_hasta else None
    if fecha_desde_parsed:
        usuarios_qs = usuarios_qs.filter(date_joined__date__gte=fecha_desde_parsed)
    if fecha_hasta_parsed:
        usuarios_qs = usuarios_qs.filter(date_joined__date__lte=fecha_hasta_parsed)

    user_paginator = Paginator(usuarios_qs.order_by('-date_joined'), 25)
    user_page = request.GET.get('user_page', 1)
    usuarios_lista = user_paginator.get_page(user_page)

    logs = list(LogAuditoria.objects.select_related('usuario').order_by('-fecha_hora').values_list(
        'id', 'usuario__username', 'accion', 'tabla_afectada', 'fecha_hora'
    )[:20])

    admin_ids = get_admin_ids()

    desarrolladores_qs = Usuario.objects.filter(rol='desarrollador').annotate(
        promedio=Coalesce(Avg('valoraciones_como_dev__puntuacion',
            filter=Q(valoraciones_como_dev__rol_evaluador='empresa')),
            Value(0.0), output_field=FloatField()),
        proyectos_comp=Count('contrataciones_dev',
            filter=Q(contrataciones_dev__estado='finalizada')),
    )
    ranking_top = list(desarrolladores_qs.filter(promedio__gte=4.0)
        .order_by('-promedio', '-proyectos_comp')[:5]
        .values_list('nombre', 'proyectos_comp', 'promedio', 'id'))
    ranking_bajo = list(desarrolladores_qs.filter(promedio__gt=0, promedio__lt=4.0)
        .order_by('promedio', 'proyectos_comp')[:5]
        .values_list('nombre', 'proyectos_comp', 'promedio', 'id'))

    salud_global = (promedio_global, p_ret)

    empresas_qs = Usuario.objects.filter(rol='empresa').annotate(
        promedio=Coalesce(Avg('valoraciones_como_empresa__puntuacion',
            filter=Q(valoraciones_como_empresa__rol_evaluador='desarrollador')),
            Value(0.0), output_field=FloatField()),
        total_eval=Count('valoraciones_como_empresa',
            filter=Q(valoraciones_como_empresa__rol_evaluador='desarrollador')),
        nombre_empresa=Coalesce(F('perfil_empresa__nombre_empresa'), Value('')),
    )
    ranking_empresas_top = list(empresas_qs.filter(promedio__gte=4.0)
        .order_by('-promedio', '-total_eval')[:5]
        .values_list('nombre', 'nombre_empresa', 'promedio', 'total_eval', 'id'))
    ranking_empresas_bajo = list(empresas_qs.filter(promedio__gt=0, promedio__lt=4.0)
        .order_by('promedio', 'total_eval')[:5]
        .values_list('nombre', 'nombre_empresa', 'promedio', 'total_eval', 'id'))

    resenas_auditoria = []
    for v in Valoracion.objects.select_related('empresa', 'desarrollador').order_by('-fecha')[:10]:
        if v.rol_evaluador == 'empresa':
            de = v.empresa.nombre
            para = v.desarrollador.nombre
        else:
            de = v.desarrollador.nombre
            para = v.empresa.nombre
        resenas_auditoria.append((de, para, v.puntuacion, v.comentario, v.rol_evaluador))

    notificaciones_admin, notificaciones_pendientes_count = get_notificaciones_context(request.user.id)

    def _tendencia_6_meses():
        hoy = timezone.localdate()
        meses_es = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        meses = []
        y, m = hoy.year, hoy.month
        for _ in range(6):
            meses.append((y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        meses.reverse()
        inicio_y, inicio_m = meses[0]
        fecha_inicio = timezone.make_aware(
            timezone.datetime(inicio_y, inicio_m, 1, 0, 0, 0)
        )
        u_rows = (
            Usuario.objects.filter(date_joined__gte=fecha_inicio)
            .annotate(mes=TruncMonth('date_joined'))
            .values('mes')
            .annotate(total=Count('id'))
        )
        p_rows = (
            Proyecto.objects.filter(fecha_publicacion__gte=fecha_inicio)
            .annotate(mes=TruncMonth('fecha_publicacion'))
            .values('mes')
            .annotate(total=Count('id'))
        )
        u_map = {(r['mes'].year, r['mes'].month): r['total'] for r in u_rows if r['mes']}
        p_map = {(r['mes'].year, r['mes'].month): r['total'] for r in p_rows if r['mes']}
        return [
            {
                'label': meses_es[mm - 1],
                'usuarios': u_map.get((yy, mm), 0),
                'proyectos': p_map.get((yy, mm), 0),
            }
            for yy, mm in meses
        ]

    context = {
        'tendencia_mensual_json': json.dumps(_tendencia_6_meses()),
        'total_usuarios': total_usuarios,
        'total_devs': total_devs,
        'total_empresas': total_empresas,
        'post_pen': post_pen,
        'promedio_global': promedio_global,
        'usuarios_todos': usuarios_lista,
        'user_q': user_q,
        'user_rol': user_rol,
        'user_estado': user_estado,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'usuarios_inactivos': usuarios_inactivos,
        'usuarios_suspendidos': usuarios_suspendidos,
        'logs_auditoria': logs,
        'ranking_talento': ranking_top,
        'ranking_bajo': ranking_bajo,
        'ranking_empresas': ranking_empresas_top,
        'ranking_empresas_bajo': ranking_empresas_bajo,
        'resenas_auditoria': resenas_auditoria,
        'salud_global': salud_global,
        'notificaciones': notificaciones_admin,
        'notificaciones_pendientes_count': notificaciones_pendientes_count,
        'admin_id': request.user.id,
        'admin_ids': list(admin_ids),
    }
    context.update(_contexto_sec_verificaciones())
    context.update(_contexto_sec_proyectos(request, proy_stats=proy_stats, p_ret=p_ret))
    context.update(_contexto_sec_chat_config(incluir_catalogo_y_chat=True, admin_ids=admin_ids))
    return render(request, 'administrador/Administrador.html', context)


@login_required
@requiere_usuario_activo
@require_POST
def admin_actualizar_configuracion_negociacion(request):
    if request.user.rol != 'administrador':
        raise PermissionDenied
    try:
        plazo_dias = int(request.POST.get('plazo_dias', ''))
        postulaciones_services.actualizar_plazo_negociacion_dias(
            plazo_dias, request.user
        )
        toast_tipo = 'success'
        toast_msg = 'Plazo global de negociación actualizado.'
    except (TypeError, ValueError, ValidationError) as exc:
        mensaje = ' '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
        toast_tipo = 'error'
        toast_msg = mensaje or 'El plazo debe estar entre 1 y 30 días.'

    if _es_htmx_request(request):
        return _htmx_admin_section_response(
            request,
            'administrador/partials/_sec_chat_config.html',
            _contexto_sec_chat_config(active_section='configSection'),
            toast_tipo,
            toast_msg,
        )

    if toast_tipo == 'success':
        messages.success(request, toast_msg)
    else:
        messages.error(request, toast_msg)
    return redirect(reverse('dashboard_admin') + '?section=configSection')


@login_required
@requiere_usuario_activo
@require_POST
def admin_regularizar_cierre_proyecto(request, proyecto_id):
    if request.user.rol != 'administrador':
        raise PermissionDenied

    destino = redirect(reverse('dashboard_admin') + '?section=projectsSection')
    fecha_cierre = parse_datetime(request.POST.get('fecha_cierre', ''))
    if fecha_cierre is not None and timezone.is_naive(fecha_cierre):
        fecha_cierre = timezone.make_aware(fecha_cierre, timezone.get_current_timezone())

    try:
        regularizar_cierre_historico(
            proyecto_id=proyecto_id,
            fecha_cierre=fecha_cierre,
            motivo=request.POST.get('motivo', ''),
            referencia_evidencia=request.POST.get('referencia_evidencia', ''),
            registrado_por=request.user,
        )
    except Proyecto.DoesNotExist:
        raise Http404 from None
    except ValidationError as exc:
        toast_tipo = 'error'
        toast_msg = ' '.join(exc.messages)
    else:
        toast_tipo = 'success'
        toast_msg = 'Fecha de cierre histórico registrada con auditoría.'

    if _es_htmx_request(request):
        return _htmx_admin_section_response(
            request,
            'administrador/partials/_sec_proyectos.html',
            _contexto_sec_proyectos(active_section='projectsSection'),
            toast_tipo,
            toast_msg,
        )

    if toast_tipo == 'success':
        messages.success(request, toast_msg)
    else:
        messages.error(request, toast_msg)
    return destino


@login_required
@require_POST
def admin_toggle_usuario(request, usuario_id):
    if request.user.rol != 'administrador': return redirect('inicio')
    user = get_object_or_404(Usuario, id=usuario_id)

    if user.id == request.user.id:
        messages.error(request, 'No puedes suspender tu propia cuenta.')
        return redirect(f"{reverse('dashboard_admin')}?section=usersSection")

    if user.rol == 'administrador':
        messages.error(request, 'No puedes modificar la cuenta de otro administrador desde el panel.')
        return redirect(f"{reverse('dashboard_admin')}?section=usersSection")

    if user.estado == 'activo':
        user.estado = 'inactivo'
        user.is_active = False
        user.bloqueado_por_intentos = False
        invalidar_sesiones_activas_usuario(user.id)
    else:
        user.estado = 'activo'
        user.is_active = True
        user.intentos_fallidos = 0
        user.bloqueado_por_intentos = False
        
    user.save()
    LogAuditoria.objects.create(
        usuario=request.user,
        accion=f"Cambió estado del usuario {user.username} a {user.estado}",
        tabla_afectada='usuarios',
        registro_id=user.id,
    )
    messages.info(request, f"Estado del usuario {user.username} actualizado a {user.estado}.")
    return redirect(reverse('dashboard_admin') + '?section=usersSection')


@login_required
@require_POST
def admin_reactivar_proyecto(request, proyecto_id):
    if request.user.rol != 'administrador':
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')
    
    with transaction.atomic():
        proyecto = Proyecto.objects.select_for_update().get(id=proyecto_id)
        
        if proyecto.estado != 'finalizado':
            messages.warning(request, "Solo se puede crear una continuación desde un proyecto finalizado.")
            return redirect('ver_avances', proyecto_id=proyecto.id)

        if proyecto.proyectos_sucesores.exists():
            messages.info(request, "Este proyecto ya tiene una continuación publicada.")
            return redirect('ver_avances', proyecto_id=proyecto.id)

        sucesor = Proyecto.objects.create(
            empresa=proyecto.empresa,
            titulo=f'Continuación de {proyecto.titulo}'[:200],
            descripcion=proyecto.descripcion,
            tipo_solucion=proyecto.tipo_solucion,
            categoria=proyecto.categoria,
            prioridad=proyecto.prioridad,
            modalidad=proyecto.modalidad,
            ciudad=proyecto.ciudad,
            vacantes=proyecto.vacantes,
            estado='publicado',
            proyecto_origen=proyecto,
        )
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f"Creó el proyecto sucesor '{sucesor.titulo}' sin reactivar '{proyecto.titulo}'",
            tabla_afectada='proyectos',
            registro_id=sucesor.pk,
            valor_anterior=f'proyecto_origen={proyecto.pk}; estado=finalizado',
            valor_nuevo='estado=publicado; contratos=0',
        )
        Notificacion.objects.create(
            usuario=proyecto.empresa,
            proyecto=sucesor,
            tipo='avance',
            mensaje=(
                f"Se creó '{sucesor.titulo}' como continuación independiente. "
                'Revisa fechas y condiciones antes de recibir postulaciones.'
            ),
        )

    messages.success(
        request,
        f"Se creó '{sucesor.titulo}'. El proyecto finalizado y sus contratos no se modificaron.",
    )
    return redirect('ver_avances', proyecto_id=sucesor.id)


@login_required
@require_POST
def admin_crear_ficha_sena(request):
    """Crea una nueva ficha en la lista blanca oficial del SENA (solo administrador)."""
    if request.user.rol != 'administrador':
        raise PermissionDenied

    destino = redirect(reverse('dashboard_admin') + '?section=fichasSenaSection')
    es_htmx = _es_htmx_request(request)
    numero_ficha = re.sub(r'[\s\-]+', '', request.POST.get('numero_ficha', '').strip())
    programa = request.POST.get('programa_formacion', '').strip()
    regional = request.POST.get('regional', '').strip() or None
    centro = request.POST.get('centro_formacion', '').strip() or None

    if not numero_ficha or not programa:
        msg = 'El número de ficha y el programa de formación son obligatorios.'
        if es_htmx:
            return _htmx_admin_section_response(
                request,
                'administrador/partials/_sec_verificaciones.html',
                _contexto_sec_verificaciones(active_section='fichasSenaSection'),
                'error',
                msg,
            )
        messages.error(request, msg)
        return destino

    if FichaSena.objects.filter(numero_ficha=numero_ficha).exists():
        msg = f'La ficha {numero_ficha} ya existe en la lista blanca oficial.'
        if es_htmx:
            return _htmx_admin_section_response(
                request,
                'administrador/partials/_sec_verificaciones.html',
                _contexto_sec_verificaciones(active_section='fichasSenaSection'),
                'error',
                msg,
            )
        messages.error(request, msg)
        return destino

    with transaction.atomic():
        ficha = FichaSena.objects.create(
            numero_ficha=numero_ficha,
            programa_formacion=programa,
            regional=regional,
            centro_formacion=centro,
            activa=True,
            creada_por=request.user,
        )
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f'Creó ficha SENA {numero_ficha} ({programa})'[:300],
            tabla_afectada='fichas_sena',
            registro_id=ficha.id,
        )
    msg = f'Ficha {numero_ficha} registrada exitosamente en la lista blanca.'
    if es_htmx:
        return _htmx_admin_section_response(
            request,
            'administrador/partials/_sec_verificaciones.html',
            _contexto_sec_verificaciones(active_section='fichasSenaSection'),
            'success',
            msg,
        )
    messages.success(request, msg)
    return destino


@login_required
@require_POST
def admin_toggle_ficha_sena(request, ficha_id):
    """Activa o desactiva una ficha SENA en la lista blanca (solo administrador)."""
    if request.user.rol != 'administrador':
        raise PermissionDenied

    destino = redirect(reverse('dashboard_admin') + '?section=fichasSenaSection')
    with transaction.atomic():
        ficha = get_object_or_404(FichaSena.objects.select_for_update(), id=ficha_id)
        ficha.activa = not ficha.activa
        ficha.save()

        accion_str = 'Activó' if ficha.activa else 'Desactivó'
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f'{accion_str} ficha SENA {ficha.numero_ficha}'[:300],
            tabla_afectada='fichas_sena',
            registro_id=ficha.id,
        )
    estado_str = 'activada' if ficha.activa else 'desactivada'
    msg = f'Ficha {ficha.numero_ficha} {estado_str} correctamente.'
    if _es_htmx_request(request):
        return _htmx_admin_section_response(
            request,
            'administrador/partials/_sec_verificaciones.html',
            _contexto_sec_verificaciones(active_section='fichasSenaSection'),
            'success',
            msg,
        )
    messages.success(request, msg)
    return destino


@login_required
@require_POST
def admin_crear_excepcion_ficha_sena(request):
    """SCRUM-225 (RF 9.1.2): autoriza una excepción individual a la lista blanca SENA."""
    if request.user.rol != 'administrador':
        raise PermissionDenied

    destino = redirect(reverse('dashboard_admin') + '?section=fichasSenaSection')
    es_htmx = _es_htmx_request(request)
    desarrollador_id = request.POST.get('desarrollador_id')
    numero_ficha = normalizar_numero_ficha(request.POST.get('numero_ficha', ''))
    justificacion = request.POST.get('justificacion', '').strip()
    dias_vigencia_raw = request.POST.get('dias_vigencia', '').strip()

    def _error_resp(msg):
        if es_htmx:
            return _htmx_admin_section_response(
                request,
                'administrador/partials/_sec_verificaciones.html',
                _contexto_sec_verificaciones(active_section='fichasSenaSection'),
                'error',
                msg,
            )
        messages.error(request, msg)
        return destino

    if not desarrollador_id or not numero_ficha or not justificacion:
        return _error_resp(
            'El desarrollador, el número de ficha y la justificación son obligatorios.'
        )

    try:
        perfil = PerfilDesarrollador.objects.select_related('usuario').get(id=desarrollador_id)
    except (PerfilDesarrollador.DoesNotExist, ValueError, TypeError):
        return _error_resp('El desarrollador indicado no existe.')

    fecha_expiracion = None
    if dias_vigencia_raw:
        try:
            dias = int(dias_vigencia_raw)
        except (TypeError, ValueError):
            return _error_resp('Los días de vigencia deben ser un número entero.')
        if dias <= 0:
            return _error_resp('Los días de vigencia deben ser mayores que cero.')
        fecha_expiracion = timezone.now() + timedelta(days=dias)

    with transaction.atomic():
        excepcion = ExcepcionFichaSena.objects.create(
            desarrollador=perfil,
            numero_ficha=numero_ficha,
            justificacion=justificacion,
            autorizado_por=request.user,
            fecha_expiracion=fecha_expiracion,
            activa=True,
        )
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=(
                f'Creó excepción SENA para {perfil.usuario.username} '
                f'(Ficha {numero_ficha})'
            )[:300],
            tabla_afectada='excepciones_ficha_sena',
            registro_id=excepcion.id,
        )
    msg = f'Excepción autorizada para la ficha {numero_ficha}.'
    if es_htmx:
        return _htmx_admin_section_response(
            request,
            'administrador/partials/_sec_verificaciones.html',
            _contexto_sec_verificaciones(active_section='fichasSenaSection'),
            'success',
            msg,
        )
    messages.success(request, msg)
    return destino


@login_required
@require_POST
def admin_revocar_excepcion_ficha_sena(request, excepcion_id):
    """SCRUM-225 (RF 9.1.2): revoca una excepción individual a la lista blanca SENA."""
    if request.user.rol != 'administrador':
        raise PermissionDenied

    destino = redirect(reverse('dashboard_admin') + '?section=fichasSenaSection')
    with transaction.atomic():
        excepcion = get_object_or_404(
            ExcepcionFichaSena.objects.select_for_update().select_related('desarrollador__usuario'),
            id=excepcion_id,
        )
        excepcion.activa = False
        excepcion.save(update_fields=['activa'])

        LogAuditoria.objects.create(
            usuario=request.user,
            accion=(
                f'Revocó excepción SENA de {excepcion.desarrollador.usuario.username} '
                f'(Ficha {excepcion.numero_ficha})'
            )[:300],
            tabla_afectada='excepciones_ficha_sena',
            registro_id=excepcion.id,
        )
    msg = f'Excepción de la ficha {excepcion.numero_ficha} revocada correctamente.'
    if _es_htmx_request(request):
        return _htmx_admin_section_response(
            request,
            'administrador/partials/_sec_verificaciones.html',
            _contexto_sec_verificaciones(active_section='fichasSenaSection'),
            'success',
            msg,
        )
    messages.success(request, msg)
    return destino


@login_required
@require_POST
def admin_depurar_notificaciones(request):
    """SCRUM-316 (HU-A16): depura notificaciones antiguas desde el panel admin."""
    if request.user.rol != 'administrador':
        raise PermissionDenied

    destino = reverse('dashboard_admin') + '?section=reportsSection'

    try:
        dias = int(request.POST.get('dias', 90))
    except (TypeError, ValueError):
        dias = 90
    dias = max(0, dias)

    incluir_no_leidas = request.POST.get('incluir_no_leidas') in ('on', 'true', '1')

    borradas = depurar_notificaciones(
        dias=dias, incluir_no_leidas=incluir_no_leidas
    )

    LogAuditoria.objects.create(
        usuario=request.user,
        accion=f"Depuración de notificaciones: {borradas} eliminadas (> {dias} días)"[:300],
        tabla_afectada='notificaciones',
    )
    msg = f"Se depuraron {borradas} notificaciones antiguas exitosamente."
    if _es_htmx_request(request):
        return _htmx_admin_section_response(
            request,
            'administrador/partials/_sec_chat_config.html',
            _contexto_sec_chat_config(active_section='configSection'),
            'success',
            msg,
        )
    messages.success(request, msg)
    return redirect(destino)

