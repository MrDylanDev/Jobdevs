"""Operaciones de negocio del ciclo de vida de los proyectos (SCRUM-156, Fase 2).

Patrón de la capa de servicios:
- una transacción (`transaction.atomic`) por operación;
- el proyecto se bloquea con `select_for_update` antes de decidir;
- los fallos se comunican con `PermissionDenied` / `ValidationError`;
- la autorización se consulta en `proyectos/policies.py`.

Las vistas conservan solo: permisos de rol/propiedad (404), parseo del input,
llamada al servicio y traducción de la excepción en un mensaje + redirect.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone

from contrataciones.models import Contratacion
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from usuarios.models import PerfilDesarrollador, PerfilEmpresa, Usuario

from .models import (
    ConfiguracionReputacion,
    Proyecto,
    RegularizacionCierreProyecto,
    Valoracion,
)
from .policies import ESTADOS_FINALIZABLES, puede_finalizar_proyecto

# RF 5.2.1 / 5.2.2: mínimo exigido al comentario cualitativo de una valoración.
MIN_COMENTARIO = 20
PLAZO_VALORACION_DIAS = 30
MENSAJE_REGULARIZACION_PENDIENTE = (
    'El proyecto requiere regularización administrativa de su fecha real de cierre '
    'antes de aceptar nuevas valoraciones.'
)
MIN_MOTIVO_REGULARIZACION = 20


def calcular_reputacion_bayesiana(
    promedio_simple,
    cantidad,
    promedio_global,
    minimo_confianza,
):
    promedio_global = Decimal(str(promedio_global))
    if cantidad == 0:
        return promedio_global.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    promedio_simple = Decimal(str(promedio_simple))
    cantidad = Decimal(cantidad)
    minimo_confianza = Decimal(minimo_confianza)
    reputacion = (
        (cantidad / (cantidad + minimo_confianza)) * promedio_simple
        + (minimo_confianza / (cantidad + minimo_confianza)) * promedio_global
    )
    return reputacion.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def obtener_minimo_confianza_reputacion():
    configuracion, _ = ConfiguracionReputacion.objects.get_or_create(pk=1)
    return configuracion.minimo_confianza


def actualizar_minimo_confianza_reputacion(nuevo_minimo, ejecutado_por):
    if ejecutado_por.rol != 'administrador':
        raise PermissionDenied('Solo un administrador puede cambiar este valor.')
    with transaction.atomic():
        configuracion, _ = ConfiguracionReputacion.objects.select_for_update().get_or_create(
            pk=1
        )
        anterior = configuracion.minimo_confianza
        configuracion.minimo_confianza = nuevo_minimo
        configuracion.full_clean()
        configuracion.save(update_fields=['minimo_confianza', 'actualizado_en'])
        if anterior != nuevo_minimo:
            LogAuditoria.objects.create(
                usuario=ejecutado_por,
                accion='Actualizó el mínimo de confianza de reputación',
                tabla_afectada='configuracion_reputacion',
                registro_id=1,
                valor_anterior=f'minimo_confianza={anterior}',
                valor_nuevo=f'minimo_confianza={nuevo_minimo}',
            )
        return configuracion


def obtener_metricas_reputacion_desarrollador(usuario_id):
    recibidas = Valoracion.objects.filter(
        desarrollador_id=usuario_id,
        rol_evaluador='empresa',
    ).aggregate(promedio=Avg('puntuacion'), cantidad=Count('id'))
    globales = Valoracion.objects.filter(
        rol_evaluador='empresa'
    ).aggregate(promedio=Avg('puntuacion'))
    promedio_simple = Decimal(str(recibidas['promedio'] or 0)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    promedio_global = Decimal(str(globales['promedio'] or 3)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    minimo_confianza = obtener_minimo_confianza_reputacion()
    cantidad = recibidas['cantidad']
    return {
        'reputacion': calcular_reputacion_bayesiana(
            promedio_simple,
            cantidad,
            promedio_global,
            minimo_confianza,
        ),
        'promedio_simple': promedio_simple,
        'cantidad': cantidad,
        'minimo_confianza': minimo_confianza,
        'promedio_global': promedio_global,
    }


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
    """Participantes activos o finalizados aún no valorados por la empresa."""
    participantes = Contratacion.objects.filter(
        proyecto=proyecto,
        estado__in=('activa', 'finalizada'),
    ).values_list('desarrollador_id', flat=True)
    return Usuario.objects.filter(id__in=participantes).exclude(
        id__in=Valoracion.objects.filter(
            proyecto=proyecto, rol_evaluador='empresa'
        ).values_list('desarrollador_id', flat=True)
    )


def obtener_fecha_cierre_fiable(proyecto):
    """Devuelve el cierre fiable más reciente, automático o regularizado."""
    fecha_historial = (
        proyecto.historial_estados.filter(estado_nuevo='finalizado')
        .order_by('-fecha')
        .values_list('fecha', flat=True)
        .first()
    )
    fecha_regularizada = (
        RegularizacionCierreProyecto.objects.filter(proyecto=proyecto)
        .values_list('fecha_cierre', flat=True)
        .first()
    )
    fechas = [fecha for fecha in (fecha_historial, fecha_regularizada) if fecha is not None]
    return max(fechas, default=None)


def validar_plazo_valoracion(proyecto):
    """RF 5.3.3: permite valorar hasta 30 días después del cierre fiable."""
    if proyecto.estado != 'finalizado':
        raise ValidationError('Las valoraciones solo se habilitan al finalizar el proyecto.')

    fecha_finalizacion = obtener_fecha_cierre_fiable(proyecto)
    if fecha_finalizacion is None:
        raise ValidationError(MENSAJE_REGULARIZACION_PENDIENTE)
    if timezone.now() > fecha_finalizacion + timedelta(days=PLAZO_VALORACION_DIAS):
        raise ValidationError(
            'El plazo de 30 días para registrar valoraciones ya finalizó.'
        )


def regularizar_cierre_historico(
    proyecto_id,
    fecha_cierre,
    motivo,
    registrado_por,
    referencia_evidencia='',
):
    """Registra de forma explícita el cierre real de un proyecto legado."""
    if getattr(registrado_por, 'rol', None) != 'administrador':
        raise PermissionDenied('Solo un administrador puede regularizar cierres históricos.')

    motivo = (motivo or '').strip()
    if len(motivo) < MIN_MOTIVO_REGULARIZACION:
        raise ValidationError(
            f'El motivo debe tener al menos {MIN_MOTIVO_REGULARIZACION} caracteres.'
        )
    if not fecha_cierre or not isinstance(fecha_cierre, timezone.datetime):
        raise ValidationError('Debes indicar una fecha y hora de cierre válida.')
    if timezone.is_naive(fecha_cierre):
        raise ValidationError('La fecha y hora de cierre debe incluir zona horaria.')

    with transaction.atomic():
        proyecto = Proyecto.objects.select_for_update().get(pk=proyecto_id)
        if proyecto.estado != 'finalizado':
            raise ValidationError('Solo se pueden regularizar proyectos finalizados.')
        if proyecto.historial_estados.filter(estado_nuevo='finalizado').exists():
            raise ValidationError('El proyecto ya tiene un cierre fiable registrado.')
        if RegularizacionCierreProyecto.objects.filter(proyecto=proyecto).exists():
            raise ValidationError('El proyecto ya tiene una regularización de cierre registrada.')

        ahora = timezone.now()
        if fecha_cierre > ahora:
            raise ValidationError('La fecha de cierre no puede estar en el futuro.')
        if fecha_cierre < proyecto.fecha_publicacion:
            raise ValidationError(
                'La fecha de cierre no puede ser anterior a la publicación del proyecto.'
            )

        regularizacion = RegularizacionCierreProyecto.objects.create(
            proyecto=proyecto,
            fecha_cierre=fecha_cierre,
            motivo=motivo,
            referencia_evidencia=(referencia_evidencia or '').strip(),
            registrado_por=registrado_por,
        )
        LogAuditoria.objects.create(
            usuario=registrado_por,
            accion=f"Regularizó la fecha real de cierre del proyecto '{proyecto.titulo}'",
            tabla_afectada='regularizaciones_cierre_proyecto',
            registro_id=regularizacion.pk,
            valor_nuevo=(
                f'fecha_cierre={fecha_cierre.isoformat()}; motivo={motivo}; '
                f'evidencia={regularizacion.referencia_evidencia}'
            ),
        )

    return regularizacion


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
    except (TypeError, ValueError) as err:
        raise ValidationError('Debes seleccionar una puntuación.') from err
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
        proyecto_ya_finalizado = proyecto.estado == 'finalizado'
        if proyecto_ya_finalizado:
            validar_plazo_valoracion(proyecto)
        elif proyecto.estado not in ESTADOS_FINALIZABLES:
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
        if restantes == 0 and not proyecto_ya_finalizado:
            validar_finalizacion(proyecto)
            _finalizar_bloque(proyecto, ejecutado_por)
            return True, 0

    return False, restantes
