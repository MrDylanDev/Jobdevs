"""Tests unitarios del servicio de almacenamiento Cloudflare R2 (S2).

Verifica la detección de configuración, la generación de URLs prefirmadas de
subida/descarga y la degradación elegante (sin excepciones) cuando R2 no está
configurado o boto3 falla.
"""

from unittest import mock

import pytest
from django.test import override_settings

from usuarios import services_storage

R2_CONFIG = {
    'CLOUDFLARE_R2_ACCOUNT_ID': 'cuenta123',
    'CLOUDFLARE_R2_ACCESS_KEY_ID': 'access-key',
    'CLOUDFLARE_R2_SECRET_ACCESS_KEY': 'secret-key',
    'CLOUDFLARE_R2_BUCKET_NAME': 'bucket-privado',
    'CLOUDFLARE_R2_ENDPOINT_URL': 'https://cuenta123.r2.cloudflarestorage.com',
}

R2_SIN_CONFIGURAR = {
    'CLOUDFLARE_R2_ACCOUNT_ID': '',
    'CLOUDFLARE_R2_ACCESS_KEY_ID': '',
    'CLOUDFLARE_R2_SECRET_ACCESS_KEY': '',
    'CLOUDFLARE_R2_BUCKET_NAME': '',
    'CLOUDFLARE_R2_ENDPOINT_URL': '',
}


class TestEstaConfiguradoR2:
    """Detección de configuración completa de Cloudflare R2."""

    @override_settings(**R2_SIN_CONFIGURAR)
    def test_false_por_defecto_sin_credenciales(self):
        assert services_storage.esta_configurado_r2() is False

    @override_settings(**R2_CONFIG)
    def test_true_con_configuracion_completa(self):
        assert services_storage.esta_configurado_r2() is True

    @override_settings(**{**R2_CONFIG, 'CLOUDFLARE_R2_BUCKET_NAME': ''})
    def test_false_si_falta_un_campo_requerido(self):
        assert services_storage.esta_configurado_r2() is False

    @override_settings(**R2_CONFIG)
    def test_false_si_boto3_no_esta_disponible(self):
        with mock.patch.object(services_storage, 'boto3', None):
            assert services_storage.esta_configurado_r2() is False


class TestGenerarUrlSubidaPrefirmada:
    """Generación de URLs prefirmadas de subida (PUT)."""

    @override_settings(**R2_SIN_CONFIGURAR)
    def test_none_sin_configuracion(self):
        assert services_storage.generar_url_subida_prefirmada('soporte.pdf') is None

    @override_settings(**R2_CONFIG)
    def test_dict_con_metadatos_cuando_esta_configurado(self):
        cliente = mock.MagicMock()
        cliente.generate_presigned_url.return_value = 'https://r2.test/upload?sig=abc'

        with mock.patch.object(services_storage.boto3, 'client', return_value=cliente):
            resultado = services_storage.generar_url_subida_prefirmada(
                '../../Soporte Empresa.PDF',
                content_type='application/pdf',
                prefijo='soportes',
            )

        assert resultado is not None
        assert resultado['url'] == 'https://r2.test/upload?sig=abc'
        assert resultado['content_type'] == 'application/pdf'
        assert resultado['expira_en'] == 300
        assert resultado['file_key'].startswith('soportes/')
        assert resultado['file_key'].endswith('_Soporte_Empresa.PDF')

        cliente.generate_presigned_url.assert_called_once()
        args, kwargs = cliente.generate_presigned_url.call_args
        assert args[0] == 'put_object'
        assert kwargs['Params']['Bucket'] == 'bucket-privado'
        assert kwargs['Params']['Key'] == resultado['file_key']
        assert kwargs['Params']['ContentType'] == 'application/pdf'
        assert kwargs['ExpiresIn'] == 300

    @override_settings(**R2_CONFIG)
    def test_respeta_expiracion_explicita(self):
        cliente = mock.MagicMock()
        cliente.generate_presigned_url.return_value = 'https://r2.test/upload'

        with mock.patch.object(services_storage.boto3, 'client', return_value=cliente):
            resultado = services_storage.generar_url_subida_prefirmada(
                'soporte.pdf', expiracion_segundos=60
            )

        assert resultado is not None
        assert resultado['expira_en'] == 60
        assert cliente.generate_presigned_url.call_args.kwargs['ExpiresIn'] == 60

    @override_settings(**R2_CONFIG)
    def test_none_ante_client_error(self):
        from botocore.exceptions import ClientError

        cliente = mock.MagicMock()
        cliente.generate_presigned_url.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'denegado'}}, 'PutObject'
        )

        with mock.patch.object(services_storage.boto3, 'client', return_value=cliente):
            assert services_storage.generar_url_subida_prefirmada('soporte.pdf') is None

    @override_settings(**R2_CONFIG)
    def test_none_ante_error_inesperado(self):
        with mock.patch.object(
            services_storage.boto3, 'client', side_effect=RuntimeError('boom')
        ):
            assert services_storage.generar_url_subida_prefirmada('soporte.pdf') is None


