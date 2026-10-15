import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date

from usuarios.models import FichaSena

User = get_user_model()


class TestRegistroView:
    """Tests for registro_view at /registro/"""

    def test_registro_page_loads(self, client):
        """GET /registro/ returns 200 and registration form."""
        response = client.get(reverse('registro'))
        assert response.status_code == 200

    def test_registro_desarrollador_success(self, client):
        """Valid desarrollador registration creates user and logs in."""
        response = client.post(reverse('registro'), {
            'username': 'nuevodev',
            'nombre': 'Nuevo Dev',
            'tipo_documento': 'cedula',
            'identificacion': '1234567890',
            'email': 'nuevodev@test.teir',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 302
        assert response.url == reverse('dashboard_desarrollador')
        assert User.objects.filter(username='nuevodev').exists()
        user = User.objects.get(username='nuevodev')
        assert user.rol == 'desarrollador'
        assert user.estado == 'activo'

    def test_registro_empresa_success(self, client):
        """Valid empresa registration creates user and logs in."""
        response = client.post(reverse('registro'), {
            'username': 'nuevaempresa',
            'nombre': 'Nueva Empresa',
            'tipo_documento': 'nit',
            'identificacion': '900123456-7',
            'email': 'empresanueva@test.teir',
            'fecha_nacimiento': '1990-06-15',
            'rol': 'empresa',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 302
        assert response.url == reverse('dashboard_empresa')
        assert User.objects.filter(username='nuevaempresa').exists()

    def test_registro_missing_required_fields(self, client):
        """Missing required fields return form with errors."""
        response = client.post(reverse('registro'), {
            'username': '',
            'nombre': '',
            'email': '',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 200

    def test_registro_password_mismatch(self, client):
        """Non-matching passwords return form with error."""
        response = client.post(reverse('registro'), {
            'username': 'fallido',
            'nombre': 'Fallido',
            'tipo_documento': 'cedula',
            'identificacion': '1111111111',
            'email': 'fallido@test.teir',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPass123!',
            'password2': 'Different!',
        })
        assert response.status_code == 200

    def test_registro_underage(self, client):
        """User under 18 cannot register."""
        response = client.post(reverse('registro'), {
            'username': 'menor',
            'nombre': 'Menor Edad',
            'tipo_documento': 'cedula',
            'identificacion': '2222222222',
            'email': 'menor@test.teir',
            'fecha_nacimiento': str(date.today().year - 16) + '-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='menor').exists()

    def test_registro_dev_with_nit_rejected(self, client):
        """Developer with NIT is rejected."""
        response = client.post(reverse('registro'), {
            'username': 'devnit',
            'nombre': 'Dev con NIT',
            'tipo_documento': 'nit',
            'identificacion': '800123456-1',
            'email': 'devnit@test.teir',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='devnit').exists()

    def test_registro_desarrollador_con_ficha_en_lista_blanca_se_verifica_automaticamente(self, client):
        admin = User.objects.create_user(
            username='admin_test',
            email='admin@test.teir',
            password='TestPass123!',
            rol='administrador',
            identificacion='1111111111',
        )
        FichaSena.objects.create(
            numero_ficha='2670123',
            programa_formacion='ADSO',
            activa=True,
            creada_por=admin,
        )

        response = client.post(reverse('registro'), {
            'username': 'devconvalida',
            'nombre': 'Dev Verificado',
            'tipo_documento': 'cedula',
            'identificacion': '1234500001',
            'email': 'devvalida@test.teir',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'ficha': '2670123',
            'programa_formacion': 'ADSO',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 302
        user = User.objects.get(username='devconvalida')
        assert user.perfil_desarrollador.estado_verificacion == 'verificado'
        assert user.perfil_desarrollador.es_verificado_sena is True
        assert user.perfil_desarrollador.ficha == '2670123'

    def test_registro_desarrollador_sin_ficha_queda_sin_verificar(self, client):
        response = client.post(reverse('registro'), {
            'username': 'devsinficha',
            'nombre': 'Dev Sin Ficha',
            'tipo_documento': 'cedula',
            'identificacion': '1234500002',
            'email': 'devsinficha@test.teir',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 302
        user = User.objects.get(username='devsinficha')
        assert user.perfil_desarrollador.estado_verificacion == 'sin_verificar'
        assert user.perfil_desarrollador.es_verificado_sena is False

    def test_registro_desarrollador_con_ficha_no_en_lista_blanca_queda_sin_verificar(self, client):
        response = client.post(reverse('registro'), {
            'username': 'devfichano',
            'nombre': 'Dev Ficha No',
            'tipo_documento': 'cedula',
            'identificacion': '1234500003',
            'email': 'devfichano@test.teir',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'ficha': '9999999',
            'programa_formacion': 'Desconocido',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 302
        user = User.objects.get(username='devfichano')
        assert user.perfil_desarrollador.estado_verificacion == 'sin_verificar'
        assert user.perfil_desarrollador.ficha == '9999999'
        assert user.perfil_desarrollador.es_verificado_sena is False

