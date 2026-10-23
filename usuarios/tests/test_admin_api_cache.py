"""RNF-21: la caché de administradores debe reflejar siempre el estado real de la BD.

Regresión de SCRUM-397: crear y actualizar invalidaban `admin_id`/`admin_ids_list`,
pero eliminar un administrador no lo hacía, de modo que la lista cacheada seguía
conteniendo al usuario borrado hasta que expirara el TTL.
"""
import pytest
from django.core.cache import cache
from django.urls import reverse

from usuarios.models import Usuario
from usuarios.utils import get_admin_ids


@pytest.fixture(autouse=True)
def _limpiar_cache():
    cache.clear()
    yield
    cache.clear()


def _crear_admin(username):
    return Usuario.objects.create_user(
        username=username,
        email=f'{username}@test.jobdevs',
        password='TestPass123!',
        rol='administrador',
    )


class TestCacheAdministradores:
    def test_eliminar_admin_invalida_la_cache(self, admin_client, admin_user):
        """Al eliminar un administrador, la lista cacheada no puede seguir conteniéndolo."""
        objetivo = _crear_admin('admin_a_borrar')
        # La lista se cachea al consultarla (get_admin_ids) y queda en memoria 5 minutos.
        assert objetivo.id in get_admin_ids()

        response = admin_client.delete(reverse('api_eliminar_usuario', args=[objetivo.id]))
        assert response.status_code == 200, response.content

        assert not Usuario.objects.filter(id=objetivo.id).exists()
        assert objetivo.id not in get_admin_ids(), (
            'la lista cacheada de administradores sigue conteniendo al usuario eliminado'
        )

    def test_crear_admin_invalida_la_cache(self, admin_client, admin_user):
        """Comportamiento previo que debe conservarse: crear un admin invalida la caché."""
        antes = get_admin_ids()
        assert admin_user.id in antes

        response = admin_client.post(
            reverse('api_crear_usuario'),
            data={'username': 'admin_nuevo', 'email': 'nuevo@test.jobdevs',
                  'password': 'TestPass123!', 'rol': 'administrador'},
            content_type='application/json',
        )
        assert response.status_code == 201, response.content

        nuevo = Usuario.objects.get(username='admin_nuevo')
        assert nuevo.id in get_admin_ids()

    def test_actualizar_rol_a_admin_invalida_la_cache(self, admin_client, admin_user, desarrollador_user):
        """Comportamiento previo que debe conservarse: cambiar el rol invalida la caché."""
        assert desarrollador_user.id not in get_admin_ids()

        response = admin_client.put(
            reverse('api_actualizar_usuario', args=[desarrollador_user.id]),
            data={'rol': 'administrador'},
            content_type='application/json',
        )
        assert response.status_code == 200, response.content

        assert desarrollador_user.id in get_admin_ids()

    def test_admin_no_puede_eliminarse_a_si_mismo(self, admin_client, admin_user):
        """Comportamiento previo que debe conservarse: el auto-borrado se rechaza."""
        response = admin_client.delete(reverse('api_eliminar_usuario', args=[admin_user.id]))
        assert response.status_code == 400
        assert Usuario.objects.filter(id=admin_user.id).exists()
