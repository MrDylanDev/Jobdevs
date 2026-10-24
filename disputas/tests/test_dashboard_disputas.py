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

    @pytest.mark.parametrize('clave,destino', [
        ('empresa1', 'dashboard_empresa'),
        ('dev1', 'dashboard_desarrollador'),
    ])
    def test_empresa_y_dev_son_redirigidos_a_su_dashboard(self, client, escenario, clave, destino):
        _login(client, escenario[clave])
        resp = client.get(reverse(self.url))
        assert resp.status_code == 302
        assert resp.url == f"{reverse(destino)}?section=disputas"


class TestPestanaDisputasEnDashboard:
    def test_empresa_solo_ve_sus_proyectos(self, client, escenario):
        _login(client, escenario['empresa1'])
        resp = client.get(reverse('dashboard_empresa'))
        assert resp.status_code == 200
        assert _ids(resp.context['disputas_activas']) == {
            escenario['abierta'].pk, escenario['mediacion'].pk}
        assert _ids(resp.context['disputas_resueltas']) == set()
        assert resp.context['disputas_activas_count'] == 2
        html = resp.content.decode()
        assert 'id="disputas"' in html
        assert 'ProyAbierta' in html
        assert 'ProyResuelta' not in html

    def test_desarrollador_solo_ve_las_suyas(self, client, escenario):
        _login(client, escenario['dev2'])
        resp = client.get(reverse('dashboard_desarrollador'))
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
        resp = client.get(reverse('dashboard_desarrollador'))
        assert extra.pk in _ids(resp.context['disputas_activas'])
        assert escenario['resuelta'].pk not in _ids(resp.context['disputas_resueltas'])

    @pytest.mark.parametrize('clave,destino,funcion', [
        ('empresa1', 'dashboard_empresa', "switchTab('disputas'"),
        ('dev1', 'dashboard_desarrollador', "verSeccion('disputas'"),
    ])
    def test_sidebar_abre_la_pestana_sin_salir_del_dashboard(
        self, client, escenario, clave, destino, funcion,
    ):
        _login(client, escenario[clave])
        html = client.get(reverse(destino)).content.decode()
        assert funcion in html
        assert f'href="{reverse("disputas:lista_disputas")}"' not in html

    @pytest.mark.parametrize('clave,destino', [
        ('empresa1', 'dashboard_empresa'),
        ('dev1', 'dashboard_desarrollador'),
    ])
    def test_boton_iniciar_disputa_y_selector_de_proyectos_elegibles(
        self, client, escenario, clave, destino,
    ):
        elegible = Proyecto.objects.create(
            empresa=escenario['empresa1'], titulo='ProyElegible', descripcion='D',
            tipo_solucion='sitio_web', prioridad='alta', vacantes=1, estado='en_desarrollo',
        )
        Contratacion.objects.create(
            proyecto=elegible, desarrollador=escenario['dev1'], empresa=escenario['empresa1'],
        )
        _login(client, escenario[clave])
        resp = client.get(reverse(destino))
        html = resp.content.decode()
        assert 'Iniciar Nueva Disputa' in html
        assert 'id="modalNuevaDisputa"' in html
        assert [p.pk for p in resp.context['proyectos_disputables']] == [elegible.pk]
        assert reverse('disputas:abrir_disputa', args=[elegible.pk]) in html

    def test_no_se_usa_bootstrap_en_la_pestana(self, client, escenario):
        _login(client, escenario['empresa1'])
        html = client.get(reverse('dashboard_empresa')).content.decode()
        assert 'data-bs-toggle' not in html
        assert 'btn-outline-danger' not in html


class TestListaAdministrador:
    def test_admin_ve_lista_con_layout_propio_y_sin_boton_de_apertura(self, client, escenario):
        _login(client, escenario['admin'])
        resp = client.get(reverse('disputas:lista_disputas'))
        assert resp.status_code == 200
        assert 'disputas/layout.html' in [t.name for t in resp.templates]
        html = resp.content.decode()
        assert 'id="btn-iniciar-disputa"' not in html
        assert 'bootstrap' not in html.lower()


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


