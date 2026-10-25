from unittest import mock

import pytest
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from usuarios.models import PerfilEmpresa, Usuario
from usuarios.utils_dian import calcular_dv_dian

URL_NAME = 'solicitar_verificacion_empresa'
NIT = '900123456'


@pytest.fixture(autouse=True)
def media_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def perfil(empresa_user):
    return PerfilEmpresa.objects.create(usuario=empresa_user)


def _pdf(name='rut.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 contenido simulado', content_type='application/pdf')


def _payload(**overrides):
    data = {
        'tipo_persona': 'juridica',
        'tipo_documento': 'NIT',
        'numero_documento': '900.123.456',
        'razon_social': 'Acme S.A.S.',
        'documento_soporte': _pdf(),
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not None}


def _messages(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


# --- Acceso ---

def test_anonimo_redirige_a_login(client):
    response = client.get(reverse(URL_NAME))
    assert response.status_code == 302
    assert reverse('login') in response.url


def test_desarrollador_recibe_403(dev_client):
    assert dev_client.get(reverse(URL_NAME)).status_code == 403
    assert dev_client.post(reverse(URL_NAME), _payload()).status_code == 403


def test_administrador_recibe_403(admin_client):
    assert admin_client.get(reverse(URL_NAME)).status_code == 403


# --- GET ---

def test_get_muestra_formulario(auth_client, perfil):
    response = auth_client.get(reverse(URL_NAME))
    assert response.status_code == 200
    html = response.content.decode()
    assert 'enctype="multipart/form-data"' in html
    for name in ('tipo_persona', 'tipo_documento', 'numero_documento', 'razon_social', 'documento_soporte'):
        assert f'name="{name}"' in html


def test_get_crea_perfil_si_no_existe(auth_client, empresa_user):
    assert auth_client.get(reverse(URL_NAME)).status_code == 200
    assert PerfilEmpresa.objects.filter(usuario=empresa_user).exists()


def test_verificada_muestra_card_sin_formulario(auth_client, perfil):
    perfil.estado_verificacion = 'verificada'
    perfil.save()
    response = auth_client.get(reverse(URL_NAME))
    html = response.content.decode()
    assert response.status_code == 200
    assert 'verificación exitosa' in html.lower()
    assert 'name="documento_soporte"' not in html


def test_verificada_no_permite_reenvio(auth_client, perfil):
    perfil.estado_verificacion = 'verificada'
    perfil.save()
    response = auth_client.post(reverse(URL_NAME), _payload())
    perfil.refresh_from_db()
    assert response.status_code == 302
    assert perfil.estado_verificacion == 'verificada'
    assert not perfil.numero_documento
    assert not LogAuditoria.objects.filter(tabla_afectada='perfil_empresa').exists()


# --- POST exitoso ---

def test_post_exitoso_guarda_datos_y_pasa_a_en_revision(auth_client, perfil, empresa_user):
    response = auth_client.post(reverse(URL_NAME), _payload())
    assert response.status_code == 302
    perfil.refresh_from_db()
    assert perfil.tipo_persona == 'juridica'
    assert perfil.tipo_documento == 'NIT'
    assert perfil.numero_documento == NIT
    assert perfil.digito_verificacion == str(calcular_dv_dian(NIT))
    assert perfil.razon_social == 'Acme S.A.S.'
    assert perfil.documento_soporte.name.startswith('verificaciones/empresas/')
    assert perfil.documento_soporte.name.endswith('.pdf')
    assert perfil.estado_verificacion == 'en_revision'
    assert perfil.fecha_solicitud_verificacion is not None


def test_post_exitoso_registra_log_y_mensaje(auth_client, perfil, empresa_user):
    response = auth_client.post(reverse(URL_NAME), _payload())
    log = LogAuditoria.objects.get(tabla_afectada='perfil_empresa')
    assert log.usuario == empresa_user
    assert log.registro_id == perfil.id
    assert any('revisi' in m.lower() for m in _messages(response))


def test_post_exitoso_notifica_a_todos_los_administradores(auth_client, perfil, admin_user):
    otro = Usuario.objects.create_user(
        username='admin2', email='a2@test.jobdevs', nombre='Admin 2',
        rol='administrador', estado='activo', password='x',
    )
    auth_client.post(reverse(URL_NAME), _payload())
    admins = Usuario.objects.filter(rol='administrador')
    assert admins.count() >= 3  # system_admin + admin_user + otro
    for admin in admins:
        assert Notificacion.objects.filter(usuario=admin).count() == 1
    assert Notificacion.objects.filter(usuario=otro).exists()
    assert not Notificacion.objects.filter(usuario=perfil.usuario).exists()


def test_post_con_cc_no_guarda_dv(auth_client, perfil):
    auth_client.post(reverse(URL_NAME), _payload(
        tipo_persona='natural', tipo_documento='CC', numero_documento='1234567890',
    ))
    perfil.refresh_from_db()
    assert perfil.numero_documento == '1234567890'
    assert perfil.digito_verificacion is None
    assert perfil.documento_completo == '1234567890'


def test_post_con_nit_guarda_dv(auth_client, perfil):
    auth_client.post(reverse(URL_NAME), _payload())
    perfil.refresh_from_db()
    assert perfil.digito_verificacion == str(calcular_dv_dian(NIT))


# --- POST inválido ---

def _assert_sin_cambios(perfil, estado='sin_verificar'):
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == estado
    assert perfil.fecha_solicitud_verificacion is None
    assert not LogAuditoria.objects.filter(tabla_afectada='perfil_empresa').exists()


def test_post_sin_numero_documento_muestra_error(auth_client, perfil):
    response = auth_client.post(reverse(URL_NAME), _payload(numero_documento=''))
    assert response.status_code == 200
    assert 'El número de documento es obligatorio' in response.content.decode()
    _assert_sin_cambios(perfil)


def test_post_sin_archivo_muestra_error(auth_client, perfil):
    response = auth_client.post(reverse(URL_NAME), _payload(documento_soporte=None))
    assert response.status_code == 200
    assert 'Adjunta el documento de soporte' in response.content.decode()
    _assert_sin_cambios(perfil)


def test_post_numero_no_numerico_muestra_error(auth_client, perfil):
    response = auth_client.post(reverse(URL_NAME), _payload(numero_documento='ABC123'))
    assert response.status_code == 200
    assert 'solo puede contener dígitos' in response.content.decode()
    _assert_sin_cambios(perfil)


def test_post_sin_razon_social_muestra_error(auth_client, perfil):
    response = auth_client.post(reverse(URL_NAME), _payload(razon_social=' '))
    assert response.status_code == 200
    assert 'La razón social es obligatoria' in response.content.decode()
    _assert_sin_cambios(perfil)


def test_post_archivo_no_pdf_muestra_error(auth_client, perfil):
    archivo = SimpleUploadedFile('rut.exe', b'MZ', content_type='application/octet-stream')
    response = auth_client.post(reverse(URL_NAME), _payload(documento_soporte=archivo))
    assert response.status_code == 200
    assert 'debe ser un archivo PDF' in response.content.decode()
    _assert_sin_cambios(perfil)


def test_post_tipo_invalido_muestra_error(auth_client, perfil):
    response = auth_client.post(reverse(URL_NAME), _payload(tipo_documento='XX'))
    assert response.status_code == 200
    assert 'Selecciona un tipo de documento válido' in response.content.decode()
    _assert_sin_cambios(perfil)


# --- Re-envío tras rechazo ---

def test_reenvio_tras_rechazo_vuelve_a_en_revision(auth_client, perfil):
    perfil.estado_verificacion = 'rechazada'
    perfil.notas_auditoria = 'Documento ilegible'
    perfil.save()
    response = auth_client.post(reverse(URL_NAME), _payload())
    assert response.status_code == 302
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == 'en_revision'
    assert perfil.numero_documento == NIT
    assert perfil.fecha_solicitud_verificacion is not None


def test_archivo_pdf_falso_por_contenido_es_rechazado(auth_client, perfil):
    falso = SimpleUploadedFile('rut.pdf', b'MZ no soy un pdf', content_type='application/pdf')
    response = auth_client.post(reverse(URL_NAME), _payload(documento_soporte=falso))
    assert response.status_code == 200
    assert 'El archivo debe ser un documento PDF válido.' in response.content.decode()
    _assert_sin_cambios(perfil)


def test_juridica_con_cc_es_rechazada(auth_client, perfil):
    response = auth_client.post(reverse(URL_NAME), _payload(tipo_documento='CC'))
    assert response.status_code == 200
    assert 'Las personas jurídicas deben identificarse con NIT.' in response.content.decode()
    _assert_sin_cambios(perfil)


def test_en_revision_bloquea_post(auth_client, perfil):
    perfil.estado_verificacion = 'en_revision'
    perfil.razon_social = 'Original'
    perfil.save()
    response = auth_client.post(reverse(URL_NAME), _payload(razon_social='Cambiada'))
    assert response.status_code == 302
    assert any('ya se encuentra en revisión' in m for m in _messages(response))
    perfil.refresh_from_db()
    assert perfil.razon_social == 'Original'
    assert perfil.estado_verificacion == 'en_revision'


def test_en_revision_oculta_formulario(auth_client, perfil):
    perfil.estado_verificacion = 'en_revision'
    perfil.save()
    html = auth_client.get(reverse(URL_NAME)).content.decode()
    assert 'name="documento_soporte"' not in html
    assert 'ya se encuentra en revisión' in html


def test_accion_log_se_trunca_a_300(auth_client, perfil):
    auth_client.post(reverse(URL_NAME), _payload(numero_documento=NIT))
    assert all(len(l.accion) <= 300 for l in LogAuditoria.objects.all())


# --- Descarga de documento soporte (S3: R2 con fallback local) ---

def _perfil_con_soporte(perfil):
    perfil.documento_soporte = SimpleUploadedFile(
        'rut.pdf', b'%PDF-1.4 contenido simulado', content_type='application/pdf'
    )
    perfil.save()
    return perfil


def test_descarga_documento_empresa_redirige_a_url_prefirmada(auth_client, perfil):
    perfil = _perfil_con_soporte(perfil)
    url = reverse('descargar_documento_soporte_empresa', args=[perfil.id])

    with mock.patch('usuarios.views.verificacion_views.esta_configurado_r2', return_value=True), \
         mock.patch(
             'usuarios.views.verificacion_views.generar_url_descarga_prefirmada',
             return_value='https://r2.test/descarga?sig=abc',
         ) as mock_url:
        response = auth_client.get(url)

    assert response.status_code == 302
    assert response.url == 'https://r2.test/descarga?sig=abc'
    mock_url.assert_called_once_with(perfil.documento_soporte.name)


def test_descarga_documento_empresa_fallback_local_sin_r2(auth_client, perfil):
    perfil = _perfil_con_soporte(perfil)
    url = reverse('descargar_documento_soporte_empresa', args=[perfil.id])

    with mock.patch('usuarios.views.verificacion_views.esta_configurado_r2', return_value=False):
        response = auth_client.get(url)

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'


def test_descarga_documento_empresa_fallback_local_si_falla_r2(auth_client, perfil):
    perfil = _perfil_con_soporte(perfil)
    url = reverse('descargar_documento_soporte_empresa', args=[perfil.id])

    with mock.patch('usuarios.views.verificacion_views.esta_configurado_r2', return_value=True), \
         mock.patch('usuarios.views.verificacion_views.generar_url_descarga_prefirmada', return_value=None):
        response = auth_client.get(url)

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'


# --- API de subida prefirmada (S4) ---

URL_PRESIGNED = reverse('api_presigned_upload')


def test_api_presigned_upload_anonimo_redirige_a_login(client):
    response = client.post(URL_PRESIGNED, data={}, content_type='application/json')
    assert response.status_code == 302
    assert reverse('login') in response.url


def test_api_presigned_upload_rechaza_get(auth_client):
    assert auth_client.get(URL_PRESIGNED).status_code == 405


def test_api_presigned_upload_503_sin_r2(auth_client):
    with mock.patch('usuarios.views.verificacion_views.esta_configurado_r2', return_value=False):
        response = auth_client.post(
            URL_PRESIGNED,
            data={'nombre_archivo': 'soporte.pdf', 'content_type': 'application/pdf'},
        )

    assert response.status_code == 503
    assert response.json()['r2_disponible'] is False


def test_api_presigned_upload_400_extension_no_permitida(auth_client):
    with mock.patch('usuarios.views.verificacion_views.esta_configurado_r2', return_value=True):
        response = auth_client.post(
            URL_PRESIGNED,
            data={'nombre_archivo': 'malware.exe', 'content_type': 'application/pdf'},
        )

    assert response.status_code == 400
    assert 'error' in response.json()


def test_api_presigned_upload_400_sin_nombre_archivo(auth_client):
    with mock.patch('usuarios.views.verificacion_views.esta_configurado_r2', return_value=True):
        response = auth_client.post(URL_PRESIGNED, data={'content_type': 'application/pdf'})

    assert response.status_code == 400


def test_api_presigned_upload_400_content_type_no_admitido(auth_client):
    with mock.patch('usuarios.views.verificacion_views.esta_configurado_r2', return_value=True):
        response = auth_client.post(
            URL_PRESIGNED,
            data={'nombre_archivo': 'soporte.pdf', 'content_type': 'application/x-msdownload'},
        )

    assert response.status_code == 400


def test_api_presigned_upload_200_con_r2(auth_client):
    resultado = {
        'url': 'https://r2.test/subida?sig=xyz',
        'file_key': 'soportes/abc_soporte.pdf',
        'content_type': 'application/pdf',
        'expira_en': 300,
    }

    with mock.patch('usuarios.views.verificacion_views.esta_configurado_r2', return_value=True), \
         mock.patch(
             'usuarios.views.verificacion_views.generar_url_subida_prefirmada',
             return_value=resultado,
         ) as mock_url:
        response = auth_client.post(
            URL_PRESIGNED,
            data={'nombre_archivo': 'soporte.pdf', 'content_type': 'application/pdf'},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload['r2_disponible'] is True
    assert payload['upload'] == resultado
    mock_url.assert_called_once_with(
        nombre_archivo='soporte.pdf',
        content_type='application/pdf',
        prefijo='soportes/empresa',
    )
