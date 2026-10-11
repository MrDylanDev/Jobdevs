import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import secrets

User = get_user_model()


class TestLoginView:
    """Tests for login_view at /login/"""

    def test_login_page_loads(self, client):
        """GET /login/ redirects to landing with login modal."""
        response = client.get(reverse('login'))
        assert response.status_code == 302
        assert response.url == '/?login=1'

    def test_login_success_empresa(self, client, empresa_user):
        """Valid empresa credentials redirect automatically to dashboard_empresa without role selection."""
        response = client.post(reverse('login'), {
            'username': 'empresa_test',
            'password': 'TestPass123!',
        })
        assert response.status_code == 302
        assert response.url == reverse('dashboard_empresa')

    def test_login_success_desarrollador(self, client, desarrollador_user):
        """Valid dev credentials redirect automatically to dashboard_desarrollador without role selection."""
        response = client.post(reverse('login'), {
            'username': 'dev_test',
            'password': 'TestPass123!',
        })
        assert response.status_code == 302
        assert response.url == reverse('dashboard_desarrollador')

    def test_login_success_admin(self, client, admin_user):
        """Valid admin credentials redirect automatically to dashboard_admin."""
        response = client.post(reverse('login'), {
            'username': 'admin_test',
            'password': 'TestPass123!',
        })
        assert response.status_code == 302
        assert response.url == reverse('dashboard_admin')

    def test_login_wrong_password(self, client, empresa_user):
        """Wrong password redirects to inicio with error."""
        response = client.post(reverse('login'), {
            'username': 'empresa_test',
            'password': 'WrongPassword!',
        })
        assert response.status_code == 302
        assert response.url == reverse('inicio')

    def test_login_wrong_password_message_identical_for_existing_and_nonexistent(self, client, empresa_user):
        """Failed attempt on existing vs nonexistent user must return identical message text (anti-enumeration)."""
        res_existing = client.post(reverse('login'), {
            'username': 'empresa_test',
            'password': 'WrongPassword!',
        }, follow=True)
        msg_existing = [m.message for m in res_existing.context['messages']]

        res_nonexistent = client.post(reverse('login'), {
            'username': 'no_existe_usuario',
            'password': 'WrongPassword!',
        }, follow=True)
        msg_nonexistent = [m.message for m in res_nonexistent.context['messages']]

        assert msg_existing == msg_nonexistent == ["Usuario o contraseña incorrectos."]

    def test_login_lockout_threshold_does_not_reveal_status(self, client, empresa_user):
        """Reaching 5 failed attempts locks out account but returns identical generic error (anti-enumeration)."""
        empresa_user.intentos_fallidos = 4
        empresa_user.save(update_fields=['intentos_fallidos'])

        response = client.post(reverse('login'), {
            'username': 'empresa_test',
            'password': 'WrongPassword!',
        }, follow=True)

        empresa_user.refresh_from_db()
        assert empresa_user.intentos_fallidos == 5
        assert empresa_user.estado == 'suspendido'
        assert not empresa_user.is_active

        messages = [m.message for m in response.context['messages']]
        assert not any('suspendida' in m.lower() for m in messages)
        assert any('incorrectos' in m.lower() for m in messages)

    def test_suspended_user_session_restoration_rejected(self, client, empresa_user):
        """If a logged in user becomes suspended, session restoration must reject them on protected views."""
        client.force_login(empresa_user)
        res1 = client.get(reverse('dashboard_empresa'))
        assert res1.status_code == 200

        empresa_user.is_active = False
        empresa_user.estado = 'suspendido'
        empresa_user.save(update_fields=['is_active', 'estado'])

        res2 = client.get(reverse('dashboard_empresa'))
        assert res2.status_code == 302

    def test_backend_get_user_rejects_inactive_user(self, db):
        """UsuarioAuthBackend.get_user must return None for inactive or suspended users."""
        from usuarios.backends import UsuarioAuthBackend
        backend = UsuarioAuthBackend()
        user = User.objects.create_user(
            username='inactive_sess',
            email='inactive_sess@test.teir',
            nombre='Inactive Sess',
            rol='desarrollador',
            estado='suspendido',
            is_active=False,
            password='TestPass123!',
        )
        assert backend.get_user(user.id) is None

    def test_login_automatic_role_routing_ignores_extra_role_param(self, client, empresa_user):
        """Even if legacy client sends rol_seleccionado='desarrollador', user lands on their real role dashboard."""
        response = client.post(reverse('login'), {
            'username': 'empresa_test',
            'password': 'TestPass123!',
            'rol_seleccionado': 'desarrollador',
        })
        assert response.status_code == 302
        assert response.url == reverse('dashboard_empresa')

    def test_login_suspended_user_blocked(self, client, suspended_user):
        """Suspended user cannot log in."""
        response = client.post(reverse('login'), {
            'username': 'suspended_test',
            'password': 'TestPass123!',
        })
        assert response.status_code == 302
        assert response.url == reverse('inicio')

    def test_login_suspended_user_wrong_password_does_not_reveal_status(self, client, suspended_user):
        """Entering wrong password for a suspended user must NOT reveal that the account is suspended (anti-enumeration)."""
        response = client.post(reverse('login'), {
            'username': 'suspended_test',
            'password': 'WrongPassword!',
        }, follow=True)
        messages = [m.message for m in response.context['messages']]
        assert not any('suspendida' in m.lower() for m in messages)
        assert any('incorrectos' in m.lower() for m in messages)

    def test_login_inactive_user_wrong_password_does_not_reveal_status(self, db, client):
        """Entering wrong password for an inactive user must NOT reveal status (anti-enumeration)."""
        User.objects.create_user(
            username='inactive_enum_test',
            email='inactive_enum@test.teir',
            nombre='Inactive Enum',
            rol='desarrollador',
            estado='inactivo',
            password='TestPass123!',
        )
        response = client.post(reverse('login'), {
            'username': 'inactive_enum_test',
            'password': 'WrongPassword!',
        }, follow=True)
        messages = [m.message for m in response.context['messages']]
        assert not any('inactiva' in m.lower() for m in messages)
        assert any('incorrectos' in m.lower() for m in messages)

    def test_login_inactive_user_blocked(self, db, client):
        """Inactive user cannot log in."""
        user = User.objects.create_user(
            username='inactive_test',
            email='inactive@test.teir',
            nombre='Inactive',
            rol='desarrollador',
            estado='inactivo',
            password='TestPass123!',
        )
        response = client.post(reverse('login'), {
            'username': 'inactive_test',
            'password': 'TestPass123!',
        })
        assert response.status_code == 302
        assert response.url == reverse('inicio')

    def test_login_nonexistent_user(self, client):
        """Login with username that doesn't exist."""
        response = client.post(reverse('login'), {
            'username': 'no_existe',
            'password': 'TestPass123!',
        })
        assert response.status_code == 302
        assert response.url == reverse('inicio')

    def test_login_increments_failed_attempts(self, client, empresa_user):
        """Failed login increments intentos_fallidos."""
        empresa_user.refresh_from_db()
        initial = empresa_user.intentos_fallidos
        client.post(reverse('login'), {
            'username': 'empresa_test',
            'password': 'WrongPassword!',
        })
        empresa_user.refresh_from_db()
        assert empresa_user.intentos_fallidos == initial + 1


