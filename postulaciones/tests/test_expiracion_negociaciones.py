from datetime import timedelta
import pytest
from django.utils import timezone
from django.urls import reverse
from django.core.management import call_command
from django.contrib.auth import get_user_model

from proyectos.models import Proyecto
from postulaciones.models import Postulacion
from contrataciones.models import ContratoDigital
from notificaciones.models import Notificacion
from logs.models import LogAuditoria
from postulaciones.services import expirar_negociaciones_vencidas

User = get_user_model()


@pytest.fixture
def escenario_negociacion(db, empresa_user, desarrollador_user):
    proyecto = Proyecto.objects.create(
        empresa=empresa_user,
        titulo='Proyecto Con Negociación',
        descripcion='Desc',
        tipo_solucion='sitio_web',
        estado='publicado',
        vacantes=1,
    )
    postulacion = Postulacion.objects.create(
        proyecto=proyecto,
        desarrollador=desarrollador_user,
        estado='en_negociacion',
        fecha_limite_negociacion=timezone.now() - timedelta(days=1),
    )
    contrato = ContratoDigital.objects.create(
        postulacion=postulacion,
        estado='pendiente_firma',
    )
    return proyecto, postulacion, contrato


class TestExpiracionNegociaciones:
    """Pruebas del servicio y flujo de expiración de negociaciones vencidas (SCRUM-217)."""

    def test_expirar_negociaciones_vencidas_libera_cupo_y_actualiza_estados(self, escenario_negociacion):
        """RF 8.1.2: Negociaciones con plazo vencido pasan a rechazada, contrato expira y vacante se libera."""
        proyecto, postulacion, contrato = escenario_negociacion

        # Al estar en negociación, no hay cupos libres
        assert proyecto.vacantes_disponibles == 0

        total = expirar_negociaciones_vencidas()
        assert total == 1

        postulacion.refresh_from_db()
        contrato.refresh_from_db()

        assert postulacion.estado == 'rechazada'
        assert contrato.estado == 'expirado'

        # El cupo se libera automáticamente
        assert proyecto.vacantes_disponibles == 1

        # Notificaciones a ambas partes
        assert Notificacion.objects.filter(usuario=postulacion.desarrollador, tipo='alerta').exists()
        assert Notificacion.objects.filter(usuario=proyecto.empresa, tipo='alerta').exists()

        # Registro en LogAuditoria
        assert LogAuditoria.objects.filter(
            tabla_afectada='postulaciones',
            registro_id=postulacion.id,
            accion__contains='Expiró negociación',
        ).exists()

    def test_expirar_negociaciones_no_toca_negociaciones_vigentes(self, db, empresa_user, desarrollador_user):
        """Negociaciones con fecha límite en el futuro no deben ser modificadas."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto Vigente',
            descripcion='Desc',
            tipo_solucion='sitio_web',
            estado='publicado',
            vacantes=1,
        )
        postulacion = Postulacion.objects.create(
            proyecto=proyecto,
            desarrollador=desarrollador_user,
            estado='en_negociacion',
            fecha_limite_negociacion=timezone.now() + timedelta(days=5),
        )
        contrato = ContratoDigital.objects.create(
            postulacion=postulacion,
            estado='pendiente_firma',
        )

        assert proyecto.vacantes_disponibles == 0
        total = expirar_negociaciones_vencidas()
        assert total == 0

        postulacion.refresh_from_db()
        contrato.refresh_from_db()
        assert postulacion.estado == 'en_negociacion'
        assert contrato.estado == 'pendiente_firma'
        assert proyecto.vacantes_disponibles == 0

    def test_firmar_contrato_digital_bloquea_si_fecha_limite_vencio(self, auth_client, escenario_negociacion):
        """Guarda reactiva: al intentar firmar un contrato vencido, se rechaza y expira en el acto."""
        proyecto, postulacion, contrato = escenario_negociacion

        url = reverse('firmar_contrato_digital', args=[contrato.id])
        response = auth_client.post(url, {'acepta_terminos': 'on'}, follow=True)
        assert response.status_code == 200

        contrato.refresh_from_db()
        postulacion.refresh_from_db()

        assert contrato.estado == 'expirado'
        assert postulacion.estado == 'rechazada'
        assert proyecto.vacantes_disponibles == 1
        content = response.content.decode()
        assert 'expirado' in content.lower()

    def test_management_command_expirar_negociaciones(self, escenario_negociacion):
        """El comando de Django ejecuta la expiración y reporta el conteo."""
        proyecto, postulacion, contrato = escenario_negociacion
        call_command('expirar_negociaciones')

        postulacion.refresh_from_db()
        contrato.refresh_from_db()
        assert postulacion.estado == 'rechazada'
        assert contrato.estado == 'expirado'

    def test_celery_task_expirar_negociaciones(self, escenario_negociacion):
        """La tarea de Celery invoca el servicio y retorna el total."""
        from postulaciones.tasks import expirar_negociaciones_vencidas_task
        resultado = expirar_negociaciones_vencidas_task.delay()
        assert resultado.get() == 1
