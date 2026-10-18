"""Políticas de autorización de la app contrataciones (SCRUM-156, Fase 2).

Centralizan quién puede decidir sobre una contratación para que vistas y
servicios no dupliquen la regla.
"""


def puede_cancelar_contratacion(usuario, contrato):
    """True si el usuario puede cancelar la contratación: es la empresa dueña
    del contrato y este sigue activo."""
    if not usuario or getattr(usuario, 'rol', None) != 'empresa':
        return False
    return contrato.empresa_id == usuario.id and contrato.estado == 'activa'
