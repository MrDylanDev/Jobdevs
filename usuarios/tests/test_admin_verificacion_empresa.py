import pytest
from django.urls import reverse
from django.utils import timezone

from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from usuarios.models import PerfilEmpresa

URL_NAME = 'admin_resolver_verificacion_empresa'


@pytest.fixture
def perfil(empresa_user):
    return PerfilEmpresa.objects.create(
        usuario=empresa_user,
        tipo_persona='juridica',
        tipo_documento='NIT',
        numero_documento='900123456',
        digito_verificacion='7',
        razon_social='Acme S.A.S.',
        documento_soporte='verificaciones/empresas/rut.pdf',
        estado_verificacion='en_revision',
        fecha_solicitud_verificacion=timezone.now(),
    )


def _url(perfil):
    return reverse(URL_NAME, args=[perfil.id])


# ── Permisos ────────────────────────────────────────────────────────────────

def test_anonimo_redirige_a_login(client, perfil):
    response = client.post(_url(perfil), {'accion': 'aprobar'})
    assert response.status_code == 302
    assert reverse('login') in response.url
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == 'en_revision'


def test_empresa_recibe_403(auth_client, perfil):
    assert auth_client.post(_url(perfil), {'accion': 'aprobar'}).status_code == 403
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == 'en_revision'


def test_desarrollador_recibe_403(dev_client, perfil):
    assert dev_client.post(_url(perfil), {'accion': 'aprobar'}).status_code == 403
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == 'en_revision'


def test_get_no_permitido(admin_client, perfil):
    assert admin_client.get(_url(perfil)).status_code == 405


# ── Aprobación ──────────────────────────────────────────────────────────────

def test_aprobar_actualiza_perfil(admin_client, admin_user, perfil):
    antes = timezone.now()
    response = admin_client.post(
        _url(perfil), {'accion': 'aprobar', 'notas': 'Documentos en regla'}
    )
    assert response.status_code == 302
    assert response.url.startswith(reverse('dashboard_admin'))
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == 'verificada'
    assert perfil.verificado_por == admin_user
    assert perfil.fecha_verificacion is not None
    assert perfil.fecha_verificacion >= antes
    assert perfil.notas_auditoria == 'Documentos en regla'


def test_aprobar_sin_notas(admin_client, perfil):
    admin_client.post(_url(perfil), {'accion': 'aprobar'})
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == 'verificada'
    assert not perfil.notas_auditoria


def test_aprobar_crea_log_y_notificacion(admin_client, admin_user, empresa_user, perfil):
    admin_client.post(_url(perfil), {'accion': 'aprobar'})
    log = LogAuditoria.objects.get(tabla_afectada='perfil_empresa', registro_id=perfil.id)
    assert log.usuario == admin_user
    assert 'aprob' in log.accion.lower()
    notif = Notificacion.objects.get(usuario=empresa_user)
    assert 'verificad' in notif.mensaje.lower() or 'aprob' in notif.mensaje.lower()


# ── Rechazo ─────────────────────────────────────────────────────────────────

def test_rechazar_actualiza_perfil(admin_client, admin_user, perfil):
    response = admin_client.post(
        _url(perfil), {'accion': 'rechazar', 'notas': 'Documento ilegible'}
    )
    assert response.status_code == 302
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == 'rechazada'
    assert perfil.verificado_por == admin_user
    assert perfil.fecha_verificacion is not None
    assert perfil.notas_auditoria == 'Documento ilegible'


def test_rechazar_crea_log_y_notificacion_con_motivo(
    admin_client, admin_user, empresa_user, perfil
):
    admin_client.post(_url(perfil), {'accion': 'rechazar', 'notas': 'Documento ilegible'})
    log = LogAuditoria.objects.get(tabla_afectada='perfil_empresa', registro_id=perfil.id)
    assert log.usuario == admin_user
    assert 'rechaz' in log.accion.lower()
    notif = Notificacion.objects.get(usuario=empresa_user)
    assert 'Documento ilegible' in notif.mensaje


def test_rechazar_exige_motivo(admin_client, empresa_user, perfil):
    admin_client.post(_url(perfil), {'accion': 'rechazar', 'notas': '  '})
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == 'en_revision'
    assert not Notificacion.objects.filter(usuario=empresa_user).exists()
    assert not LogAuditoria.objects.filter(
        tabla_afectada='perfil_empresa', registro_id=perfil.id
    ).exists()


def test_accion_invalida_no_cambia_estado(admin_client, perfil):
    admin_client.post(_url(perfil), {'accion': 'otra'})
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == 'en_revision'


