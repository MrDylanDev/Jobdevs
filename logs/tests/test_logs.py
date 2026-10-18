import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from logs.models import LogAuditoria

User = get_user_model()


class TestLogAuditoriaModel:
    """Tests for LogAuditoria model."""

    def test_crear_log(self, db):
        """LogAuditoria records user actions."""
        user = User.objects.create_user(
            username='lg', email='lg@test.jobdevs',
            nombre='LG', rol='administrador', estado='activo',
            password='TestPass123!',
        )
        log = LogAuditoria.objects.create(
            usuario=user, accion='TEST',
            tabla_afectada='usuarios',
        )
        assert log.id is not None
        assert log.accion == 'TEST'
        assert log.usuario == user

    def test_log_str(self, db):
        """__str__ shows usuario and accion."""
        user = User.objects.create_user(
            username='lg2', email='lg2@test.jobdevs',
            nombre='LG2', rol='administrador', estado='activo',
            password='TestPass123!',
        )
        log = LogAuditoria.objects.create(
            usuario=user, accion='LOGIN',
            tabla_afectada='usuarios',
        )
        assert 'lg2' in str(log)
        assert 'LOGIN' in str(log)


class TestReportes:
    """Tests for report views (admin only)."""

    def test_reporte_vista_impresion_accessible(self, admin_client):
        """Admin can access report view."""
        response = admin_client.get(reverse('reporte_vista_impresion'))
        assert response.status_code == 200

    def test_reporte_blocked_anon(self, client):
        """Anonymous cannot access reports."""
        response = client.get(reverse('reporte_vista_impresion'))
        assert response.status_code == 302
