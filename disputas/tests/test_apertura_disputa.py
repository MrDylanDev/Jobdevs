import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from contrataciones.models import Contratacion
from disputas.models import Disputa
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import HistorialEstadoProyecto, Proyecto

User = get_user_model()


def _user(username, rol):
    return User.objects.create_user(
        username=username, email=f'{username}@test.jobdevs', nombre=username,
        rol=rol, estado='activo', password='TestPass123!',
    )


@pytest.fixture
def escenario(db):
    empresa = _user('ap_empresa', 'empresa')
    dev = _user('ap_dev', 'desarrollador')
    admin = _user('ap_admin', 'administrador')
    admin2 = _user('ap_admin2', 'administrador')
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo='Proyecto Disputado', descripcion='D',
        tipo_solucion='sitio_web', prioridad='alta', vacantes=1,
        estado='en_desarrollo',
    )
    contratacion = Contratacion.objects.create(
        proyecto=proyecto, desarrollador=dev, empresa=empresa,
    )
    return {'empresa': empresa, 'dev': dev, 'admin': admin, 'admin2': admin2,
            'proyecto': proyecto, 'contratacion': contratacion}


def _url(proyecto):
    return reverse('disputas:abrir_disputa', args=[proyecto.id])


def _login(client, user):
    client.login(username=user.username, password='TestPass123!')


class TestAcceso:
    def test_anonimo_redirige_a_login(self, client, escenario):
        resp = client.post(_url(escenario['proyecto']), {'motivo': 'x'})
        assert resp.status_code == 302
        assert '/login' in resp.url or 'login' in resp.url
        assert Disputa.objects.count() == 0

    def test_get_muestra_formulario(self, client, escenario):
        _login(client, escenario['dev'])
        resp = client.get(_url(escenario['proyecto']))
        assert resp.status_code == 200
        content = resp.content.decode()
        assert 'Proyecto Disputado' in content
        assert 'name="motivo"' in content
        assert 'Iniciar Mediación' in content

    def test_tercero_desarrollador_recibe_403(self, client, escenario):
        otro = _user('ap_otro_dev', 'desarrollador')
        _login(client, otro)
        assert client.get(_url(escenario['proyecto'])).status_code == 403
        resp = client.post(_url(escenario['proyecto']), {'motivo': 'x'})
        assert resp.status_code == 403
        assert Disputa.objects.count() == 0

    def test_otra_empresa_recibe_403(self, client, escenario):
        otra = _user('ap_otra_empresa', 'empresa')
        _login(client, otra)
        resp = client.post(_url(escenario['proyecto']), {'motivo': 'x'})
        assert resp.status_code == 403
        escenario['proyecto'].refresh_from_db()
        assert escenario['proyecto'].estado == 'en_desarrollo'

    def test_dev_con_contratacion_no_activa_recibe_403(self, client, escenario):
        Contratacion.objects.filter(pk=escenario['contratacion'].pk).update(estado='cancelada')
        _login(client, escenario['dev'])
        resp = client.post(_url(escenario['proyecto']), {'motivo': 'x'})
        assert resp.status_code == 403

    def test_proyecto_inexistente_404(self, client, escenario):
        _login(client, escenario['dev'])
        assert client.get(reverse('disputas:abrir_disputa', args=[99999])).status_code == 404


