"""Servicios de notificaciones.

SCRUM-316 (HU-A16): depuración unificada de notificaciones antiguas, reutilizable
por el comando de gestión y por el endpoint administrativo del panel.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Notificacion


def depurar_notificaciones(*, dias=90, incluir_no_leidas=False, dry_run=False) -> int:
    """Elimina notificaciones más antiguas que ``dias`` y retorna cuántas borró.

    - Con ``incluir_no_leidas=False`` (default) solo depura notificaciones leídas.
    - Con ``dry_run=True`` retorna el conteo sin eliminar registros.
    - Lanza ``ValueError`` si ``dias`` es negativo.
    """
    if dias < 0:
        raise ValueError("El parámetro días debe ser un entero positivo o cero.")

    cutoff = timezone.now() - timedelta(days=dias)
    qs = Notificacion.objects.filter(fecha__lt=cutoff)

    if not incluir_no_leidas:
        qs = qs.filter(leida=True)

    total = qs.count()
    if dry_run or total == 0:
        return total

    with transaction.atomic():
        deleted_count, _ = qs.delete()

    return deleted_count
