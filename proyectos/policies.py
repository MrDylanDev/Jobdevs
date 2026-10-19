"""Políticas de autorización de la app proyectos (SCRUM-156, Fase 2).

Definen en un solo lugar quién puede gestionar o finalizar un proyecto, para
que vistas y servicios dejen de duplicar la regla con matices distintos.
"""

#: Estados en los que un proyecto admite cerrarse (hallazgo 5 de la auditoría).
ESTADOS_FINALIZABLES = ('en_desarrollo', 'en_revision')


def puede_gestionar_proyecto(usuario, proyecto):
    """True si el usuario es la empresa dueña del proyecto."""
    return bool(
        usuario
        and getattr(usuario, 'rol', None) == 'empresa'
        and proyecto is not None
        and proyecto.empresa_id == usuario.id
    )


def puede_finalizar_proyecto(usuario, proyecto):
    """True si el usuario puede finalizar el proyecto: es dueño y el estado
    del proyecto lo admite."""
    return (
        puede_gestionar_proyecto(usuario, proyecto)
        and proyecto.estado in ESTADOS_FINALIZABLES
    )
