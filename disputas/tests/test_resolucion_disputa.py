from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models.query import QuerySet
from django.urls import reverse

from contrataciones.models import Contratacion
from disputas.models import Disputa
from disputas.services import resolver_disputa
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import HistorialEstadoProyecto, Proyecto, Entregable
from avances.models import Avance

User = get_user_model()

DICTAMEN = 'Tras revisar las pruebas, el mediador decide lo siguiente.'


def _user(username, rol):
    return User.objects.create_user(
        username=username, email=f'{username}@test.jobdevs', nombre=username,
        rol=rol, estado='activo', password='TestPass123!',
    )


def _login(client, user):
    client.login(username=user.username, password='TestPass123!')


@pytest.fixture
def caso(db):
    empresa = _user('rd_empresa', 'empresa')
    dev = _user('rd_dev', 'desarrollador')
    admin = _user('rd_admin', 'administrador')
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo='Proyecto Disputado', descripcion='D',
        tipo_solucion='sitio_web', prioridad='alta', vacantes=1,
        estado='en_disputa',
    )
    contratacion = Contratacion.objects.create(
        proyecto=proyecto, desarrollador=dev, empresa=empresa, estado='en_disputa',
    )
    disputa = Disputa.objects.create(
        proyecto=proyecto, contratacion=contratacion, iniciado_por=dev,
        motivo='Motivo de prueba', estado='en_mediacion',
    )
    return {'empresa': empresa, 'dev': dev, 'admin': admin, 'proyecto': proyecto,
            'contratacion': contratacion, 'disputa': disputa}


def _url(d):
    return reverse('disputas:resolver_disputa', args=[d.id])


def _post(client, caso, resolucion='reanudar_proyecto', dictamen=DICTAMEN):
    return client.post(_url(caso['disputa']), {'resolucion': resolucion, 'dictamen': dictamen})


def _refrescar(caso):
    for k in ('empresa', 'dev', 'proyecto', 'contratacion', 'disputa'):
        caso[k].refresh_from_db()


class TestPermisos:
    @pytest.mark.parametrize('quien', ['empresa', 'dev'])
    def test_no_admin_recibe_403(self, client, caso, quien):
        _login(client, caso[quien])
        resp = _post(client, caso)
        assert resp.status_code == 403
        _refrescar(caso)
        assert caso['disputa'].estado == 'en_mediacion'
        assert caso['proyecto'].estado == 'en_disputa'

    def test_servicio_rechaza_no_admin(self, caso):
        with pytest.raises(PermissionDenied):
            resolver_disputa(caso['disputa'], caso['empresa'], 'reanudar_proyecto', DICTAMEN)

    def test_anonimo_redirige_a_login(self, client, caso):
        resp = _post(client, caso)
        assert resp.status_code == 302
        assert 'login' in resp['Location']

    def test_get_no_permitido(self, client, caso):
        _login(client, caso['admin'])
        assert client.get(_url(caso['disputa'])).status_code == 405


class TestValidaciones:
    def test_disputa_ya_resuelta_devuelve_400(self, client, caso):
        _login(client, caso['admin'])
        assert _post(client, caso).status_code == 302
        resp = _post(client, caso, 'sancionar_empresa')
        assert resp.status_code == 400
        assert 'ya fue resuelta' in resp.content.decode()
        _refrescar(caso)
        assert caso['disputa'].resolucion == 'reanudar_proyecto'
        assert caso['empresa'].estado == 'activo'

    def test_servicio_disputa_resuelta_lanza_validation_error(self, caso):
        resolver_disputa(caso['disputa'], caso['admin'], 'reanudar_proyecto', DICTAMEN)
        with pytest.raises(ValidationError):
            resolver_disputa(caso['disputa'], caso['admin'], 'cancelar_contrato', DICTAMEN)

    @pytest.mark.parametrize('dictamen', ['', '   '])
    def test_dictamen_vacio_devuelve_400(self, client, caso, dictamen):
        _login(client, caso['admin'])
        resp = _post(client, caso, dictamen=dictamen)
        assert resp.status_code == 400
        _refrescar(caso)
        assert caso['disputa'].estado == 'en_mediacion'
        assert caso['proyecto'].estado == 'en_disputa'

    @pytest.mark.parametrize('resolucion', ['', 'inventada'])
    def test_resolucion_invalida_devuelve_400(self, client, caso, resolucion):
        _login(client, caso['admin'])
        resp = _post(client, caso, resolucion=resolucion)
        assert resp.status_code == 400
        _refrescar(caso)
        assert caso['disputa'].estado == 'en_mediacion'
        assert caso['contratacion'].estado == 'en_disputa'

    def test_servicio_valida_dictamen_y_resolucion(self, caso):
        with pytest.raises(ValidationError):
            resolver_disputa(caso['disputa'], caso['admin'], 'reanudar_proyecto', '')
        with pytest.raises(ValidationError):
            resolver_disputa(caso['disputa'], caso['admin'], 'x', DICTAMEN)


