"""Operaciones de negocio de la app contrataciones (SCRUM-156, Fase 2).

Patrón de la capa de servicios:
- una transacción (`transaction.atomic`) por operación;
- la contratación se bloquea con `select_for_update` para evitar dobles
  cancelaciones por peticiones concurrentes;
- los fallos se comunican con `PermissionDenied` / `ValidationError`;
- la autorización se consulta en `contrataciones/policies.py`.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import Proyecto

from .models import Contratacion
from .policies import puede_cancelar_contratacion


def cancelar_contratacion(contratacion_id, ejecutado_por, motivo=''):
    """Cancela una contratación activa (RF 3.4.1 / SCRUM-223) y reabre el proyecto si era
    la última contratación vigente.

    Devuelve la `Contratacion` cancelada. Lanza `PermissionDenied` si el
    usuario no está autorizado y `ValidationError` si la operación incumple
    una regla de negocio o carece de motivo suficiente.
    """
    motivo = (motivo or '').strip()
    if not motivo:
        raise ValidationError('Debes indicar el motivo de la cancelación.')
    if len(motivo) < 10:
        raise ValidationError('El motivo de cancelación debe tener al menos 10 caracteres.')

    try:
        contexto = Contratacion.objects.select_related('proyecto').get(
            id=contratacion_id
        )
    except Contratacion.DoesNotExist:
        raise PermissionDenied('No tienes autorización sobre este contrato.')

    with transaction.atomic():
        contrato = Contratacion.objects.select_for_update().get(
            id=contexto.id, empresa=contexto.empresa_id
        )

        if not puede_cancelar_contratacion(ejecutado_por, contrato):
            if contrato.empresa_id != getattr(ejecutado_por, 'id', None):
                raise PermissionDenied('No tienes autorización sobre este contrato.')
            raise ValidationError(
                f"Solo se pueden cancelar contratos activos (estado actual: '{contrato.get_estado_display()}')."
            )

        estado_previo = contrato.estado
        contrato.estado = 'cancelada'
        contrato.motivo_cancelacion = motivo
        contrato.save(update_fields=['estado', 'motivo_cancelacion'])

        # RF 3.4.1: la vacante se libera al cancelar. Si el proyecto seguía en
        # desarrollo pero ya tiene cupo libre, vuelve a la vitrina.
        proyecto = Proyecto.objects.select_for_update().get(id=contrato.proyecto_id)
        contratos_restantes = Contratacion.objects.filter(
            proyecto=proyecto, estado='activa'
        ).count()
        if proyecto.estado == 'en_desarrollo' and contratos_restantes < proyecto.vacantes:
            estado_anterior = proyecto.estado
            proyecto.estado = 'publicado'
            proyecto.save()
            proyecto.registrar_cambio_estado(
                'publicado', ejecutado_por, estado_anterior=estado_anterior
            )

        Notificacion.objects.create(
            usuario=contrato.desarrollador,
            proyecto=contrato.proyecto,
            tipo='alerta',
            mensaje=(
                f"Tu contratación para el proyecto '{contrato.proyecto.titulo}' "
                f"ha sido cancelada por la empresa. Motivo: {motivo}"
            )[:500],
        )

        LogAuditoria.objects.create(
            usuario=ejecutado_por,
            accion=f"Canceló contratación en {contrato.proyecto.titulo}: {motivo}"[:300],
            tabla_afectada='contrataciones',
            registro_id=contrato.id,
            valor_anterior=estado_previo,
            valor_nuevo='cancelada',
        )

    return contrato
