"""
Tests unitarios y de integración para clientes HTTP asíncronos externos (SCRUM-190).
Verifica timeouts, reintentos con backoff y degradación elegante ante caídas o latencia.
"""

from unittest import mock
import httpx
import pytest

from usuarios.clients_external import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_TIMEOUT,
    consultar_ficha_sena_api,
    consultar_nit_dian_api,
    fetch_with_retry,
    get_async_client,
)
from usuarios.models import FichaSena
from usuarios.services_sena import validar_ficha_sena_api_async
from usuarios.utils_dian import validar_nit_dian_api_async


@pytest.mark.asyncio
class TestAsyncHttpClient:
    """Pruebas del cliente httpx base con timeouts y reintentos."""

    async def test_get_async_client_configuracion(self):
        client = get_async_client()
        try:
            assert isinstance(client, httpx.AsyncClient)
            assert client.timeout.read == DEFAULT_TIMEOUT
            assert client.timeout.connect == DEFAULT_CONNECT_TIMEOUT
            assert "JobDevs" in client.headers["User-Agent"]
        finally:
            await client.aclose()

    async def test_fetch_with_retry_exitoso_primer_intento(self):
        mock_response = httpx.Response(200, json={"status": "ok"})
        mock_client = mock.AsyncMock(spec=httpx.AsyncClient)
        mock_client.request.return_value = mock_response

        res = await fetch_with_retry("GET", "https://api.test/status", client=mock_client)
        assert res is not None
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}
        assert mock_client.request.call_count == 1

    async def test_fetch_with_retry_recupera_tras_error_503(self):
        """Simula fallo transitorio 503 seguido de éxito 200."""
        resp_503 = httpx.Response(503, text="Service Unavailable")
        resp_200 = httpx.Response(200, json={"data": "ok"})

        mock_client = mock.AsyncMock(spec=httpx.AsyncClient)
        mock_client.request.side_effect = [resp_503, resp_200]

        res = await fetch_with_retry(
            "GET", "https://api.test/flaky",
            client=mock_client, max_retries=2, backoff_factor=0.01
        )
        assert res is not None
        assert res.status_code == 200
        assert mock_client.request.call_count == 2

    async def test_fetch_with_retry_agota_reintentos_en_timeout(self):
        """Simula timeout repetido y verifica degradación sin excepción no capturada."""
        mock_client = mock.AsyncMock(spec=httpx.AsyncClient)
        mock_client.request.side_effect = httpx.TimeoutException("Read timeout")

        res = await fetch_with_retry(
            "GET", "https://api.test/slow",
            client=mock_client, max_retries=2, backoff_factor=0.01
        )
        assert res is None
        assert mock_client.request.call_count == 3  # intento inicial + 2 reintentos


@pytest.mark.asyncio
class TestConsultarNitDianApi:
    """Pruebas de validación externa asíncrona DIAN y fallback a Módulo 11."""

    async def test_dian_api_exitosa(self):
        resp_data = {
            "valido": True,
            "dv": 1,
            "razon_social": "SENA TECNOLOGÍA SAS",
            "estado": "activo",
            "detalle": "NIT activo y verificado en DIAN",
        }
        mock_response = httpx.Response(200, json=resp_data)
        mock_client = mock.AsyncMock(spec=httpx.AsyncClient)
        mock_client.request.return_value = mock_response

        res = await consultar_nit_dian_api(
            "899999034-1", client=mock_client, api_url="https://api.dian.gov.co/rut"
        )
        assert res["valido"] is True
        assert res["dv"] == 1
        assert res["razon_social"] == "SENA TECNOLOGÍA SAS"
        assert res["fuente"] == "api_dian"
        assert res["degradado"] is False

    async def test_dian_api_indisponible_degrada_a_modulo_11_local(self):
        """Cuando la API externa falla con timeout, degrada a Módulo 11 local."""
        mock_client = mock.AsyncMock(spec=httpx.AsyncClient)
        mock_client.request.side_effect = httpx.ConnectTimeout("Connection timed out")

        # NIT oficial DIAN 899.999.034 con DV 1
        res = await consultar_nit_dian_api(
            "899999034-1", client=mock_client, api_url="https://api.dian.gov.co/rut"
        )
        assert res["valido"] is True
        assert res["dv"] == 1
        assert res["fuente"] == "validacion_local"
        assert res["degradado"] is True

    async def test_dian_api_sin_url_ejecuta_validacion_local(self):
        """Si no hay URL de API externa configurada, valida Módulo 11 inmediatamente."""
        res = await validar_nit_dian_api_async("890903938-8")
        assert res["valido"] is True
        assert res["dv"] == 8
        assert res["fuente"] == "validacion_local"
        assert res["degradado"] is False

    async def test_dian_api_nit_invalido_local(self):
        # 890.903.938 tiene DV 8, pasamos 2 incorrecto
        res = await validar_nit_dian_api_async("890903938-2")
        assert res["valido"] is False


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestConsultarFichaSenaApi:
    """Pruebas de validación externa asíncrona SENA y fallback a lista blanca."""

    async def test_sena_api_exitosa(self):
        resp_data = {
            "valida": True,
            "activa": True,
            "programa": "Análisis y Desarrollo de Software",
            "regional": "Distrito Capital",
            "centro": "CEET",
        }
        mock_response = httpx.Response(200, json=resp_data)
        mock_client = mock.AsyncMock(spec=httpx.AsyncClient)
        mock_client.request.return_value = mock_response

        res = await consultar_ficha_sena_api(
            "2670999", client=mock_client, api_url="https://sofia.sena.edu.co/api"
        )
        assert res["valida"] is True
        assert res["activa"] is True
        assert res["programa"] == "Análisis y Desarrollo de Software"
        assert res["fuente"] == "api_sena"
        assert res["degradado"] is False

    async def test_sena_api_caida_degrada_a_lista_blanca_local(self):
        """Si la API remota da timeout o 500, consulta la lista blanca en BD."""
        await FichaSena.objects.acreate(
            numero_ficha="2670999",
            programa_formacion="ADSO Local",
            regional="Antioquia",
            centro_formacion="CTMA",
            activa=True,
        )

        mock_client = mock.AsyncMock(spec=httpx.AsyncClient)
        mock_client.request.side_effect = httpx.ReadTimeout("Timeout")

        res = await consultar_ficha_sena_api(
            "2670999", client=mock_client, api_url="https://sofia.sena.edu.co/api"
        )
        assert res["valida"] is True
        assert res["activa"] is True
        assert res["programa"] == "ADSO Local"
        assert res["fuente"] == "lista_blanca_local"
        assert res["degradado"] is True

    async def test_sena_api_sin_url_consulta_lista_blanca_directa(self):
        await FichaSena.objects.acreate(
            numero_ficha="2500111",
            programa_formacion="Programación de Software",
            activa=False,
        )

        res = await validar_ficha_sena_api_async("2500111")
        assert res["valida"] is True
        assert res["activa"] is False
        assert res["fuente"] == "lista_blanca_local"
        assert res["degradado"] is False
