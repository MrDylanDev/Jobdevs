"""Tests unitarios del servicio cancelar_contratacion (SCRUM-156, Fase 2)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from contrataciones.models import Contratacion
from contrataciones.services import cancelar_contratacion
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


class TestCancelarContratacion:

    def test_cancela_notifica_y_audita(self, empresa_user, proyecto, contrato, desarrollador_user):
        resultado = cancelar_contratacion(contrato.id, empresa_user)

        assert resultado.estado == 'cancelada'
        assert Notificacion.objects.filter(
            usuario=desarrollador_user, proyecto=proyecto, tipo='alerta'
        ).exists()
        assert LogAuditoria.objects.filter(
            usuario=empresa_user, tabla_afectada='contrataciones', registro_id=contrato.id
        ).exists()

    def test_reabre_el_proyecto_si_era_la_ultima_contratacion(self, empresa_user, proyecto, contrato):
        cancelar_contratacion(contrato.id, empresa_user)

        proyecto.refresh_from_db()
        assert proyecto.estado == 'publicado'

    def test_no_reabre_el_proyecto_si_quedan_contratos_activos(
        self, empresa_user, proyecto, contrato
    ):
        otro_dev = User.objects.create_user(
            username='dev_activo_c', email='dev_activo_c@test.jobdevs',
            nombre='Dev Activo', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=otro_dev, empresa=empresa_user, estado='activa',
        )

        cancelar_contratacion(contrato.id, empresa_user)

        proyecto.refresh_from_db()
        assert proyecto.estado == 'en_desarrollo'

    def test_libera_la_vacante_si_quedan_cupos(self, empresa_user, proyecto, contrato):
        """RF 3.4.1: con vacantes libres el proyecto vuelve a la vitrina."""
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

        cancelar_contratacion(contrato.id, empresa_user)

        proyecto.refresh_from_db()
        assert proyecto.estado == 'publicado'
        assert proyecto.vacantes_disponibles == 1

    def test_rechaza_contrato_ya_cancelado(self, empresa_user, contrato):
        contrato.estado = 'cancelada'
        contrato.save()

        with pytest.raises(ValidationError) as exc:
            cancelar_contratacion(contrato.id, empresa_user)

        assert 'contratos activos' in str(exc.value)

    def test_permission_denied_para_otra_empresa(self, db, contrato):
        intruso = User.objects.create_user(
            username='intruso_c', email='intruso_c@test.jobdevs',
            nombre='Intruso C', rol='empresa', estado='activo',
            password='TestPass123!',
        )

        with pytest.raises(PermissionDenied):
            cancelar_contratacion(contrato.id, intruso)

        contrato.refresh_from_db()
        assert contrato.estado == 'activa'

    def test_permission_denied_para_desarrollador(self, desarrollador_user, contrato):
        with pytest.raises(PermissionDenied):
            cancelar_contratacion(contrato.id, desarrollador_user)
