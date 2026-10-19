import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class TestUsuarioActivoMiddleware:
    """Tests para UsuarioActivoMiddleware (SCRUM-170 / RF 1.3.2)."""

    def test_usuario_activo_accede_normalmente(self, client, empresa_user):
        """Usuario activo navega sin interrupción."""
        client.force_login(empresa_user)
        response = client.get(reverse('listar_proyectos'))
        assert response.status_code == 200

    def test_usuario_suspendido_es_expulsado_en_rutas_de_negocio(self, client, suspended_user):
        """SCRUM-170: Usuario suspendido es expulsado de rutas que no tenían decorador individual."""
        client.force_login(suspended_user)
        # Intentar acceder a listado de proyectos
        response = client.get(reverse('listar_proyectos'))
        assert response.status_code == 302
        assert response.url.startswith(reverse('login'))

        # Verificar que la sesión zombi fue purgada
        assert '_auth_user_id' not in client.session

    def test_usuario_inactivo_es_expulsado(self, client, db):
        """Usuario con is_active=False es expulsado inmediatamente."""
        inactivo = User.objects.create_user(
            username='user_inactivo',
            email='inactivo@test.jobdevs',
            nombre='Inactivo',
            rol='desarrollador',
            estado='inactivo',
            is_active=False,
            password='TestPass123!',
        )
        client.force_login(inactivo)
        response = client.get(reverse('mensajeria_inbox'))
        assert response.status_code == 302
        assert response.url.startswith(reverse('login'))
        assert '_auth_user_id' not in client.session

    def test_usuario_anonimo_no_es_afectado(self, client):
        """Visitante anónimo navega sin ser redirigido por el middleware."""
        response = client.get(reverse('inicio'))
        assert response.status_code == 200
