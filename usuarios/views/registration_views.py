from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import redirect, render

from logs.models import LogAuditoria

from ..forms import RegistroUsuarioForm


def registro_view(request):
    if not getattr(settings, 'ALLOW_PUBLIC_REGISTRATION', True):
        return render(
            request,
            'publico/registro.html',
            {'registro_deshabilitado': True},
            status=403,
        )

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()

            LogAuditoria.objects.create(
                usuario=user,
                accion=(
                    'Aceptó las Condiciones del servicio, la Política de '
                    'privacidad y la Política de cookies al registrarse en la plataforma.'
                ),
                tabla_afectada='usuarios',
                registro_id=user.id,
                valor_nuevo='acepta_terminos=True',
            )

            # Despacho asíncrono de correo de bienvenida vía Celery (SCRUM-201).
            # Si el broker no está disponible, el registro continúa igualmente.
            if user.email:
                from notificaciones.tasks import despachar_email_transaccional
                dashboard_path = '/empresa/dashboard/' if user.rol == 'empresa' else '/desarrollador/dashboard/'
                dashboard_url = request.build_absolute_uri(dashboard_path)
                despachar_email_transaccional(
                    asunto='¡Bienvenido a JobDevs!',
                    template_name='emails/bienvenida.html',
                    contexto={
                        'usuario': {
                            'nombre': user.nombre,
                            'username': user.username,
                            'email': user.email,
                            'rol': user.rol,
                        },
                        'dashboard_url': dashboard_url,
                    },
                    destinatarios=[user.email],
                )

            login(request, user)
            if user.rol == 'empresa': return redirect('dashboard_empresa')
            return redirect('dashboard_desarrollador')
    else:
        form = RegistroUsuarioForm()
    return render(request, 'publico/registro.html', {'form': form})
