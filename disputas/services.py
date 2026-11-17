from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from contrataciones.models import Contratacion, SolicitudCancelacion
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import Proyecto
from usuarios.models import Usuario

from .models import Disputa

ESTADOS_DISPUTABLES = ('en_desarrollo', 'en_revision')
ESTADOS_ACTIVOS = ('abierta', 'en_mediacion')
LONGITUD_MINIMA_MOTIVO = 80
# SCRUM-232 (RF 10.1.2): estados válidos para el filtro fino del centro de disputas.
ESTADOS_VALIDOS = tuple(valor for valor, _ in Disputa.ESTADO)
CATEGORIAS_EVIDENCIA_OBLIGATORIA = (
    'incumplimiento_contractual',
    'falta_comunicacion_grave',
    'bloqueo_insumos',
    'inactividad',
)


def abrir_disputa(
    proyecto,
    usuario,
    motivo,
    contratacion=None,
    categoria='incumplimiento_contractual',
    evidencia_url='',
    evidencia_archivo=None,
    declara_evidencia_no_disponible=False,
    confirma_intento_previo=True,
    confirma_gravedad=True,
    acepta_sanciones=True,
):
    """Abre una disputa y congela proyecto y contratación de forma atómica.

    Lanza PermissionDenied si el usuario no participa en el proyecto y
    ValidationError si el motivo está vacío o no alcanza la longitud mínima,
    la causal no es válida, no se confirman las reglas y el intento previo
    (y la gravedad, salvo en fuerza mayor) o el proyecto
    no es disputable.
    """
    motivo = (motivo or '').strip()
    if not motivo:
        raise ValidationError('Debes indicar el motivo de la disputa.')

    if len(motivo) < LONGITUD_MINIMA_MOTIVO:
        raise ValidationError(
            f'El motivo de la disputa debe ser detallado y contar con al menos '
            f'{LONGITUD_MINIMA_MOTIVO} caracteres explicando los hechos y antecedentes.'
        )

    categorias_validas = dict(Disputa.CATEGORIAS)
    if not categoria or categoria not in categorias_validas:
        raise ValidationError('Debes seleccionar una causal válida para iniciar la mediación.')

    requiere_gravedad = categoria != 'fuerza_mayor'
    if not (confirma_intento_previo and acepta_sanciones and (
        confirma_gravedad or not requiere_gravedad
    )):
        raise ValidationError(
            'Debes confirmar el intento previo y aceptar las reglas de mediación; '
            'salvo en fuerza mayor, también confirmar la gravedad del conflicto.'
        )

    evidencia_url = (evidencia_url or '').strip()
    if evidencia_archivo:
        from .validators import validar_evidencia_archivo
        validar_evidencia_archivo(evidencia_archivo)
    if evidencia_url and not (evidencia_url.startswith('http://') or evidencia_url.startswith('https://')):
        raise ValidationError('La URL de evidencia debe iniciar con http:// o https://.')
    if categoria in CATEGORIAS_EVIDENCIA_OBLIGATORIA and not (
        evidencia_url or evidencia_archivo
    ):
        raise ValidationError(
            'Esta causal requiere evidencia verificable para iniciar la mediación.'
        )
    if categoria == 'fuerza_mayor' and not (
        evidencia_url or evidencia_archivo or declara_evidencia_no_disponible
    ):
        raise ValidationError(
            'En fuerza mayor debes aportar evidencia o declarar expresamente '
            'que no está disponible.'
        )

    with transaction.atomic():
        proyecto = Proyecto.objects.select_for_update().get(pk=proyecto.pk)
        activas = Contratacion.objects.select_for_update().filter(
            proyecto=proyecto, estado='activa',
        )

        es_empresa = usuario.pk == proyecto.empresa_id
        if contratacion is not None and contratacion.proyecto_id != proyecto.pk:
            raise PermissionDenied('La contratación no pertenece al proyecto.')

        if es_empresa:
            if contratacion is not None:
                contratacion = activas.filter(pk=contratacion.pk).first()
            else:
                contratacion = activas.order_by('pk').first()
        else:
            contratacion = activas.filter(desarrollador=usuario).first()
            if contratacion is None:
                raise PermissionDenied('No participas en este proyecto.')

        if proyecto.estado not in ESTADOS_DISPUTABLES:
            raise ValidationError(
                f"No se puede abrir una disputa sobre un proyecto en estado "
                f"'{proyecto.get_estado_display()}'."
            )

        estado_ant = proyecto.estado
        proyecto.estado = 'en_disputa'
        proyecto.save()
        proyecto.registrar_cambio_estado('en_disputa', usuario, estado_ant)

        if contratacion is not None:
            contratacion.estado = 'en_disputa'
            contratacion.save()

        disputa = Disputa.objects.create(
            proyecto=proyecto,
            contratacion=contratacion,
            iniciado_por=usuario,
            categoria=categoria,
            motivo=motivo,
            evidencia_url=evidencia_url,
            evidencia_archivo=evidencia_archivo,
            declara_evidencia_no_disponible=declara_evidencia_no_disponible,
            estado='abierta',
        )
        if contratacion is not None:
            # Conservar los expedientes previos, pero impedir una decisión paralela
            # sobre el mismo contrato mientras está bajo mediación.
            pendientes = SolicitudCancelacion.objects.select_for_update().filter(
                contratacion=contratacion,
                estado__in=['pendiente_acuerdo', 'pendiente_revision'],
            )
            for solicitud in pendientes:
                estado_anterior = solicitud.estado
                solicitud.estado = 'rechazada'
                solicitud.dictamen = f'Sustituida por la disputa #{disputa.pk}.'
                solicitud.fecha_resolucion = timezone.now()
                solicitud.save(update_fields=['estado', 'dictamen', 'fecha_resolucion'])
                LogAuditoria.objects.create(
                    usuario=usuario,
                    accion=f'Sustituyó solicitud de cancelación #{solicitud.pk} por disputa #{disputa.pk}',
                    tabla_afectada='solicitudes_cancelacion', registro_id=solicitud.pk,
                    valor_anterior=estado_anterior, valor_nuevo='rechazada',
                )
                for destinatario_id in {contratacion.empresa_id, contratacion.desarrollador_id}:
                    Notificacion.objects.create(
                        usuario_id=destinatario_id, proyecto=proyecto, tipo='alerta',
                        mensaje=(f'Solicitud de cancelación #{solicitud.pk} sustituida '
                                 f'por la disputa #{disputa.pk}; su historial se conserva.'),
                    )

        LogAuditoria.objects.create(
            usuario=usuario,
            accion=f"Apertura de disputa para proyecto '{proyecto.titulo}'",
            tabla_afectada='disputas',
            registro_id=disputa.id,
        )

        if es_empresa:
            if contratacion is not None:
                contraparte_ids = {contratacion.desarrollador_id}
            else:
                contraparte_ids = set(
                    Contratacion.objects.filter(proyecto=proyecto, estado='activa')
                    .values_list('desarrollador_id', flat=True)
                )
        else:
            contraparte_ids = {proyecto.empresa_id}
        admin_ids = set(
            Usuario.objects.filter(rol='administrador', estado='activo')
            .values_list('pk', flat=True)
        )
        destinatarios = (contraparte_ids | admin_ids) - {usuario.pk}
        Notificacion.objects.bulk_create([
            Notificacion(
                usuario_id=uid, proyecto=proyecto, tipo='alerta',
                mensaje=(
                    f"Se abrió una disputa en el proyecto '{proyecto.titulo}' "
                    f"por {usuario.nombre or usuario.username}. El proyecto quedó congelado."
                ),
            )
            for uid in destinatarios
        ])

    return disputa


