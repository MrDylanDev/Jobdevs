import io
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

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
        username='aprendiz_carlos',
        email='carlos@sena.edu.co',
        password='Password123!',
        rol='desarrollador',
        identificacion='1000000002',
    )
    PerfilDesarrollador.objects.get_or_create(usuario=user)
    return user


@pytest.fixture
def otro_dev_user(db):
    user = Usuario.objects.create_user(
        username='aprendiz_ana',
        email='ana@sena.edu.co',
        password='Password123!',
        rol='desarrollador',
        identificacion='1000000003',
    )
    PerfilDesarrollador.objects.get_or_create(usuario=user)
    return user


@pytest.fixture
def empresa_user(db):
    return Usuario.objects.create_user(
        username='empresa_tech',
        email='contacto@tech.com',
        password='Password123!',
        rol='empresa',
        identificacion='900123456',
    )


@pytest.fixture
def ficha_activa(db, admin_user):
    return FichaSena.objects.create(
        numero_ficha='2670123',
        programa_formacion='Análisis y Desarrollo de Software (ADSO)',
        activa=True,
        creada_por=admin_user,
    )


@pytest.mark.django_db
class TestVerificacionDesarrolladorViews:
    def test_anonimo_redirige_a_login(self, client):
        url = reverse('solicitar_verificacion_desarrollador')
        response = client.get(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_empresa_recibe_403(self, client, empresa_user):
        client.force_login(empresa_user)
        response = client.get(reverse('solicitar_verificacion_desarrollador'))
        assert response.status_code == 403

    def test_administrador_recibe_403(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse('solicitar_verificacion_desarrollador'))
        assert response.status_code == 403

    def test_desarrollador_get_muestra_formulario(self, client, dev_user):
        client.force_login(dev_user)
        response = client.get(reverse('solicitar_verificacion_desarrollador'))
        assert response.status_code == 200
        assert 'perfil' in response.context
        assert 'desarrollador/verificacion.html' in [t.name for t in response.templates]

    def test_desarrollador_post_con_ficha_en_lista_blanca_verifica_automaticamente(
        self, client, dev_user, ficha_activa
    ):
        client.force_login(dev_user)
        response = client.post(
            reverse('solicitar_verificacion_desarrollador'),
            {
                'metodo': 'automatica',
                'ficha': '2670123',
                'programa_formacion': 'ADSO',
            },
            follow=True,
        )
        assert response.status_code == 200
        perfil = dev_user.perfil_desarrollador
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'verificado'
        assert perfil.es_verificado_sena is True
        assert perfil.ficha_sena == ficha_activa

    def test_desarrollador_post_automatica_con_ficha_invalida_muestra_error(
        self, client, dev_user
    ):
        client.force_login(dev_user)
        response = client.post(
            reverse('solicitar_verificacion_desarrollador'),
            {
                'metodo': 'automatica',
                'ficha': '0000000',
                'programa_formacion': 'ADSO',
            },
        )
        assert response.status_code == 200
        perfil = dev_user.perfil_desarrollador
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'sin_verificar'
        assert 'errores' in response.context
        assert 'ficha' in response.context['errores']

    def test_desarrollador_post_manual_con_pdf_pasa_a_en_revision(
        self, client, dev_user
    ):
        client.force_login(dev_user)
        pdf_file = SimpleUploadedFile(
            'soporte_sena.pdf',
            b'%PDF-1.4 test soporte sena valido',
            content_type='application/pdf',
        )
        response = client.post(
            reverse('solicitar_verificacion_desarrollador'),
            {
                'metodo': 'manual',
                'ficha': '2899999',
                'programa_formacion': 'ADSO',
                'documento_soporte': pdf_file,
            },
            follow=True,
        )
        assert response.status_code == 200
        perfil = dev_user.perfil_desarrollador
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'en_revision'
        assert perfil.ficha == '2899999'
        assert bool(perfil.documento_soporte) is True

    def test_desarrollador_post_manual_egresado_con_diploma_pasa_a_en_revision(
        self, client, dev_user
    ):
        client.force_login(dev_user)
        pdf_file = SimpleUploadedFile(
            'diploma_egresado.pdf',
            b'%PDF-1.4 diploma egresado sena',
            content_type='application/pdf',
        )
        response = client.post(
            reverse('solicitar_verificacion_desarrollador'),
            {
                'metodo': 'manual',
                'condicion_sena': 'egresado',
                'ficha': '',
                'programa_formacion': 'ADSO',
                'documento_soporte': pdf_file,
            },
            follow=True,
        )
        assert response.status_code == 200
        perfil = dev_user.perfil_desarrollador
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'en_revision'
        assert perfil.condicion_sena == 'egresado'
        assert bool(perfil.documento_soporte) is True

    def test_desarrollador_en_revision_bloquea_nuevo_post(
        self, client, dev_user
    ):
        perfil = dev_user.perfil_desarrollador
        perfil.estado_verificacion = 'en_revision'
        perfil.save()

        client.force_login(dev_user)
        response = client.post(
            reverse('solicitar_verificacion_desarrollador'),
            {'metodo': 'automatica', 'ficha': '2670123'},
            follow=True,
        )
        assert response.status_code == 200
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'en_revision'

    def test_desarrollador_verificado_no_permite_reenvio(
        self, client, dev_user, ficha_activa
    ):
        perfil = dev_user.perfil_desarrollador
        perfil.estado_verificacion = 'verificado'
        perfil.ficha_sena = ficha_activa
        perfil.save()

        client.force_login(dev_user)
        response = client.post(
            reverse('solicitar_verificacion_desarrollador'),
            {'metodo': 'automatica', 'ficha': '2670123'},
            follow=True,
        )
        assert response.status_code == 200
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'verificado'


@pytest.mark.django_db
class TestDescargarDocumentoSoporteDesarrollador:
    def test_descarga_documento_anonimo_redirige_a_login(self, client, dev_user):
        url = reverse('descargar_documento_soporte_desarrollador', args=[dev_user.perfil_desarrollador.id])
        response = client.get(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_descarga_documento_admin_ok(self, client, admin_user, dev_user):
        perfil = dev_user.perfil_desarrollador
        perfil.documento_soporte = SimpleUploadedFile('doc.pdf', b'%PDF-1.4 sena', content_type='application/pdf')
        perfil.save()

        client.force_login(admin_user)
        url = reverse('descargar_documento_soporte_desarrollador', args=[perfil.id])
        response = client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'

    def test_descarga_documento_dev_dueno_ok(self, client, dev_user):
        perfil = dev_user.perfil_desarrollador
        perfil.documento_soporte = SimpleUploadedFile('doc.pdf', b'%PDF-1.4 sena', content_type='application/pdf')
        perfil.save()

        client.force_login(dev_user)
        url = reverse('descargar_documento_soporte_desarrollador', args=[perfil.id])
        response = client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'

    def test_descarga_documento_otro_dev_recibe_403(self, client, otro_dev_user, dev_user):
        perfil = dev_user.perfil_desarrollador
        perfil.documento_soporte = SimpleUploadedFile('doc.pdf', b'%PDF-1.4 sena', content_type='application/pdf')
        perfil.save()

        client.force_login(otro_dev_user)
        url = reverse('descargar_documento_soporte_desarrollador', args=[perfil.id])
        response = client.get(url)
        assert response.status_code == 403
