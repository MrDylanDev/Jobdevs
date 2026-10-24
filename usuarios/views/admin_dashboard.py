import os
import re
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.db.models import Avg, Q, Count, Prefetch, OuterRef, Subquery, Value, FloatField, F, Max
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import timedelta
from django.core.paginator import Paginator
from ..models import Usuario, PerfilEmpresa, PerfilDesarrollador, FichaSena
from ..decorators import requiere_usuario_activo
from ..utils import get_admin_ids, invalidar_sesiones_activas_usuario
from proyectos.models import Proyecto, Valoracion, CategoriaSolucion
from postulaciones.models import Postulacion
from contrataciones.models import Contratacion
from disputas.models import Disputa
from notificaciones.models import Notificacion
from notificaciones.services import depurar_notificaciones
from mensajes.models import Mensaje
from logs.models import LogAuditoria
from ._helpers import get_notificaciones_context, cached_or_compute


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
            estado='en_desarrollo', fecha_limite__lt=timezone.now()
        ).count()
        return user_stats, proy_stats, post_pen, promedio_global, p_ret

    user_stats, proy_stats, post_pen, promedio_global, p_ret = cached_or_compute(
        'admin:global_stats', 60, _global_stats
    )

    total_empresas = user_stats['total_empresas']
    total_devs = user_stats['total_devs']
    usuarios_inactivos = user_stats['inactivos']
    usuarios_suspendidos = user_stats['suspendidos']
    p_pub = proy_stats['p_pub']
    p_des = proy_stats['p_des']
    p_fin = proy_stats['p_fin']
    total_proyectos = p_pub + p_des + p_fin
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

    proy_q = request.GET.get('proy_q', '').strip()
    proy_estado = request.GET.get('proy_estado', '').strip()

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
    proy_page = request.GET.get('proy_page', 1)
    proyectos_lista = proy_paginator.get_page(proy_page)
    
    logs = list(LogAuditoria.objects.select_related('usuario').order_by('-fecha_hora').values_list(
        'id', 'usuario__username', 'accion', 'tabla_afectada', 'fecha_hora'
    )[:20])

    admin_ids = get_admin_ids()
    mensajes_no_leidos_admin = Mensaje.objects.filter(receptor_id__in=admin_ids, leido=False).count()

    mensajes_soporte = Mensaje.objects.filter(Q(remitente_id__in=admin_ids) | Q(receptor_id__in=admin_ids)).values_list('remitente_id', 'receptor_id')
    u_ids = set()
    for r, s in mensajes_soporte:
        if r not in admin_ids: u_ids.add(r)
        if s not in admin_ids: u_ids.add(s)
    
    ultimo_mensaje_sq = Mensaje.objects.filter(
        (Q(remitente=OuterRef('pk'), receptor_id__in=admin_ids) | 
         Q(remitente_id__in=admin_ids, receptor=OuterRef('pk')))
    ).order_by('-fecha_envio').values('id')[:1]

    contactos = Usuario.objects.filter(id__in=u_ids).annotate(
        ultimo_mensaje_id=Subquery(ultimo_mensaje_sq)
    )
    
    conversaciones = []
    mensajes_ids = [c.ultimo_mensaje_id for c in contactos if c.ultimo_mensaje_id]
    ultimos_mensajes = {m.id: m for m in Mensaje.objects.filter(id__in=mensajes_ids).select_related('remitente')}

    for contacto in contactos:
        ultimo_m = ultimos_mensajes.get(contacto.ultimo_mensaje_id)
        if ultimo_m:
            tiene_pendientes = (ultimo_m.remitente_id == contacto.id and not ultimo_m.leido)
            conversaciones.append({
                'usuario': contacto, 
                'ultimo_mensaje': ultimo_m,
                'pendiente': tiene_pendientes
            })
    conversaciones.sort(key=lambda x: x['ultimo_mensaje'].fecha_envio, reverse=True)

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
    ranking_bajo = list(desarrolladores_qs.filter(promedio__lt=4.0)
        .order_by('promedio', 'proyectos_comp')[:5]
        .values_list('nombre', 'proyectos_comp', 'promedio', 'id'))

    salud_global = (promedio_global, p_ret)

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
        alertas_retraso.append((p.titulo, p.empresa.nombre, dev_nombre, dias))

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
    ranking_empresas_bajo = list(empresas_qs.filter(promedio__lt=4.0)
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

    categorias_solucion = CategoriaSolucion.objects.annotate(
        proyectos_count=Count('proyectos')
    ).order_by('nombre')

    disputas_activas = list(
        Disputa.objects.filter(estado__in=('abierta', 'en_mediacion'))
        .select_related('proyecto__empresa', 'iniciado_por', 'mediador')
        .order_by('-fecha_creacion')
    )

    # SCRUM-232 (RF 10.1.2): conteos por estado para el panel de mediación.
    disputas_por_estado = {clave: 0 for clave, _ in Disputa.ESTADO}
    for fila in Disputa.objects.values('estado').annotate(total=Count('id')):
        disputas_por_estado[fila['estado']] = fila['total']

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

    # SCRUM-311: mecanismo oficial de verificación SENA. No existe API pública de
    # SOFIA Plus, así que el padrón institucional SENA (lista blanca local) es el
    # mecanismo primario y SENA_API_URL queda como pasarela institucional opcional.
    sena_api_url = getattr(settings, 'SENA_API_URL', os.environ.get('SENA_API_URL', ''))
    sena_modo_verificacion = 'pasarela_externa' if sena_api_url else 'padron_oficial'

    context = {
        'desarrolladores_en_revision': desarrolladores_en_revision,
        'total_desarrolladores_en_revision': total_desarrolladores_en_revision,
        'fichas_sena': fichas_sena,
        'total_fichas_sena': total_fichas_sena,
        'sena_modo_verificacion': sena_modo_verificacion,
        'sena_api_url': sena_api_url,
        'empresas_en_revision': empresas_en_revision,
        'total_empresas_en_revision': total_empresas_en_revision,
        'disputas_activas': disputas_activas,
        'total_disputas_activas': len(disputas_activas),
        'disputas_por_estado': disputas_por_estado,
        'categorias_solucion': categorias_solucion,
        'total_usuarios': total_usuarios, 'total_proyectos': total_proyectos,
        'total_devs': total_devs, 'total_empresas': total_empresas,
        'p_pub': p_pub, 'p_des': p_des, 'p_fin': p_fin,
        'post_pen': post_pen, 'promedio_global': promedio_global, 'p_ret': p_ret,
        'usuarios_todos': usuarios_lista, 'proyectos_todos': proyectos_lista,
        'user_q': user_q, 'user_rol': user_rol, 'user_estado': user_estado,
        'fecha_desde': fecha_desde, 'fecha_hasta': fecha_hasta, 'usuarios_inactivos': usuarios_inactivos,
        'usuarios_suspendidos': usuarios_suspendidos,
        'proy_q': proy_q, 'proy_estado': proy_estado,
        'logs_auditoria': logs, 'conversaciones': conversaciones, 
        'mensajes_no_leidos_admin': mensajes_no_leidos_admin,
        'ranking_talento': ranking_top,
        'ranking_bajo': ranking_bajo,
        'ranking_empresas': ranking_empresas_top,
        'ranking_empresas_bajo': ranking_empresas_bajo,
        'resenas_auditoria': resenas_auditoria,
        'salud_global': salud_global,
        'alertas_retraso': alertas_retraso,
        'dias_alerta_retraso': dias_alerta,
        'notificaciones': notificaciones_admin,
        'notificaciones_pendientes_count': notificaciones_pendientes_count,
        'admin_id': request.user.id,
        'admin_ids': list(admin_ids)
    }
    return render(request, 'administrador/Administrador.html', context)


@login_required
@require_POST
def admin_toggle_usuario(request, usuario_id):
    if request.user.rol != 'administrador': return redirect('inicio')
    user = get_object_or_404(Usuario, id=usuario_id)
    
    if user.estado == 'activo':
        user.estado = 'inactivo'
        user.is_active = False
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
            messages.warning(request, "Solo se pueden reactivar proyectos finalizados.")
            return redirect('ver_avances', proyecto_id=proyecto.id)

        estado_anterior = proyecto.estado
        proyecto.estado = 'en_desarrollo'
        proyecto.save()
        proyecto.registrar_cambio_estado('en_desarrollo', request.user, estado_anterior=estado_anterior)
        
        Contratacion.objects.filter(proyecto=proyecto, estado='finalizada').update(estado='activa')
        
        notificaciones = [
            Notificacion(
                usuario=proyecto.empresa,
                tipo='avance',
                mensaje=f"SOPORTE: Tu proyecto '{proyecto.titulo}' ha sido reactivado exitosamente."
            )
        ]
        
        devs_ids = Contratacion.objects.filter(proyecto=proyecto, estado='activa').values_list('desarrollador_id', flat=True)
        for dev_id in devs_ids:
            notificaciones.append(Notificacion(
                usuario_id=dev_id,
                tipo='avance',
                mensaje=f"ALERTA: El proyecto '{proyecto.titulo}' ha sido reactivado por la empresa."
            ))
        
        Notificacion.objects.bulk_create(notificaciones)

    messages.success(request, f"Proyecto '{proyecto.titulo}' reactivado y contratos restablecidos.")
    return redirect('ver_avances', proyecto_id=proyecto.id)


@login_required
@require_POST
def admin_crear_ficha_sena(request):
    """Crea una nueva ficha en la lista blanca oficial del SENA (solo administrador)."""
    if request.user.rol != 'administrador':
        raise PermissionDenied

    destino = redirect(reverse('dashboard_admin') + '?section=fichasSenaSection')
    numero_ficha = re.sub(r'[\s\-]+', '', request.POST.get('numero_ficha', '').strip())
    programa = request.POST.get('programa_formacion', '').strip()
    regional = request.POST.get('regional', '').strip() or None
    centro = request.POST.get('centro_formacion', '').strip() or None

    if not numero_ficha or not programa:
        messages.error(request, 'El número de ficha y el programa de formación son obligatorios.')
        return destino

    if FichaSena.objects.filter(numero_ficha=numero_ficha).exists():
        messages.error(request, f'La ficha {numero_ficha} ya existe en la lista blanca oficial.')
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
    messages.success(request, f'Ficha {numero_ficha} registrada exitosamente en la lista blanca.')
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
    messages.success(request, f'Ficha {ficha.numero_ficha} {estado_str} correctamente.')
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
    messages.success(
        request,
        f"Se depuraron {borradas} notificaciones antiguas exitosamente.",
    )
    return redirect(destino)

