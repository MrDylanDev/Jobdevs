"""Perfil integrado en el dashboard y modal flotante de verificación SENA."""

import pytest
from django.urls import reverse

from logs.models import LogAuditoria
from usuarios.models import FichaSena, PerfilDesarrollador, Usuario


@pytest.fixture
def dev(db):
    user = Usuario.objects.create_user(
        username='dev_perfil_ui',
        email='dev_perfil_ui@test.jobdevs',
        password='Password123!',
        rol='desarrollador',
        identificacion='1000000999',
    )
    PerfilDesarrollador.objects.get_or_create(usuario=user)
    return user


@pytest.fixture
def dev_client(client, dev):
    client.force_login(dev)
    return client


def _dashboard(dev_client, query=''):
    return dev_client.get(reverse('dashboard_desarrollador') + query)


@pytest.mark.django_db
class TestPerfilIntegradoEnDashboard:
    def test_perfil_es_seccion_del_dashboard(self, dev_client):
        html = _dashboard(dev_client).content.decode()
        assert 'id="perfil" class="seccion-v"' in html
        assert "verSeccion('perfil'" in html
        # El acceso ya no debe ser un enlace a la página independiente.
        assert f'href="{reverse("editar_perfil")}"' not in html

    def test_modal_de_verificacion_presente_en_dashboard(self, dev_client):
        html = _dashboard(dev_client).content.decode()
        assert 'id="modalVerificacion"' in html
        assert 'abrirVerificacion()' in html
        assert html.count('data-verificacion-form') == 3
        assert html.count('value="dashboard"') >= 3

    def test_banner_verificacion_usa_tema_oscuro(self, dev_client):
        html = _dashboard(dev_client).content.decode()
        assert 'jd-alert jd-alert-warning' in html
        assert 'data-testid="alerta-verificacion-sena"' in html

    def test_seccion_inicial_desde_query(self, dev_client):
        response = _dashboard(dev_client, '?seccion=perfil')
        assert response.context['seccion_activa'] == 'perfil'
        assert 'data-seccion-inicial="perfil"' in response.content.decode()

    def test_seccion_invalida_cae_en_inicio(self, dev_client):
        response = _dashboard(dev_client, '?seccion=no-existe')
        assert response.context['seccion_activa'] == 'inicio'


@pytest.mark.django_db
class TestPostPerfilDesdeDashboard:
    def test_actualiza_perfil_audita_y_vuelve_a_seccion(self, dev_client, dev):
        response = dev_client.post(
            reverse('dashboard_desarrollador'),
            {
                'accion': 'perfil',
                'telefono': '3109998877',
                'habilidades': 'Python, Django',
                'portafolio_url': 'https://github.com/dev',
            },
        )
        assert response.status_code == 302
        assert response['Location'].endswith('?seccion=perfil')
        perfil = PerfilDesarrollador.objects.get(usuario=dev)
        assert perfil.telefono == '3109998877'
        assert perfil.habilidades == 'Python, Django'
        assert LogAuditoria.objects.filter(
            usuario=dev, tabla_afectada='perfil_desarrollador'
        ).exists()

    def test_datos_invalidos_conservan_seccion_y_muestran_error(self, dev_client, dev):
        response = dev_client.post(
            reverse('dashboard_desarrollador'),
            {'accion': 'perfil', 'portafolio_url': 'no-es-una-url'},
        )
        assert response.status_code == 200
        assert response.context['seccion_activa'] == 'perfil'
        assert 'data-seccion-inicial="perfil"' in response.content.decode()
        assert 'jd-error' in response.content.decode()
        perfil = PerfilDesarrollador.objects.get(usuario=dev)
        assert not perfil.portafolio_url


@pytest.mark.django_db
class TestVerificacionInlineDesdeModal:
    url = staticmethod(lambda: reverse('solicitar_verificacion_desarrollador'))

    def test_ficha_invalida_responde_json_sin_redirigir(self, dev_client):
        response = dev_client.post(
            self.url(),
            {'origen': 'dashboard', 'metodo': 'automatica', 'ficha': '0000000'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False
        assert 'ficha' in data['errores']
        assert data['estado'] == 'sin_verificar'

    def test_ficha_valida_verifica_y_responde_json(self, dev_client, dev):
        FichaSena.objects.create(
            numero_ficha='2670999', programa_formacion='ADSO', activa=True
        )
        response = dev_client.post(
            self.url(),
            {'origen': 'dashboard', 'metodo': 'automatica', 'ficha': '2670999'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['verificado'] is True
        assert data['estado'] == 'verificado'
        perfil = PerfilDesarrollador.objects.get(usuario=dev)
        assert perfil.es_verificado_sena is True

    def test_sin_origen_mantiene_flujo_html_clasico(self, dev_client):
        FichaSena.objects.create(
            numero_ficha='2670888', programa_formacion='ADSO', activa=True
        )
        response = dev_client.post(
            self.url(), {'metodo': 'automatica', 'ficha': '2670888'}
        )
        assert response.status_code == 302

    def test_metodo_invalido_responde_json(self, dev_client):
        response = dev_client.post(
            self.url(),
            {'origen': 'dashboard', 'metodo': 'inexistente'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert response.status_code == 400
        assert response.json()['ok'] is False
