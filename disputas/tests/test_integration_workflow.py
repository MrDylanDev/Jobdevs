import pytest
from django.urls import reverse

from contrataciones.models import Contratacion
from disputas.models import Disputa, MensajeDisputa
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import Proyecto


@pytest.mark.django_db
class TestWorkflowCompletoDisputas:
    """Verifica el ciclo de vida completo de una disputa de extremo a extremo."""

    def test_ciclo_completo_escalamiento_mediacion_y_resolucion(
        self, client, empresa_user, desarrollador_user, admin_user
    ):
        # 1. Setup: Proyecto en desarrollo con contratación activa
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo="E2E Mediación Proyecto",
            descripcion="Descripción proyecto en conflicto",
            estado="en_desarrollo",
            vacantes=1,
        )
        contratacion = Contratacion.objects.create(
            proyecto=proyecto,
            empresa=empresa_user,
            desarrollador=desarrollador_user,
            estado="activa",
        )

        # 2. Desarrollador escala a disputa
        client.force_login(desarrollador_user)
        resp_abrir = client.post(
            reverse("disputas:abrir_disputa", args=[proyecto.pk]),
            {"motivo": "Incumplimiento de términos y falta de retroalimentación."},
        )
        assert resp_abrir.status_code == 302

        # Verificar congelamiento
        proyecto.refresh_from_db()
        contratacion.refresh_from_db()
        assert proyecto.estado == "en_disputa"
        assert contratacion.estado == "en_disputa"

        disputa = Disputa.objects.get(proyecto=proyecto)
        assert disputa.estado == "abierta"
        assert disputa.iniciado_por == desarrollador_user
        assert disputa.contratacion == contratacion

        # 3. Intercambio de mensajes en la sala tripartita
        url_mensaje = reverse("disputas:enviar_mensaje_disputa", args=[disputa.pk])

        # Mensaje del dev
        resp_msg_dev = client.post(
            url_mensaje,
            {"contenido": "Adjunto evidencia de que entregué el sprint a tiempo."},
        )
        assert resp_msg_dev.status_code == 302

        # Mensaje de la empresa
        client.force_login(empresa_user)
        resp_msg_emp = client.post(
            url_mensaje,
            {"contenido": "No cumplió con los estándares de calidad requeridos."},
        )
        assert resp_msg_emp.status_code == 302

        assert MensajeDisputa.objects.filter(disputa=disputa).count() == 2

        # 4. Administrador interviene
        client.force_login(admin_user)
        resp_msg_admin = client.post(
            url_mensaje,
            {"contenido": "Soy el mediador asignado. Revisaré el repositorio y el contrato."},
        )
        assert resp_msg_admin.status_code == 302

        disputa.refresh_from_db()
        assert disputa.estado == "en_mediacion"
        assert disputa.mediador == admin_user

        # 5. Administrador emite resolución vinculante: reanudar proyecto
        url_resolver = reverse("disputas:resolver_disputa", args=[disputa.pk])
        resp_resolver = client.post(
            url_resolver,
            {
                "resolucion": "reanudar_proyecto",
                "dictamen": "Se otorga una prórroga de 5 días para subsanar observaciones de código.",
            },
        )
        assert resp_resolver.status_code == 302

        disputa.refresh_from_db()
        proyecto.refresh_from_db()
        contratacion.refresh_from_db()

        assert disputa.estado == "resuelta"
        assert disputa.resolucion == "reanudar_proyecto"
        assert "prórroga de 5 días" in disputa.notas_resolucion
        assert disputa.fecha_resolucion is not None

        # Acciones automáticas ejecutadas: descongelamiento
        assert proyecto.estado == "en_desarrollo"
        assert contratacion.estado == "activa"

        # Trazabilidad y auditoría
        assert LogAuditoria.objects.filter(
            tabla_afectada="disputas", registro_id=disputa.pk
        ).count() >= 2  # Apertura y resolución

        # 6. Intentar enviar mensaje en disputa resuelta -> debe fallar (400)
        resp_post_cierre = client.post(
            url_mensaje,
            {"contenido": "Mensaje posterior a la resolución."},
        )
        assert resp_post_cierre.status_code == 400
        assert MensajeDisputa.objects.filter(disputa=disputa).count() == 3
