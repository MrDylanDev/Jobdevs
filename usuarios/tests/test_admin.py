import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client
from proyectos.models import Proyecto

User = get_user_model()


class TestDashboardAdmin:
    """Tests for dashboard_admin view and admin-only features."""

    def test_admin_access_dashboard(self, admin_client):
        """Admin can access their dashboard."""
        response = admin_client.get(reverse('dashboard_admin'))
        assert response.status_code == 200

    def test_non_admin_blocked(self, auth_client, dev_client, client):
        """Non-admin users cannot access admin dashboard."""
        for c in [auth_client, dev_client, client]:
            response = c.get(reverse('dashboard_admin'))
            assert response.status_code == 302

    def test_dashboard_shows_stats(self, admin_client):
        """Admin dashboard includes statistics."""
        response = admin_client.get(reverse('dashboard_admin'))
        content = response.content.decode()
        assert 'Panel Administrador' in content or 'TEIR' in content
        assert response.status_code == 200

    def test_dashboard_lists_users(self, admin_client, empresa_user, desarrollador_user):
        """Admin dashboard lists all users."""
        response = admin_client.get(reverse('dashboard_admin'))
        content = response.content.decode()
        assert 'empresa_test' in content
        assert 'dev_test' in content

    def test_dashboard_lists_projects(self, admin_client, empresa_user):
        """Admin dashboard shows project data when projects exist."""
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Admin Proj',
            descripcion='Test', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = admin_client.get(reverse('dashboard_admin'))
        content = response.content.decode()
        assert 'Admin Proj' in content


class TestAdminToggleUsuario:
    """Tests for admin_toggle_usuario view."""

    def test_admin_can_toggle_user(self, admin_client, empresa_user):
        """Admin can activate/suspend a user."""
        response = admin_client.post(
            reverse('admin_toggle_usuario', args=[empresa_user.id])
        )
        assert response.status_code == 302
        empresa_user.refresh_from_db()
        assert not empresa_user.is_active

    def test_non_admin_cannot_toggle(self, auth_client, desarrollador_user):
        """Non-admin cannot toggle users."""
        response = auth_client.post(
            reverse('admin_toggle_usuario', args=[desarrollador_user.id])
        )
        assert response.status_code == 302

    def test_admin_toggle_usuario_invalida_sesion_activa_inmediatamente(self, admin_client, desarrollador_user):
        """RF 1.3.2 (SCRUM-44): Suspender usuario elimina su sesión activa de django_session en tiempo real."""
        dev_client = Client()
        login_ok = dev_client.login(username=desarrollador_user.username, password='TestPass123!')
        assert login_ok is True
        session_key = dev_client.cookies['sessionid'].value
        assert Session.objects.filter(session_key=session_key).exists()

        # Admin suspende al desarrollador
        response = admin_client.post(reverse('admin_toggle_usuario', args=[desarrollador_user.id]))
        assert response.status_code == 302
        desarrollador_user.refresh_from_db()
        assert not desarrollador_user.is_active

        # Sesión destruida en base de datos inmediatamente
        assert not Session.objects.filter(session_key=session_key).exists()

        # Próxima petición del usuario es expulsada a login
        res_dev = dev_client.get(reverse('dashboard_desarrollador'))
        assert res_dev.status_code == 302
        assert '/login/' in res_dev.url


class TestAdminReactivarProyecto:
    """Tests for admin_reactivar_proyecto view."""

    def test_admin_can_reactivate(self, admin_client, empresa_user):
        """Admin can reactivate a finalized project."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Finalizado Proj',
            descripcion='T', tipo_solucion='sitio_web',
            estado='finalizado',
        )
        response = admin_client.post(
            reverse('admin_reactivar_proyecto', args=[proyecto.id])
        )
        assert response.status_code == 302
        proyecto.refresh_from_db()
        assert proyecto.estado != 'finalizado'

    def test_non_admin_cannot_reactivate(self, auth_client, empresa_user):
        """Non-admin cannot reactivate projects."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Otro Finalizado',
            descripcion='T', tipo_solucion='sitio_web',
            estado='finalizado',
        )
        response = auth_client.post(
            reverse('admin_reactivar_proyecto', args=[proyecto.id])
        )
        assert response.status_code == 302
        proyecto.refresh_from_db()
        assert proyecto.estado == 'finalizado'


