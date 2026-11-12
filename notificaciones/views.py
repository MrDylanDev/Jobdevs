import asyncio
import json
import time

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.handlers.asgi import ASGIRequest
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Notificacion


def _formatear_fecha(fecha):
    """Formatea una fecha en la zona horaria del proyecto (America/Bogota)."""
    if not fecha:
        return ''
    if timezone.is_aware(fecha):
        fecha = timezone.localtime(fecha)
    return fecha.strftime('%d/%m/%Y %H:%M')


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
        n['fecha'] = _formatear_fecha(n.get('fecha'))
    return count, nuevas


def _estado_inicial_sse(user_id):
    """Estado de partida del stream: no leídas y último id conocido."""
    count, _ = _obtener_estado_notificaciones(user_id, ultimo_id=0)
    ultimo_id = (
        Notificacion.objects.filter(usuario_id=user_id)
        .order_by('-id')
        .values_list('id', flat=True)
        .first()
        or 0
    )
    return count, ultimo_id


def _paso_sse(user_id, ultimo_id, ultimo_count, heartbeat_cycles):
    """
    Ejecuta una iteración de sondeo del stream y devuelve los eventos a emitir.

    Es síncrona y accede al ORM en el hilo del request (WSGI) o mediante
    sync_to_async (ASGI). No duerme: el driver decide cómo esperar.
    """
    count, nuevas = _obtener_estado_notificaciones(user_id, ultimo_id)
    eventos = []

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
            eventos.append(f"event: notificacion\ndata: {payload}\n\n")
        ultimo_count = count
        heartbeat_cycles = 0
    elif count != ultimo_count:
        ultimo_count = count
        payload = json.dumps({'tipo': 'sync', 'unread_count': count})
        eventos.append(f"event: sync\ndata: {payload}\n\n")
    else:
        heartbeat_cycles += 1
        if heartbeat_cycles >= 5:
            heartbeat_cycles = 0
            eventos.append(": ping\n\n")

    return eventos, ultimo_id, ultimo_count, heartbeat_cycles


def notificaciones_event_generator(user, interval=2.0, max_iterations=None):
    """
    Generador síncrono de SSE para WSGI (runserver, LiveServerTestCase y
    gunicorn síncrono). Emite 'init', 'notificacion', 'sync' y heartbeats.
    """
    user_id = user.id
    count, ultimo_id = _estado_inicial_sse(user_id)
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
        eventos, ultimo_id, ultimo_count, heartbeat_cycles = _paso_sse(
            user_id, ultimo_id, ultimo_count, heartbeat_cycles
        )
        for evento in eventos:
            yield evento


async def notificaciones_event_generator_async(user, interval=2.0, max_iterations=None):
    """
    Generador asíncrono de SSE para ASGI (Gunicorn + UvicornWorker en producción).

    Bajo ASGI, Django consume por completo los iteradores síncronos con
    sync_to_async(list); como este stream es infinito, eso bloquearía la respuesta.
    Por eso el driver es async, usa asyncio.sleep y ejecuta las consultas ORM
    mediante sync_to_async (thread_sensitive=True, mismo hilo que el request).
    """
    user_id = user.id
    count, ultimo_id = await sync_to_async(_estado_inicial_sse)(user_id)
    ultimo_count = count

    yield f"event: init\ndata: {json.dumps({'tipo': 'init', 'unread_count': count})}\n\n"

    iterations = 0
    heartbeat_cycles = 0

    while True:
        if max_iterations is not None and iterations >= max_iterations:
            break
        iterations += 1

        await asyncio.sleep(interval)
        eventos, ultimo_id, ultimo_count, heartbeat_cycles = await sync_to_async(_paso_sse)(
            user_id, ultimo_id, ultimo_count, heartbeat_cycles
        )
        for evento in eventos:
            yield evento


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

    # WSGI y ASGI necesitan drivers distintos: bajo ASGI un iterador síncrono
    # infinito se consume entero (sync_to_async(list)) y el stream nunca responde.
    if isinstance(request, ASGIRequest):
        generador = notificaciones_event_generator_async(
            request.user, interval=interval, max_iterations=max_iter
        )
    else:
        generador = notificaciones_event_generator(
            request.user, interval=interval, max_iterations=max_iter
        )

    response = StreamingHttpResponse(generador, content_type='text/event-stream')
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
                'fecha': _formatear_fecha(notificacion.fecha),
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
