"""Tests unitarios del servicio aceptar_postulacion (SCRUM-156, Fase 2).

Prueban la capa de servicios directamente: transacción, cupos, locks y efectos
secundarios (contratación, equipo, historial, notificación y auditoría).
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from contrataciones.models import Contratacion
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from postulaciones.models import Postulacion
from postulaciones.services import aceptar_postulacion
from proyectos.models import Equipo, HistorialEstadoProyecto, Proyecto

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

    def test_crea_contratacion_equipo_y_estado_en_desarrollo(self, empresa_user, desarrollador_user, postulacion):
        contratacion = aceptar_postulacion(postulacion.id, empresa_user)

        assert contratacion.estado == 'activa'
        assert contratacion.desarrollador_id == desarrollador_user.id
        assert contratacion.empresa_id == empresa_user.id

        postulacion.refresh_from_db()
        assert postulacion.estado == 'aceptada'

        postulacion.proyecto.refresh_from_db()
        assert postulacion.proyecto.estado == 'en_desarrollo'

        assert Equipo.objects.filter(
            proyecto=postulacion.proyecto, miembros=desarrollador_user
        ).exists()

    def test_registra_historial_notificacion_y_auditoria(self, empresa_user, desarrollador_user, postulacion):
        aceptar_postulacion(postulacion.id, empresa_user)

        historial = HistorialEstadoProyecto.objects.get(proyecto=postulacion.proyecto)
        assert historial.estado_nuevo == 'en_desarrollo'
        assert historial.estado_anterior == 'publicado'

        assert Notificacion.objects.filter(
            usuario=desarrollador_user, proyecto=postulacion.proyecto, tipo='aprobacion'
        ).exists()
        assert LogAuditoria.objects.filter(
            usuario=empresa_user, tabla_afectada='postulaciones', registro_id=postulacion.id
        ).exists()

    def test_rechaza_si_no_quedan_vacantes(self, empresa_user, desarrollador_user, proyecto, postulacion):
        # Otra contratación activa ya ocupa la única vacante disponible
        proyecto.vacantes = 1
        proyecto.save()
        otro_dev = User.objects.create_user(
            username='dev_ocupado', email='ocupado@test.jobdevs',
            nombre='Dev Ocupado', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=otro_dev, empresa=empresa_user, estado='activa',
        )

        with pytest.raises(ValidationError) as exc:
            aceptar_postulacion(postulacion.id, empresa_user)

        assert 'vacantes' in str(exc.value)
        # La postulación no cambia de estado (rollback)
        postulacion.refresh_from_db()
        assert postulacion.estado == 'pendiente'
        assert not Contratacion.objects.filter(
            proyecto=proyecto, desarrollador=desarrollador_user
        ).exists()

    def test_rechaza_proyecto_finalizado(self, empresa_user, postulacion):
        proyecto = postulacion.proyecto
        proyecto.estado = 'finalizado'
        proyecto.save()

        with pytest.raises(ValidationError) as exc:
            aceptar_postulacion(postulacion.id, empresa_user)

        assert 'no se pueden aceptar' in str(exc.value).lower()
        assert not Contratacion.objects.filter(proyecto=proyecto).exists()

    def test_rechaza_postulacion_ya_procesada(self, empresa_user, postulacion):
        postulacion.estado = 'rechazada'
        postulacion.save()

        with pytest.raises(ValidationError) as exc:
            aceptar_postulacion(postulacion.id, empresa_user)

        assert 'ya fue procesada' in str(exc.value)

    def test_permission_denied_para_otra_empresa(self, otra_empresa, postulacion):
        with pytest.raises(PermissionDenied):
            aceptar_postulacion(postulacion.id, otra_empresa)

        postulacion.refresh_from_db()
        assert postulacion.estado == 'pendiente'
