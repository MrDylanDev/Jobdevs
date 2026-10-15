import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from usuarios.models import FichaSena, PerfilDesarrollador

Usuario = get_user_model()


@pytest.fixture
def admin_user(db):
    return Usuario.objects.create_user(
        username='admin_sena',
        email='admin@sena.edu.co',
        password='Password123!',
        rol='administrador',
        identificacion='1000000001',
    )


@pytest.fixture
def dev_user(db):
    user = Usuario.objects.create_user(
        username='aprendiz_pedro',
        email='pedro@sena.edu.co',
        password='Password123!',
        rol='desarrollador',
        identificacion='1000000002',
    )
    PerfilDesarrollador.objects.get_or_create(usuario=user)
    return user


@pytest.fixture
def empresa_user(db):
    return Usuario.objects.create_user(
        username='empresa_corp',
        email='empresa@corp.com',
        password='Password123!',
        rol='empresa',
        identificacion='900999888',
    )


@pytest.fixture
def dev_en_revision(dev_user):
    perfil = dev_user.perfil_desarrollador
    perfil.estado_verificacion = 'en_revision'
    perfil.ficha = '2670123'
    perfil.programa_formacion = 'ADSO'
    perfil.documento_soporte = SimpleUploadedFile('doc.pdf', b'%PDF-1.4 sena', content_type='application/pdf')
    perfil.save()
    return perfil


@pytest.mark.django_db
class TestAdminResolverVerificacionDesarrollador:
    def test_anonimo_redirige_a_login(self, client, dev_en_revision):
        url = reverse('admin_resolver_verificacion_desarrollador', args=[dev_en_revision.id])
        response = client.post(url, {'accion': 'aprobar'})
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_no_admin_recibe_403(self, client, dev_en_revision, empresa_user, dev_user):
        url = reverse('admin_resolver_verificacion_desarrollador', args=[dev_en_revision.id])
        client.force_login(empresa_user)
        assert client.post(url, {'accion': 'aprobar'}).status_code == 403

        client.force_login(dev_user)
        assert client.post(url, {'accion': 'aprobar'}).status_code == 403

    def test_get_no_permitido(self, client, admin_user, dev_en_revision):
        client.force_login(admin_user)
        url = reverse('admin_resolver_verificacion_desarrollador', args=[dev_en_revision.id])
        response = client.get(url)
        assert response.status_code == 405

    def test_aprobar_desarrollador_actualiza_perfil_y_notifica(self, client, admin_user, dev_en_revision, dev_user):
        client.force_login(admin_user)
        url = reverse('admin_resolver_verificacion_desarrollador', args=[dev_en_revision.id])
        response = client.post(url, {'accion': 'aprobar', 'notas': 'Todo verificado en SofíaPlus'}, follow=True)
        assert response.status_code == 200

        dev_en_revision.refresh_from_db()
        assert dev_en_revision.estado_verificacion == 'verificado'
        assert dev_en_revision.es_verificado_sena is True
        assert dev_en_revision.verificado_por == admin_user
        assert dev_en_revision.notas_auditoria == 'Todo verificado en SofíaPlus'

        assert LogAuditoria.objects.filter(usuario=admin_user, tabla_afectada='perfil_desarrollador').exists()
        assert Notificacion.objects.filter(usuario=dev_user, tipo='aprobacion').exists()

    def test_rechazar_desarrollador_con_motivo(self, client, admin_user, dev_en_revision, dev_user):
        client.force_login(admin_user)
        url = reverse('admin_resolver_verificacion_desarrollador', args=[dev_en_revision.id])
        response = client.post(url, {'accion': 'rechazar', 'notas': 'Documento ilegible'}, follow=True)
        assert response.status_code == 200

        dev_en_revision.refresh_from_db()
        assert dev_en_revision.estado_verificacion == 'rechazado'
        assert dev_en_revision.es_verificado_sena is False
        assert dev_en_revision.notas_auditoria == 'Documento ilegible'

        assert Notificacion.objects.filter(usuario=dev_user, tipo='alerta').exists()

    def test_rechazar_sin_motivo_no_cambia_estado(self, client, admin_user, dev_en_revision):
        client.force_login(admin_user)
        url = reverse('admin_resolver_verificacion_desarrollador', args=[dev_en_revision.id])
        response = client.post(url, {'accion': 'rechazar', 'notas': ''}, follow=True)
        assert response.status_code == 200

        dev_en_revision.refresh_from_db()
        assert dev_en_revision.estado_verificacion == 'en_revision'


