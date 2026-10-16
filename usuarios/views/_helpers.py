from django.conf import settings
from django.core.cache import cache

from notificaciones.models import Notificacion


def cached_or_compute(key, ttl, builder):
    """RNF-10: cache de queries con TTL.

    - En tests (settings.TESTING) se ejecuta el builder directamente para
      no contaminar aserciones con datos cacheados.
    - En producción usa el backend configurado (DatabaseCache/LocMem).
    """
    if getattr(settings, 'TESTING', False):
        return builder()

    value = cache.get(key)
    if value is None:
        value = builder()
        cache.set(key, value, ttl)
    return value


def get_notificaciones_context(user_id):
    """Retorna historial de notificaciones y conteo de pendientes."""
    notificaciones_recientes = list(
        Notificacion.objects.filter(usuario_id=user_id)
        .order_by('-fecha')
        .values('tipo', 'mensaje', 'fecha', 'leida')[:10]
    )
    pendientes_count = Notificacion.objects.filter(usuario_id=user_id, leida=False).count()
    return notificaciones_recientes, pendientes_count