class TestGenerarUrlDescargaPrefirmada:
    """Generación de URLs prefirmadas de descarga (GET)."""

    @override_settings(**R2_SIN_CONFIGURAR)
    def test_none_sin_configuracion(self):
        assert services_storage.generar_url_descarga_prefirmada('soportes/x.pdf') is None

    @override_settings(**R2_CONFIG)
    def test_url_string_cuando_esta_configurado(self):
        cliente = mock.MagicMock()
        cliente.generate_presigned_url.return_value = 'https://r2.test/download?sig=xyz'

        with mock.patch.object(services_storage.boto3, 'client', return_value=cliente):
            url = services_storage.generar_url_descarga_prefirmada('soportes/x.pdf')

        assert url == 'https://r2.test/download?sig=xyz'
        args, kwargs = cliente.generate_presigned_url.call_args
        assert args[0] == 'get_object'
        assert kwargs['Params'] == {
            'Bucket': 'bucket-privado',
            'Key': 'soportes/x.pdf',
        }
        assert kwargs['ExpiresIn'] == 900

    @override_settings(**R2_CONFIG)
    def test_respeta_expiracion_explicita(self):
        cliente = mock.MagicMock()
        cliente.generate_presigned_url.return_value = 'https://r2.test/download'

        with mock.patch.object(services_storage.boto3, 'client', return_value=cliente):
            services_storage.generar_url_descarga_prefirmada(
                'soportes/x.pdf', expiracion_segundos=120
            )

        assert cliente.generate_presigned_url.call_args.kwargs['ExpiresIn'] == 120

    @override_settings(**R2_CONFIG)
    def test_none_ante_client_error(self):
        from botocore.exceptions import ClientError

        cliente = mock.MagicMock()
        cliente.generate_presigned_url.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'no existe'}}, 'GetObject'
        )

        with mock.patch.object(services_storage.boto3, 'client', return_value=cliente):
            assert services_storage.generar_url_descarga_prefirmada('soportes/x.pdf') is None


class TestObtenerClienteR2:
    """Configuración del cliente S3 hacia el endpoint de Cloudflare R2."""

    @override_settings(**R2_CONFIG)
    def test_cliente_s3_con_endpoint_y_firma_v4(self):
        with mock.patch.object(services_storage.boto3, 'client') as mock_client:
            services_storage.obtener_cliente_r2()

        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        assert args[0] == 's3'
        assert kwargs['endpoint_url'] == R2_CONFIG['CLOUDFLARE_R2_ENDPOINT_URL']
        assert kwargs['aws_access_key_id'] == 'access-key'
        assert kwargs['aws_secret_access_key'] == 'secret-key'
        assert kwargs['config'].signature_version == 's3v4'
        assert kwargs['region_name'] == 'auto'


@pytest.mark.django_db
class TestFallbackSinBoto3:
    """El módulo no debe romper cuando boto3 no está instalado."""

    @override_settings(**R2_CONFIG)
    def test_funciones_degradan_sin_boto3(self):
        with mock.patch.object(services_storage, 'boto3', None):
            assert services_storage.generar_url_subida_prefirmada('x.pdf') is None
            assert services_storage.generar_url_descarga_prefirmada('x.pdf') is None
