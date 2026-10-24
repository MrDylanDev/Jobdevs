"""
Tareas Celery asíncronas para el módulo de postulaciones (SCRUM-217).
"""

import logging
from celery import shared_task
from .services import expirar_negociaciones_vencidas

logger = logging.getLogger(__name__)


@shared_task(name='postulaciones.expirar_negociaciones_vencidas')
def expirar_negociaciones_vencidas_task() -> int:
    """Tarea periódica Celery para expirar negociaciones inactivas y liberar cupos."""
    total = expirar_negociaciones_vencidas()
    logger.info("Tarea Celery: expiradas %d negociaciones vencidas.", total)
    return total
