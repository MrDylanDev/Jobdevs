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

from contrataciones.models import Contratacion
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import Proyecto, Equipo

from .models import Postulacion
from .policies import puede_aceptar_postulacion


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

        LogAuditoria.objects.create(
            usuario=ejecutado_por,
            accion=(
                f"Aceptó postulación de {postulacion.desarrollador.nombre} "
                f"en {proyecto.titulo}"
            ),
            tabla_afectada='postulaciones',
            registro_id=postulacion.id,
        )

    return contratacion