class TestDatosDashboardDisputasFiltro:
    """SCRUM-232 (RF 10.1.2): filtro fino y conteos por estado."""

    def _datos(self, usuario, estado=None):
        from disputas.services import datos_dashboard_disputas
        return datos_dashboard_disputas(usuario, estado=estado)

    def test_conteos_por_estado_admin(self, escenario):
        datos = self._datos(escenario['admin'])
        assert datos['disputas_por_estado'] == {
            'abierta': 1, 'en_mediacion': 1, 'resuelta': 1, 'cancelada': 1,
        }
        assert datos['total_disputas'] == 4

    def test_conteos_por_estado_empresa(self, escenario):
        datos = self._datos(escenario['empresa1'])
        assert datos['disputas_por_estado'] == {
            'abierta': 1, 'en_mediacion': 1, 'resuelta': 0, 'cancelada': 0,
        }
        assert datos['total_disputas'] == 2

    def test_conteos_por_estado_desarrollador(self, escenario):
        datos = self._datos(escenario['dev2'])
        assert datos['disputas_por_estado'] == {
            'abierta': 0, 'en_mediacion': 0, 'resuelta': 1, 'cancelada': 1,
        }
        assert datos['total_disputas'] == 2

    @pytest.mark.parametrize('estado', ['abierta', 'en_mediacion', 'resuelta', 'cancelada'])
    def test_filtro_por_estado_admin(self, escenario, estado):
        datos = self._datos(escenario['admin'], estado=estado)
        esperada = {'abierta': escenario['abierta'], 'en_mediacion': escenario['mediacion'],
                    'resuelta': escenario['resuelta'], 'cancelada': escenario['cancelada']}[estado]
        assert datos['filtro_estado_actual'] == estado
        assert _ids(datos['disputas_filtradas']) == {esperada.pk}

    def test_filtro_por_estado_empresa(self, escenario):
        datos = self._datos(escenario['empresa1'], estado='en_mediacion')
        assert _ids(datos['disputas_filtradas']) == {escenario['mediacion'].pk}

    def test_filtro_por_estado_dev(self, escenario):
        datos = self._datos(escenario['dev2'], estado='cancelada')
        assert _ids(datos['disputas_filtradas']) == {escenario['cancelada'].pk}

    def test_estado_invalido_no_filtra(self, escenario):
        datos = self._datos(escenario['admin'], estado='inexistente')
        assert datos['filtro_estado_actual'] == ''
        assert len(datos['disputas_filtradas']) == 4

    def test_sin_estado_devuelve_todas(self, escenario):
        datos = self._datos(escenario['admin'])
        assert datos['filtro_estado_actual'] == ''
        fechas = [d.fecha_creacion for d in datos['disputas_filtradas']]
        assert len(fechas) == 4
        assert fechas == sorted(fechas, reverse=True)

    def test_claves_preexistentes_intactas(self, escenario):
        datos = self._datos(escenario['empresa1'], estado='abierta')
        assert _ids(datos['disputas_activas']) == {
            escenario['abierta'].pk, escenario['mediacion'].pk}
        assert _ids(datos['disputas_resueltas']) == set()
        assert 'proyectos_disputables' in datos


class TestFiltroEstadoEnVistas:
    """SCRUM-232: la vista acepta ?estado= y renderiza la barra de filtros."""

    def test_lista_disputas_admin_acepta_estado(self, client, escenario):
        _login(client, escenario['admin'])
        resp = client.get(reverse('disputas:lista_disputas'), {'estado': 'en_mediacion'})
        assert resp.status_code == 200
        assert resp.context['filtro_estado_actual'] == 'en_mediacion'
        assert _ids(resp.context['disputas_filtradas']) == {escenario['mediacion'].pk}
        html = resp.content.decode()
        assert 'data-testid="filtro-disputas"' in html
        assert 'En mediación (1)' in html

    def test_lista_disputas_renderiza_todos_los_conteos(self, client, escenario):
        _login(client, escenario['admin'])
        html = client.get(reverse('disputas:lista_disputas')).content.decode()
        assert 'data-testid="filtro-disputas"' in html
        assert 'Abiertas (1)' in html
        assert 'Resueltas (1)' in html
        assert 'Canceladas (1)' in html
        assert 'Todos (4)' in html

    def test_dashboard_empresa_acepta_estado(self, client, escenario):
        _login(client, escenario['empresa1'])
        resp = client.get(reverse('dashboard_empresa'), {
            'section': 'disputas', 'estado': 'abierta'})
        assert resp.status_code == 200
        assert resp.context['filtro_estado_actual'] == 'abierta'
        assert _ids(resp.context['disputas_filtradas']) == {escenario['abierta'].pk}
        html = resp.content.decode()
        assert 'data-testid="filtro-disputas"' in html
        assert 'section=disputas&amp;estado=abierta' in html

    def test_dashboard_dev_acepta_estado(self, client, escenario):
        _login(client, escenario['dev2'])
        resp = client.get(reverse('dashboard_desarrollador'), {
            'section': 'disputas', 'estado': 'resuelta'})
        assert resp.status_code == 200
        assert resp.context['filtro_estado_actual'] == 'resuelta'
        assert _ids(resp.context['disputas_filtradas']) == {escenario['resuelta'].pk}

    def test_dashboard_admin_incluye_conteos(self, client, escenario):
        _login(client, escenario['admin'])
        resp = client.get(reverse('dashboard_admin'))
        assert resp.status_code == 200
        assert resp.context['disputas_por_estado'] == {
            'abierta': 1, 'en_mediacion': 1, 'resuelta': 1, 'cancelada': 1,
        }
