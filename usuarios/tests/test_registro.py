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
            'email': 'nuevodev@test.jobdevs',
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
        """Valid empresa registration creates user and logs in with sector and ciudad (SCRUM-37)."""
        response = client.post(reverse('registro'), {
            'username': 'nuevaempresa',
            'nombre': 'Nueva Empresa',
            'tipo_documento': 'nit',
            'identificacion': '900123456-7',
            'sector': 'Fintech y Banca Digital',
            'ciudad': 'Bogotá D.C.',
            'email': 'empresanueva@test.jobdevs',
            'fecha_nacimiento': '1990-06-15',
            'rol': 'empresa',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 302
        assert response.url == reverse('dashboard_empresa')
        assert User.objects.filter(username='nuevaempresa').exists()
        user = User.objects.get(username='nuevaempresa')
        assert user.perfil_empresa.sector == 'Fintech y Banca Digital'
        assert user.perfil_empresa.ciudad == 'Bogotá D.C.'
        assert user.perfil_empresa.nombre_empresa == 'Nueva Empresa'

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
            'email': 'fallido@test.jobdevs',
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
            'email': 'menor@test.jobdevs',
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
            'email': 'devnit@test.jobdevs',
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
            email='admin@test.jobdevs',
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
            'email': 'devvalida@test.jobdevs',
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
            'email': 'devsinficha@test.jobdevs',
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
            'email': 'devfichano@test.jobdevs',
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

    def test_registro_desarrollador_ficha_lista_blanca_programa_no_coincide_es_rechazado(self, client):
        """SCRUM-229 (RF 1.2.1): el programa debe coincidir con el oficial de la ficha."""
        admin = User.objects.create_user(
            username='admin_programas',
            email='admin_programas@test.jobdevs',
            password='TestPass123!',
            rol='administrador',
            identificacion='1111111199',
        )
        FichaSena.objects.create(
            numero_ficha='2670999',
            programa_formacion='ADSO',
            activa=True,
            creada_por=admin,
        )

        response = client.post(reverse('registro'), {
            'username': 'devprogramano',
            'nombre': 'Dev Programa No',
            'tipo_documento': 'cedula',
            'identificacion': '1234500099',
            'email': 'devprogramano@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'ficha': '2670999',
            'programa_formacion': 'Cocina',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='devprogramano').exists()
        assert 'programa_formacion' in response.context['form'].errors
        assert 'no coincide' in response.context['form'].errors['programa_formacion'][0]

    def test_registro_desarrollador_ficha_lista_blanca_programa_coincide_se_verifica(self, client):
        """SCRUM-229: alias tolerante (ADSO) coincide con el nombre oficial de la ficha."""
        admin = User.objects.create_user(
            username='admin_programas2',
            email='admin_programas2@test.jobdevs',
            password='TestPass123!',
            rol='administrador',
            identificacion='1111111198',
        )
        FichaSena.objects.create(
            numero_ficha='2670998',
            programa_formacion='ADSO',
            activa=True,
            creada_por=admin,
        )

        response = client.post(reverse('registro'), {
            'username': 'devprogramasi',
            'nombre': 'Dev Programa Si',
            'tipo_documento': 'cedula',
            'identificacion': '1234500098',
            'email': 'devprogramasi@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'ficha': '2670998',
            'programa_formacion': 'Análisis y Desarrollo de Software',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 302
        user = User.objects.get(username='devprogramasi')
        assert user.perfil_desarrollador.estado_verificacion == 'verificado'

    def test_registro_desarrollador_sin_ficha_programa_invalido_es_rechazado(self, client):
        """SCRUM-229: sin ficha, el programa debe pertenecer al catálogo oficial."""
        response = client.post(reverse('registro'), {
            'username': 'devinventado',
            'nombre': 'Dev Inventado',
            'tipo_documento': 'cedula',
            'identificacion': '1234500097',
            'email': 'devinventado@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'programa_formacion': 'Inventado 123',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='devinventado').exists()
        assert 'programa_formacion' in response.context['form'].errors
        assert 'válido' in response.context['form'].errors['programa_formacion'][0]

    def test_registro_desarrollador_sin_ficha_programa_catalogo_es_aceptado(self, client):
        """SCRUM-229: sin ficha, un programa del catálogo es aceptado y queda sin verificar."""
        response = client.post(reverse('registro'), {
            'username': 'devvideojuegos',
            'nombre': 'Dev Videojuegos',
            'tipo_documento': 'cedula',
            'identificacion': '1234500096',
            'email': 'devvideojuegos@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'programa_formacion': 'Desarrollo de Videojuegos',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 302
        user = User.objects.get(username='devvideojuegos')
        assert user.perfil_desarrollador.estado_verificacion == 'sin_verificar'

    def test_registro_identificacion_duplicada_muestra_error(self, client):
        """RF 1.1.1 (SCRUM-37): El NIT o número de identificación debe ser único en el sistema."""
        User.objects.create_user(
            username='existente',
            email='existente@test.jobdevs',
            identificacion='900999888-1',
            password='TestPassword123!',
        )
        response = client.post(reverse('registro'), {
            'username': 'intento_duplicado',
            'nombre': 'Empresa Clon',
            'tipo_documento': 'nit',
            'identificacion': '900999888-1',
            'sector': 'Servicios',
            'ciudad': 'Cali',
            'email': 'clon@test.jobdevs',
            'fecha_nacimiento': '1995-01-01',
            'rol': 'empresa',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='intento_duplicado').exists()
        assert 'form' in response.context
        assert 'identificacion' in response.context['form'].errors
        assert 'ya se encuentra registrado' in response.context['form'].errors['identificacion'][0]

    def test_registro_sin_campo_username_autoasigna_email_como_username(self, client):
        """SCRUM-164: Registro sin campo username autoasigna el correo como username en BD."""
        response = client.post(reverse('registro'), {
            'nombre': 'Registro Solo Email',
            'tipo_documento': 'cedula',
            'identificacion': '1040506070',
            'email': 'soloemail@test.jobdevs',
            'fecha_nacimiento': '2001-08-10',
            'rol': 'desarrollador',
            'password1': 'EmailPass123!',
            'password2': 'EmailPass123!',
        })
        assert response.status_code == 302
        assert User.objects.filter(email='soloemail@test.jobdevs').exists()
        user = User.objects.get(email='soloemail@test.jobdevs')
        assert user.username == 'soloemail@test.jobdevs'
        assert user.nombre == 'Registro Solo Email'

    def test_registro_email_duplicado_rechazado(self, client):
        """SCRUM-164: El correo electrónico debe ser único al registrarse."""
        User.objects.create_user(
            username='existente_email@test.jobdevs',
            email='existente_email@test.jobdevs',
            identificacion='1040506099',
            password='TestPassword123!',
        )
        response = client.post(reverse('registro'), {
            'nombre': 'Otro Usuario',
            'tipo_documento': 'cedula',
            'identificacion': '1040506088',
            'email': 'existente_email@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
        })
        assert response.status_code == 200
        assert 'form' in response.context
        assert 'email' in response.context['form'].errors
        assert 'ya se encuentra registrado' in response.context['form'].errors['email'][0]

    def test_registro_despacha_email_bienvenida_desarrollador(self, client):
        """SCRUM-201: El registro de desarrollador despacha un correo de bienvenida asíncrono con Celery."""
        from django.core import mail
        mail.outbox.clear()

        response = client.post(reverse('registro'), {
            'username': 'bienvenida_dev',
            'nombre': 'Aprendiz Juan',
            'tipo_documento': 'cedula',
            'identificacion': '1099887766',
            'email': 'juan_bienvenida@test.jobdevs',
            'fecha_nacimiento': '2001-05-20',
            'rol': 'desarrollador',
            'password1': 'BienvenidoPass123!',
            'password2': 'BienvenidoPass123!',
        })
        assert response.status_code == 302
        assert len(mail.outbox) == 1

        email = mail.outbox[0]
        assert email.to == ['juan_bienvenida@test.jobdevs']
        assert 'Bienvenido a JobDevs' in email.subject
        assert 'Aprendiz Juan' in email.body
        assert 'Ir a mi Panel de Desarrollador' in email.body
        html_body, mime = email.alternatives[0]
        assert mime == 'text/html'
        assert 'desarrollador/dashboard' in html_body

    def test_registro_despacha_email_bienvenida_empresa(self, client):
        """SCRUM-201: El registro de empresa despacha un correo de bienvenida con instrucciones corporativas."""
        from django.core import mail
        mail.outbox.clear()

        response = client.post(reverse('registro'), {
            'username': 'bienvenida_empresa',
            'nombre': 'Empresa Digital SAS',
            'tipo_documento': 'nit',
            'identificacion': '901234567-1',
            'sector': 'Software',
            'ciudad': 'Medellín',
            'email': 'contacto@digital.jobdevs',
            'fecha_nacimiento': '1995-10-10',
            'rol': 'empresa',
            'password1': 'BienvenidoPass123!',
            'password2': 'BienvenidoPass123!',
        })
        assert response.status_code == 302
        assert len(mail.outbox) == 1

        email = mail.outbox[0]
        assert email.to == ['contacto@digital.jobdevs']
        assert 'Empresa Digital SAS' in email.body
        assert 'Ir a mi Panel de Empresa' in email.body
        html_body, mime = email.alternatives[0]
        assert mime == 'text/html'
        assert 'empresa/dashboard' in html_body




