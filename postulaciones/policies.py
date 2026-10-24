"""Políticas de autorización de la app postulaciones (SCRUM-156, Fase 2).

Centralizan la pregunta "¿puede este usuario realizar esta acción?" para que
vistas y servicios no reescriban la misma regla con variantes distintas.
"""

ESTADOS_PROYECTO_ACEPTABLES = ('publicado', 'en_desarrollo')


def es_empresa_propietaria(usuario, proyecto):
    """True si el usuario es la empresa dueña del proyecto."""
    return bool(
        usuario
        and getattr(usuario, 'rol', None) == 'empresa'
        and proyecto is not None
        and proyecto.empresa_id == usuario.id
    )


def puede_postularse(desarrollador, proyecto):
    """True si el desarrollador puede postularse al proyecto.

    Reglas: no auto-postulación (la empresa no se postula a lo suyo) y
    proyecto en estado que admite postulaciones. La validación de la fecha
    límite y el límite de 3 postulaciones activas viven en el servicio,
    porque dependen de datos que se bloquean en la transacción.
    """
    if not desarrollador or getattr(desarrollador, 'rol', None) != 'desarrollador':
        return False
    if proyecto.empresa_id == desarrollador.id:
        return False
    return proyecto.estado == 'publicado'


def puede_aceptar_postulacion(usuario, postulacion):
    """True si el usuario puede aceptar la postulación: rol empresa, proyecto
    propio, postulación pendiente y proyecto en estado que admite contratación.

    Es la validación de *autorización*; la validación de cupos y los bloqueos
    de fila los hace el servicio dentro de su transacción.
    """
    if not usuario or getattr(usuario, 'rol', None) != 'empresa':
        return False
    proyecto = postulacion.proyecto
    if proyecto.empresa_id != usuario.id:
        return False
    return (
        postulacion.estado == 'pendiente'
        and proyecto.estado in ESTADOS_PROYECTO_ACEPTABLES
    )


def puede_rechazar_postulacion(usuario, postulacion):
    """True si el usuario es la empresa dueña del proyecto y la postulación está en pendiente o en negociación."""
    if not usuario or getattr(usuario, 'rol', None) != 'empresa':
        return False
    if postulacion.proyecto.empresa_id != usuario.id:
        return False
    return postulacion.estado in ('pendiente', 'en_negociacion')

