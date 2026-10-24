import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from contrataciones.models import Contratacion
from disputas.models import Disputa, MensajeDisputa
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import Proyecto

User = get_user_model()


def _user(username, rol):
    return User.objects.create_user(
        username=username, email=f'{username}@test.jobdevs', nombre=username,
        rol=rol, estado='activo', password='TestPass123!',
    )


def _login(client, user):
    client.login(username=user.username, password='TestPass123!')


@pytest.fixture
def sala(db):
    empresa = _user('sm_empresa', 'empresa')
    dev = _user('sm_dev', 'desarrollador')
    admin = _user('sm_admin', 'administrador')
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo='Proyecto en Sala', descripcion='D',
        tipo_solucion='sitio_web', prioridad='alta', vacantes=1,
        estado='en_disputa',
    )
    contratacion = Contratacion.objects.create(
        proyecto=proyecto, desarrollador=dev, empresa=empresa, estado='en_disputa',
    )
    disputa = Disputa.objects.create(
        proyecto=proyecto, contratacion=contratacion, iniciado_por=dev,
        motivo='Motivo de prueba', estado='abierta',
    )
    return {'empresa': empresa, 'dev': dev, 'admin': admin,
            'proyecto': proyecto, 'contratacion': contratacion, 'disputa': disputa}


def _detalle(d):
    return reverse('disputas:detalle_disputa', args=[d.id])


def _enviar(d):
    return reverse('disputas:enviar_mensaje_disputa', args=[d.id])


class TestAccesoSala:
    @pytest.mark.parametrize('quien', ['empresa', 'dev', 'admin'])
    def test_participantes_acceden(self, client, sala, quien):
        _login(client, sala[quien])
        resp = client.get(_detalle(sala['disputa']))
        assert resp.status_code == 200
        assert 'disputas/sala_mediacion.html' in [t.name for t in resp.templates]
        assert 'Proyecto en Sala' in resp.content.decode()

    def test_otro_dev_403(self, client, sala):
        _login(client, _user('sm_otro_dev', 'desarrollador'))
        assert client.get(_detalle(sala['disputa'])).status_code == 403

    def test_otra_empresa_403(self, client, sala):
        _login(client, _user('sm_otra_empresa', 'empresa'))
        assert client.get(_detalle(sala['disputa'])).status_code == 403

    def test_anonimo_redirige_a_login(self, client, sala):
        resp = client.get(_detalle(sala['disputa']))
        assert resp.status_code == 302
        assert 'login' in resp.url

    def test_disputa_inexistente_404(self, client, sala):
        _login(client, sala['admin'])
        assert client.get(reverse('disputas:detalle_disputa', args=[99999])).status_code == 404


class TestEnvioMensajes:
    @pytest.mark.parametrize('quien', ['empresa', 'dev', 'admin'])
    def test_participantes_envian(self, client, sala, quien):
        _login(client, sala[quien])
        resp = client.post(_enviar(sala['disputa']), {'contenido': 'Hola a todos'})
        assert resp.status_code == 302
        assert resp.url == _detalle(sala['disputa'])
        m = MensajeDisputa.objects.get()
        assert m.emisor == sala[quien]
        assert m.contenido == 'Hola a todos'
        assert m.disputa == sala['disputa']

    def test_tercero_403(self, client, sala):
        _login(client, _user('sm_tercero', 'desarrollador'))
        resp = client.post(_enviar(sala['disputa']), {'contenido': 'Intruso'})
        assert resp.status_code == 403
        assert MensajeDisputa.objects.count() == 0

    def test_otra_empresa_403(self, client, sala):
        _login(client, _user('sm_otra_emp', 'empresa'))
        resp = client.post(_enviar(sala['disputa']), {'contenido': 'Intruso'})
        assert resp.status_code == 403
        assert MensajeDisputa.objects.count() == 0

    def test_anonimo_redirige_a_login(self, client, sala):
        resp = client.post(_enviar(sala['disputa']), {'contenido': 'x'})
        assert resp.status_code == 302
        assert 'login' in resp.url
        assert MensajeDisputa.objects.count() == 0

    def test_get_no_permitido(self, client, sala):
        _login(client, sala['dev'])
        assert client.get(_enviar(sala['disputa'])).status_code == 405

    @pytest.mark.parametrize('contenido', ['', '   ', '\n\t '])
    def test_contenido_vacio_rechazado(self, client, sala, contenido):
        _login(client, sala['dev'])
        resp = client.post(_enviar(sala['disputa']), {'contenido': contenido})
        assert resp.status_code == 400
        assert MensajeDisputa.objects.count() == 0

    @pytest.mark.parametrize('estado', ['resuelta', 'cancelada'])
    def test_disputa_cerrada_no_admite_mensajes(self, client, sala, estado):
        Disputa.objects.filter(pk=sala['disputa'].pk).update(estado=estado)
        _login(client, sala['admin'])
        resp = client.post(_enviar(sala['disputa']), {'contenido': 'Tarde'})
        assert resp.status_code == 400
        assert MensajeDisputa.objects.count() == 0

    def test_contenido_se_recorta(self, client, sala):
        _login(client, sala['dev'])
        client.post(_enviar(sala['disputa']), {'contenido': '  hola  '})
        assert MensajeDisputa.objects.get().contenido == 'hola'


