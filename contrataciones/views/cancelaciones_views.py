import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .. import services
from ..models import Contratacion, SolicitudCancelacion
from ._helpers import _es_htmx


def _destino_cancelaciones(usuario):
    """Empresa vive en la pestaña de su panel; dev y admin, en la página propia."""
    if getattr(usuario, 'rol', None) == 'empresa':
        return f"{reverse('dashboard_empresa')}?section=cancelaciones"
    return reverse('solicitudes_cancelacion')


@login_required
def listar_contrataciones_empresa(request):
    """Listado de todos los desarrolladores contratados por la empresa"""
    if request.user.rol != 'empresa':
        return redirect('inicio')

    contrataciones = Contratacion.objects.filter(empresa=request.user).select_related('proyecto', 'desarrollador').order_by('-fecha_inicio')
    return render(request, 'contrataciones/lista_empresa.html', {'contrataciones': contrataciones})


@login_required
def ver_detalle_contrato(request, contratacion_id):
    """Ver detalles técnicos de un contrato específico"""
    contrato = get_object_or_404(Contratacion, id=contratacion_id)

    # Seguridad
    if request.user != contrato.empresa and request.user != contrato.desarrollador and request.user.rol != 'administrador':
        return redirect('inicio')

    return render(request, 'contrataciones/detalle.html', {'contrato': contrato})


def _contexto_solicitudes_cancelacion(usuario):
    """Construye el contexto compartido para la página de solicitudes de dev/admin."""
    rol = usuario.rol
    solicitudes = SolicitudCancelacion.objects.select_related(
        'contratacion__proyecto', 'contratacion__empresa',
        'contratacion__desarrollador', 'solicitante', 'resuelto_por',
    )
    contratos = Contratacion.objects.none()
    if rol == 'desarrollador':
        solicitudes = solicitudes.filter(contratacion__desarrollador=usuario)
        contratos = Contratacion.objects.filter(
            desarrollador=usuario, estado='activa',
        ).exclude(
            proyecto__estado='en_disputa',
        ).exclude(
            solicitudes_cancelacion__estado__in=['pendiente_acuerdo', 'pendiente_revision'],
        ).select_related('proyecto', 'empresa', 'desarrollador')
    else:
        solicitudes = solicitudes.exclude(causal='acuerdo_mutuo').exclude(estado='pendiente_acuerdo')

    return {
        'solicitudes': solicitudes.order_by('-fecha_creacion'),
        'contratos': contratos,
        'causales': SolicitudCancelacion.CAUSALES,
        'rol': rol,
    }


def _render_cancelaciones_htmx(request, *, toast=None):
    """Devuelve el partial/panel actualizado de cancelaciones + HX-Trigger toast."""
    if request.user.rol == 'empresa':
        response = render(
            request,
            'empresa/partials/_tab_cancelaciones.html',
            services.datos_dashboard_cancelaciones(request.user),
        )
    else:
        response = render(
            request,
            'contrataciones/solicitudes_cancelacion.html',
            _contexto_solicitudes_cancelacion(request.user),
        )
    if toast:
        tipo, mensaje = toast
        response['HX-Trigger'] = json.dumps({
            'jobdevs:toast': {'tipo': tipo, 'mensaje': mensaje},
        })
    return response


@login_required
@require_POST
def cancelar_contratacion(request, contratacion_id):
    """Ruta histórica: inicia una solicitud; nunca cancela inmediatamente."""
    if request.user.rol not in ('empresa', 'desarrollador'):
        raise PermissionDenied

    titular = 'empresa' if request.user.rol == 'empresa' else 'desarrollador'
    contrato = get_object_or_404(Contratacion, id=contratacion_id, **{titular: request.user})
    motivo = request.POST.get('motivo_cancelacion') or request.POST.get('motivo') or ''
    causal = request.POST.get('causal', '')
    evidencia = request.POST.get('evidencia', '')
    if causal in ('incumplimiento', 'inactividad'):
        messages.info(request, 'Para un conflicto grave completa el formulario formal de disputa; esta solicitud no se guardó.')
        return redirect(
            f"{reverse('disputas:abrir_disputa', args=[contrato.proyecto_id])}"
            f"?contratacion_id={contrato.pk}"
        )

    try:
        services.solicitar_cancelacion(
            contratacion_id, request.user, causal=causal, motivo=motivo, evidencia=evidencia,
        )
        toast_tipo = 'success'
        msg = 'Solicitud registrada. El contrato sigue activo hasta su aprobación.'
    except PermissionDenied as exc:
        toast_tipo = 'error'
        msg = str(exc)
    except ValidationError as exc:
        toast_tipo = 'error'
        msg = ' '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)

    if _es_htmx(request):
        return _render_cancelaciones_htmx(request, toast=(toast_tipo, msg))

    getattr(messages, toast_tipo)(request, msg)
    return redirect(_destino_cancelaciones(request.user))


@login_required
def solicitudes_cancelacion(request):
    """Consulta privada de solicitudes y contratos que aún admiten una solicitud."""
    rol = request.user.rol
    if rol not in ('empresa', 'desarrollador', 'administrador'):
        raise PermissionDenied
    if rol == 'empresa':
        # La empresa gestiona el flujo dentro de su panel; la URL histórica
        # sobrevive como atajo para no romper enlaces ni marcadores.
        return redirect(_destino_cancelaciones(request.user))
    return render(
        request,
        'contrataciones/solicitudes_cancelacion.html',
        _contexto_solicitudes_cancelacion(request.user),
    )


@login_required
@require_POST
def resolver_solicitud_cancelacion(request, solicitud_id):
    decision = request.POST.get('decision')
    if decision not in ('aprobar', 'rechazar'):
        msg = 'Selecciona una decisión válida.'
        if _es_htmx(request):
            return _render_cancelaciones_htmx(request, toast=('error', msg))
        messages.error(request, msg)
        return redirect(_destino_cancelaciones(request.user))
    try:
        services.resolver_solicitud_cancelacion(
            solicitud_id, request.user, aprobar=(decision == 'aprobar'),
            dictamen=request.POST.get('dictamen', ''),
        )
        toast_tipo = 'success'
        msg = 'Decisión registrada y notificada a ambas partes.'
    except ValidationError as exc:
        toast_tipo = 'error'
        msg = ' '.join(exc.messages)

    if _es_htmx(request):
        return _render_cancelaciones_htmx(request, toast=(toast_tipo, msg))

    getattr(messages, toast_tipo)(request, msg)
    return redirect(_destino_cancelaciones(request.user))
