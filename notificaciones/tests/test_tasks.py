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

    def test_purgar_notificaciones_elimina_leidas_antiguas_y_conserva_recientes(self):
        """SCRUM-200: Celery Beat purga notificaciones leídas anteriores al corte y conserva recientes y no leídas."""
        from datetime import timedelta
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from notificaciones.models import Notificacion
        from notificaciones.tasks import purgar_notificaciones_antiguas_task

        User = get_user_model()
        user = User.objects.create_user(
            username='user_purga', email='purga@test.jobdevs', password='Password123!', rol='desarrollador'
        )

        hace_40_dias = timezone.now() - timedelta(days=40)

        # 1. Leída antigua (debe ser borrada)
        n_leida_antigua = Notificacion.objects.create(
            usuario=user, mensaje='Leída antigua', leida=True, tipo='alerta'
        )
        Notificacion.objects.filter(id=n_leida_antigua.id).update(fecha=hace_40_dias)

        # 2. No leída antigua (debe conservarse por defecto)
        n_no_leida_antigua = Notificacion.objects.create(
            usuario=user, mensaje='No leída antigua', leida=False, tipo='alerta'
        )
        Notificacion.objects.filter(id=n_no_leida_antigua.id).update(fecha=hace_40_dias)

        # 3. Leída reciente (debe conservarse)
        n_leida_reciente = Notificacion.objects.create(
            usuario=user, mensaje='Leída reciente', leida=True, tipo='alerta'
        )

        res = purgar_notificaciones_antiguas_task.delay(dias=30, incluir_no_leidas=False)
        borradas = res.get()

        assert borradas == 1
        assert not Notificacion.objects.filter(id=n_leida_antigua.id).exists()
        assert Notificacion.objects.filter(id=n_no_leida_antigua.id).exists()
        assert Notificacion.objects.filter(id=n_leida_reciente.id).exists()

    def test_purgar_notificaciones_incluye_no_leidas_con_flag(self):
        """SCRUM-200: Con incluir_no_leidas=True, purga tanto leídas como no leídas antiguas."""
        from datetime import timedelta
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from notificaciones.models import Notificacion
        from notificaciones.tasks import purgar_notificaciones_antiguas_task

        User = get_user_model()
        user = User.objects.create_user(
            username='user_purga_all', email='purga_all@test.jobdevs', password='Password123!', rol='desarrollador'
        )

        hace_50_dias = timezone.now() - timedelta(days=50)

        n1 = Notificacion.objects.create(usuario=user, mensaje='N1', leida=True)
        Notificacion.objects.filter(id=n1.id).update(fecha=hace_50_dias)
        n2 = Notificacion.objects.create(usuario=user, mensaje='N2', leida=False)
        Notificacion.objects.filter(id=n2.id).update(fecha=hace_50_dias)

        res = purgar_notificaciones_antiguas_task.delay(dias=30, incluir_no_leidas=True)
        assert res.get() == 2
        assert Notificacion.objects.filter(usuario=user).count() == 0

    def test_celery_beat_schedule_configuracion(self):
        """SCRUM-200: CELERY_BEAT_SCHEDULE está registrado en settings."""
        from django.conf import settings
        beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
        assert 'purgar-notificaciones-medianoche' in beat_schedule
        config_purga = beat_schedule['purgar-notificaciones-medianoche']
        assert config_purga['task'] == 'notificaciones.purgar_notificaciones_antiguas'

