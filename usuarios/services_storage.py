"""Servicio de almacenamiento privado con Cloudflare R2 y URLs prefirmadas (S2).

Expone una interfaz mínima para que las vistas y la API puedan solicitar URLs
temporales de subida/descarga sin acoplarse a un proveedor concreto:

- ``esta_configurado_r2()``: indica si hay credenciales completas y boto3.
- ``generar_url_subida_prefirmada()``: URL temporal para ``put_object``.
- ``generar_url_descarga_prefirmada()``: URL temporal para ``get_object``.

Todas las funciones degradan de forma transparente: si R2 no está configurado,
boto3 no está instalado o el proveedor falla, retornan ``None`` para que el
llamador use el almacenamiento local (``MEDIA_ROOT``) en su lugar.
"""

import logging
import re
import uuid

from django.conf import settings

try:  # pragma: no cover - la ausencia de boto3 es un escenario de fallback
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover
    boto3 = None

    class Config:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self.signature_version = kwargs.get('signature_version')

    class BotoCoreError(Exception):  # type: ignore[no-redef]
        pass

    class ClientError(Exception):  # type: ignore[no-redef]
        pass

logger = logging.getLogger(__name__)

_CARACTERES_INVALIDOS = re.compile(r'[^A-Za-z0-9._-]')

_REQUERIDOS_R2 = (
    'CLOUDFLARE_R2_ACCOUNT_ID',
    'CLOUDFLARE_R2_ACCESS_KEY_ID',
    'CLOUDFLARE_R2_SECRET_ACCESS_KEY',
    'CLOUDFLARE_R2_BUCKET_NAME',
    'CLOUDFLARE_R2_ENDPOINT_URL',
)


def esta_configurado_r2() -> bool:
    """Retorna ``True`` solo si boto3 está disponible y R2 está completo."""
    if boto3 is None:
        return False
    return all(
        str(getattr(settings, nombre, '') or '').strip()
        for nombre in _REQUERIDOS_R2
    )


def _sanitizar_nombre_archivo(nombre_archivo: str) -> str:
    """Limpia un nombre de archivo para usarlo como sufijo de la key S3."""
    # Se descartan componentes de ruta para evitar traversal (../, /abs, etc.).
    base = str(nombre_archivo or '').replace('\\', '/').rsplit('/', 1)[-1]
    limpio = _CARACTERES_INVALIDOS.sub('_', base).lstrip('._-')
    return limpio or 'archivo'


def obtener_cliente_r2():
    """Construye un cliente S3 apuntando al endpoint de Cloudflare R2."""
    if not esta_configurado_r2():
        return None
    return boto3.client(
        's3',
        endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT_URL,
        aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
        region_name='auto',
        config=Config(signature_version='s3v4'),
    )


def generar_url_subida_prefirmada(
    nombre_archivo: str,
    content_type: str = 'application/pdf',
    prefijo: str = 'soportes',
    expiracion_segundos: int | None = None,
) -> dict | None:
    """Genera una URL prefirmada de subida (``put_object``) a Cloudflare R2.

    Retorna un dict con ``url``, ``file_key``, ``content_type`` y ``expira_en``,
    o ``None`` si R2 no está configurado o el proveedor falla.
    """
    if not esta_configurado_r2():
        logger.warning(
            "Cloudflare R2 no está configurado; se usará almacenamiento local."
        )
        return None

    expiracion = int(
        expiracion_segundos
        if expiracion_segundos is not None
        else getattr(settings, 'R2_UPLOAD_URL_EXPIRACION_SEGUNDOS', 300)
    )

    nombre_limpio = _sanitizar_nombre_archivo(nombre_archivo)
    prefijo_normalizado = str(prefijo or '').strip('/') or 'soportes'
    file_key = f"{prefijo_normalizado}/{uuid.uuid4().hex[:12]}_{nombre_limpio}"

    try:
        cliente = obtener_cliente_r2()
        url = cliente.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.CLOUDFLARE_R2_BUCKET_NAME,
                'Key': file_key,
                'ContentType': content_type,
            },
            ExpiresIn=expiracion,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.warning("Fallo generando URL de subida R2: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - degradación transparente
        logger.exception("Error inesperado generando URL de subida R2: %s", exc)
        return None

    return {
        'url': url,
        'file_key': file_key,
        'content_type': content_type,
        'expira_en': expiracion,
    }


def generar_url_descarga_prefirmada(
    file_key: str,
    expiracion_segundos: int | None = None,
) -> str | None:
    """Genera una URL prefirmada de descarga (``get_object``) de Cloudflare R2.

    Retorna la URL firmada o ``None`` si R2 no está configurado o falla.
    """
    if not esta_configurado_r2():
        logger.warning(
            "Cloudflare R2 no está configurado; se usará almacenamiento local."
        )
        return None

    expiracion = int(
        expiracion_segundos
        if expiracion_segundos is not None
        else getattr(settings, 'R2_DOWNLOAD_URL_EXPIRACION_SEGUNDOS', 900)
    )

    try:
        cliente = obtener_cliente_r2()
        return cliente.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.CLOUDFLARE_R2_BUCKET_NAME,
                'Key': file_key,
            },
            ExpiresIn=expiracion,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.warning("Fallo generando URL de descarga R2: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - degradación transparente
        logger.exception("Error inesperado generando URL de descarga R2: %s", exc)
        return None
