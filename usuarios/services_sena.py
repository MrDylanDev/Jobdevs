import os
import re
import unicodedata

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from .models import ExcepcionFichaSena, FichaSena, PerfilDesarrollador, Usuario

MAX_SOPORTE_DEV_BYTES = 5 * 1024 * 1024  # 5 MB

# SCRUM-229 (RF 1.2.1): catálogo de programas oficiales SENA del área de
# tecnología y software usados para validar el registro de desarrolladores.
PROGRAMAS_SENA_SOFTWARE = (
    'Análisis y Desarrollo de Software',
    'ADSO',
    'Programación de Software',
    'Desarrollo de Aplicaciones Web',
    'Desarrollo de Videojuegos',
    'Diseño y Desarrollo de Sistemas de Información',
    'Análisis y Desarrollo de Sistemas de Información',
    'ADSI',
    'Administración de Sistemas Informáticos',
    'Gestión de Bases de Datos',
    'Gestión de Redes de Datos',
    'Seguridad Informática',
    'Mantenimiento de Equipos de Cómputo',
    'Tecnólogo en Análisis y Desarrollo de Software',
    'Tecnólogo en Programación de Software',
    'Técnico en Programación de Software',
)


# Grupos de programas equivalentes (nombre oficial, sigla y variantes de nivel
# de formación). Permiten comprobar coherencia entre la ficha y el programa
# ingresado sin exigir una coincidencia literal del texto.
_GRUPOS_PROGRAMAS_EQUIVALENTES = (
    (
        'analisis y desarrollo de software',
        'adso',
        'tecnologo en analisis y desarrollo de software',
    ),
    (
        'programacion de software',
        'tecnologo en programacion de software',
        'tecnico en programacion de software',
    ),
    (
        'analisis y desarrollo de sistemas de informacion',
        'adsi',
    ),
)


def normalizar_programa_formacion(programa):
    """Normaliza un programa de formación: sin tildes, minúsculas y espacios simples."""
    if not programa:
        return ''
    texto = unicodedata.normalize('NFKD', str(programa))
    texto = ''.join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9]+', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def programa_formacion_es_valido(programa):
    """Indica si el programa pertenece al catálogo oficial de software/tecnología SENA."""
    normalizado = normalizar_programa_formacion(programa)
    if not normalizado:
        return False
    catalogo = {normalizar_programa_formacion(item) for item in PROGRAMAS_SENA_SOFTWARE}
    return normalizado in catalogo


def _grupo_programa(normalizado):
    """Devuelve el índice del grupo equivalente al programa normalizado, si existe."""
    for indice, grupo in enumerate(_GRUPOS_PROGRAMAS_EQUIVALENTES):
        if normalizado in grupo:
            return indice
    # Tolerar textos con sufijos o aclaraciones, p. ej. "... (ADSO)".
    for indice, grupo in enumerate(_GRUPOS_PROGRAMAS_EQUIVALENTES):
        for variante in grupo:
            if len(variante) >= 4 and (variante in normalizado or normalizado in variante):
                return indice
    return None


def programas_formacion_coinciden(prog_a, prog_b):
    """Comprueba si dos programas son equivalentes (tolerante a tildes y alias)."""
    a = normalizar_programa_formacion(prog_a)
    b = normalizar_programa_formacion(prog_b)
    if not a or not b:
        return False
    if a == b:
        return True
    grupo_a = _grupo_programa(a)
    grupo_b = _grupo_programa(b)
    return grupo_a is not None and grupo_a == grupo_b


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


def buscar_excepcion_ficha_activa(numero_ficha, perfil):
    """SCRUM-225 (RF 9.1.2): devuelve la excepción vigente del aprendiz para esa ficha.

    Una excepción es vigente si está activa y no ha expirado. Las excepciones sin
    fecha de expiración se consideran permanentes hasta que un administrador las revoque.
    """
    limpio = normalizar_numero_ficha(numero_ficha)
    if not perfil or not limpio:
        return None

    return (
        ExcepcionFichaSena.objects.filter(
            desarrollador=perfil,
            numero_ficha=limpio,
            activa=True,
        )
        .filter(Q(fecha_expiracion__isnull=True) | Q(fecha_expiracion__gt=timezone.now()))
        .order_by('fecha_creacion')
        .first()
    )


def verificar_desarrollador_automatico(perfil, numero_ficha, programa_formacion=None, usuario_solicitante=None):
    """Verifica de forma automática al aprendiz si su ficha está en la lista blanca activa.

    Si la ficha no está en el padrón oficial, se resuelve la verificación con una
    excepción individual vigente (SCRUM-225 / RF 9.1.2), dejando trazabilidad completa.
    """
    ficha_obj, error = validar_ficha_sena_en_lista_blanca(numero_ficha, programa_formacion)
    if error:
        excepcion = buscar_excepcion_ficha_activa(numero_ficha, perfil)
        if not excepcion:
            return False, error
        return _verificar_por_excepcion(perfil, excepcion, programa_formacion, usuario_solicitante)

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


