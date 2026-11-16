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


def es_parte_del_contrato(usuario, contrato):
    """Solo la empresa y el desarrollador titulares pueden proponer acuerdos."""
    return bool(usuario and (
        (getattr(usuario, 'rol', None) == 'empresa' and contrato.empresa_id == usuario.pk)
        or (getattr(usuario, 'rol', None) == 'desarrollador' and contrato.desarrollador_id == usuario.pk)
    ))


def puede_confirmar_acuerdo(usuario, contrato, solicitud):
    """La aceptación siempre corresponde a la parte que no hizo la propuesta."""
    return (
        es_parte_del_contrato(usuario, contrato)
        and solicitud.solicitante_id in (contrato.empresa_id, contrato.desarrollador_id)
        and usuario.pk != solicitud.solicitante_id
    )