class TestApertura:
    def test_desarrollador_abre_disputa(self, client, escenario):
        _login(client, escenario['dev'])
        resp = client.post(_url(escenario['proyecto']), {'motivo': 'No pagan'})
        disputa = Disputa.objects.get()
        assert resp.status_code == 302
        assert resp.url == reverse('disputas:detalle_disputa', args=[disputa.id])
        assert disputa.iniciado_por == escenario['dev']
        assert disputa.motivo == 'No pagan'
        assert disputa.estado == 'abierta'
        assert disputa.contratacion == escenario['contratacion']

    def test_empresa_abre_disputa(self, client, escenario):
        _login(client, escenario['empresa'])
        resp = client.post(_url(escenario['proyecto']), {'motivo': 'No entrega'})
        disputa = Disputa.objects.get()
        assert resp.status_code == 302
        assert disputa.iniciado_por == escenario['empresa']
        assert disputa.contratacion == escenario['contratacion']

    def test_congelamiento_atomico(self, client, escenario):
        _login(client, escenario['dev'])
        client.post(_url(escenario['proyecto']), {'motivo': 'Motivo'})
        escenario['proyecto'].refresh_from_db()
        escenario['contratacion'].refresh_from_db()
        assert escenario['proyecto'].estado == 'en_disputa'
        assert escenario['contratacion'].estado == 'en_disputa'

    def test_historial_estado_registrado(self, client, escenario):
        _login(client, escenario['dev'])
        client.post(_url(escenario['proyecto']), {'motivo': 'Motivo'})
        h = HistorialEstadoProyecto.objects.get(proyecto=escenario['proyecto'])
        assert h.estado_anterior == 'en_desarrollo'
        assert h.estado_nuevo == 'en_disputa'
        assert h.cambiado_por == escenario['dev']

    def test_log_auditoria_creado(self, client, escenario):
        _login(client, escenario['empresa'])
        client.post(_url(escenario['proyecto']), {'motivo': 'Motivo'})
        disputa = Disputa.objects.get()
        log = LogAuditoria.objects.get(tabla_afectada='disputas')
        assert log.usuario == escenario['empresa']
        assert log.registro_id == disputa.id
        assert 'Proyecto Disputado' in log.accion

    def test_notificaciones_contraparte_y_admins(self, client, escenario):
        _login(client, escenario['dev'])
        client.post(_url(escenario['proyecto']), {'motivo': 'Motivo'})
        destinatarios = set(
            Notificacion.objects.filter(proyecto=escenario['proyecto'])
            .values_list('usuario__username', flat=True)
        )
        admins = set(User.objects.filter(rol='administrador').values_list('username', flat=True))
        assert destinatarios == {'ap_empresa'} | admins
        assert {'ap_admin', 'ap_admin2'} <= destinatarios

    def test_notificaciones_empresa_inicia_notifica_dev(self, client, escenario):
        _login(client, escenario['empresa'])
        client.post(_url(escenario['proyecto']), {'motivo': 'Motivo'})
        destinatarios = set(
            Notificacion.objects.filter(proyecto=escenario['proyecto'])
            .values_list('usuario__username', flat=True)
        )
        admins = set(User.objects.filter(rol='administrador').values_list('username', flat=True))
        assert destinatarios == {'ap_dev'} | admins
        assert 'ap_empresa' not in destinatarios


class TestValidacion:
    @pytest.mark.parametrize('motivo', ['', '   ', '\n\t '])
    def test_motivo_vacio_rechazado(self, client, escenario, motivo):
        _login(client, escenario['dev'])
        resp = client.post(_url(escenario['proyecto']), {'motivo': motivo})
        assert resp.status_code == 200
        assert Disputa.objects.count() == 0
        escenario['proyecto'].refresh_from_db()
        assert escenario['proyecto'].estado == 'en_desarrollo'

    @pytest.mark.parametrize('estado', ['finalizado', 'en_disputa'])
    def test_no_se_puede_abrir_en_estado_invalido(self, client, escenario, estado):
        Proyecto.objects.filter(pk=escenario['proyecto'].pk).update(estado=estado)
        _login(client, escenario['dev'])
        resp = client.post(_url(escenario['proyecto']), {'motivo': 'Motivo'})
        assert resp.status_code == 400
        assert Disputa.objects.count() == 0
        escenario['proyecto'].refresh_from_db()
        assert escenario['proyecto'].estado == estado
        assert not HistorialEstadoProyecto.objects.filter(proyecto=escenario['proyecto']).exists()
