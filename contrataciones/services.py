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
from django.utils import timezone

from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import Proyecto

from .models import Contratacion, SolicitudCancelacion
from .policies import es_parte_del_contrato, puede_confirmar_acuerdo


def solicitar_cancelacion(contratacion_id, empresa, causal, motivo, evidencia=''):
    """Cualquiera de las partes propone; solo la contraparte puede aceptar.

    `empresa` conserva el nombre del argumento histórico, pero admite también
    al desarrollador titular. Fuerza mayor no implica incumplimiento.
    """
    if causal in ('incumplimiento', 'inactividad'):
        raise ValidationError('Para una terminación unilateral usa el proceso de disputa.')
    motivo = (motivo or '').strip()
    evidencia = (evidencia or '').strip()
    if causal not in dict(SolicitudCancelacion.CAUSALES):
        raise ValidationError('Selecciona una causal válida.')
    if not motivo:
        raise ValidationError('Debes indicar el motivo de la cancelación.')
    if len(motivo) < 10:
        raise ValidationError('El motivo de cancelación debe tener al menos 10 caracteres.')

    with transaction.atomic():
        contrato = Contratacion.objects.select_for_update().filter(pk=contratacion_id).first()
        if contrato is None or not es_parte_del_contrato(empresa, contrato):
            raise PermissionDenied('No tienes autorización sobre este contrato.')
        if contrato.proyecto.estado == 'en_disputa':
            raise ValidationError('El proyecto está en disputa; espera la resolución antes de proponer un acuerdo.')
        if contrato.estado != 'activa':
            raise ValidationError('Solo se pueden cancelar contratos activos.')
        if SolicitudCancelacion.objects.filter(
            contratacion=contrato, estado__in=['pendiente_acuerdo', 'pendiente_revision'],
        ).exists():
            raise ValidationError('Ya existe una solicitud de cancelación pendiente.')

        estado = 'pendiente_acuerdo'
        solicitud = SolicitudCancelacion.objects.create(
            contratacion=contrato, solicitante=empresa, causal=causal,
            motivo=motivo, evidencia=evidencia, estado=estado,
        )
        destinatarios = [
            contrato.desarrollador_id if empresa.pk == contrato.empresa_id else contrato.empresa_id,
        ]

        Notificacion.objects.bulk_create([
            Notificacion(
                usuario_id=uid, proyecto_id=contrato.proyecto_id, tipo='alerta',
                mensaje=f'Solicitud de cancelación #{solicitud.pk} pendiente de tu confirmación. El contrato sigue activo.',
            )
            for uid in set(destinatarios)
        ])
        LogAuditoria.objects.create(
            usuario=empresa, accion=f'Solicitó cancelación de contratación #{contrato.pk} ({causal})',
            tabla_afectada='solicitudes_cancelacion', registro_id=solicitud.pk,
            valor_nuevo=estado,
        )
    return solicitud


def resolver_solicitud_cancelacion(solicitud_id, ejecutado_por, aprobar, dictamen=''):
    """Decide la contraparte en acuerdos o el admin en expedientes heredados."""
    with transaction.atomic():
        referencia = SolicitudCancelacion.objects.filter(pk=solicitud_id).values(
            'contratacion_id',
        ).first()
        if referencia is None:
            raise PermissionDenied('No tienes autorización sobre esta solicitud.')
        contrato = Contratacion.objects.select_for_update().get(pk=referencia['contratacion_id'])
        solicitud = SolicitudCancelacion.objects.select_for_update().get(pk=solicitud_id)
        if solicitud.contratacion_id != contrato.pk:
            raise ValidationError('La solicitud no pertenece al contrato.')

        es_acuerdo = (
            solicitud.causal == 'acuerdo_mutuo'
            or solicitud.estado == 'pendiente_acuerdo'
        )
        if es_acuerdo:
            if not puede_confirmar_acuerdo(ejecutado_por, contrato, solicitud):
                raise PermissionDenied('Solo la contraparte puede confirmar este acuerdo.')
            esperado = 'pendiente_acuerdo'
        else:
            if getattr(ejecutado_por, 'rol', None) != 'administrador':
                raise PermissionDenied('Solo un administrador puede revisar esta causa.')
            esperado = 'pendiente_revision'
        if solicitud.estado != esperado:
            raise ValidationError('La solicitud ya no está pendiente de decisión.')
        if contrato.estado != 'activa':
            raise ValidationError('El contrato ya no está activo.')
        if contrato.proyecto.estado == 'en_disputa':
            raise ValidationError('El proyecto está en disputa; espera su resolución.')
        dictamen = (dictamen or '').strip()
        if not es_acuerdo and not dictamen:
            raise ValidationError('Indica el dictamen que fundamenta la decisión.')
        if es_acuerdo and not dictamen:
            dictamen = ('Acuerdo confirmado por ambas partes.' if aprobar
                        else 'La contraparte no confirmó el acuerdo.')

        solicitud.estado = 'aprobada' if aprobar else 'rechazada'
        solicitud.resuelto_por = ejecutado_por
        solicitud.dictamen = dictamen
        solicitud.fecha_resolucion = timezone.now()
        solicitud.save(update_fields=['estado', 'resuelto_por', 'dictamen', 'fecha_resolucion'])
        if aprobar:
            cancelar_contratacion(contrato.pk, ejecutado_por, solicitud_id=solicitud.pk)
        for usuario_id in {contrato.empresa_id, contrato.desarrollador_id}:
            Notificacion.objects.create(
                usuario_id=usuario_id, proyecto_id=contrato.proyecto_id, tipo='alerta',
                mensaje=f'Solicitud de cancelación #{solicitud.pk} {solicitud.estado}. {dictamen}'[:500],
            )
        LogAuditoria.objects.create(
            usuario=ejecutado_por,
            accion=f'Resolvió solicitud de cancelación #{solicitud.pk}: {solicitud.estado}',
            tabla_afectada='solicitudes_cancelacion', registro_id=solicitud.pk,
            valor_anterior=esperado, valor_nuevo=solicitud.estado,
        )
    return solicitud