@pytest.mark.django_db
class TestAdminGestionListaBlancaFichas:
    def test_crear_ficha_sena_ok(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse('admin_crear_ficha_sena')
        response = client.post(url, {
            'numero_ficha': '2670111',
            'programa_formacion': 'ADSO',
            'regional': 'Distrito Capital',
            'centro_formacion': 'Centro de Servicios Financieros',
        }, follow=True)
        assert response.status_code == 200
        assert FichaSena.objects.filter(numero_ficha='2670111').exists()
        ficha = FichaSena.objects.get(numero_ficha='2670111')
        assert ficha.programa_formacion == 'ADSO'
        assert ficha.activa is True
        assert ficha.creada_por == admin_user
        assert LogAuditoria.objects.filter(tabla_afectada='fichas_sena', registro_id=ficha.id).exists()

    def test_crear_ficha_sena_duplicada_muestra_error(self, client, admin_user):
        FichaSena.objects.create(numero_ficha='2670222', programa_formacion='ADSO', creada_por=admin_user)
        client.force_login(admin_user)
        url = reverse('admin_crear_ficha_sena')
        response = client.post(url, {
            'numero_ficha': '2670222',
            'programa_formacion': 'ADSO',
        }, follow=True)
        assert response.status_code == 200
        assert FichaSena.objects.filter(numero_ficha='2670222').count() == 1

    def test_toggle_ficha_sena(self, client, admin_user):
        ficha = FichaSena.objects.create(numero_ficha='2670333', programa_formacion='ADSO', activa=True, creada_por=admin_user)
        client.force_login(admin_user)
        url = reverse('admin_toggle_ficha_sena', args=[ficha.id])
        response = client.post(url, follow=True)
        assert response.status_code == 200
        ficha.refresh_from_db()
        assert ficha.activa is False

        # Activar de nuevo
        response = client.post(url, follow=True)
        assert response.status_code == 200
        ficha.refresh_from_db()
        assert ficha.activa is True


@pytest.mark.django_db
class TestDashboardAdminContextoVerificacionSena:
    def test_contexto_incluye_fichas_y_desarrolladores_en_revision(self, client, admin_user, dev_en_revision):
        FichaSena.objects.create(numero_ficha='2670444', programa_formacion='ADSO', creada_por=admin_user)
        client.force_login(admin_user)
        response = client.get(reverse('dashboard_admin'))
        assert response.status_code == 200
        assert 'desarrolladores_en_revision' in response.context
        assert 'total_desarrolladores_en_revision' in response.context
        assert response.context['total_desarrolladores_en_revision'] >= 1
        assert 'fichas_sena' in response.context
        assert 'total_fichas_sena' in response.context
        assert response.context['total_fichas_sena'] >= 1

    def test_dashboard_muestra_egresado_en_revision(self, client, admin_user, dev_user):
        perfil = dev_user.perfil_desarrollador
        perfil.condicion_sena = 'egresado'
        perfil.estado_verificacion = 'en_revision'
        perfil.programa_formacion = 'ADSO Tecnólogo'
        perfil.documento_soporte = SimpleUploadedFile('diploma.pdf', b'%PDF-1.4 sena', content_type='application/pdf')
        perfil.save()

        client.force_login(admin_user)
        response = client.get(reverse('dashboard_admin'))
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Egresado SENA' in content
        assert 'Ver Diploma' in content
