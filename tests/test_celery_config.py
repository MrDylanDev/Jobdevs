"""
Tests unitarios y de integración para la configuración de Celery y Mailpit (SCRUM-197).
"""

from django.conf import settings
from config import celery_app


class TestCeleryConfiguration:
    """Verifica que Celery esté configurado correctamente con Django."""

    def test_celery_app_instancia_y_nombre(self):
        """La aplicación de Celery está inicializada con el nombre del proyecto."""
        assert celery_app is not None
        assert celery_app.main == 'jobdevs'

    def test_celery_eager_mode_en_tests(self):
        """En entorno de pruebas, Celery ejecuta en modo eager para no depender de workers externos."""
        assert getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False) is True
        assert getattr(settings, 'CELERY_TASK_EAGER_PROPAGATES', False) is True

    def test_ejecucion_tarea_celery_eager(self):
        """Una tarea Celery ejecuta sincrónicamente en tests con delay()."""
        @celery_app.task
        def sumar(a, b):
            return a + b

        resultado = sumar.delay(10, 25)
        assert resultado.get() == 35

    def test_docker_compose_configura_mailpit_y_celery(self):
        """docker-compose.yml incluye los servicios mailpit y celery_worker en teir_network."""
        with open('docker-compose.yml', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'mailpit:' in content
        assert 'axllent/mailpit' in content
        assert '1025:1025' in content
        assert '8025:8025' in content
        assert 'celery_worker:' in content
        assert 'celery -A config worker' in content or '["celery", "-A", "config", "worker"' in content
