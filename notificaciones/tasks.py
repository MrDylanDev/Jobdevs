"""
Tareas Celery asíncronas para el módulo de notificaciones y correos transaccionales (SCRUM-198).
"""

import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='notificaciones.enviar_email_transaccional',
    max_retries=3,
    default_retry_delay=5,
)
def enviar_email_transaccional_task(
    self,
    asunto: str,
    template_name: str,
    contexto: dict[str, Any],
    destinatarios: list[str],
    from_email: str | None = None,
) -> bool:
    """
    Despacha de forma asíncrona un correo electrónico transaccional multipart (HTML + Texto Plano).
    Reintenta automáticamente hasta 3 veces ante fallos de conexión SMTP.
    """
    if not destinatarios:
        logger.warning("Intento de envío de correo sin destinatarios: asunto=%s", asunto)
        return False

    remitente = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'JobDevs <noreply@jobdevs.edu.co>')

    try:
        html_content = render_to_string(template_name, contexto)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=remitente,
            to=destinatarios,
        )
        msg.attach_alternative(html_content, "text/html")
        enviados = msg.send(fail_silently=False)
        logger.info("Correo '%s' enviado exitosamente a %s", asunto, destinatarios)
        return bool(enviados)
    except Exception as exc:
        logger.error("Error enviando correo '%s' a %s: %s", asunto, destinatarios, exc)
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.critical("Se agotaron los reintentos para correo '%s' a %s", asunto, destinatarios)
            raise
