from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.core.cache import cache
from django.http import JsonResponse
from functools import wraps
import time

def requiere_usuario_activo(view_func):
    """
    Decorador para asegurar que el usuario no esté bloqueado.
    Si está suspendido o inactivo, cierra la sesión y redirige al login.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Solo expulsamos si el estado es explícitamente de bloqueo
            if request.user.estado in ['suspendido', 'inactivo']:
                logout(request)
                messages.error(request, "Tu cuenta ha sido suspendida o está inactiva. Contacta al administrador.")
                return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def api_ratelimit(max_requests=60, window_seconds=60):
    """
    Limita la tasa de peticiones a un endpoint de API usando la cache de Django de forma atómica.
    Retorna 429 Too Many Requests si se excede el límite dentro de la ventana de tiempo.
    Usa X-Real-IP (sobreescrito por proxy inverso) para evitar spoofing vía X-Forwarded-For.
    Utiliza buckets temporales fijos en la clave para garantizar una ventana exacta independientemente
    del backend de caché (como DatabaseCache) y calcular Retry-After con precisión.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Priorizar HTTP_X_REAL_IP (sobreescrito por Nginx) sobre REMOTE_ADDR.
            # Evitar HTTP_X_FORWARDED_FOR ya que puede ser manipulado por el cliente.
            ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR') or '127.0.0.1'

            user_part = f"user_{request.user.id}" if getattr(request, 'user', None) and request.user.is_authenticated else "anon"

            now = int(time.time())
            window_bucket = now // window_seconds
            time_remaining = max(1, window_seconds - (now % window_seconds))

            cache_key = f"rl:{view_func.__name__}:{user_part}:{ip}:{window_bucket}"
            key_timeout = time_remaining + 5

            # Operación atómica: add inicial o incremento atómico en el bucket actual
            added = cache.add(cache_key, 1, timeout=key_timeout)
            if added:
                count = 1
            else:
                try:
                    count = cache.incr(cache_key)
                except ValueError:
                    cache.set(cache_key, 1, timeout=key_timeout)
                    count = 1

            if count > max_requests:
                response = JsonResponse({
                    'error': 'Demasiadas solicitudes. Límite de tasa excedido.',
                    'retry_after': time_remaining,
                }, status=429)
                response['Retry-After'] = str(time_remaining)
                return response

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
