from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class UsuarioActivoMiddleware:
    """
    Middleware global de seguridad (SCRUM-170 / RF 1.3.2).
    Intercepta todas las solicitudes autenticadas y verifica que el usuario no esté
    suspendido o inactivo. Si la cuenta está bloqueada o inactiva, fuerza el cierre
    de sesión inmediato, envía un mensaje explicativo y redirige al login.
    Protege todas las URLs de negocio (proyectos, mensajes, avances, disputas, etc.)
    sin depender de decoradores individuales en cada vista.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            estado = getattr(user, 'estado', 'activo')
            is_active = getattr(user, 'is_active', True)
            if estado in ('suspendido', 'inactivo') or not is_active:
                logout(request)
                messages.error(
                    request,
                    "Tu cuenta ha sido suspendida o está inactiva. Contacta al administrador."
                )
                return redirect('login')
        elif request.session.get('_auth_user_id'):
            # Si el backend rechazó la autenticación (user_can_authenticate=False),
            # limpiar inmediatamente la sesión zombi.
            request.session.flush()

        return self.get_response(request)
