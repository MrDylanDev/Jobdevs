"""
Tests unitarios para las tareas Celery de correos transaccionales (SCRUM-198).
"""

from unittest import mock
import pytest
from django.core import mail
from notificaciones.tasks import enviar_email_transaccional_task


@pytest.mark.django_db
class TestEmailTransaccionalTask:
    """Verifica el despacho asíncrono de emails con Celery y plantillas HTML."""

    def test_enviar_email_sin_destinatarios_retorna_false(self):
        """Si la lista de destinatarios está vacía, no intenta despachar y retorna False."""
        res = enviar_email_transaccional_task.delay(
            asunto="Test Sin Destinatarios",
            template_name="emails/base_email.html",
            contexto={},
            destinatarios=[],
        )
        assert res.get() is False
        assert len(mail.outbox) == 0

    def test_enviar_email_recuperar_password_exitoso(self):
        """Despacha correo HTML y texto plano para restablecimiento de contraseña."""
        mail.outbox.clear()

        contexto = {
            'usuario': {'nombre': 'Carlos Aprendiz', 'email': 'carlos@sena.edu.co'},
            'reset_url': 'https://jobdevs.edu.co/restablecer/token123456/',
        }

        res = enviar_email_transaccional_task.delay(
            asunto="Restablecer tu contraseña en JobDevs",
            template_name="emails/recuperar_password.html",
            contexto=contexto,
            destinatarios=['carlos@sena.edu.co'],
        )

        assert res.get() is True
        assert len(mail.outbox) == 1

        email_enviado = mail.outbox[0]
        assert email_enviado.subject == "Restablecer tu contraseña en JobDevs"
        assert email_enviado.to == ['carlos@sena.edu.co']
        assert 'token123456' in email_enviado.body  # Texto plano
        assert len(email_enviado.alternatives) == 1
        html_body, mime = email_enviado.alternatives[0]
        assert mime == 'text/html'
        assert 'token123456' in html_body
        assert 'Carlos Aprendiz' in html_body

    def test_enviar_email_postulacion_aceptada_exitoso(self):
        """Despacha correo de felicitaciones ante postulación aceptada."""
        mail.outbox.clear()

        contexto = {
            'usuario': {'nombre': 'Laura Dev', 'username': 'lauradev'},
            'empresa': {'nombre': 'Tech Innovations SAS'},
            'proyecto': {'titulo': 'Desarrollo E-Commerce Microservicios', 'tipo_solucion': 'sitio_web'},
            'dashboard_url': 'https://jobdevs.edu.co/desarrollador/dashboard/',
        }

        res = enviar_email_transaccional_task.delay(
            asunto="¡Tu postulación fue aceptada!",
            template_name="emails/postulacion_aceptada.html",
            contexto=contexto,
            destinatarios=['laura@test.jobdevs'],
        )

        assert res.get() is True
        assert len(mail.outbox) == 1

        email_enviado = mail.outbox[0]
        assert email_enviado.to == ['laura@test.jobdevs']
        assert 'Tech Innovations SAS' in email_enviado.body
        assert 'Desarrollo E-Commerce Microservicios' in email_enviado.body
