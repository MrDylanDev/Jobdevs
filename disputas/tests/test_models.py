import pytest
from django.contrib.auth import get_user_model

from contrataciones.models import Contratacion
from proyectos.models import Proyecto

User = get_user_model()


def _user(username, rol):
    return User.objects.create_user(
        username=username, email=f'{username}@test.jobdevs', nombre=username,
        rol=rol, estado='activo', password='TestPass123!',
    )


@pytest.fixture
def escenario(db):
    empresa = _user('disp_empresa', 'empresa')
    dev = _user('disp_dev', 'desarrollador')
    admin = _user('disp_admin', 'administrador')
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo='P', descripcion='D',
        tipo_solucion='sitio_web', prioridad='alta', vacantes=1,
        estado='en_desarrollo',
    )
    contratacion = Contratacion.objects.create(
        proyecto=proyecto, desarrollador=dev, empresa=empresa,
    )
    return {'empresa': empresa, 'dev': dev, 'admin': admin,
            'proyecto': proyecto, 'contratacion': contratacion}


class TestEstadosCongelamiento:
    def test_proyecto_estado_en_disputa(self):
        assert ('en_disputa', 'En Disputa') in Proyecto.ESTADO

    def test_contratacion_estado_en_disputa(self):
        assert ('en_disputa', 'En Disputa') in Contratacion.ESTADO

    def test_proyecto_puede_guardar_en_disputa(self, escenario):
        p = escenario['proyecto']
        p.estado = 'en_disputa'
        p.save()
        p.refresh_from_db()
        assert p.get_estado_display() == 'En Disputa'


class TestDisputaModel:
    def test_crear_disputa_estado_por_defecto(self, escenario):
        from disputas.models import Disputa
        d = Disputa.objects.create(
            proyecto=escenario['proyecto'],
            contratacion=escenario['contratacion'],
            iniciado_por=escenario['empresa'],
            motivo='Incumplimiento',
        )
        assert d.id is not None
        assert d.estado == 'abierta'
        assert d.mediador is None
        assert d.resolucion in (None, '')

    def test_choices_estado(self):
        from disputas.models import Disputa
        valores = {c[0] for c in Disputa.ESTADO}
        assert valores == {'abierta', 'en_mediacion', 'resuelta', 'cancelada'}

    def test_choices_resolucion(self):
        from disputas.models import Disputa
        valores = {c[0] for c in Disputa.RESOLUCION}
        assert valores == {
            'reanudar_proyecto', 'cancelar_contrato',
            'sancionar_empresa', 'sancionar_desarrollador',
        }

    def test_contratacion_nullable(self, escenario):
        from disputas.models import Disputa
        d = Disputa.objects.create(
            proyecto=escenario['proyecto'],
            iniciado_por=escenario['dev'],
            motivo='x',
        )
        assert d.contratacion is None

    def test_mediador_y_resolucion(self, escenario):
        from disputas.models import Disputa
        d = Disputa.objects.create(
            proyecto=escenario['proyecto'],
            contratacion=escenario['contratacion'],
            iniciado_por=escenario['dev'],
            mediador=escenario['admin'],
            estado='resuelta',
            resolucion='reanudar_proyecto',
            motivo='x',
        )
        d.refresh_from_db()
        assert d.mediador == escenario['admin']
        assert d.resolucion == 'reanudar_proyecto'
        assert d in escenario['admin'].disputas_mediadas.all()
        assert d in escenario['dev'].disputas_iniciadas.all()
        assert d in escenario['proyecto'].disputas.all()


class TestMensajeDisputaModel:
    def test_crear_mensaje(self, escenario):
        from disputas.models import Disputa, MensajeDisputa
        d = Disputa.objects.create(
            proyecto=escenario['proyecto'],
            iniciado_por=escenario['empresa'], motivo='x',
        )
        m = MensajeDisputa.objects.create(
            disputa=d, emisor=escenario['empresa'], contenido='Hola',
        )
        assert m.id is not None
        assert m.fecha_envio is not None
        assert m.disputa == d
        assert m.emisor == escenario['empresa']
        assert list(d.mensajes.all()) == [m]
