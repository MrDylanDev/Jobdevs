from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from contrataciones.models import Contratacion
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import Proyecto
from usuarios.models import Usuario

from .models import Disputa

ESTADOS_DISPUTABLES = ('en_desarrollo', 'en_revision')


def abrir_disputa(proyecto, usuario, motivo, contratacion=None):
    """Abre una disputa y congela proyecto y contratación de forma atómica.

    Lanza PermissionDenied si el usuario no participa en el proyecto y
    ValidationError si el motivo está vacío o el proyecto no es disputable.
    """
    motivo = (motivo or '').strip()
    if not motivo:
        raise ValidationError('Debes indicar el motivo de la disputa.')

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
            proyecto=proyecto, contratacion=contratacion, iniciado_por=usuario,
            motivo=motivo, estado='abierta',
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
