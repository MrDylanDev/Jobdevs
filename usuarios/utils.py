from django.core.cache import cache
from .models import Usuario

def get_admin_id():
    """
    Retorna el ID del primer administrador encontrado, usando caché para optimizar el rendimiento.
    Retorna None si no existe ningún administrador en el sistema (nunca usa un ID por defecto).
    """
    cached_id = cache.get('admin_id')
    if cached_id is not None:
        return cached_id

    admin_id = Usuario.objects.filter(rol='administrador').values_list('id', flat=True).first()

    # Solo cacheamos si encontramos un admin real; evitamos cachear None
    if admin_id is not None:
        cache.set('admin_id', admin_id, timeout=300)

    return admin_id  # Puede ser None si no hay administradores

def get_admin_ids():
    """Retorna una lista con los IDs de todos los administradores del sistema, optimizando con caché."""
    cached_ids = cache.get('admin_ids_list')
    if cached_ids:
        return cached_ids
        
    ids = list(Usuario.objects.filter(rol='administrador').values_list('id', flat=True))
    
    # Cacheamos la lista por 5 minutos
    cache.set('admin_ids_list', ids, timeout=300)
    return ids


def invalidar_sesiones_activas_usuario(usuario_id_o_ids):
    """
    Invalida y elimina inmediatamente todas las sesiones activas en base de datos
    para el usuario o lista de usuarios especificados (RF 1.3.2 / SCRUM-44).
    Retorna el número de sesiones eliminadas.
    """
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    if isinstance(usuario_id_o_ids, (int, str)):
        target_ids = {str(usuario_id_o_ids)}
    else:
        target_ids = {str(uid) for uid in usuario_id_o_ids}

    if not target_ids:
        return 0

    sesiones_a_eliminar = []
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        try:
            data = session.get_decoded()
            if str(data.get('_auth_user_id', '')) in target_ids:
                sesiones_a_eliminar.append(session.session_key)
        except Exception:
            pass

    if sesiones_a_eliminar:
        Session.objects.filter(session_key__in=sesiones_a_eliminar).delete()

    return len(sesiones_a_eliminar)