class TestApiBulkToggle:
    """Tests for api_bulk_toggle endpoint."""

    def test_admin_bulk_activate(self, admin_client, db):
        """Admin can bulk activate users."""
        user1 = User.objects.create_user(
            username='bulk1', email='bulk1@t.teir', nombre='B1',
            rol='desarrollador', estado='suspendido', is_active=False,
            password='TestPass123!',
        )
        user2 = User.objects.create_user(
            username='bulk2', email='bulk2@t.teir', nombre='B2',
            rol='desarrollador', estado='suspendido', is_active=False,
            password='TestPass123!',
        )
        import json
        response = admin_client.post(
            reverse('api_bulk_toggle'),
            data=json.dumps({'ids': [user1.id, user2.id], 'action': 'activate'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 2
        user1.refresh_from_db()
        user2.refresh_from_db()
        assert user1.is_active
        assert user2.is_active

    def test_admin_bulk_suspend(self, admin_client, desarrollador_user):
        """Admin can bulk suspend users and their active sessions are deleted (SCRUM-44)."""
        import json
        user2 = User.objects.create_user(
            username='bulk3', email='bulk3@t.teir', nombre='B3',
            rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        c1 = Client()
        c1.login(username=desarrollador_user.username, password='TestPass123!')
        s1 = c1.cookies['sessionid'].value

        c2 = Client()
        c2.login(username='bulk3', password='TestPass123!')
        s2 = c2.cookies['sessionid'].value

        assert Session.objects.filter(session_key=s1).exists()
        assert Session.objects.filter(session_key=s2).exists()

        response = admin_client.post(
            reverse('api_bulk_toggle'),
            data=json.dumps({'ids': [desarrollador_user.id, user2.id], 'action': 'suspend'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        desarrollador_user.refresh_from_db()
        user2.refresh_from_db()
        assert not desarrollador_user.is_active
        assert not user2.is_active

        # Ambas sesiones activas fueron destruidas de raíz
        assert not Session.objects.filter(session_key=s1).exists()
        assert not Session.objects.filter(session_key=s2).exists()

    def test_non_admin_cannot_bulk(self, auth_client, desarrollador_user):
        """Non-admin cannot use bulk toggle."""
        import json
        response = auth_client.post(
            reverse('api_bulk_toggle'),
            data=json.dumps({'ids': [desarrollador_user.id], 'action': 'activate'}),
            content_type='application/json',
        )
        assert response.status_code == 403

    def test_admin_cannot_suspend_self(self, admin_client, admin_user):
        """Admin cannot suspend themselves via bulk."""
        import json
        response = admin_client.post(
            reverse('api_bulk_toggle'),
            data=json.dumps({'ids': [admin_user.id], 'action': 'suspend'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        admin_user.refresh_from_db()
        assert admin_user.is_active  # Not suspended


class TestApiRateLimit:
    """Tests for rate limiting on admin API endpoints."""

    def test_api_usuarios_rate_limit(self, admin_client):
        """Exceeding rate limit on api_usuarios returns 429 Too Many Requests."""
        import time
        from django.core.cache import cache
        cache.clear()

        response = admin_client.get(reverse('api_usuarios'))
        assert response.status_code == 200

        # Simulate reaching rate limit
        user_id = admin_client.session['_auth_user_id']
        window_bucket = int(time.time() // 60)
        cache_key = f"rl:api_usuarios:user_{user_id}:127.0.0.1:{window_bucket}"
        cache.set(cache_key, 60, timeout=60)

        response = admin_client.get(reverse('api_usuarios'))
        assert response.status_code == 429
        data = response.json()
        assert 'Demasiadas solicitudes' in data['error']
        assert int(response['Retry-After']) <= 60

    def test_api_crear_usuario_rate_limit(self, admin_client):
        """Mutation endpoints like api_crear_usuario enforce tighter rate limiting."""
        import time
        from django.core.cache import cache
        cache.clear()

        user_id = admin_client.session['_auth_user_id']
        window_bucket = int(time.time() // 60)
        cache_key = f"rl:api_crear_usuario:user_{user_id}:127.0.0.1:{window_bucket}"
        cache.set(cache_key, 30, timeout=60)

        response = admin_client.post(
            reverse('api_crear_usuario'),
            data='{}',
            content_type='application/json',
        )
        assert response.status_code == 429
        assert 'Demasiadas solicitudes' in response.json()['error']
