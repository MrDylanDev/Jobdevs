"""
RNF-03 — Rendimiento: Tiempo de carga de dashboards < 2 segundos.

Verifica que el renderizado de los dashboards principales (Desarrollador,
Empresa y Administrador) se completa en menos de 2 segundos bajo condiciones normales.
"""

import time
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def auth_users(db):
    dev = User.objects.create_user(
        username='dev_rnf03', email='dev@rnf03.test', password='TestPassword123*',
        rol='desarrollador', estado='activo', nombre='Dev RNF03'
    )
    empresa = User.objects.create_user(
        username='empresa_rnf03', email='empresa@rnf03.test', password='TestPassword123*',
        rol='empresa', estado='activo', nombre='Empresa RNF03'
    )
    admin = User.objects.create_user(
        username='admin_rnf03', email='admin@rnf03.test', password='TestPassword123*',
        rol='administrador', estado='activo', is_superuser=True, nombre='Admin RNF03'
    )
    return {'dev': dev, 'empresa': empresa, 'admin': admin}


@pytest.mark.django_db
class TestRNF03RendimientoDashboards:
    """Verifica que el tiempo de respuesta de cada dashboard sea inferior a 2.0 segundos."""

    def test_dashboard_desarrollador_tiempo_inferior_dos_segundos(self, client, auth_users):
        client.force_login(auth_users['dev'])
        # Warm-up de loaders de plantillas y sesión
        client.get(reverse('dashboard_desarrollador'))

        inicio = time.perf_counter()
        response = client.get(reverse('dashboard_desarrollador'))
        duracion = time.perf_counter() - inicio

        assert response.status_code == 200
        assert duracion < 2.0, f"Dashboard desarrollador tardó {duracion:.3f}s (máximo permitido 2.0s)"

    def test_dashboard_empresa_tiempo_inferior_dos_segundos(self, client, auth_users):
        client.force_login(auth_users['empresa'])
        # Warm-up
        client.get(reverse('dashboard_empresa'))

        inicio = time.perf_counter()
        response = client.get(reverse('dashboard_empresa'))
        duracion = time.perf_counter() - inicio

        assert response.status_code == 200
        assert duracion < 2.0, f"Dashboard empresa tardó {duracion:.3f}s (máximo permitido 2.0s)"

    def test_dashboard_administrador_tiempo_inferior_dos_segundos(self, client, auth_users):
        client.force_login(auth_users['admin'])
        # Warm-up
        client.get(reverse('dashboard_admin'))

        inicio = time.perf_counter()
        response = client.get(reverse('dashboard_admin'))
        duracion = time.perf_counter() - inicio

        assert response.status_code == 200
        assert duracion < 2.0, f"Dashboard administrador tardó {duracion:.3f}s (máximo permitido 2.0s)"
