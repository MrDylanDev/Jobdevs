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
from proyectos.models import Proyecto, Equipo

from .models import Postulacion
from .policies import puede_aceptar_postulacion, puede_rechazar_postulacion


def aceptar_postulacion(postulacion_id, ejecutado_por):
    """Acepta una postulación pendiente y crea la contratación (RF 3.3.2).

    Bloquea primero la fila del proyecto para serializar la decisión de
    vacantes y devuelve la `Contratacion` creada.

    Lanza `PermissionDenied` si el usuario no está autorizado y
    `ValidationError` si la operación incumple una regla de negocio.
    """
    try:
        contexto = Postulacion.objects.select_related('proyecto').get(
            id=postulacion_id, proyecto__empresa=ejecutado_por
        )
    except Postulacion.DoesNotExist:
        raise PermissionDenied('No tienes autorización sobre esta postulación.')

    with transaction.atomic():
        # El proyecto se bloquea primero: serializa la decisión de vacantes
        proyecto = Proyecto.objects.select_for_update().get(id=contexto.proyecto_id)
        postulacion = Postulacion.objects.select_for_update().get(
            id=postulacion_id, proyecto=proyecto
        )

        if proyecto.estado not in ('publicado', 'en_desarrollo'):
            raise ValidationError(
                f"No se pueden aceptar postulaciones en un proyecto con estado "
                f"'{proyecto.get_estado_display()}'."
            )
        if postulacion.estado != 'pendiente':
            raise ValidationError('La postulación ya fue procesada o no existe.')
        if not puede_aceptar_postulacion(ejecutado_por, postulacion):
            raise PermissionDenied('No tienes autorización para aceptar esta postulación.')

        # Cupos (RF 3.3.2): contrataciones activas + negociaciones en curso
        contrataciones_activas = Contratacion.objects.filter(
            proyecto=proyecto, estado='activa'
        ).count()
        postulaciones_en_negociacion = Postulacion.objects.filter(
            proyecto=proyecto, estado='en_negociacion'
        ).exclude(id=postulacion.id).count()
        if contrataciones_activas + postulaciones_en_negociacion >= proyecto.vacantes:
            raise ValidationError('El proyecto ya ha alcanzado el límite de vacantes disponibles.')

        contratacion = Contratacion.objects.create(
            proyecto=proyecto,
            desarrollador=postulacion.desarrollador,
            empresa=ejecutado_por,
            estado='activa',
        )

        nombre_equipo = f'Equipo {proyecto.titulo}'[:100]
        equipo, _ = Equipo.objects.get_or_create(
            proyecto=proyecto,
            nombre=nombre_equipo,
            defaults={'nombre': nombre_equipo},
        )
        equipo.miembros.add(postulacion.desarrollador)

        postulacion.estado = 'aceptada'
        postulacion.save()

        if proyecto.estado == 'publicado':
            estado_anterior = proyecto.estado
            proyecto.estado = 'en_desarrollo'
            proyecto.save()
            proyecto.registrar_cambio_estado(
                'en_desarrollo', ejecutado_por, estado_anterior=estado_anterior
            )

        Notificacion.objects.create(
            usuario=postulacion.desarrollador,
            proyecto=proyecto,
            tipo='aprobacion',
            mensaje=(
                f"¡Felicidades! Tu postulación al proyecto '{proyecto.titulo}' "
                f"ha sido aceptada y tu contratación está activa."
            ),
        )

        # Despacho asíncrono de correo transaccional vía Celery (SCRUM-199)
        if postulacion.desarrollador.email:
            from notificaciones.tasks import enviar_email_transaccional_task
            enviar_email_transaccional_task.delay(
                asunto=f"¡Tu postulación al proyecto '{proyecto.titulo}' fue aceptada!",
                template_name='emails/postulacion_aceptada.html',
                contexto={
                    'usuario': {
                        'nombre': postulacion.desarrollador.nombre,
                        'username': postulacion.desarrollador.username,
                    },
                    'empresa': {
                        'nombre': ejecutado_por.nombre or ejecutado_por.username,
                        'username': ejecutado_por.username,
                    },
                    'proyecto': {
                        'titulo': proyecto.titulo,
                        'tipo_solucion': proyecto.get_tipo_solucion_display(),
                    },
                },
                destinatarios=[postulacion.desarrollador.email],
            )

        LogAuditoria.objects.create(
            usuario=ejecutado_por,
            accion=(
                f"Aceptó postulación de {postulacion.desarrollador.nombre} "
                f"en {proyecto.titulo}"
            )[:300],
            tabla_afectada='postulaciones',
            registro_id=postulacion.id,
        )

    return contratacion


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
