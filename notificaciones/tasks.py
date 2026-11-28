"""
Tareas Celery asíncronas para el módulo de notificaciones y correos transaccionales (SCRUM-198).
"""

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F, Q
from django.template.loader import render_to_string
from django.utils import timezone
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


def despachar_email_transaccional(**kwargs: Any) -> bool:
    """
    Encola un correo transaccional sin acoplar la petición HTTP al broker.

    Devuelve True si la tarea se encoló. Si el broker (Redis) no está
    disponible, registra el fallo y devuelve False para que el flujo de
    negocio (registro, recuperación de contraseña, postulación, etc.) no
    termine en un error 500.

    Se captura Exception de forma deliberada: cualquier fallo de
    infraestructura del broker no debe invalidar una operación ya persistida.
    """
    try:
        enviar_email_transaccional_task.delay(**kwargs)
        return True
    except Exception as exc:
        logger.error(
            "No se pudo encolar el correo '%s' a %s; broker Celery no disponible: %s",
            kwargs.get('asunto'),
            kwargs.get('destinatarios'),
            exc,
        )
        return False


@shared_task(name='notificaciones.purgar_notificaciones_antiguas')
def purgar_notificaciones_antiguas_task(dias: int = 30, incluir_no_leidas: bool = False) -> int:
    """
    Tarea periódica de Celery Beat (SCRUM-200).
    Elimina notificaciones con más de N días de antigüedad para optimizar almacenamiento.
    Por defecto elimina solo aquellas marcadas como leídas.
    """
    from datetime import timedelta

    from django.utils import timezone

    from notificaciones.models import Notificacion

    cutoff = timezone.now() - timedelta(days=dias)
    qs = Notificacion.objects.filter(fecha__lt=cutoff)
    if not incluir_no_leidas:
        qs = qs.filter(leida=True)

    borradas, _ = qs.delete()
    logger.info("Purga Celery Beat: eliminadas %d notificaciones con más de %d días.", borradas, dias)
    return borradas


@shared_task(name='notificaciones.enviar_avisos_cumplimiento')
def enviar_avisos_cumplimiento_task() -> int:
    """Avisos internos 48 h antes del fin del día local y al vencimiento.

    Una fecha sin hora vence al finalizar ese día local. La marca única
    conserva la deduplicación incluso tras purgar notificaciones leídas.
    """
    from notificaciones.models import AvisoCumplimiento, Notificacion
    from proyectos.models import Proyecto
    from usuarios.models import Usuario

    hoy = timezone.localdate()
    administradores = list(Usuario.objects.filter(
        rol='administrador', estado='activo', is_active=True,
    ).values_list('id', flat=True))
    # Una reprogramación invalida avisos no leídos de la fecha anterior.
    obsoletos = AvisoCumplimiento.objects.filter(
        Q(proyecto__fecha_cumplimiento__isnull=True)
        | ~Q(fecha_cumplimiento=F('proyecto__fecha_cumplimiento'))
    ).select_related('notificacion')
    for aviso in list(obsoletos):
        with transaction.atomic():
            if aviso.notificacion_id:
                Notificacion.objects.filter(pk=aviso.notificacion_id, leida=False).delete()
            aviso.delete()
    total = 0
    for etapa, fecha, descripcion in (
        ('anticipado', hoy + timedelta(days=1), 'vence en 48 horas'),
        ('vencido', hoy - timedelta(days=1), 'ha vencido'),
    ):
        proyectos = Proyecto.objects.filter(
            estado__in=('publicado', 'en_desarrollo', 'en_revision'),
            fecha_cumplimiento=fecha,
        ).select_related('empresa')
        for proyecto in list(proyectos):
            destinatarios = set(administradores)
            if proyecto.empresa.is_active and proyecto.empresa.estado == 'activo':
                destinatarios.add(proyecto.empresa_id)
            mensaje = (
                f"La fecha de cumplimiento del proyecto '{proyecto.titulo}' {descripcion} "
                f"({fecha:%Y-%m-%d})."
            )
            for usuario_id in destinatarios:
                with transaction.atomic():
                    marca, creado = AvisoCumplimiento.objects.get_or_create(
                        proyecto=proyecto, usuario_id=usuario_id,
                        fecha_cumplimiento=fecha, etapa=etapa,
                    )
                    if creado:
                        marca.notificacion = Notificacion.objects.create(
                            usuario_id=usuario_id, proyecto=proyecto,
                            tipo='alerta', mensaje=mensaje,
                        )
                        marca.save(update_fields=['notificacion'])
                        total += 1
    return total
