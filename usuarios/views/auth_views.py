from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from datetime import timedelta
import secrets

from ..models import Usuario


def login_view(request):
    if request.method == 'POST':
        identificador = (request.POST.get('email') or request.POST.get('username') or '').strip()
        password = request.POST.get('password')
        
        # 1. Autenticación normal primero (previene timing side-channels y enumeración)
        # authenticate() corre hashing para usuarios existentes y un dummy hasher
        # para usuarios inexistentes, igualando el tiempo de respuesta.
        user = authenticate(request=request, username=identificador, password=password)

        if user is not None:
            # Si el usuario proveyó credenciales válidas pero su cuenta está suspendida o inactiva
            if user.estado in ['suspendido', 'inactivo'] or not user.is_active:
                messages.error(
                    request,
                    "Tu cuenta ha sido suspendida o está inactiva. Por favor, comunícate con el administrador para más información."
                )
                return redirect('inicio')

            # Login exitoso: Resetear intentos fallidos si tenía alguno
            if user.intentos_fallidos > 0 or getattr(user, 'bloqueado_por_intentos', False):
                user.intentos_fallidos = 0
                user.bloqueado_por_intentos = False
                user.save(update_fields=['intentos_fallidos', 'bloqueado_por_intentos'])

            login(request, user)

            # Si hay next y es admin, redirigir solo si el host/esquema es seguro y permitido
            next_url = request.POST.get('next', '')
            if next_url and user.rol == 'administrador':
                if url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)

            # Redirección automática según el rol del usuario autenticado
            if user.rol == 'administrador':
                return redirect('dashboard_admin')
            if user.rol == 'empresa':
                return redirect('dashboard_empresa')
            return redirect('dashboard_desarrollador')            
        
        # 2. Credenciales inválidas (usuario no existe o contraseña incorrecta).
        # authenticate() ejecutó exactamente un ciclo criptográfico (hasher real o dummy).
        # Si el usuario existe en DB, incrementamos intentos fallidos y bloqueamos al llegar a 5,
        # pero NUNCA exponemos la existencia de la cuenta ni el conteo en el mensaje de error.
        user_to_check = Usuario.objects.filter(
            Q(email__iexact=identificador) | Q(username__iexact=identificador)
        ).first()
        if user_to_check:
            user_to_check.intentos_fallidos += 1
            if user_to_check.intentos_fallidos >= 5:
                # Solo marcar bloqueado_por_intentos si la cuenta no estaba ya suspendida administrativamente
                if user_to_check.estado not in ('suspendido', 'inactivo'):
                    user_to_check.bloqueado_por_intentos = True
                user_to_check.estado = 'suspendido'
                user_to_check.is_active = False  # Bloquear a nivel Django
                user_to_check.save(update_fields=['intentos_fallidos', 'estado', 'is_active', 'bloqueado_por_intentos'])
            else:
                user_to_check.save(update_fields=['intentos_fallidos'])

        messages.error(request, "Correo o contraseña incorrectos.")
        return redirect('inicio')
            
    # Si viene del admin, mostrar login estilo admin
    next_url = request.GET.get('next', '')
    if '/admin/' in next_url:
        from django.contrib.auth.forms import AuthenticationForm
        form = AuthenticationForm()
        return render(request, 'admin/login.html', {'form': form, 'next': next_url})
    return redirect('/?login=1')

from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect('inicio')

def recuperar_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            usuario = Usuario.objects.get(email=email)
            token = secrets.token_urlsafe(32)
            usuario.token_recuperacion = token
            usuario.token_expiracion = timezone.now() + timedelta(hours=1)
            usuario.save(update_fields=['token_recuperacion', 'token_expiracion'])
            
            enlace = request.build_absolute_uri(reverse('restablecer', args=[token]))
            
            mensaje = f"""
Hola {usuario.nombre},

Recibimos una solicitud para restablecer tu contraseña en JobDevs.
Para elegir una nueva contraseña, haz clic en el siguiente enlace:

{enlace}

Este enlace expirará en 1 hora. Si no solicitaste este cambio, puedes ignorar este correo.

Saludos,
El equipo de JobDevs
"""
            send_mail(
                'Restablecer tu contraseña en JobDevs',
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Usuario.DoesNotExist:
            pass # No revelamos si el email existe o no por seguridad
            
        messages.success(request, "Si el correo electrónico existe en nuestra base de datos, recibirás instrucciones para restablecer tu contraseña.")
        return redirect('/?login=1')
            
    return redirect('/?login=1')

def restablecer_view(request, token):
    try:
        usuario = Usuario.objects.get(token_recuperacion=token)
        
        # Verificar expiración
        if usuario.token_expiracion and usuario.token_expiracion < timezone.now():
            messages.error(request, "El enlace de recuperación ha expirado. Por favor, solicita uno nuevo.")
            return redirect('/?login=1')
            
        if request.method == 'POST':
            password = request.POST.get('password')
            password_confirm = request.POST.get('password_confirm')
            
            if password != password_confirm:
                messages.error(request, "Las contraseñas no coinciden.")
                return render(request, 'publico/restablecercon.html', {'token': token})
                
            if len(password) < 8:
                messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
                return render(request, 'publico/restablecercon.html', {'token': token})

            # Validar complejidad con los validadores oficiales de Django
            try:
                validate_password(password, user=usuario)
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
                return render(request, 'publico/restablecercon.html', {'token': token})

            # Actualizar contraseña e invalidar token
            usuario.set_password(password)
            usuario.token_recuperacion = None
            usuario.token_expiracion = None

            # Solo reactivar si la cuenta estaba bloqueada por exceso de intentos fallidos.
            # Las suspensiones administrativas tienen bloqueado_por_intentos=False y se preservan.
            if getattr(usuario, 'bloqueado_por_intentos', False):
                usuario.bloqueado_por_intentos = False
                usuario.estado = 'activo'
                usuario.is_active = True

            usuario.intentos_fallidos = 0
            usuario.save()
            
            messages.success(request, "Tu contraseña ha sido restablecida exitosamente. Ahora puedes iniciar sesión.")
            return redirect('login')
            
        return render(request, 'publico/restablecercon.html', {'token': token})
        
    except Usuario.DoesNotExist:
        messages.error(request, "El enlace de recuperación es inválido o ya ha sido utilizado.")
        return redirect('login')
