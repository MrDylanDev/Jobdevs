"""Tests del servicio heredado de aceptación y del rechazo de postulaciones."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from contrataciones.models import Contratacion
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from postulaciones.models import Postulacion
from postulaciones.services import aceptar_postulacion
from proyectos.models import Proyecto

User = get_user_model()


@pytest.fixture
def proyecto(empresa_user):
    return Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto Servicio', descripcion='D',
        tipo_solucion='sitio_web', estado='publicado', vacantes=2,
    )


@pytest.fixture
def postulacion(proyecto, desarrollador_user):
    return Postulacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, estado='pendiente',
    )


@pytest.fixture
def otra_empresa(db):
    return User.objects.create_user(
        username='otra_empresa_serv', email='otra_serv@test.jobdevs',
        nombre='Otra Empresa', rol='empresa', estado='activo',
        password='TestPass123!',
    )


class TestAceptarPostulacionServicio:
    def test_servicio_heredado_no_crea_contratacion_sin_firma(self, empresa_user, postulacion):
        with pytest.raises(ValidationError, match='firmas'):
            aceptar_postulacion(postulacion.id, empresa_user)

        postulacion.refresh_from_db()
        assert postulacion.estado == 'pendiente'
        assert not Contratacion.objects.filter(proyecto=postulacion.proyecto).exists()

    def test_permission_denied_para_otra_empresa(self, otra_empresa, postulacion):
        with pytest.raises(PermissionDenied):
            aceptar_postulacion(postulacion.id, otra_empresa)

        postulacion.refresh_from_db()
        assert postulacion.estado == 'pendiente'


class TestRechazarPostulacion:
    """Pruebas del servicio rechazar_postulacion (SCRUM-310)."""

    def test_empresa_puede_rechazar_postulacion_pendiente(self, empresa_user, desarrollador_user, postulacion):
        from postulaciones.services import rechazar_postulacion
        res = rechazar_postulacion(postulacion.id, empresa_user)
        assert res is True
        postulacion.refresh_from_db()
        assert postulacion.estado == 'rechazada'
        assert Notificacion.objects.filter(
            usuario=desarrollador_user, tipo='alerta', mensaje__contains='no ha sido seleccionada'
        ).exists()
        assert LogAuditoria.objects.filter(
            tabla_afectada='postulaciones', registro_id=postulacion.id, accion__contains='Rechazó postulación'
        ).exists()

    def test_rechazar_postulacion_en_negociacion_cancela_contrato(self, empresa_user, desarrollador_user, postulacion):
        from contrataciones.models import ContratoDigital
        from postulaciones.services import rechazar_postulacion
        postulacion.estado = 'en_negociacion'
        postulacion.save()
        contrato = ContratoDigital.objects.create(postulacion=postulacion, estado='pendiente_firma')

        rechazar_postulacion(postulacion.id, empresa_user)
        postulacion.refresh_from_db()
        contrato.refresh_from_db()
        assert postulacion.estado == 'rechazada'
        assert contrato.estado == 'rechazado'

    def test_rechazar_postulacion_otra_empresa_lanza_permission_denied(self, otra_empresa, postulacion):
        from postulaciones.services import rechazar_postulacion
        with pytest.raises(PermissionDenied):
            rechazar_postulacion(postulacion.id, otra_empresa)
        postulacion.refresh_from_db()
        assert postulacion.estado == 'pendiente'