class TestTransicionMediacion:
    def test_admin_en_abierta_pasa_a_mediacion_y_se_asigna(self, client, sala):
        _login(client, sala['admin'])
        client.post(_enviar(sala['disputa']), {'contenido': 'Soy el mediador'})
        sala['disputa'].refresh_from_db()
        assert sala['disputa'].estado == 'en_mediacion'
        assert sala['disputa'].mediador == sala['admin']

    def test_admin_no_reemplaza_mediador_existente(self, client, sala):
        otro_admin = _user('sm_admin2', 'administrador')
        Disputa.objects.filter(pk=sala['disputa'].pk).update(mediador=otro_admin)
        _login(client, sala['admin'])
        client.post(_enviar(sala['disputa']), {'contenido': 'Hola'})
        sala['disputa'].refresh_from_db()
        assert sala['disputa'].estado == 'en_mediacion'
        assert sala['disputa'].mediador == otro_admin

    @pytest.mark.parametrize('quien', ['empresa', 'dev'])
    def test_no_admin_no_cambia_estado(self, client, sala, quien):
        _login(client, sala[quien])
        client.post(_enviar(sala['disputa']), {'contenido': 'Hola'})
        sala['disputa'].refresh_from_db()
        assert sala['disputa'].estado == 'abierta'
        assert sala['disputa'].mediador is None

    def test_admin_en_mediacion_mantiene_estado(self, client, sala):
        Disputa.objects.filter(pk=sala['disputa'].pk).update(
            estado='en_mediacion', mediador=sala['admin'])
        _login(client, sala['admin'])
        resp = client.post(_enviar(sala['disputa']), {'contenido': 'Seguimos'})
        assert resp.status_code == 302
        sala['disputa'].refresh_from_db()
        assert sala['disputa'].estado == 'en_mediacion'


class TestNotificaciones:
    def _destinatarios(self, sala):
        return set(
            Notificacion.objects.filter(proyecto=sala['proyecto'], tipo='mensaje')
            .values_list('usuario__username', flat=True)
        )

    def test_empresa_notifica_dev_y_admins(self, client, sala):
        _login(client, sala['empresa'])
        client.post(_enviar(sala['disputa']), {'contenido': 'Hola'})
        admins = set(User.objects.filter(rol='administrador').values_list('username', flat=True))
        assert 'sm_admin' in admins
        assert self._destinatarios(sala) == {'sm_dev'} | admins

    def test_dev_notifica_empresa_y_admins(self, client, sala):
        _login(client, sala['dev'])
        client.post(_enviar(sala['disputa']), {'contenido': 'Hola'})
        admins = set(User.objects.filter(rol='administrador').values_list('username', flat=True))
        assert 'sm_admin' in admins
        assert self._destinatarios(sala) == {'sm_empresa'} | admins

    def test_admin_notifica_empresa_y_dev(self, client, sala):
        _login(client, sala['admin'])
        client.post(_enviar(sala['disputa']), {'contenido': 'Hola'})
        assert self._destinatarios(sala) == {'sm_empresa', 'sm_dev'}

    def test_con_mediador_asignado_solo_notifica_al_mediador(self, client, sala):
        _user('sm_admin_ajeno', 'administrador')
        Disputa.objects.filter(pk=sala['disputa'].pk).update(
            estado='en_mediacion', mediador=sala['admin'])
        _login(client, sala['dev'])
        client.post(_enviar(sala['disputa']), {'contenido': 'Hola'})
        assert self._destinatarios(sala) == {'sm_empresa', 'sm_admin'}

    def test_emisor_no_se_autonotifica(self, client, sala):
        _login(client, sala['dev'])
        client.post(_enviar(sala['disputa']), {'contenido': 'Hola'})
        assert 'sm_dev' not in self._destinatarios(sala)

    def test_rechazo_no_genera_notificaciones(self, client, sala):
        _login(client, sala['dev'])
        client.post(_enviar(sala['disputa']), {'contenido': '  '})
        assert Notificacion.objects.filter(tipo='mensaje').count() == 0


