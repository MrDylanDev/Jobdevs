"""Operaciones de negocio de la app postulaciones (SCRUM-156, Fase 2).

Patrón de la capa de servicios:
- una transacción (`transaction.atomic`) por operación;
- los recursos compartidos (cupos de vacantes) se bloquean con
  `select_for_update` para cerrar las race conditions;
- los fallos se comunican con `PermissionDenied` / `ValidationError`,
  nunca con mensajes de Django ni redirects: eso lo decide la vista;
- la autorización se consulta en `postulaciones/policies.py`.

Las vistas quedan reducidas a: validar sesión/rol, parsear el input, llamar
al servicio y traducir la excepción en un mensaje para el usuario.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from contrataciones.models import Contratacion
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import Proyecto

from .models import ConfiguracionNegociacion, Postulacion
from .policies import puede_rechazar_postulacion


def obtener_plazo_negociacion_dias():
    configuracion, _ = ConfiguracionNegociacion.objects.get_or_create(pk=1)
    return configuracion.plazo_dias


def actualizar_plazo_negociacion_dias(nuevo_plazo, ejecutado_por):
    if ejecutado_por.rol != 'administrador':
        raise PermissionDenied('Solo un administrador puede cambiar este plazo.')

    with transaction.atomic():
        configuracion, _ = ConfiguracionNegociacion.objects.select_for_update().get_or_create(pk=1)
        anterior = configuracion.plazo_dias
        configuracion.plazo_dias = nuevo_plazo
        configuracion.full_clean()
        configuracion.save(update_fields=['plazo_dias', 'actualizado_en'])
        if anterior != nuevo_plazo:
            LogAuditoria.objects.create(
                usuario=ejecutado_por,
                accion='Actualizó el plazo global de negociación',
                tabla_afectada='configuracion_negociacion',
                registro_id=1,
                valor_anterior=f'plazo_dias={anterior}',
                valor_nuevo=f'plazo_dias={nuevo_plazo}',
            )
        return configuracion


def aceptar_postulacion(postulacion_id, ejecutado_por):
    """Bloquea el antiguo acceso directo, incluso para llamadas fuera de la vista."""
    if not Postulacion.objects.filter(
        id=postulacion_id, proyecto__empresa=ejecutado_por,
    ).exists():
        raise PermissionDenied('No tienes autorización sobre esta postulación.')
    raise ValidationError('La contratación requiere ambas firmas; inicia la negociación.')


def expirar_negociacion(postulacion_id):
    """Expira una postulación en negociación vencida y libera el cupo (RF 8.1.2 / SCRUM-217).

    - Bloquea la fila de la postulación dentro de una transacción.
    - Cambia postulacion.estado = 'rechazada'.
    - Si existe ContratoDigital asociado, cambia estado = 'expirado'.
    - Notifica a ambas partes (empresa y desarrollador).
    - Registra auditoría en LogAuditoria.
    """
    with transaction.atomic():
        try:
            postulacion = (
                Postulacion.objects.select_for_update()
                .select_related('proyecto', 'desarrollador', 'proyecto__empresa')
                .get(id=postulacion_id)
            )
        except Postulacion.DoesNotExist:
            return False

        if postulacion.estado != 'en_negociacion':
            return False

        from contrataciones.models import ContratoDigital
        try:
            contrato = ContratoDigital.objects.select_for_update().get(postulacion_id=postulacion.id)
            if contrato.estado == 'firmado':
                # Ya fue firmado concurrentemente por ambas partes
                return False
            if contrato.estado in ('borrador', 'pendiente_firma'):
                contrato.estado = 'expirado'
                contrato.save(update_fields=['estado', 'fecha_actualizacion'])
        except ContratoDigital.DoesNotExist:
            pass

        postulacion.estado = 'rechazada'
        postulacion.save(update_fields=['estado'])

        # Notificar al desarrollador
        Notificacion.objects.create(
            usuario=postulacion.desarrollador,
            proyecto=postulacion.proyecto,
            tipo='alerta',
            mensaje=(
                f"El plazo para formalizar la negociación del proyecto "
                f"'{postulacion.proyecto.titulo}' ha expirado."
            ),
        )

        # Notificar a la empresa
        if postulacion.proyecto.empresa:
            Notificacion.objects.create(
                usuario=postulacion.proyecto.empresa,
                proyecto=postulacion.proyecto,
                tipo='alerta',
                mensaje=(
                    f"La negociación con {postulacion.desarrollador.nombre or postulacion.desarrollador.username} "
                    f"para el proyecto '{postulacion.proyecto.titulo}' ha expirado por superar el límite de tiempo."
                ),
            )

        LogAuditoria.objects.create(
            usuario=postulacion.proyecto.empresa,
            accion=(
                f"Expiró negociación de {postulacion.desarrollador.username} "
                f"en {postulacion.proyecto.titulo} por límite de tiempo"
            )[:300],
            tabla_afectada='postulaciones',
            registro_id=postulacion.id,
        )

        return True


def expirar_negociaciones_vencidas(referencia_tiempo=None):
    """Busca todas las postulaciones en negociación cuya fecha límite haya vencido y las expira.

    Retorna la cantidad de negociaciones expiradas.
    """
    ahora = referencia_tiempo or timezone.now()
    vencidas_ids = list(
        Postulacion.objects.filter(
            estado='en_negociacion',
            fecha_limite_negociacion__isnull=False,
            fecha_limite_negociacion__lt=ahora,
        ).values_list('id', flat=True)
    )

    expiradas = 0
    for p_id in vencidas_ids:
        if expirar_negociacion(p_id):
            expiradas += 1

    return expiradas


def rechazar_postulacion(postulacion_id, ejecutado_por, motivo=''):
    """Rechaza formalmente una postulación individual por la empresa (SCRUM-310).

    - Bloquea la postulación dentro de una transacción con select_for_update.
    - Valida autorización con puede_rechazar_postulacion.
    - Si existe un contrato digital asociado en borrador o pendiente de firma, se pasa a 'rechazado'.
    - Notifica al desarrollador sobre el rechazo.
    - Registra auditoría en LogAuditoria.
    """
    with transaction.atomic():
        try:
            postulacion = (
                Postulacion.objects.select_for_update()
                .select_related('proyecto', 'desarrollador', 'proyecto__empresa')
                .get(id=postulacion_id)
            )
        except Postulacion.DoesNotExist:
            raise ValidationError('La postulación no existe.')

        if not puede_rechazar_postulacion(ejecutado_por, postulacion):
            raise PermissionDenied('No tienes autorización para rechazar esta postulación.')

        postulacion.estado = 'rechazada'
        postulacion.save(update_fields=['estado'])

        from contrataciones.models import ContratoDigital
        try:
            contrato = ContratoDigital.objects.select_for_update().get(postulacion_id=postulacion.id)
            if contrato.estado in ('borrador', 'pendiente_firma'):
                contrato.estado = 'rechazado'
                contrato.save(update_fields=['estado', 'fecha_actualizacion'])
        except ContratoDigital.DoesNotExist:
            pass

        mensaje_notif = (
            f"Tu postulación al proyecto '{postulacion.proyecto.titulo}' "
            f"no ha sido seleccionada por la empresa."
        )
        if motivo.strip():
            mensaje_notif += f" Motivo: {motivo.strip()}"

        Notificacion.objects.create(
            usuario=postulacion.desarrollador,
            proyecto=postulacion.proyecto,
            tipo='alerta',
            mensaje=mensaje_notif[:500],
        )

        LogAuditoria.objects.create(
            usuario=ejecutado_por,
            accion=(
                f"Rechazó postulación de {postulacion.desarrollador.username} "
                f"en {postulacion.proyecto.titulo}"
            )[:300],
            tabla_afectada='postulaciones',
            registro_id=postulacion.id,
        )

        return True
