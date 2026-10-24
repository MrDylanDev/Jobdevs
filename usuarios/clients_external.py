"""
Cliente HTTP asíncrono con httpx para validaciones externas con SENA y DIAN (SCRUM-190).

Provee cliente httpx.AsyncClient con timeouts estrictos, reintentos exponenciales
con backoff y degradación elegante ante caídas o latencia en servicios externos.

Padrón institucional SENA (SCRUM-311)
-------------------------------------
No existe API pública oficial de SOFIA Plus / SENA. Por esa razón, la fuente
primaria oficial de verificación de fichas en JobDevs es el **Padrón
Institucional SENA**, materializado en la lista blanca local del modelo
``FichaSena`` (``fuente='lista_blanca_local'``, ``degradado=False``).

``SENA_API_URL`` se mantiene únicamente como **pasarela institucional externa
opcional**: si está configurada y responde, se usa (``fuente='api_sena'``); si
no está configurada, la consulta al padrón local es el mecanismo oficial
estándar de producción y no se reporta como degradación (``degradado=False``).
Sólo se reporta degradación cuando la pasarela estaba configurada y falló.
"""

import asyncio
import logging
import os
from typing import Any

from django.conf import settings
import httpx

from . import utils_dian

logger = logging.getLogger(__name__)

# Configuraciones de endpoints y timeouts (configurables en settings o variables de entorno)
DIAN_API_URL = getattr(settings, 'DIAN_API_URL', os.environ.get('DIAN_API_URL', ''))
SENA_API_URL = getattr(settings, 'SENA_API_URL', os.environ.get('SENA_API_URL', ''))

DEFAULT_TIMEOUT = float(getattr(settings, 'EXTERNAL_HTTP_TIMEOUT', 5.0))
DEFAULT_CONNECT_TIMEOUT = float(getattr(settings, 'EXTERNAL_HTTP_CONNECT_TIMEOUT', 2.0))
DEFAULT_MAX_RETRIES = int(getattr(settings, 'EXTERNAL_HTTP_MAX_RETRIES', 2))


def get_async_client(timeout: float | None = None) -> httpx.AsyncClient:
    """Crea una instancia configurada de httpx.AsyncClient con timeouts estrictos."""
    t = timeout if timeout is not None else DEFAULT_TIMEOUT
    return httpx.AsyncClient(
        timeout=httpx.Timeout(t, connect=DEFAULT_CONNECT_TIMEOUT),
        headers={
            "User-Agent": "JobDevs-Platform/1.0 (+https://jobdevs.sena.edu.co)",
            "Accept": "application/json",
        },
        follow_redirects=False,
    )


async def fetch_with_retry(
    method: str,
    url: str,
    client: httpx.AsyncClient | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = 0.1,
    **kwargs: Any,
) -> httpx.Response | None:
    """
    Ejecuta una petición HTTP asíncrona con reintentos exponenciales ante timeouts o errores 5xx.
    Retorna la respuesta HTTP si es exitosa o 4xx, o None si se agotaron los reintentos.
    """
    own_client = False
    if client is None:
        client = get_async_client()
        own_client = True

    try:
        for attempt in range(max_retries + 1):
            try:
                response = await client.request(method, url, **kwargs)
                # Si es 5xx, reintentar (posible indisponibilidad transitoria)
                if response.status_code >= 500 and attempt < max_retries:
                    logger.warning(
                        "Servicio externo %s devolvió status %d (intento %d/%d)",
                        url, response.status_code, attempt + 1, max_retries
                    )
                    await asyncio.sleep(backoff_factor * (2 ** attempt))
                    continue
                return response
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < max_retries:
                    logger.warning(
                        "Fallo de red o timeout al conectar con %s: %s (intento %d/%d)",
                        url, exc, attempt + 1, max_retries
                    )
                    await asyncio.sleep(backoff_factor * (2 ** attempt))
                    continue
                logger.error(
                    "Se agotaron los %d reintentos conectando a %s: %s",
                    max_retries, url, exc
                )
                return None
    finally:
        if own_client:
            await client.aclose()