class TestAuditoriaMensajes:
    """SCRUM-234 (RF 10.2.1): trazabilidad de mensajes sin guardar el contenido."""

    CONTENIDO = 'TEXTO_CONFIDENCIAL_SALA_XYZ'

    def test_envio_http_registra_log_auditoria(self, client, sala):
        _login(client, sala['dev'])
        client.post(_enviar(sala['disputa']), {'contenido': self.CONTENIDO})

        log = LogAuditoria.objects.get(tabla_afectada='mensajes_disputa')
        assert log.registro_id == sala['disputa'].id
        assert log.usuario == sala['dev']
        assert 'HTTP' in log.accion

    def test_log_no_almacena_el_contenido_del_mensaje(self, client, sala):
        _login(client, sala['dev'])
        client.post(_enviar(sala['disputa']), {'contenido': self.CONTENIDO})

        log = LogAuditoria.objects.get(tabla_afectada='mensajes_disputa')
        for valor in (log.accion, log.valor_anterior, log.valor_nuevo):
            assert self.CONTENIDO not in (valor or '')
        # El mensaje sí se persiste en su propia tabla.
        assert MensajeDisputa.objects.filter(contenido=self.CONTENIDO).exists()

    def test_cada_mensaje_genera_su_propio_log(self, client, sala):
        _login(client, sala['empresa'])
        client.post(_enviar(sala['disputa']), {'contenido': 'primero'})
        _login(client, sala['dev'])
        client.post(_enviar(sala['disputa']), {'contenido': 'segundo'})

        logs = LogAuditoria.objects.filter(tabla_afectada='mensajes_disputa').order_by('pk')
        assert [l.usuario_id for l in logs] == [sala['empresa'].id, sala['dev'].id]

    @pytest.mark.parametrize('contenido', ['', '   '])
    def test_mensaje_rechazado_no_audita(self, client, sala, contenido):
        _login(client, sala['dev'])
        resp = client.post(_enviar(sala['disputa']), {'contenido': contenido})
        assert resp.status_code == 400
        assert LogAuditoria.objects.filter(tabla_afectada='mensajes_disputa').count() == 0


class TestRenderHistorial:
    def test_historial_cronologico_con_rol(self, client, sala):
        d = sala['disputa']
        MensajeDisputa.objects.create(disputa=d, emisor=sala['dev'], contenido='PRIMERO_DEV')
        MensajeDisputa.objects.create(disputa=d, emisor=sala['empresa'], contenido='SEGUNDO_EMPRESA')
        MensajeDisputa.objects.create(disputa=d, emisor=sala['admin'], contenido='TERCERO_ADMIN')
        _login(client, sala['empresa'])
        content = client.get(_detalle(d)).content.decode()
        i1 = content.index('PRIMERO_DEV')
        i2 = content.index('SEGUNDO_EMPRESA')
        i3 = content.index('TERCERO_ADMIN')
        assert i1 < i2 < i3
        assert 'Mediador Admin' in content
        assert 'Desarrollador' in content
        assert 'Empresa' in content

    def test_formulario_visible_si_activa(self, client, sala):
        _login(client, sala['dev'])
        content = client.get(_detalle(sala['disputa'])).content.decode()
        assert 'name="contenido"' in content
        assert 'csrfmiddlewaretoken' in content

    @pytest.mark.parametrize('estado', ['resuelta', 'cancelada'])
    def test_formulario_oculto_si_cerrada(self, client, sala, estado):
        Disputa.objects.filter(pk=sala['disputa'].pk).update(estado=estado)
        _login(client, sala['dev'])
        content = client.get(_detalle(sala['disputa'])).content.decode()
        assert 'name="contenido"' not in content

    def test_resuelta_muestra_dictamen(self, client, sala):
        from django.utils import timezone
        Disputa.objects.filter(pk=sala['disputa'].pk).update(
            estado='resuelta', resolucion='reanudar_proyecto',
            notas_resolucion='DICTAMEN_FINAL', fecha_resolucion=timezone.now())
        _login(client, sala['empresa'])
        content = client.get(_detalle(sala['disputa'])).content.decode()
        assert 'DICTAMEN_FINAL' in content
