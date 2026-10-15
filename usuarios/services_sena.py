import os
import re

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from .models import FichaSena, PerfilDesarrollador, Usuario

MAX_SOPORTE_DEV_BYTES = 5 * 1024 * 1024  # 5 MB


def normalizar_numero_ficha(numero_ficha):
    """Elimina espacios y guiones del número de ficha."""
    if not numero_ficha:
        return ''
    return re.sub(r'[\s\-]+', '', str(numero_ficha).strip())


def validar_ficha_sena_en_lista_blanca(numero_ficha, programa_formacion=None):
    """Busca y valida una ficha en la lista blanca oficial activa."""
    limpio = normalizar_numero_ficha(numero_ficha)
    if not limpio:
        return None, 'El número de ficha es obligatorio.'

    ficha = FichaSena.objects.filter(numero_ficha=limpio).first()
    if not ficha:
        return None, f'La ficha {limpio} no se encuentra registrada en la lista blanca oficial del SENA.'
    if not ficha.activa:
        return None, f'La ficha {limpio} se encuentra inactiva en la lista blanca oficial del SENA.'

    return ficha, None


def verificar_desarrollador_automatico(perfil, numero_ficha, programa_formacion=None, usuario_solicitante=None):
    """Verifica de forma automática al aprendiz si su ficha está en la lista blanca activa."""
    ficha_obj, error = validar_ficha_sena_en_lista_blanca(numero_ficha, programa_formacion)
    if error:
        return False, error

    with transaction.atomic():
        perfil_locked = PerfilDesarrollador.objects.select_for_update().select_related('usuario').get(id=perfil.id)
        perfil_locked.ficha_sena = ficha_obj
        perfil_locked.ficha = ficha_obj.numero_ficha
        perfil_locked.programa_formacion = programa_formacion or ficha_obj.programa_formacion
        perfil_locked.estado_verificacion = 'verificado'
        perfil_locked.fecha_solicitud_verificacion = timezone.now()
        perfil_locked.fecha_verificacion = timezone.now()
        perfil_locked.notas_auditoria = 'Verificación automática contra lista blanca SENA.'
        perfil_locked.save()

        LogAuditoria.objects.create(
            usuario=usuario_solicitante or perfil_locked.usuario,
            accion=f'Verificación automática SENA exitosa (Ficha {ficha_obj.numero_ficha})'[:300],
            tabla_afectada='perfil_desarrollador',
            registro_id=perfil_locked.id,
        )

        Notificacion.objects.create(
            usuario=perfil_locked.usuario,
            tipo='aprobacion',
            mensaje=f'¡Tu identidad SENA fue verificada exitosamente con la ficha {ficha_obj.numero_ficha}!',
        )

    return True, 'Identidad SENA verificada automáticamente con éxito.'