async def consultar_nit_dian_api(
    nit_con_o_sin_dv: str | int,
    client: httpx.AsyncClient | None = None,
    api_url: str | None = None,
) -> dict[str, Any]:
    """
    Valida un NIT contra la API externa de la DIAN de forma asíncrona.
    Si la API no está configurada, no responde o falla por timeout/red,
    aplica degradación elegante ejecutando la validación matemática Módulo 11 local.
    """
    limpio = utils_dian.limpiar_documento(str(nit_con_o_sin_dv))
    url = api_url if api_url is not None else DIAN_API_URL

    # Si hay API configurada, intentar consumo asíncrono
    if url:
        endpoint = f"{url.rstrip('/')}/{limpio}"
        response = await fetch_with_retry("GET", endpoint, client=client)
        if response is not None and response.status_code == 200:
            try:
                data = response.json()
                return {
                    "valido": bool(data.get("valido", True)),
                    "dv": data.get("dv"),
                    "razon_social": data.get("razon_social"),
                    "estado": data.get("estado", "activo"),
                    "fuente": "api_dian",
                    "degradado": False,
                    "detalle": data.get("detalle", "Validado exitosamente contra DIAN"),
                }
            except Exception as e:
                logger.warning("Error parseando respuesta JSON de DIAN: %s", e)

    # Fallback / Degradación elegante a validación local Módulo 11
    try:
        if len(limpio) >= 2:
            base, dv_provisto = limpio[:-1], int(limpio[-1])
            dv_calculado = utils_dian.calcular_dv_dian(base)
            valido = (dv_provisto == dv_calculado)
            dv_final = dv_provisto
        else:
            dv_final = utils_dian.calcular_dv_dian(limpio)
            valido = True
        
        return {
            "valido": valido,
            "dv": dv_final,
            "razon_social": None,
            "estado": "activo" if valido else "invalido",
            "fuente": "validacion_local",
            "degradado": bool(url),  # True si había URL pero falló
            "detalle": "Validado localmente con algoritmo oficial Módulo 11",
        }
    except Exception as exc:
        return {
            "valido": False,
            "dv": None,
            "razon_social": None,
            "estado": "error",
            "fuente": "validacion_local",
            "degradado": True,
            "detalle": str(exc),
        }


async def consultar_ficha_sena_api(
    numero_ficha: str | int,
    client: httpx.AsyncClient | None = None,
    api_url: str | None = None,
) -> dict[str, Any]:
    """
    Valida una ficha de formación contra el mecanismo oficial de verificación SENA.

    No existe API pública oficial de SOFIA Plus / SENA. La fuente primaria oficial
    es el **padrón institucional SENA**, es decir la lista blanca local del modelo
    ``FichaSena`` (``fuente='lista_blanca_local'``, ``degradado=False``).

    ``SENA_API_URL`` actúa sólo como **pasarela institucional externa opcional**:
    cuando está configurada y responde se devuelve ``fuente='api_sena'``; cuando
    no está configurada se consulta directamente el padrón oficial local, lo que
    no es una degradación. Sólo hay degradación real (``degradado=True``) si la
    pasarela externa estaba configurada y falló, o si el padrón local falló.
    """
    from .models import FichaSena
    from .services_sena import normalizar_numero_ficha

    limpio = normalizar_numero_ficha(str(numero_ficha))
    url = api_url if api_url is not None else SENA_API_URL

    if url and limpio:
        endpoint = f"{url.rstrip('/')}/fichas/{limpio}"
        response = await fetch_with_retry("GET", endpoint, client=client)
        if response is not None and response.status_code == 200:
            try:
                data = response.json()
                return {
                    "valida": bool(data.get("valida", True)),
                    "activa": bool(data.get("activa", True)),
                    "numero_ficha": limpio,
                    "programa": data.get("programa"),
                    "regional": data.get("regional"),
                    "centro": data.get("centro"),
                    "fuente": "api_sena",
                    "degradado": False,
                    "detalle": data.get("detalle", "Validada contra servicio SOFIA Plus"),
                }
            except Exception as e:
                logger.warning("Error parseando JSON de API SENA: %s", e)

    # Mecanismo oficial por defecto: padrón institucional SENA (lista blanca local).
    # Sólo se reporta degradación cuando la pasarela externa estaba configurada.
    try:
        ficha = await FichaSena.objects.filter(numero_ficha=limpio).afirst()
        if not ficha:
            return {
                "valida": False,
                "activa": False,
                "numero_ficha": limpio,
                "programa": None,
                "regional": None,
                "centro": None,
                "fuente": "lista_blanca_local",
                "degradado": bool(url),
                "detalle": (
                    f"Ficha {limpio} no encontrada en el padrón institucional SENA "
                    "(Lista Blanca Oficial)"
                ),
            }

        return {
            "valida": True,
            "activa": ficha.activa,
            "numero_ficha": ficha.numero_ficha,
            "programa": ficha.programa_formacion,
            "regional": ficha.regional,
            "centro": ficha.centro_formacion,
            "fuente": "lista_blanca_local",
            "degradado": bool(url),
            "detalle": (
                "Validada contra el padrón institucional SENA (Lista Blanca Oficial)"
                if ficha.activa
                else "Ficha inactiva en el padrón institucional SENA (Lista Blanca Oficial)"
            ),
        }
    except Exception as exc:
        return {
            "valida": False,
            "activa": False,
            "numero_ficha": limpio,
            "programa": None,
            "regional": None,
            "centro": None,
            "fuente": "lista_blanca_local",
            "degradado": True,
            "detalle": str(exc),
        }
