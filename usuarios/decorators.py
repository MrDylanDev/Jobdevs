from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.core.cache import cache
from django.http import JsonResponse
from functools import wraps

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
    Limita la tasa de peticiones a un endpoint de API usando la cache de Django.
    Retorna 429 Too Many Requests si se excede el límite dentro de la ventana de tiempo.
    La clave se basa en la IP del cliente y, si está autenticado, en su ID de usuario.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1'))
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()

            user_part = f"user_{request.user.id}" if getattr(request, 'user', None) and request.user.is_authenticated else "anon"
            cache_key = f"rl:{view_func.__name__}:{user_part}:{ip}"

            current_requests = cache.get(cache_key, 0)
            if current_requests >= max_requests:
                response = JsonResponse({
                    'error': 'Demasiadas solicitudes. Límite de tasa excedido.',
                    'retry_after': window_seconds,
                }, status=429)
                response['Retry-After'] = str(window_seconds)
                return response

            if current_requests == 0:
                cache.set(cache_key, 1, timeout=window_seconds)
            else:
                try:
                    cache.incr(cache_key)
                except ValueError:
                    cache.set(cache_key, current_requests + 1, timeout=window_seconds)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
