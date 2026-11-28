"""Pruebas de cancelación tras acuerdo confirmado o revisión administrativa."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from contrataciones.models import Contratacion, SolicitudCancelacion
from contrataciones.services import (
    resolver_solicitud_cancelacion,
    solicitar_cancelacion,
)
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import Proyecto

User = get_user_model()


@pytest.fixture
def proyecto(empresa_user):
    return Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto Contratos', descripcion='D',
        tipo_solucion='sitio_web', estado='en_desarrollo',
    )


@pytest.fixture
def contrato(proyecto, empresa_user, desarrollador_user):
    return Contratacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, empresa=empresa_user, estado='activa',
    )


MOTIVO_TEST = 'Cancelación debidamente justificada por la empresa'


def _aprobar(contrato, empresa, admin):
    solicitud = SolicitudCancelacion.objects.create(
        contratacion=contrato, solicitante=empresa,
        causal='incumplimiento', motivo=MOTIVO_TEST,
        evidencia='Hito sin entrega y seguimiento documentado.',
        estado='pendiente_revision',
    )
    resolver_solicitud_cancelacion(
        solicitud.id, admin, aprobar=True, dictamen='Evidencia del hito revisada.',
    )
    contrato.refresh_from_db()
    return contrato


class TestCancelarContratacion:
    def test_cancela_notifica_y_audita(self, empresa_user, admin_user, proyecto, contrato, desarrollador_user):
        resultado = _aprobar(contrato, empresa_user, admin_user)
        assert resultado.estado == 'cancelada'
        assert resultado.motivo_cancelacion == MOTIVO_TEST
        assert Notificacion.objects.filter(
            usuario=desarrollador_user, proyecto=proyecto, tipo='alerta'
        ).exists()
        log = LogAuditoria.objects.get(
            usuario=admin_user, tabla_afectada='contrataciones', registro_id=contrato.id
        )
        assert log.valor_anterior == 'activa'
        assert log.valor_nuevo == 'cancelada'

    def test_cancelar_sin_motivo_falla_validation_error(self, empresa_user, contrato):
        with pytest.raises(ValidationError) as exc:
            solicitar_cancelacion(contrato.id, empresa_user, causal='acuerdo_mutuo', motivo='')
        assert 'indicar el motivo' in str(exc.value).lower()

    def test_cancelar_motivo_corto_falla_validation_error(self, empresa_user, contrato):
        with pytest.raises(ValidationError) as exc:
            solicitar_cancelacion(contrato.id, empresa_user, causal='acuerdo_mutuo', motivo='Corto')
        assert 'al menos 10 caracteres' in str(exc.value).lower()

    def test_reabre_el_proyecto_si_era_la_ultima_contratacion(self, empresa_user, admin_user, proyecto, contrato):
        _aprobar(contrato, empresa_user, admin_user)
        proyecto.refresh_from_db()
        assert proyecto.estado == 'publicado'

    def test_no_reabre_el_proyecto_si_quedan_contratos_activos(
        self, empresa_user, admin_user, proyecto, contrato,
    ):
        otro_dev = User.objects.create_user(
            username='dev_activo_c', email='dev_activo_c@test.jobdevs',
            nombre='Dev Activo', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=otro_dev, empresa=empresa_user, estado='activa',
        )
        _aprobar(contrato, empresa_user, admin_user)
        proyecto.refresh_from_db()
        assert proyecto.estado == 'en_desarrollo'

    def test_libera_la_vacante_si_quedan_cupos(self, empresa_user, admin_user, proyecto, contrato):
        proyecto.vacantes = 2
        proyecto.save()
        otro_dev = User.objects.create_user(
            username='dev_segundo_c', email='dev_segundo_c@test.jobdevs',
            nombre='Dev Segundo', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=otro_dev, empresa=empresa_user, estado='activa',
        )
        _aprobar(contrato, empresa_user, admin_user)
        proyecto.refresh_from_db()
        assert proyecto.estado == 'publicado'
        assert proyecto.vacantes_disponibles == 1

    def test_rechaza_contrato_ya_cancelado(self, empresa_user, contrato):
        contrato.estado = 'cancelada'
        contrato.save()
        with pytest.raises(ValidationError) as exc:
            solicitar_cancelacion(contrato.id, empresa_user, causal='acuerdo_mutuo', motivo=MOTIVO_TEST)
        assert 'contratos activos' in str(exc.value)

    def test_permission_denied_para_otra_empresa(self, db, contrato):
        intruso = User.objects.create_user(
            username='intruso_c', email='intruso_c@test.jobdevs',
            nombre='Intruso C', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        with pytest.raises(PermissionDenied):
            solicitar_cancelacion(contrato.id, intruso, causal='acuerdo_mutuo', motivo=MOTIVO_TEST)
        contrato.refresh_from_db()
        assert contrato.estado == 'activa'

    def test_desarrollador_titular_puede_proponer_sin_cancelar(self, desarrollador_user, contrato):
        solicitud = solicitar_cancelacion(
            contrato.id, desarrollador_user, causal='acuerdo_mutuo', motivo=MOTIVO_TEST,
        )
        assert solicitud.solicitante == desarrollador_user
        assert solicitud.estado == 'pendiente_acuerdo'
        contrato.refresh_from_db()
        assert contrato.estado == 'activa'
