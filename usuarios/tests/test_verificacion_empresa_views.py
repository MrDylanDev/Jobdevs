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
        username='admin2', email='a2@test.teir', nombre='Admin 2',
        rol='administrador', estado='activo', password='x',
    )
    auth_client.post(reverse(URL_NAME), _payload())
    admins = Usuario.objects.filter(rol='administrador')
    assert admins.count() >= 3  # system_admin + admin_user + otro
    for admin in admins:
        assert Notificacion.objects.filter(usuario=admin).count() == 1
    assert Notificacion.objects.filter(usuario=otro).exists()
    assert not Notificacion.objects.filter(usuario=perfil.usuario).exists()


def test_post_con_cc_calcula_dv(auth_client, perfil):
    auth_client.post(reverse(URL_NAME), _payload(
        tipo_persona='natural', tipo_documento='CC', numero_documento='1234567890',
    ))
    perfil.refresh_from_db()
    assert perfil.numero_documento == '1234567890'
    assert perfil.digito_verificacion == str(calcular_dv_dian('1234567890'))


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