RESOLUCIONES = tuple(valor for valor, _ in Disputa.RESOLUCION)
ESTADOS_CERRADOS = ('resuelta', 'cancelada')


def _cambiar_estado_proyecto(proyecto, nuevo_estado, usuario):
    estado_ant = proyecto.estado
    proyecto.estado = nuevo_estado
    proyecto.save()
    proyecto.registrar_cambio_estado(nuevo_estado, usuario, estado_ant)


def resolver_disputa(disputa, admin_user, resolucion, dictamen):
    """Emite la resolución vinculante de una disputa y ejecuta sus acciones.

    Todo ocurre en una única transacción con bloqueo de filas. Lanza
    PermissionDenied si el usuario no es administrador y ValidationError si
    el dictamen/resolución son inválidos o la disputa ya está cerrada.
    """
    if getattr(admin_user, 'rol', None) != 'administrador':
        raise PermissionDenied('Solo un administrador puede resolver disputas.')

    dictamen = (dictamen or '').strip()
    if resolucion not in RESOLUCIONES:
        raise ValidationError('Selecciona una resolución válida.')
    if not dictamen:
        raise ValidationError('Debes indicar el dictamen que fundamenta la resolución.')

    with transaction.atomic():
        disputa = Disputa.objects.select_for_update().get(pk=disputa.pk)
        if disputa.estado in ESTADOS_CERRADOS:
            raise ValidationError('Esta disputa ya fue resuelta o cerrada y no puede resolverse de nuevo.')

        proyecto = Proyecto.objects.select_for_update().get(pk=disputa.proyecto_id)
        contratacion = None
        if disputa.contratacion_id:
            contratacion = Contratacion.objects.select_for_update().get(pk=disputa.contratacion_id)
        empresa = Usuario.objects.select_for_update().get(pk=proyecto.empresa_id)
        desarrollador = None
        if contratacion is not None:
            desarrollador = Usuario.objects.select_for_update().get(pk=contratacion.desarrollador_id)

        if resolucion == 'reanudar_proyecto':
            nuevo_estado_proyecto, nuevo_estado_contrato = 'en_desarrollo', 'activa'
            efecto = 'El proyecto y la contratación se reanudan.'
        elif resolucion == 'cancelar_contrato':
            nuevo_estado_proyecto, nuevo_estado_contrato = 'en_desarrollo', 'cancelada'
            efecto = 'El contrato fue cancelado y el proyecto quedó nuevamente en desarrollo.'
        elif resolucion == 'sancionar_empresa':
            nuevo_estado_proyecto, nuevo_estado_contrato = 'inactivo', 'cancelada'
            efecto = 'El contrato fue cancelado, el proyecto inactivado y la empresa suspendida.'
            empresa.estado = 'suspendido'
            empresa.is_active = False
            empresa.save()
        else:  # sancionar_desarrollador
            nuevo_estado_proyecto, nuevo_estado_contrato = 'en_desarrollo', 'cancelada'
            efecto = 'El contrato fue cancelado y el desarrollador suspendido.'
            if desarrollador is not None:
                desarrollador.estado = 'suspendido'
                desarrollador.is_active = False
                desarrollador.save()

        if contratacion is not None:
            contratacion.estado = nuevo_estado_contrato
            contratacion.save()
            if resolucion in ('cancelar_contrato', 'sancionar_desarrollador') and (
                Contratacion.objects.filter(
                    proyecto=proyecto, estado__in=['activa', 'en_disputa'],
                ).count() < proyecto.vacantes
            ):
                nuevo_estado_proyecto = 'publicado'
        if resolucion == 'cancelar_contrato':
            efecto = (f'El contrato fue cancelado y el proyecto quedó '
                      f'{nuevo_estado_proyecto.replace("_", " ")}.')
        elif resolucion == 'sancionar_desarrollador':
            efecto = (f'El contrato fue cancelado, el desarrollador suspendido y '
                      f'el proyecto quedó {nuevo_estado_proyecto.replace("_", " ")}.')
        _cambiar_estado_proyecto(proyecto, nuevo_estado_proyecto, admin_user)

        # Efectos colaterales sobre hitos y avances (SCRUM-218)
        if resolucion in ('cancelar_contrato', 'sancionar_desarrollador'):
            from avances.models import Avance
            from proyectos.models import Entregable

            if desarrollador is not None:
                avances_pendientes = Avance.objects.select_for_update().filter(
                    proyecto=proyecto,
                    desarrollador=desarrollador,
                    estado='pendiente',
                )
                for av in avances_pendientes:
                    av.estado = 'rechazado'
                    av.comentario_revision = (
                        f"Rechazado automáticamente por resolución de disputa #{disputa.pk}: {dictamen}"
                    )[:500]
                    av.save(update_fields=['estado', 'comentario_revision'])
                    if av.entregable and av.entregable.estado == 'en_revision':
                        av.entregable.estado = 'pendiente'
                        av.entregable.save(update_fields=['estado'])

            entregables_en_revision = Entregable.objects.select_for_update().filter(
                proyecto=proyecto,
                estado='en_revision',
            )
            for ent in entregables_en_revision:
                ent.estado = 'pendiente'
                ent.save(update_fields=['estado'])
        elif resolucion == 'sancionar_empresa':
            from proyectos.models import Entregable
            entregables_en_revision = Entregable.objects.select_for_update().filter(
                proyecto=proyecto,
                estado='en_revision',
            )
            for ent in entregables_en_revision:
                ent.estado = 'pendiente'
                ent.save(update_fields=['estado'])

        disputa.estado = 'resuelta'
        disputa.resolucion = resolucion
        disputa.notas_resolucion = dictamen
        disputa.fecha_resolucion = timezone.now()
        disputa.mediador = admin_user
        disputa.save()

        LogAuditoria.objects.create(
            usuario=admin_user,
            accion=(
                f"Resolución de disputa #{disputa.pk} ({disputa.get_resolucion_display()}) "
                f"del proyecto '{proyecto.titulo}'"
            ),
            tabla_afectada='disputas',
            registro_id=disputa.id,
        )

        destinatarios = {empresa.pk}
        if desarrollador is not None:
            destinatarios.add(desarrollador.pk)
        Notificacion.objects.bulk_create([
            Notificacion(
                usuario_id=uid, proyecto=proyecto, tipo='alerta',
                mensaje=(
                    f"La disputa #{disputa.pk} del proyecto '{proyecto.titulo}' fue resuelta: "
                    f"{disputa.get_resolucion_display()}. {efecto}"
                ),
            )
            for uid in destinatarios
        ])

    return disputa


