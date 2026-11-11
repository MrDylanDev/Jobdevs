import json
import time
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.conf import settings
from .models import Notificacion
from django.contrib import messages


def _obtener_estado_notificaciones(user_id, ultimo_id=0):
    """Consulta el conteo de no leídas y las notificaciones nuevas."""
    qs = Notificacion.objects.filter(usuario_id=user_id, leida=False)
    count = qs.count()
    nuevas = list(
        qs.filter(id__gt=ultimo_id)
        .order_by('id')
        .values('id', 'tipo', 'mensaje', 'fecha')[:10]
    )
    for n in nuevas:
        if n.get('fecha'):
            n['fecha'] = n['fecha'].strftime('%d/%m/%Y %H:%M')
    return count, nuevas


def notificaciones_event_generator(user, interval=2.0, max_iterations=None):
    """
    Generador síncrono para Server-Sent Events (SSE).
    Emite 'init' inicial con unread_count, 'notificacion' ante nuevas notificaciones,
    'sync' si el conteo disminuye (leídas en otra pestaña), y heartbeats ': ping'.

    Debe ser síncrono: StreamingHttpResponse solo sirve iteradores asíncronos de
    forma no bufferizada bajo ASGI. Bajo WSGI (runserver, LiveServerTestCase de los
    tests E2E y gunicorn síncrono) Django no puede iterar un async generator, lo
    bufferiza por completo y, al ser un stream infinito, deja el hilo colgado.
    """
    user_id = user.id
    count, _ = _obtener_estado_notificaciones(user_id, ultimo_id=0)

    ultimo_id = (
        Notificacion.objects.filter(usuario_id=user_id)
        .order_by('-id')
        .values_list('id', flat=True)
        .first()
        or 0
    )
    ultimo_count = count

    # Evento inicial con conteo no leído
    yield f"event: init\ndata: {json.dumps({'tipo': 'init', 'unread_count': count})}\n\n"

    iterations = 0
    heartbeat_cycles = 0

    while True:
        if max_iterations is not None and iterations >= max_iterations:
            break
        iterations += 1

        time.sleep(interval)

        count, nuevas = _obtener_estado_notificaciones(user_id, ultimo_id)
        if nuevas:
            for notif in nuevas:
                ultimo_id = max(ultimo_id, notif['id'])
                payload = json.dumps({
                    'id': notif['id'],
                    'tipo': notif['tipo'],
                    'mensaje': notif['mensaje'],
                    'fecha': notif['fecha'],
                    'unread_count': count,
                })
                yield f"event: notificacion\ndata: {payload}\n\n"
            ultimo_count = count
        elif count != ultimo_count:
            ultimo_count = count
            payload = json.dumps({'tipo': 'sync', 'unread_count': count})
            yield f"event: sync\ndata: {payload}\n\n"
        else:
            heartbeat_cycles += 1
            if heartbeat_cycles >= 5:
                heartbeat_cycles = 0
                yield ": ping\n\n"


def notificaciones_stream(request):
    """
    Endpoint SSE (Server-Sent Events) sirviendo text/event-stream.
    Requiere usuario autenticado. Deshabilita buffering para proxies inversos (Nginx).
    """
    if not request.user.is_authenticated:
        return HttpResponse("No autenticado", status=401, content_type="text/plain")

    # Seguridad: En producción fijar valores seguros para prevenir saturación (DoS).
    # Solo en entorno de pruebas (settings.TESTING) se permiten overrides vía query params.
    if getattr(settings, 'TESTING', False):
        try:
            interval = float(request.GET.get('interval', 2.0))
            interval = max(0.05, min(interval, 60.0))
        except (ValueError, TypeError):
            interval = 2.0

        max_iter_val = request.GET.get('max_iterations')
        max_iter = int(max_iter_val) if max_iter_val and max_iter_val.isdigit() else None
    else:
        interval = 2.0
        max_iter = None

    response = StreamingHttpResponse(
        notificaciones_event_generator(request.user, interval=interval, max_iterations=max_iter),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'
    return response

@login_required
def lista_notificaciones(request):
    """Lista todas las notificaciones del usuario actual con select_related y paginación."""
    notificaciones_qs = Notificacion.objects.filter(
        usuario=request.user
    ).select_related('proyecto').order_by('-fecha')
    
    paginator = Paginator(notificaciones_qs, 20)
    page_number = request.GET.get('page')
    notificaciones = paginator.get_page(page_number)
    
    return render(request, 'notificaciones/lista.html', {
        'notificaciones': notificaciones,
    })

@login_required
@require_POST
def marcar_leida(request, notificacion_id):
    """Marca una notificación específica como leída (soporta AJAX y redirección tradicional)."""
    notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
    notificacion.leida = True
    notificacion.save()

    is_ajax = (
        request.headers.get('Accept') == 'application/json'
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    if is_ajax:
        unread_count = Notificacion.objects.filter(usuario=request.user, leida=False).count()
        return JsonResponse({
            'status': 'ok',
            'notificacion_id': notificacion_id,
            'unread_count': unread_count,
            'mensaje': 'Notificación marcada como leída.',
        })

    return redirect('notificaciones_lista')

@login_required
@require_POST
def marcar_todas_leidas(request):
    """Marca todas las notificaciones pendientes del usuario como leídas (SCRUM-173 / SCRUM-193)."""
    actualizadas = Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
    mensaje = "Todas las notificaciones han sido marcadas como leídas."

    is_ajax = (
        request.headers.get('Accept') == 'application/json'
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    if is_ajax:
        return JsonResponse({
            'status': 'ok',
            'unread_count': 0,
            'actualizadas': actualizadas,
            'mensaje': mensaje,
        })

    messages.success(request, mensaje)
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect('notificaciones_lista')


@login_required
def api_lista_notificaciones(request):
    """Lista las notificaciones del usuario en JSON para verlas sin salir del dashboard."""
    try:
        limite = int(request.GET.get('limite', 100))
    except (TypeError, ValueError):
        limite = 100
    limite = max(1, min(limite, 500))

    notificaciones = list(
        Notificacion.objects.filter(usuario=request.user)
        .order_by('-fecha')[:limite]
    )
    unread_count = Notificacion.objects.filter(usuario=request.user, leida=False).count()

    return JsonResponse({
        'notificaciones': [
            {
                'id': notificacion.id,
                'tipo': notificacion.tipo,
                'tipo_display': notificacion.get_tipo_display(),
                'mensaje': notificacion.mensaje,
                'fecha': notificacion.fecha.strftime('%d/%m/%Y %H:%M'),
                'leida': notificacion.leida,
            }
            for notificacion in notificaciones
        ],
        'unread_count': unread_count,
    })


@login_required
@require_POST
def limpiar_notificaciones(request):
    """Elimina las notificaciones del usuario para que no se acumulen en el panel."""
    eliminadas, _ = Notificacion.objects.filter(usuario=request.user).delete()
    mensaje = "Todas las notificaciones han sido eliminadas."

    is_ajax = (
        request.headers.get('Accept') == 'application/json'
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    if is_ajax:
        return JsonResponse({
            'status': 'ok',
            'unread_count': 0,
            'eliminadas': eliminadas,
            'mensaje': mensaje,
        })

    messages.success(request, mensaje)
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect('notificaciones_lista')
