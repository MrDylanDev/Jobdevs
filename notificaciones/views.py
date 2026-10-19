import asyncio
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import StreamingHttpResponse, HttpResponse
from asgiref.sync import sync_to_async
from .models import Notificacion
from django.contrib import messages


async def _obtener_estado_notificaciones(user_id, ultimo_id=0):
    """Consulta de forma asíncrona el conteo de no leídas y notificaciones nuevas."""
    def _query():
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

    return await sync_to_async(_query)()


async def notificaciones_event_generator(user, interval=2.0, max_iterations=None):
    """
    Generador asíncrono para Server-Sent Events (SSE).
    Emite 'init' inicial con unread_count, 'notificacion' ante nuevas notificaciones,
    'sync' si el conteo disminuye (leídas en otra pestaña), y heartbeats ': ping'.
    """
    user_id = user.id
    count, _ = await _obtener_estado_notificaciones(user_id, ultimo_id=0)

    def _get_max_id():
        return Notificacion.objects.filter(usuario_id=user_id).order_by('-id').values_list('id', flat=True).first() or 0
    ultimo_id = await sync_to_async(_get_max_id)()
    ultimo_count = count

    # Evento inicial con conteo no leído
    yield f"event: init\ndata: {json.dumps({'tipo': 'init', 'unread_count': count})}\n\n"

    iterations = 0
    heartbeat_cycles = 0

    while True:
        if max_iterations is not None and iterations >= max_iterations:
            break
        iterations += 1

        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break

        count, nuevas = await _obtener_estado_notificaciones(user_id, ultimo_id)
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

    try:
        interval = float(request.GET.get('interval', 2.0))
        interval = max(0.05, min(interval, 60.0))
    except (ValueError, TypeError):
        interval = 2.0

    max_iter_val = request.GET.get('max_iterations')
    max_iter = int(max_iter_val) if max_iter_val and max_iter_val.isdigit() else None

    response = StreamingHttpResponse(
        notificaciones_event_generator(request.user, interval=interval, max_iterations=max_iter),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'
    response['Connection'] = 'keep-alive'
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
    """Marca una notificación específica como leída."""
    notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
    notificacion.leida = True
    notificacion.save()
    return redirect('notificaciones_lista')

@login_required
@require_POST
def marcar_todas_leidas(request):
    """Marca todas las notificaciones pendientes del usuario como leídas (SCRUM-173)."""
    Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
    messages.success(request, "Todas las notificaciones han sido marcadas como leídas.")
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect('notificaciones_lista')
