"""Operaciones de negocio de la app mensajes (SCRUM-156, Fase 2).

La autorización vive en `mensajes/policies.py` y aquí quedan las operaciones
mutadoras: crear el mensaje y su notificación en una sola transacción, de modo
que no exista un mensaje sin notificación (ni al revés) si algo falla.

Las políticas se reexportan al final para no romper imports históricos.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from contrataciones.models import Contratacion
from notificaciones.models import Notificacion
from proyectos.models import Proyecto

from .models import Mensaje

LONGITUD_MAXIMA_MENSAJE = 2000


def _validar_contenido(contenido):
    """Normaliza y valida el cuerpo del mensaje (RF 4.1)."""
    contenido = (contenido or '').strip()
    if not contenido:
        raise ValidationError('El mensaje no puede estar vacío.')
    if len(contenido) > LONGITUD_MAXIMA_MENSAJE:
        raise ValidationError(
            f'El mensaje no puede superar los {LONGITUD_MAXIMA_MENSAJE} caracteres.'
        )
    return contenido


def _validar_proyecto_activo(proyecto):
    """Un proyecto finalizado es de solo lectura."""
    if proyecto is not None and proyecto.estado == 'finalizado':
        raise ValidationError('No se pueden enviar mensajes a proyectos finalizados.')


def enviar_mensaje(remitente, receptor, contenido, proyecto=None, titulo=None):
    """Envía un mensaje directo y crea su notificación de forma atómica.

    Devuelve el `Mensaje` creado. Lanza `PermissionDenied` si las políticas no
    autorizan la conversación y `ValidationError` si el contenido es inválido.
    """
    # Import local para evitar ciclos: policies importa modelos de otras apps
    from .policies import puede_comunicarse

    contenido = _validar_contenido(contenido)
    _validar_proyecto_activo(proyecto)

    if not puede_comunicarse(remitente, receptor, proyecto):
        raise PermissionDenied('No tienes autorización para comunicarte con este usuario.')

    with transaction.atomic():
        mensaje = Mensaje.objects.create(
            remitente=remitente,
            receptor=receptor,
            titulo=titulo,
            contenido=contenido,
            proyecto=proyecto,
        )
        Notificacion.objects.create(
            usuario=receptor,
            proyecto=proyecto,
            tipo='mensaje',
            mensaje=(
                f"{remitente.nombre or remitente.username} te envió un mensaje: "
                f"{titulo or (proyecto.titulo if proyecto else 'General')}"
            ),
        )

    return mensaje


def enviar_mensaje_grupal(remitente, proyecto, contenido):
    """Publica un mensaje en el chat grupal del proyecto y notifica al equipo.

    Bloquea la fila del proyecto (`select_for_update`) para serializar el orden
    de los mensajes del mismo proyecto. Devuelve el `Mensaje` creado.
    """
    from .policies import puede_participar_en_chat_grupal

    contenido = _validar_contenido(contenido)

    if not puede_participar_en_chat_grupal(remitente, proyecto):
        raise PermissionDenied('No tienes autorización para escribir en este chat grupal.')

    with transaction.atomic():
        proyecto = Proyecto.objects.select_for_update().get(id=proyecto.id)
        _validar_proyecto_activo(proyecto)

        mensaje = Mensaje.objects.create(
            remitente=remitente,
            receptor=None,  # Mensaje grupal
            titulo=f"Espacio de Trabajo: {proyecto.titulo}",
            contenido=contenido,
            proyecto=proyecto,
        )

        # Notificar a todos los participantes del proyecto excepto el remitente
        destinatarios_ids = set(
            Contratacion.objects.filter(
                proyecto=proyecto, estado__in=['activa', 'finalizada']
            ).values_list('desarrollador_id', flat=True)
        )
        destinatarios_ids.add(proyecto.empresa_id)
        destinatarios_ids.discard(remitente.id)

        notificaciones = [
            Notificacion(
                usuario_id=dest_id,
                proyecto=proyecto,
                tipo='mensaje',
                mensaje=f"{remitente.nombre or remitente.username} envió un mensaje en '{proyecto.titulo}'",
            )
            for dest_id in destinatarios_ids
        ]
        if notificaciones:
            Notificacion.objects.bulk_create(notificaciones)

    return mensaje


# ── Reexport de políticas (compatibilidad con imports históricos) ──────────
from .policies import (  # noqa: E402,F401
    obtener_destinatarios_disponibles,
    puede_comunicarse,
    puede_enviar_mensaje,
    puede_participar_en_chat_grupal,
    puede_ver_mensaje,
)

__all__ = [
    'enviar_mensaje',
    'enviar_mensaje_grupal',
    'obtener_destinatarios_disponibles',
    'puede_comunicarse',
    'puede_enviar_mensaje',
    'puede_participar_en_chat_grupal',
    'puede_ver_mensaje',
]