class TestComunes:
    def _resolver(self, client, caso, resolucion):
        _login(client, caso['admin'])
        resp = _post(client, caso, resolucion)
        assert resp.status_code == 302
        assert resp['Location'] == reverse('disputas:detalle_disputa', args=[caso['disputa'].id])
        _refrescar(caso)

    @pytest.mark.parametrize('resolucion', [
        'reanudar_proyecto', 'cancelar_contrato', 'sancionar_empresa', 'sancionar_desarrollador',
    ])
    def test_actualiza_disputa_auditoria_y_notificaciones(self, client, caso, resolucion):
        self._resolver(client, caso, resolucion)
        d = caso['disputa']
        assert d.estado == 'resuelta'
        assert d.resolucion == resolucion
        assert d.notas_resolucion == DICTAMEN
        assert d.fecha_resolucion is not None
        assert d.mediador == caso['admin']

        log = LogAuditoria.objects.get(tabla_afectada='disputas', registro_id=d.id)
        assert log.usuario == caso['admin']

        destinos = set(
            Notificacion.objects.filter(proyecto=caso['proyecto'])
            .values_list('usuario_id', flat=True)
        )
        assert destinos == {caso['empresa'].pk, caso['dev'].pk}


class TestReanudar:
    def test_reanudar_proyecto(self, client, caso):
        _login(client, caso['admin'])
        _post(client, caso, 'reanudar_proyecto')
        _refrescar(caso)
        assert caso['proyecto'].estado == 'en_desarrollo'
        assert caso['contratacion'].estado == 'activa'
        assert HistorialEstadoProyecto.objects.filter(
            proyecto=caso['proyecto'], estado_anterior='en_disputa',
            estado_nuevo='en_desarrollo', cambiado_por=caso['admin'],
        ).exists()
        assert caso['empresa'].is_active and caso['dev'].is_active


class TestCancelar:
    def test_cancelar_contrato(self, client, caso):
        _login(client, caso['admin'])
        _post(client, caso, 'cancelar_contrato')
        _refrescar(caso)
        assert caso['contratacion'].estado == 'cancelada'
        assert caso['proyecto'].estado == 'en_desarrollo'
        assert HistorialEstadoProyecto.objects.filter(
            proyecto=caso['proyecto'], estado_nuevo='en_desarrollo',
        ).exists()
        assert caso['empresa'].is_active and caso['dev'].is_active


class TestSancionEmpresa:
    def test_sancionar_empresa(self, client, caso):
        _login(client, caso['admin'])
        _post(client, caso, 'sancionar_empresa')
        _refrescar(caso)
        assert caso['contratacion'].estado == 'cancelada'
        assert caso['proyecto'].estado == 'inactivo'
        assert caso['empresa'].estado == 'suspendido'
        assert caso['empresa'].is_active is False
        assert caso['dev'].estado == 'activo' and caso['dev'].is_active
        assert HistorialEstadoProyecto.objects.filter(
            proyecto=caso['proyecto'], estado_nuevo='inactivo',
        ).exists()


class TestSancionDesarrollador:
    def test_sancionar_desarrollador(self, client, caso):
        _login(client, caso['admin'])
        _post(client, caso, 'sancionar_desarrollador')
        _refrescar(caso)
        assert caso['contratacion'].estado == 'cancelada'
        assert caso['proyecto'].estado == 'en_desarrollo'
        assert caso['dev'].estado == 'suspendido'
        assert caso['dev'].is_active is False
        assert caso['empresa'].estado == 'activo' and caso['empresa'].is_active