class TestLogoutView:
    """Tests for logout_view at /logout/"""

    def test_logout_redirects_to_inicio(self, auth_client):
        """Logout clears session and redirects."""
        response = auth_client.get(reverse('logout'))
        assert response.status_code == 302
        assert response.url == reverse('inicio')

    def test_logout_clears_session(self, auth_client, client):
        """After logout, dashboard is inaccessible."""
        auth_client.get(reverse('logout'))
        response = client.get(reverse('dashboard_empresa'))
        assert response.status_code == 302  # Redirects to login


class TestRecoveryView:
    """Tests for recuperar_view at /recuperar/"""

    def test_recovery_get_redirects_to_landing(self, client):
        """GET /recuperar/ redirects to landing with login param."""
        response = client.get(reverse('recuperar'))
        assert response.status_code == 302
        assert response.url == '/?login=1'

    def test_recovery_post_valid_email(self, client, empresa_user):
        """POST with valid email sends recovery email and redirects."""
        response = client.post(reverse('recuperar'), {
            'email': 'empresa@test.teir',
        })
        assert response.status_code == 302
        assert response.url == '/?login=1'
        assert len(mail.outbox) == 1
        assert 'Restablecer' in mail.outbox[0].subject

    def test_recovery_post_sets_token(self, client, empresa_user):
        """Valid recovery request sets token and expiration."""
        client.post(reverse('recuperar'), {
            'email': 'empresa@test.teir',
        })
        empresa_user.refresh_from_db()
        assert empresa_user.token_recuperacion is not None
        assert empresa_user.token_expiracion is not None

    def test_recovery_post_unknown_email_no_leak(self, client):
        """POST with unknown email still shows success (security)."""
        response = client.post(reverse('recuperar'), {
            'email': 'no_existe@test.teir',
        })
        assert response.status_code == 302
        assert len(mail.outbox) == 0


class TestRestablecerView:
    """Tests for restablecer_view at /restablecer/<token>/"""

    @pytest.fixture
    def user_with_token(self, empresa_user):
        """Empresa user with a valid recovery token."""
        token = secrets.token_urlsafe(32)
        empresa_user.token_recuperacion = token
        empresa_user.token_expiracion = timezone.now() + timedelta(hours=1)
        empresa_user.save()
        return empresa_user, token

    def test_restablecer_valid_token_loads_form(self, client, user_with_token):
        """GET with valid token returns the reset form."""
        user, token = user_with_token
        response = client.get(reverse('restablecer', args=[token]))
        assert response.status_code == 200

    def test_restablecer_expired_token_redirects(self, client, empresa_user):
        """Expired token redirects to landing."""
        token = secrets.token_urlsafe(32)
        empresa_user.token_recuperacion = token
        empresa_user.token_expiracion = timezone.now() - timedelta(hours=1)
        empresa_user.save()
        response = client.get(reverse('restablecer', args=[token]))
        assert response.status_code == 302
        assert response.url == '/?login=1'

    def test_restablecer_invalid_token_redirects(self, client):
        """Invalid/unknown token redirects to login."""
        response = client.get(reverse('restablecer', args=['invalid-token']))
        assert response.status_code == 302

    def test_restablecer_post_changes_password(self, client, user_with_token):
        """POST with valid token and matching passwords resets password."""
        user, token = user_with_token
        response = client.post(
            reverse('restablecer', args=[token]),
            {'password': 'NewPass456!', 'password_confirm': 'NewPass456!'}
        )
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.check_password('NewPass456!')
        assert user.token_recuperacion is None

    def test_restablecer_mismatched_passwords(self, client, user_with_token):
        """Non-matching passwords show form again with error."""
        user, token = user_with_token
        response = client.post(
            reverse('restablecer', args=[token]),
            {'password': 'NewPass456!', 'password_confirm': 'Different!'}
        )
        assert response.status_code == 200

    def test_restablecer_short_password(self, client, user_with_token):
        """Password shorter than 8 chars is rejected."""
        user, token = user_with_token
        response = client.post(
            reverse('restablecer', args=[token]),
            {'password': 'Ab1!', 'password_confirm': 'Ab1!'}
        )
        assert response.status_code == 200