def cancelar_contratacion(contratacion_id, ejecutado_por, motivo='', solicitud_id=None):
    """Formaliza solo solicitudes aprobadas; nunca una cancelación directa.

    Devuelve la `Contratacion` cancelada. Lanza `PermissionDenied` si el
    usuario no resolvió la solicitud y `ValidationError` si sigue pendiente.
    """
    if solicitud_id is None:
        raise ValidationError('La cancelación requiere una solicitud aprobada.')

    try:
        contexto = Contratacion.objects.select_related('proyecto').get(
            id=contratacion_id
        )
    except Contratacion.DoesNotExist as err:
        raise PermissionDenied('No tienes autorización sobre este contrato.') from err

    with transaction.atomic():
        contrato = Contratacion.objects.select_for_update().get(
            id=contexto.id, empresa=contexto.empresa_id
        )
        solicitud = SolicitudCancelacion.objects.select_for_update().filter(
            pk=solicitud_id, contratacion=contrato, estado='aprobada',
            resuelto_por=ejecutado_por,
        ).first()
        if solicitud is None:
            raise PermissionDenied('No tienes autorización sobre esta solicitud.')
        if solicitud.causal == 'acuerdo_mutuo' or (
            solicitud.causal == 'fuerza_mayor' and ejecutado_por.rol != 'administrador'
        ):
            autorizado = puede_confirmar_acuerdo(ejecutado_por, contrato, solicitud)
        else:
            autorizado = ejecutado_por.rol == 'administrador'
        if not autorizado:
            raise PermissionDenied('No puedes formalizar esta cancelación.')
        if contrato.estado != 'activa':
            raise ValidationError(
                f"Solo se pueden cancelar contratos activos (estado actual: '{contrato.get_estado_display()}')."
            )

        motivo = solicitud.motivo
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
                f"ha finalizado tras la aprobación de la solicitud de cancelación. Motivo: {motivo}"
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


def datos_dashboard_cancelaciones(empresa):
    """Datos de la pestaña de cancelaciones del panel de Empresa.

    Replica las reglas de la página histórica para que la empresa no vea dos
    universos distintos: solo contratos activos, fuera de disputa y sin una
    solicitud viva, más el historial completo de sus propias solicitudes.
    """
    solicitudes = SolicitudCancelacion.objects.filter(
        contratacion__empresa=empresa,
    ).select_related(
        'contratacion__proyecto', 'contratacion__desarrollador',
        'solicitante', 'resuelto_por',
    ).order_by('-fecha_creacion')
    contratos = Contratacion.objects.filter(
        empresa=empresa, estado='activa',
    ).exclude(
        proyecto__estado='en_disputa',
    ).exclude(
        solicitudes_cancelacion__estado__in=['pendiente_acuerdo', 'pendiente_revision'],
    ).select_related('proyecto', 'desarrollador').order_by('-fecha_inicio', '-id')

    pendientes = [
        s for s in solicitudes
        if s.estado in ('pendiente_acuerdo', 'pendiente_revision')
    ]

    return {
        'solicitudes_cancelacion': solicitudes,
        'contratos_cancelables': contratos,
        'cancelaciones_pendientes_count': len(pendientes),
    }
