"""Políticas de autorización de la app mensajes (SCRUM-156, Fase 2).

Aquí vive la pregunta "¿puede este usuario comunicarse / ver este mensaje?".
Antes estaba repartida entre vistas y servicios con variantes distintas, lo que
habilitó el bypass de mensajería corregido en la auditoría.
"""

from contrataciones.models import Contratacion
from postulaciones.models import Postulacion
from usuarios.models import Usuario


def _existe_relacion_empresa_dev(empresa, dev, proyecto=None):
    """Verifica si existe postulación o contratación válida entre la empresa y el desarrollador."""
    contrataciones_q = Contratacion.objects.filter(
        empresa=empresa, desarrollador=dev, estado__in=['activa', 'finalizada']
    )
    postulaciones_q = Postulacion.objects.filter(
        proyecto__empresa=empresa, desarrollador=dev, estado__in=['pendiente', 'en_negociacion', 'aceptada']
    )
    if proyecto:
        contrataciones_q = contrataciones_q.filter(proyecto=proyecto)
        postulaciones_q = postulaciones_q.filter(proyecto=proyecto)
    return contrataciones_q.exists() or postulaciones_q.exists()


def _usuario_vinculado_a_proyecto(usuario, proyecto):
    """Verifica si el usuario tiene relación con un proyecto específico."""
    if usuario.rol == 'administrador':
        return True
    if usuario.rol == 'empresa':
        return proyecto.empresa_id == usuario.id
    if usuario.rol == 'desarrollador':
        tiene_contratacion = Contratacion.objects.filter(
            proyecto=proyecto, desarrollador=usuario, estado__in=['activa', 'finalizada']
        ).exists()
        tiene_postulacion = Postulacion.objects.filter(
            proyecto=proyecto, desarrollador=usuario, estado__in=['pendiente', 'en_negociacion', 'aceptada']
        ).exists()
        return tiene_contratacion or tiene_postulacion
    return False


def puede_comunicarse(emisor, receptor, proyecto=None):
    """
    Verifica si dos usuarios tienen autorización legítima para comunicarse por mensajería.
    - Prohíbe comunicarse consigo mismo.
    - Administradores pueden comunicarse con cualquier usuario.
    - Empresa y Desarrollador requieren postulación o contratación válida (activa o finalizada).
    - Desarrolladores entre sí requieren compartir al menos un proyecto con contratación activa o finalizada.
    - Si se especifica un proyecto, ambos deben estar vinculados a él.
    """
    if not emisor or not receptor or emisor.id == receptor.id:
        return False

    if emisor.rol == 'administrador' or receptor.rol == 'administrador':
        return True

    if proyecto and not (_usuario_vinculado_a_proyecto(emisor, proyecto) and _usuario_vinculado_a_proyecto(receptor, proyecto)):
        return False

    if emisor.rol == 'empresa' and receptor.rol == 'desarrollador':
        return _existe_relacion_empresa_dev(empresa=emisor, dev=receptor, proyecto=proyecto)
    elif emisor.rol == 'desarrollador' and receptor.rol == 'empresa':
        return _existe_relacion_empresa_dev(empresa=receptor, dev=emisor, proyecto=proyecto)

    if emisor.rol == 'desarrollador' and receptor.rol == 'desarrollador':
        proyectos_emisor = Contratacion.objects.filter(
            desarrollador=emisor, estado__in=['activa', 'finalizada']
        ).values_list('proyecto_id', flat=True)
        return Contratacion.objects.filter(
            desarrollador=receptor, proyecto_id__in=proyectos_emisor, estado__in=['activa', 'finalizada']
        ).exists()

    return False


def puede_enviar_mensaje(emisor, receptor, proyecto=None):
    """True si el emisor puede enviar un mensaje directo al receptor."""
    return puede_comunicarse(emisor, receptor, proyecto)


def puede_participar_en_chat_grupal(usuario, proyecto):
    """True si el usuario puede leer/escribir el chat grupal de un proyecto.

    Participan: la empresa dueña, los desarrolladores con contratación activa o
    finalizada y los administradores.
    """
    if not usuario or proyecto is None:
        return False
    if usuario.rol == 'administrador':
        return True
    if usuario.rol == 'empresa':
        return proyecto.empresa_id == usuario.id
    if usuario.rol == 'desarrollador':
        return Contratacion.objects.filter(
            proyecto=proyecto, desarrollador=usuario, estado__in=['activa', 'finalizada']
        ).exists()
    return False


def puede_ver_mensaje(usuario, mensaje):
    """True solo para el remitente o el receptor del mensaje (evita IDOR)."""
    if not usuario or mensaje is None:
        return False
    return usuario.id in (mensaje.remitente_id, mensaje.receptor_id)


def obtener_destinatarios_disponibles(usuario):
    """
    Retorna el QuerySet de usuarios con los que el usuario actual puede comunicarse legalmente.
    """
    if usuario.rol == 'administrador':
        return Usuario.objects.filter(is_active=True).exclude(id=usuario.id).order_by('nombre', 'username')

    admins_ids = list(Usuario.objects.filter(rol='administrador', is_active=True).values_list('id', flat=True))

    if usuario.rol == 'empresa':
        devs_postulados = list(Postulacion.objects.filter(
            proyecto__empresa=usuario, estado__in=['pendiente', 'en_negociacion', 'aceptada']
        ).values_list('desarrollador_id', flat=True))
        devs_contratados = list(Contratacion.objects.filter(
            empresa=usuario, estado__in=['activa', 'finalizada']
        ).values_list('desarrollador_id', flat=True))
        permitidos_ids = set(devs_postulados + devs_contratados + admins_ids)
        permitidos_ids.discard(usuario.id)
        return Usuario.objects.filter(id__in=permitidos_ids, is_active=True).order_by('nombre', 'username')

    if usuario.rol == 'desarrollador':
        empresas_contratadas = list(Contratacion.objects.filter(
            desarrollador=usuario, estado__in=['activa', 'finalizada']
        ).values_list('empresa_id', flat=True))
        empresas_postuladas = list(Postulacion.objects.filter(
            desarrollador=usuario, estado__in=['pendiente', 'en_negociacion', 'aceptada']
        ).values_list('proyecto__empresa_id', flat=True))
        permitidos_ids = set(empresas_contratadas + empresas_postuladas + admins_ids)
        permitidos_ids.discard(usuario.id)
        return Usuario.objects.filter(id__in=permitidos_ids, is_active=True).order_by('nombre', 'username')

    return Usuario.objects.none()
