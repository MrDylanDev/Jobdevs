"""Operaciones de negocio del ciclo de vida de los proyectos (SCRUM-156, Fase 2).

Patrón de la capa de servicios:
- una transacción (`transaction.atomic`) por operación;
- el proyecto se bloquea con `select_for_update` antes de decidir;
- los fallos se comunican con `PermissionDenied` / `ValidationError`;
- la autorización se consulta en `proyectos/policies.py`.

Las vistas conservan solo: permisos de rol/propiedad (404), parseo del input,
llamada al servicio y traducción de la excepción en un mensaje + redirect.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Avg

from contrataciones.models import Contratacion
from notificaciones.models import Notificacion
from usuarios.models import PerfilDesarrollador, PerfilEmpresa

from .models import Proyecto, Valoracion
from .policies import ESTADOS_FINALIZABLES, puede_finalizar_proyecto

# RF 5.2.1 / 5.2.2: mínimo exigido al comentario cualitativo de una valoración.
MIN_COMENTARIO = 20


def recalcular_reputacion_desarrollador(usuario_id):
    """RF 5.3.1: persiste el promedio de valoraciones recibidas por el dev.

    Los campos denormalizados son la fuente que leen el listado de postulantes
    y el ranking del administrador; sin este escritor quedaban siempre en 0.00.
    """
    promedio = (
        Valoracion.objects.filter(
            desarrollador_id=usuario_id, rol_evaluador='empresa'
        ).aggregate(valor=Avg('puntuacion'))['valor']
        or 0
    )
    PerfilDesarrollador.objects.filter(usuario_id=usuario_id).update(
        calificacion_promedio=round(promedio, 2)
    )


def recalcular_reputacion_empresa(usuario_id):
    """RF 5.3.1: persiste el promedio de valoraciones recibidas por la empresa."""
    promedio = (
        Valoracion.objects.filter(
            empresa_id=usuario_id, rol_evaluador='desarrollador'
        ).aggregate(valor=Avg('puntuacion'))['valor']
        or 0
    )
    PerfilEmpresa.objects.filter(usuario_id=usuario_id).update(
        calificacion_promedio=round(promedio, 2)
    )


def recalcular_proyectos_completados(usuario_id):
    """RF 7.2.1: proyectos distintos con contratación finalizada para el dev.

    Se recalcula desde las contrataciones en lugar de incrementar un contador:
    así no se desincroniza con cancelaciones ni con la reactivación admin.
    """
    total = (
        Contratacion.objects.filter(
            desarrollador_id=usuario_id, estado='finalizada'
        ).values('proyecto_id').distinct().count()
    )
    PerfilDesarrollador.objects.filter(usuario_id=usuario_id).update(
        num_proyectos_completados=total
    )


def desarrolladores_pendientes(proyecto):
    """Contratados activos que aún no han sido valorados por la empresa."""
    return Contratacion.objects.desarrolladores_activos(proyecto).exclude(
        id__in=Valoracion.objects.filter(
            proyecto=proyecto, rol_evaluador='empresa'
        ).values_list('desarrollador_id', flat=True)
    )


def validar_finalizacion(proyecto):
    """Reglas previas a finalizar: estado y hitos completados.

    Lanza `ValidationError` con el mensaje apto para el usuario final.
    """
    if proyecto.estado not in ESTADOS_FINALIZABLES:
        raise ValidationError(
            f"No se puede finalizar un proyecto con estado '{proyecto.get_estado_display()}'."
        )

    hitos_totales = proyecto.entregables.count()
    hitos_completados = proyecto.entregables.filter(estado='completado').count()

    if hitos_totales == 0:
        raise ValidationError('No puedes finalizar un proyecto que no tiene hitos definidos.')
    if hitos_completados < hitos_totales:
        pendientes = hitos_totales - hitos_completados
        raise ValidationError(
            f'No puedes finalizar el proyecto. Aún quedan {pendientes} hitos sin completar o validar.'
        )


def _finalizar_bloque(proyecto, ejecutado_por):
    """Ejecuta la finalización dentro de la transacción.

    El proyecto debe llegar con la fila bloqueada. Cierra las contrataciones
    activas, notifica al equipo y registra el cambio de estado en el historial.
    """
    contratos = Contratacion.objects.filter(proyecto=proyecto, estado='activa')

    notificaciones = [
        Notificacion(
            usuario=contrato.desarrollador,
            proyecto=proyecto,
            tipo='aprobacion',
            mensaje=f"El proyecto '{proyecto.titulo}' ha finalizado. ¡Gracias por tu trabajo!",
        )
        for contrato in contratos
    ]
    if notificaciones:
        Notificacion.objects.bulk_create(notificaciones)

    desarrolladores = list(contratos.values_list('desarrollador_id', flat=True))

    contratos.update(estado='finalizada')

    for desarrollador_id in desarrolladores:
        recalcular_proyectos_completados(desarrollador_id)

    estado_anterior = proyecto.estado
    proyecto.estado = 'finalizado'
    proyecto.save()
    proyecto.registrar_cambio_estado(
        'finalizado', ejecutado_por, estado_anterior=estado_anterior
    )


def finalizar_proyecto(proyecto_id, ejecutado_por):
    """Finaliza un proyecto: valida estado/hitos, cierra contratos y notifica.

    Devuelve el `Proyecto` finalizado. Lanza `PermissionDenied` si el proyecto
    no pertenece al usuario y `ValidationError` si alguna regla lo impide.
    """
    with transaction.atomic():
        proyecto = Proyecto.objects.select_for_update().get(id=proyecto_id)

        if proyecto.empresa_id != getattr(ejecutado_por, 'id', None):
            raise PermissionDenied('Este proyecto no pertenece a tu empresa.')
        if proyecto.estado == 'finalizado':
            raise ValidationError(
                f"El proyecto '{proyecto.titulo}' ya ha sido finalizado anteriormente."
            )
        if not puede_finalizar_proyecto(ejecutado_por, proyecto):
            raise ValidationError(
                f"No se puede finalizar un proyecto con estado '{proyecto.get_estado_display()}'."
            )

        validar_finalizacion(proyecto)
        _finalizar_bloque(proyecto, ejecutado_por)

    return proyecto


def valorar_y_finalizar_si_ultima(
    proyecto_id, desarrollador_id, puntuacion, comentario, ejecutado_por
):
    """Registra la valoración de la empresa y cierra el proyecto si era la última.

    Devuelve una tupla ``(finalizado, restantes)``:
    - ``(True, 0)`` si con esta valoración no quedan colaboradores pendientes;
    - ``(False, n)`` si aún faltan ``n`` colaboradores por calificar.

    Lanza `ValidationError` si la puntuación es inválida, si ya se valoró a
    ese desarrollador o si el proyecto no cumple las reglas de finalización.
    """
    try:
        puntuacion = int(puntuacion)
    except (TypeError, ValueError):
        raise ValidationError('Debes seleccionar una puntuación.')
    if not 1 <= puntuacion <= 5:
        raise ValidationError('La puntuación debe estar entre 1 y 5.')

    # RF 5.2.1: el comentario cualitativo es obligatorio.
    comentario = (comentario or '').strip()
    if len(comentario) < MIN_COMENTARIO:
        raise ValidationError(
            f'El comentario es obligatorio y debe tener al menos {MIN_COMENTARIO} caracteres.'
        )

    with transaction.atomic():
        proyecto = Proyecto.objects.select_for_update().get(id=proyecto_id)

        if proyecto.empresa_id != getattr(ejecutado_por, 'id', None):
            raise PermissionDenied('Este proyecto no pertenece a tu empresa.')
        if proyecto.estado not in ESTADOS_FINALIZABLES:
            raise ValidationError(
                f"No se puede valorar en un proyecto con estado '{proyecto.get_estado_display()}'."
            )
        if Valoracion.objects.filter(
            proyecto=proyecto, desarrollador_id=desarrollador_id, rol_evaluador='empresa'
        ).exists():
            raise ValidationError('Ya has calificado a este desarrollador para este proyecto.')

        Valoracion.objects.create(
            proyecto=proyecto,
            empresa=ejecutado_por,
            desarrollador_id=desarrollador_id,
            puntuacion=puntuacion,
            comentario=comentario,
            rol_evaluador='empresa',
        )

        # RF 5.3.1: mantener el campo denormalizado en sincronía al calificar.
        recalcular_reputacion_desarrollador(desarrollador_id)

        restantes = desarrolladores_pendientes(proyecto).count()
        if restantes == 0:
            validar_finalizacion(proyecto)
            _finalizar_bloque(proyecto, ejecutado_por)
            return True, 0

    return False, restantes