def solicitar_verificacion_manual_desarrollador(perfil, numero_ficha, programa_formacion, documento_soporte, usuario_solicitante):
    """Gestiona la solicitud manual de verificación cuando la ficha no está en lista blanca."""
    errores = {}
    limpio = normalizar_numero_ficha(numero_ficha)
    if not limpio:
        errores['ficha'] = 'El número de ficha es obligatorio.'

    programa = (programa_formacion or '').strip()
    if not programa:
        errores['programa_formacion'] = 'El programa de formación es obligatorio.'

    if documento_soporte is None:
        if not perfil.documento_soporte or perfil.estado_verificacion == 'sin_verificar':
            errores['documento_soporte'] = 'Adjunta el documento de soporte (Carnet o Certificado SENA) en formato PDF.'
    else:
        ext = os.path.splitext(documento_soporte.name)[1].lower()
        if ext != '.pdf':
            errores['documento_soporte'] = 'El documento de soporte debe ser un archivo PDF.'
        elif documento_soporte.size > MAX_SOPORTE_DEV_BYTES:
            errores['documento_soporte'] = 'El documento de soporte no puede superar los 5 MB.'
        else:
            cabecera = documento_soporte.read(1024)
            documento_soporte.seek(0)
            if not cabecera.startswith(b'%PDF-'):
                errores['documento_soporte'] = 'El archivo debe ser un documento PDF válido.'

    if errores:
        return False, 'Por favor corrige los errores del formulario.', errores

    with transaction.atomic():
        perfil_locked = PerfilDesarrollador.objects.select_for_update().select_related('usuario').get(id=perfil.id)
        perfil_locked.ficha = limpio
        perfil_locked.programa_formacion = programa
        if documento_soporte is not None:
            perfil_locked.documento_soporte = documento_soporte
        perfil_locked.estado_verificacion = 'en_revision'
        perfil_locked.fecha_solicitud_verificacion = timezone.now()
        perfil_locked.save()

        LogAuditoria.objects.create(
            usuario=usuario_solicitante,
            accion=f'Solicitud manual de verificación SENA (Ficha {limpio})'[:300],
            tabla_afectada='perfil_desarrollador',
            registro_id=perfil_locked.id,
        )

        Notificacion.objects.bulk_create([
            Notificacion(
                usuario=admin,
                tipo='alerta',
                mensaje=f'El aprendiz {usuario_solicitante.nombre} solicitó verificación manual SENA (Ficha {limpio}).',
            )
            for admin in Usuario.objects.filter(rol='administrador')
        ])

    return True, 'Solicitud enviada a revisión por el equipo administrativo.', {}


def admin_resolver_verificacion_desarrollador(perfil_id, admin_user, accion, notas=None):
    """Aprueba o rechaza una solicitud manual de verificación de aprendiz SENA."""
    if admin_user.rol != 'administrador':
        raise PermissionDenied('Solo los administradores pueden resolver verificaciones.')

    if accion not in ('aprobar', 'rechazar'):
        return False, 'Acción no válida.'

    notas = (notas or '').strip()
    if accion == 'rechazar' and not notas:
        return False, 'Debes indicar el motivo del rechazo.'

    with transaction.atomic():
        perfil = get_object_or_404(
            PerfilDesarrollador.objects.select_for_update().select_related('usuario'),
            id=perfil_id,
        )
        if perfil.estado_verificacion != 'en_revision':
            return False, 'Esta solicitud ya no está en revisión.'

        perfil.fecha_verificacion = timezone.now()
        perfil.verificado_por = admin_user
        perfil.notas_auditoria = notas or None

        nombre = perfil.usuario.nombre or perfil.usuario.username
        if accion == 'aprobar':
            perfil.estado_verificacion = 'verificado'
            accion_log = f'Aprobó la verificación SENA del aprendiz {nombre} (Ficha {perfil.ficha})'
            mensaje = (
                f'¡Felicidades {nombre}! Tu identidad SENA ha sido verificada. '
                'Ya cuentas con la insignia oficial y puedes postularte a proyectos.'
            )
            if notas:
                mensaje += f' Observaciones: {notas}'
            tipo_notif = 'aprobacion'
        else:
            perfil.estado_verificacion = 'rechazado'
            accion_log = f'Rechazó la verificación SENA del aprendiz {nombre} (Ficha {perfil.ficha})'
            mensaje = (
                f'Tu solicitud de verificación SENA fue rechazada. '
                f'Motivo: {notas}. Puedes actualizar tus datos y enviar una nueva solicitud.'
            )
            tipo_notif = 'alerta'

        perfil.save()

        LogAuditoria.objects.create(
            usuario=admin_user,
            accion=accion_log[:300],
            tabla_afectada='perfil_desarrollador',
            registro_id=perfil.id,
        )

        Notificacion.objects.create(
            usuario=perfil.usuario,
            tipo=tipo_notif,
            mensaje=mensaje,
        )

    return True, f'Solicitud {accion}ada con éxito.'
