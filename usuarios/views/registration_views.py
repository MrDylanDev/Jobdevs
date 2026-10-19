from django.shortcuts import render, redirect
from django.contrib.auth import login

from ..forms import RegistroUsuarioForm


def registro_view(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Despacho asíncrono de correo de bienvenida vía Celery (SCRUM-201)
            if user.email:
                from notificaciones.tasks import enviar_email_transaccional_task
                dashboard_path = '/empresa/dashboard/' if user.rol == 'empresa' else '/desarrollador/dashboard/'
                dashboard_url = request.build_absolute_uri(dashboard_path)
                enviar_email_transaccional_task.delay(
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