def _verificar_por_excepcion(perfil, excepcion, programa_formacion, usuario_solicitante):
    """Aplica la verificación autorizada por una excepción vigente y la audita."""
    limpio = excepcion.numero_ficha

    with transaction.atomic():
        perfil_locked = PerfilDesarrollador.objects.select_for_update().select_related('usuario').get(id=perfil.id)
        perfil_locked.estado_verificacion = 'verificado'
        perfil_locked.ficha = limpio
        perfil_locked.programa_formacion = programa_formacion or perfil_locked.programa_formacion
        perfil_locked.fecha_solicitud_verificacion = timezone.now()
        perfil_locked.fecha_verificacion = timezone.now()
        perfil_locked.notas_auditoria = f'Verificación mediante excepción autorizada (Ficha {limpio}).'
        perfil_locked.save()

        LogAuditoria.objects.create(
            usuario=usuario_solicitante or perfil_locked.usuario,
            accion=f'Verificación por excepción autorizada SENA (Ficha {limpio}, excepción #{excepcion.id})'[:300],
            tabla_afectada='excepciones_ficha_sena',
            registro_id=excepcion.id,
        )

        Notificacion.objects.create(
            usuario=perfil_locked.usuario,
            tipo='aprobacion',
            mensaje=(
                f'¡Tu identidad SENA fue verificada exitosamente mediante una excepción '
                f'autorizada con la ficha {limpio}!'
            ),
        )

    return True, 'Verificación exitosa mediante excepción autorizada.'


def solicitar_verificacion_manual_desarrollador(perfil, numero_ficha, programa_formacion, documento_soporte, usuario_solicitante, condicion_sena='aprendiz'):
    """Gestiona la solicitud manual de verificación para aprendices en formación o egresados SENA."""
    errores = {}
    limpio = normalizar_numero_ficha(numero_ficha)

    condicion = condicion_sena if condicion_sena in ('aprendiz', 'egresado') else 'aprendiz'

    if condicion == 'aprendiz' and not limpio:
        errores['ficha'] = 'El número de ficha es obligatorio para aprendices en formación.'

    programa = (programa_formacion or '').strip()
    if not programa:
        errores['programa_formacion'] = 'El programa de formación es obligatorio.'

    if documento_soporte is None:
        if not perfil.documento_soporte or perfil.estado_verificacion == 'sin_verificar':
            if condicion == 'egresado':
                errores['documento_soporte'] = 'Adjunta el diploma o acta de grado en formato PDF.'
            else:
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
        perfil_locked.condicion_sena = condicion
        perfil_locked.ficha = limpio
        perfil_locked.programa_formacion = programa
        if documento_soporte is not None:
            perfil_locked.documento_soporte = documento_soporte
        perfil_locked.estado_verificacion = 'en_revision'
        perfil_locked.fecha_solicitud_verificacion = timezone.now()
        perfil_locked.save()

        etiqueta_condicion = 'egresado SENA' if condicion == 'egresado' else f'aprendiz SENA (Ficha {limpio})'
        LogAuditoria.objects.create(
            usuario=usuario_solicitante,
            accion=f'Solicitud manual de verificación como {etiqueta_condicion}'[:300],
            tabla_afectada='perfil_desarrollador',
            registro_id=perfil_locked.id,
        )

        nombre_dev = usuario_solicitante.nombre or usuario_solicitante.username
        mensaje_admin = (
            f'El desarrollador {nombre_dev} solicitó verificación como egresado SENA ({programa}).'
            if condicion == 'egresado' else
            f'El aprendiz {nombre_dev} solicitó verificación manual SENA (Ficha {limpio}).'
        )
        Notificacion.objects.bulk_create([
            Notificacion(
                usuario=admin,
                tipo='alerta',
                mensaje=mensaje_admin,
            )
            for admin in Usuario.objects.filter(rol='administrador')
        ])
        from usuarios.tasks import analizar_documento_soporte_task
        transaction.on_commit(lambda: analizar_documento_soporte_task.delay(perfil_locked.id, 'desarrollador'))

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
            if perfil.condicion_sena == 'egresado':
                accion_log = f'Aprobó la verificación de egresado SENA de {nombre} ({perfil.programa_formacion})'
                mensaje = (
                    f'¡Felicidades {nombre}! Tu condición de Egresado SENA ha sido verificada. '
                    'Ya cuentas con la insignia oficial y puedes postularte a proyectos.'
                )
            else:
                accion_log = f'Aprobó la verificación SENA del aprendiz {nombre} (Ficha {perfil.ficha})'
                mensaje = (
                    f'¡Felicidades {nombre}! Tu identidad de Aprendiz SENA ha sido verificada. '
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


async def validar_ficha_sena_api_async(numero_ficha: str | int, **kwargs):
    """Valida una ficha de forma asíncrona contra API externa SENA con fallback a lista blanca local (SCRUM-190)."""
    from .clients_external import consultar_ficha_sena_api
    return await consultar_ficha_sena_api(numero_ficha, **kwargs)
