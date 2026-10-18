import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from contrataciones.models import Contratacion
from disputas.models import Disputa
from proyectos.models import Proyecto

User = get_user_model()


def _user(username, rol):
    return User.objects.create_user(
        username=username, email=f'{username}@test.jobdevs', nombre=username,
        rol=rol, estado='activo', password='TestPass123!',
    )


def _login(client, user):
    client.login(username=user.username, password='TestPass123!')


def _disputa(empresa, dev, titulo, estado='abierta', iniciado_por=None, con_contratacion=True):
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo=titulo, descripcion='D', tipo_solucion='sitio_web',
        prioridad='alta', vacantes=1, estado='en_disputa',
    )
    contratacion = None
    if con_contratacion:
        contratacion = Contratacion.objects.create(
            proyecto=proyecto, desarrollador=dev, empresa=empresa, estado='en_disputa',
        )
    kwargs = {}
    if estado in ('resuelta', 'cancelada'):
        kwargs['fecha_resolucion'] = timezone.now()
    return Disputa.objects.create(
        proyecto=proyecto, contratacion=contratacion, iniciado_por=iniciado_por or dev,
        motivo=f'Motivo {titulo}', estado=estado, **kwargs,
    )


@pytest.fixture
def escenario(db):
    admin = _user('dd_admin', 'administrador')
    empresa1 = _user('dd_empresa1', 'empresa')
    empresa2 = _user('dd_empresa2', 'empresa')
    dev1 = _user('dd_dev1', 'desarrollador')
    dev2 = _user('dd_dev2', 'desarrollador')
    d_abierta = _disputa(empresa1, dev1, 'ProyAbierta', 'abierta')
    d_mediacion = _disputa(empresa1, dev1, 'ProyMediacion', 'en_mediacion')
    d_resuelta = _disputa(empresa2, dev2, 'ProyResuelta', 'resuelta')
    d_cancelada = _disputa(empresa2, dev2, 'ProyCancelada', 'cancelada')
    return {
        'admin': admin, 'empresa1': empresa1, 'empresa2': empresa2,
        'dev1': dev1, 'dev2': dev2,
        'abierta': d_abierta, 'mediacion': d_mediacion,
        'resuelta': d_resuelta, 'cancelada': d_cancelada,
    }


def _ids(qs):
    return {d.pk for d in qs}


class TestListaDisputas:
    url = 'disputas:lista_disputas'

    def test_anonimo_redirige_a_login(self, client, escenario):
        resp = client.get(reverse(self.url))
        assert resp.status_code == 302
        assert '/login' in resp.url.lower() or 'login' in resp.url.lower()

    def test_admin_ve_todas(self, client, escenario):
        _login(client, escenario['admin'])
        resp = client.get(reverse(self.url))
        assert resp.status_code == 200
        assert 'disputas/lista_disputas.html' in [t.name for t in resp.templates]
        assert _ids(resp.context['disputas_activas']) == {
            escenario['abierta'].pk, escenario['mediacion'].pk}
        assert _ids(resp.context['disputas_resueltas']) == {
            escenario['resuelta'].pk, escenario['cancelada'].pk}
        html = resp.content.decode()
        assert 'Centro de Mediación y Resolución de Disputas' in html
        assert reverse('disputas:detalle_disputa', args=[escenario['abierta'].pk]) in html

    def test_empresa_solo_ve_sus_proyectos(self, client, escenario):
        _login(client, escenario['empresa1'])
        resp = client.get(reverse(self.url))
        assert resp.status_code == 200
        assert _ids(resp.context['disputas_activas']) == {
            escenario['abierta'].pk, escenario['mediacion'].pk}
        assert _ids(resp.context['disputas_resueltas']) == set()
        html = resp.content.decode()
        assert 'ProyResuelta' not in html

    def test_desarrollador_solo_ve_las_suyas(self, client, escenario):
        _login(client, escenario['dev2'])
        resp = client.get(reverse(self.url))
        assert resp.status_code == 200
        assert _ids(resp.context['disputas_activas']) == set()
        assert _ids(resp.context['disputas_resueltas']) == {
            escenario['resuelta'].pk, escenario['cancelada'].pk}
        assert 'ProyAbierta' not in resp.content.decode()

    def test_desarrollador_ve_las_que_inicio_sin_contratacion(self, client, escenario):
        extra = _disputa(
            escenario['empresa2'], escenario['dev2'], 'ProyIniciada', 'abierta',
            iniciado_por=escenario['dev1'], con_contratacion=False,
        )
        _login(client, escenario['dev1'])
        resp = client.get(reverse(self.url))
        assert extra.pk in _ids(resp.context['disputas_activas'])
        assert escenario['resuelta'].pk not in _ids(resp.context['disputas_resueltas'])


class TestDashboardAdminDisputas:
    def test_contexto_incluye_disputas_activas(self, client, escenario):
        _login(client, escenario['admin'])
        resp = client.get(reverse('dashboard_admin'))
        assert resp.status_code == 200
        assert _ids(resp.context['disputas_activas']) == {
            escenario['abierta'].pk, escenario['mediacion'].pk}
        assert resp.context['total_disputas_activas'] == 2

    def test_template_renderiza_panel_mediacion(self, client, escenario):
        _login(client, escenario['admin'])
        html = client.get(reverse('dashboard_admin')).content.decode()
        assert 'Mediación y Disputas' in html
        inicio = html.index('id="disputasSection"')
        panel = html[inicio:html.index('</section>', inicio)]
        assert 'ProyAbierta' in panel
        assert 'ProyMediacion' in panel
        assert 'ProyResuelta' not in panel
        assert reverse('disputas:detalle_disputa', args=[escenario['abierta'].pk]) in panel
        assert reverse('disputas:lista_disputas') in panel

    def test_sin_disputas_activas(self, client, db):
        admin = _user('dd_admin_solo', 'administrador')
        _login(client, admin)
        resp = client.get(reverse('dashboard_admin'))
        assert resp.status_code == 200
        assert resp.context['total_disputas_activas'] == 0