class TestAtomicidad:
    def test_usa_select_for_update(self, caso):
        llamadas = []
        original = QuerySet.select_for_update

        def espia(self, *a, **kw):
            llamadas.append(self.model.__name__)
            return original(self, *a, **kw)

        with mock.patch.object(QuerySet, 'select_for_update', espia):
            resolver_disputa(caso['disputa'], caso['admin'], 'sancionar_empresa', DICTAMEN)
        assert {'Disputa', 'Proyecto', 'Contratacion'} <= set(llamadas)

    def test_rollback_si_falla_a_mitad(self, caso):
        with mock.patch(
            'disputas.services.Notificacion.objects.bulk_create',
            side_effect=RuntimeError('boom'),
        ):
            with pytest.raises(RuntimeError):
                resolver_disputa(caso['disputa'], caso['admin'], 'sancionar_empresa', DICTAMEN)
        _refrescar(caso)
        assert caso['disputa'].estado == 'en_mediacion'
        assert caso['proyecto'].estado == 'en_disputa'
        assert caso['contratacion'].estado == 'en_disputa'
        assert caso['empresa'].is_active and caso['empresa'].estado == 'activo'
        assert not LogAuditoria.objects.filter(tabla_afectada='disputas').exists()


class TestTemplate:
    def test_admin_ve_formulario_si_abierta(self, client, caso):
        _login(client, caso['admin'])
        content = client.get(reverse('disputas:detalle_disputa', args=[caso['disputa'].id])).content.decode()
        assert 'Emitir Resolución Vinculante' in content
        assert 'name="dictamen"' in content
        assert 'sancionar_desarrollador' in content
        assert _url(caso['disputa']) in content

    @pytest.mark.parametrize('quien', ['empresa', 'dev'])
    def test_no_admin_no_ve_formulario(self, client, caso, quien):
        _login(client, caso[quien])
        content = client.get(reverse('disputas:detalle_disputa', args=[caso['disputa'].id])).content.decode()
        assert 'Emitir Resolución Vinculante' not in content

    def test_formulario_oculto_si_resuelta(self, client, caso):
        Disputa.objects.filter(pk=caso['disputa'].pk).update(estado='resuelta')
        _login(client, caso['admin'])
        content = client.get(reverse('disputas:detalle_disputa', args=[caso['disputa'].id])).content.decode()
        assert 'Emitir Resolución Vinculante' not in content


class TestEfectosColateralesResolucion:
    """Pruebas de efectos colaterales de resolución de disputas sobre avances e hitos (SCRUM-218)."""

    def test_cancelar_contrato_limpia_avances_y_hitos_en_revision(self, caso):
        """Al cancelar contrato, los avances pendientes se rechazan y los hitos en revisión vuelven a pendiente."""
        hito = Entregable.objects.create(
            proyecto=caso['proyecto'], titulo='Hito Disputado', estado='en_revision'
        )
        avance = Avance.objects.create(
            proyecto=caso['proyecto'], entregable=hito, desarrollador=caso['dev'],
            estado='pendiente', descripcion='Avance en conflicto',
        )

        resolver_disputa(caso['disputa'], caso['admin'], 'cancelar_contrato', DICTAMEN)

        avance.refresh_from_db()
        hito.refresh_from_db()

        assert avance.estado == 'rechazado'
        assert 'resolución de disputa' in avance.comentario_revision.lower()
        assert hito.estado == 'pendiente'

    def test_sancionar_desarrollador_limpia_avances_y_hitos_en_revision(self, caso):
        """Al sancionar desarrollador, los avances pendientes se rechazan y los hitos vuelven a pendiente."""
        hito = Entregable.objects.create(
            proyecto=caso['proyecto'], titulo='Hito Sanción', estado='en_revision'
        )
        avance = Avance.objects.create(
            proyecto=caso['proyecto'], entregable=hito, desarrollador=caso['dev'],
            estado='pendiente', descripcion='Avance no completado',
        )

        resolver_disputa(caso['disputa'], caso['admin'], 'sancionar_desarrollador', DICTAMEN)

        avance.refresh_from_db()
        hito.refresh_from_db()

        assert avance.estado == 'rechazado'
        assert hito.estado == 'pendiente'
        assert caso['dev'].refresh_from_db() or caso['dev'].estado == 'suspendido'

    def test_reanudar_proyecto_conserva_avances_pendientes(self, caso):
        """Al reanudar proyecto, los avances pendientes se conservan intactos."""
        hito = Entregable.objects.create(
            proyecto=caso['proyecto'], titulo='Hito Reanudado', estado='en_revision'
        )
        avance = Avance.objects.create(
            proyecto=caso['proyecto'], entregable=hito, desarrollador=caso['dev'],
            estado='pendiente', descripcion='Avance preservado',
        )

        resolver_disputa(caso['disputa'], caso['admin'], 'reanudar_proyecto', DICTAMEN)

        avance.refresh_from_db()
        hito.refresh_from_db()

        assert avance.estado == 'pendiente'
        assert hito.estado == 'en_revision'