def auditar_mensaje_disputa(disputa, emisor, canal='HTTP'):
    """Registra en LogAuditoria el envío de un mensaje en la sala de mediación.

    SCRUM-234 (RF 10.2.1): deja traza del emisor, la disputa y el canal usado
    (HTTP o WebSocket). Por confidencialidad de las partes NO se guarda el
    contenido del mensaje en ningún campo del log.
    """
    LogAuditoria.objects.create(
        usuario=emisor,
        accion=(
            f"Envió mensaje en sala de mediación de disputa #{disputa.pk} vía {canal}"
        )[:300],
        tabla_afectada='mensajes_disputa',
        registro_id=disputa.pk,
    )


def datos_dashboard_disputas(usuario, estado=None):
    """Datos de la pestaña/lista de disputas para un usuario según su rol.

    Devuelve disputas activas, historial y los proyectos sobre los que el
    usuario puede abrir una disputa (solo empresa y desarrollador).

    SCRUM-232 (RF 10.1.2): agrega de forma aditiva el filtro fino por estado
    (``estado``), el mapa de conteos ``disputas_por_estado`` y la lista
    ``disputas_filtradas`` sin alterar las claves preexistentes.
    """
    qs = Disputa.objects.select_related(
        'proyecto__empresa', 'contratacion__desarrollador', 'iniciado_por', 'mediador',
    )
    if usuario.rol == 'administrador':
        proyectos = Proyecto.objects.none()
    elif usuario.rol == 'empresa':
        qs = qs.filter(proyecto__empresa=usuario)
        proyectos = Proyecto.objects.filter(
            empresa=usuario,
            estado__in=ESTADOS_DISPUTABLES,
            contrataciones__estado='activa',
        )
    else:
        qs = qs.filter(Q(contratacion__desarrollador=usuario) | Q(iniciado_por=usuario))
        proyectos = Proyecto.objects.filter(
            contrataciones__desarrollador=usuario,
            contrataciones__estado='activa',
            estado__in=ESTADOS_DISPUTABLES,
        ).select_related('empresa')

    disputas = list(qs.order_by('-fecha_creacion'))
    activas = [disputa for disputa in disputas if disputa.estado in ESTADOS_ACTIVOS]
    resueltas = sorted(
        (disputa for disputa in disputas if disputa.estado in ('resuelta', 'cancelada')),
        key=lambda disputa: (disputa.fecha_resolucion or disputa.fecha_creacion, disputa.fecha_creacion),
        reverse=True,
    )
    disputas_por_estado = {clave: 0 for clave in ESTADOS_VALIDOS}
    for disputa in disputas:
        disputas_por_estado[disputa.estado] += 1

    filtro_estado_actual = estado if estado in ESTADOS_VALIDOS else ''
    if filtro_estado_actual:
        disputas_filtradas = [
            disputa for disputa in disputas if disputa.estado == filtro_estado_actual
        ]
    else:
        disputas_filtradas = disputas

    return {
        'disputas_activas': activas,
        'disputas_resueltas': resueltas,
        'proyectos_disputables': proyectos.distinct().order_by('-fecha_publicacion', '-id'),
        'disputas_filtradas': disputas_filtradas,
        'disputas_por_estado': disputas_por_estado,
        'filtro_estado_actual': filtro_estado_actual,
        'total_disputas': sum(disputas_por_estado.values()),
    }
