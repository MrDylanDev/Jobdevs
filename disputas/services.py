from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from contrataciones.models import Contratacion
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


def abrir_disputa(
    proyecto,
    usuario,
    motivo,
    contratacion=None,
    categoria='incumplimiento_contractual',
    evidencia_url='',
    confirma_intento_previo=True,
    confirma_gravedad=True,
    acepta_sanciones=True,
):
    """Abre una disputa y congela proyecto y contratación de forma atómica.

    Lanza PermissionDenied si el usuario no participa en el proyecto y
    ValidationError si el motivo está vacío o no alcanza la longitud mínima,
    la causal no es válida, no se confirma el checklist de gravedad o el proyecto
    no es disputable.
    """
    motivo = (motivo or '').strip()
    if not motivo:
        raise ValidationError('Debes indicar el motivo de la disputa.')

    if len(motivo) < LONGITUD_MINIMA_MOTIVO:
        raise ValidationError(
            f'El motivo de la disputa debe ser detallado y contar con al menos '
            f'{LONGITUD_MINIMA_MOTIVO} caracteres explicando los antecedentes graves del conflicto.'
        )

    categorias_validas = dict(Disputa.CATEGORIAS)
    if not categoria or categoria not in categorias_validas:
        raise ValidationError('Debes seleccionar una causal grave válida para iniciar la disputa.')

    if not (confirma_intento_previo and confirma_gravedad and acepta_sanciones):
        raise ValidationError(
            'Debes certificar el agotamiento de la vía previa y confirmar la gravedad del conflicto.'
        )

    evidencia_url = (evidencia_url or '').strip()
    if evidencia_url and not (evidencia_url.startswith('http://') or evidencia_url.startswith('https://')):
        raise ValidationError('La URL de evidencia debe iniciar con http:// o https://.')

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
            estado='abierta',
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

        _cambiar_estado_proyecto(proyecto, nuevo_estado_proyecto, admin_user)
        if contratacion is not None:
            contratacion.estado = nuevo_estado_contrato
            contratacion.save()

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

    activas = qs.filter(estado__in=ESTADOS_ACTIVOS).order_by('-fecha_creacion')
    resueltas = qs.filter(estado__in=('resuelta', 'cancelada')).order_by(
        '-fecha_resolucion', '-fecha_creacion',
    )

    disputas_por_estado = {clave: 0 for clave in ESTADOS_VALIDOS}
    for fila in qs.values('estado').annotate(total=Count('id')):
        disputas_por_estado[fila['estado']] = fila['total']

    filtro_estado_actual = estado if estado in ESTADOS_VALIDOS else ''
    if filtro_estado_actual:
        disputas_filtradas = qs.filter(estado=filtro_estado_actual).order_by('-fecha_creacion')
    else:
        disputas_filtradas = qs.all().order_by('-fecha_creacion')

    return {
        'disputas_activas': activas,
        'disputas_resueltas': resueltas,
        'proyectos_disputables': proyectos.distinct().order_by('-fecha_publicacion', '-id'),
        'disputas_filtradas': disputas_filtradas,
        'disputas_por_estado': disputas_por_estado,
        'filtro_estado_actual': filtro_estado_actual,
        'total_disputas': sum(disputas_por_estado.values()),
    }