def test_solo_resuelve_solicitudes_en_revision(admin_client, empresa_user, perfil):
    perfil.estado_verificacion = 'verificada'
    perfil.save()
    admin_client.post(_url(perfil), {'accion': 'rechazar', 'notas': 'x'})
    perfil.refresh_from_db()
    assert perfil.estado_verificacion == 'verificada'
    assert not Notificacion.objects.filter(usuario=empresa_user).exists()


def test_perfil_inexistente_404(admin_client):
    assert admin_client.post(
        reverse(URL_NAME, args=[999999]), {'accion': 'aprobar'}
    ).status_code == 404


# ── Dashboard ───────────────────────────────────────────────────────────────

def test_dashboard_contexto_empresas_en_revision(admin_client, perfil):
    response = admin_client.get(reverse('dashboard_admin'))
    assert response.status_code == 200
    assert list(response.context['empresas_en_revision']) == [perfil]
    assert response.context['total_empresas_en_revision'] == 1


def test_dashboard_excluye_otros_estados(admin_client, perfil):
    perfil.estado_verificacion = 'verificada'
    perfil.save()
    response = admin_client.get(reverse('dashboard_admin'))
    assert list(response.context['empresas_en_revision']) == []
    assert response.context['total_empresas_en_revision'] == 0


def test_dashboard_renderiza_panel_verificacion(admin_client, perfil):
    html = admin_client.get(reverse('dashboard_admin')).content.decode()
    assert 'Verificación de Empresas' in html
    assert 'Acme S.A.S.' in html
    assert '900123456-7' in html
    doc_url = reverse('descargar_documento_soporte_empresa', args=[perfil.id])
    assert doc_url in html
    assert perfil.documento_soporte.url not in html
    assert 'aria-label="Motivo del rechazo de verificación"' in html
    assert _url(perfil) in html
    assert 'value="aprobar"' in html
    assert 'value="rechazar"' in html


def test_dashboard_sin_documento_no_muestra_enlace(admin_client, perfil):
    perfil.documento_soporte = ''
    perfil.save()
    html = admin_client.get(reverse('dashboard_admin')).content.decode()
    assert 'Acme S.A.S.' in html
    assert 'verificaciones/empresas/rut.pdf' not in html


def test_dashboard_limita_a_50_y_cuenta_total(admin_client, perfil):
    from usuarios.models import Usuario
    for i in range(55):
        u = Usuario.objects.create_user(
            username=f'emp_extra_{i}', email=f'extra{i}@test.jobdevs', nombre=f'Extra {i}',
            rol='empresa', estado='activo', password='x',
        )
        PerfilEmpresa.objects.create(
            usuario=u, razon_social=f'Extra {i}', estado_verificacion='en_revision',
            fecha_solicitud_verificacion=timezone.now(),
        )
    response = admin_client.get(reverse('dashboard_admin'))
    assert response.context['total_empresas_en_revision'] == 56
    assert len(response.context['empresas_en_revision']) == 50


# ── Descarga privada del documento de soporte ───────────────────────────────

def _doc_url(perfil):
    return reverse('descargar_documento_soporte_empresa', args=[perfil.id])


@pytest.fixture
def perfil_con_archivo(perfil, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    from django.core.files.base import ContentFile
    perfil.documento_soporte.save('rut.pdf', ContentFile(b'%PDF-1.4 secreto'), save=True)
    return perfil


def test_descarga_documento_anonimo_redirige_a_login(client, perfil_con_archivo):
    response = client.get(_doc_url(perfil_con_archivo))
    assert response.status_code == 302
    assert reverse('login') in response.url


def test_descarga_documento_admin_ok(admin_client, perfil_con_archivo):
    response = admin_client.get(_doc_url(perfil_con_archivo))
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'
    assert b''.join(response.streaming_content) == b'%PDF-1.4 secreto'


def test_descarga_documento_empresa_duena_ok(client, perfil_con_archivo, empresa_user):
    client.force_login(empresa_user)
    assert client.get(_doc_url(perfil_con_archivo)).status_code == 200


def test_descarga_documento_otro_usuario_403(dev_client, perfil_con_archivo):
    assert dev_client.get(_doc_url(perfil_con_archivo)).status_code == 403


def test_descarga_documento_sin_archivo_404(admin_client, perfil):
    perfil.documento_soporte = ''
    perfil.save()
    assert admin_client.get(_doc_url(perfil)).status_code == 404
