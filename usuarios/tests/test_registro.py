from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse

from logs.models import LogAuditoria
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
            'acepta_terminos': 'on',
        })
        assert response.status_code == 302
        assert response.url == reverse('dashboard_desarrollador')
        assert User.objects.filter(username='nuevodev').exists()
        user = User.objects.get(username='nuevodev')
        assert user.rol == 'desarrollador'
        assert user.estado == 'activo'

    def test_registro_dev_guarda_habilidades_programa_sin_ficha(self, client):
        response = client.post(reverse('registro'), {
            'nombre': 'Aprendiz Uno',
            'tipo_documento': 'cedula',
            'identificacion': '1234567898',
            'email': 'aprendiz.uno@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'habilidades': '  Python, Django  ',
            'programa_formacion': 'ADSO',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'acepta_terminos': 'on',
        })
        assert response.status_code == 302
        perfil = User.objects.get(email='aprendiz.uno@test.jobdevs').perfil_desarrollador
        assert perfil.habilidades == 'Python, Django'
        assert perfil.programa_formacion == 'ADSO'
        assert not perfil.ficha

    def test_registro_muestra_datos_academicos_solo_para_dev(self, client):
        response = client.get(reverse('registro'))
        assert response.status_code == 200
        content = response.content.decode()
        for campo in ('habilidades', 'programa_formacion', 'ficha'):
            assert f'name="{campo}"' in content
        assert 'id="container_desarrollador_academico"' in content

    def test_registro_empresa_success(self, client):
        """Valid empresa registration creates user and logs in with sector and ciudad (SCRUM-37)."""
        response = client.post(reverse('registro'), {
            'username': 'nuevaempresa',
            'nombre': 'Nueva Empresa',
            'tipo_documento': 'nit',
            'identificacion': '900123456-8',
            'sector': 'Fintech y Banca Digital',
            'ciudad': 'Bogotá D.C.',
            'email': 'empresanueva@test.jobdevs',
            'fecha_nacimiento': '1990-06-15',
            'rol': 'empresa',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'acepta_terminos': 'on',
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
            'acepta_terminos': 'on',
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
            'acepta_terminos': 'on',
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
            'acepta_terminos': 'on',
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
            'acepta_terminos': 'on',
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
            'acepta_terminos': 'on',
        })
        assert response.status_code == 302
        user = User.objects.get(username='devvideojuegos')
        assert user.perfil_desarrollador.estado_verificacion == 'sin_verificar'

    def test_registro_identificacion_duplicada_muestra_error(self, client):
        """RF 1.1.1 (SCRUM-37): El NIT o número de identificación debe ser único en el sistema."""
        User.objects.create_user(
            username='existente',
            email='existente@test.jobdevs',
            identificacion='900999888-5',
            password='TestPassword123!',
        )
        response = client.post(reverse('registro'), {
            'username': 'intento_duplicado',
            'nombre': 'Empresa Clon',
            'tipo_documento': 'nit',
            'identificacion': '900999888-5',
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
            'acepta_terminos': 'on',
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
            'acepta_terminos': 'on',
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
            'identificacion': '901234567-7',
            'sector': 'Software',
            'ciudad': 'Medellín',
            'email': 'contacto@digital.jobdevs',
            'fecha_nacimiento': '1995-10-10',
            'rol': 'empresa',
            'password1': 'BienvenidoPass123!',
            'password2': 'BienvenidoPass123!',
            'acepta_terminos': 'on',
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





    def test_registro_no_falla_si_broker_celery_no_esta_disponible(self, client):
        """Regresión: un broker caído no debe romper el registro ya persistido."""
        from unittest import mock

        with mock.patch(
            'notificaciones.tasks.enviar_email_transaccional_task.delay',
            side_effect=RuntimeError('Retry limit exceeded while trying to reconnect to the Celery result store backend.'),
        ):
            response = client.post(reverse('registro'), {
                'username': 'devbrokercaido',
                'nombre': 'Dev Broker Caido',
                'tipo_documento': 'cedula',
                'identificacion': '99887766',
                'email': 'devbrokercaido@test.jobdevs',
                'fecha_nacimiento': '2000-01-01',
                'rol': 'desarrollador',
                'password1': 'TestPass123!',
                'password2': 'TestPass123!',
                'acepta_terminos': 'on',
            })

        assert response.status_code == 302
        assert response.url == reverse('dashboard_desarrollador')
        assert User.objects.filter(username='devbrokercaido').exists()

    def test_registro_get_bloqueado_cuando_registro_publico_deshabilitado(self, client, settings):
        """GET /registro/ returns 403 and institutional notice when ALLOW_PUBLIC_REGISTRATION is False."""
        settings.ALLOW_PUBLIC_REGISTRATION = False
        response = client.get(reverse('registro'))
        assert response.status_code == 403
        html = response.content.decode('utf-8')
        assert 'registro-deshabilitado' in html
        assert '<form method="post"' not in html

    def test_registro_post_bloqueado_cuando_registro_publico_deshabilitado(self, client, settings):
        """POST /registro/ returns 403 and creates no user when ALLOW_PUBLIC_REGISTRATION is False."""
        settings.ALLOW_PUBLIC_REGISTRATION = False
        count_before = User.objects.count()
        response = client.post(reverse('registro'), {
            'username': 'bloqueado_dev',
            'nombre': 'Bloqueado Dev',
            'tipo_documento': 'cedula',
            'identificacion': '55443322',
            'email': 'bloqueado@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 403
        assert User.objects.count() == count_before
        assert not User.objects.filter(username='bloqueado_dev').exists()

    def test_landing_oculta_enlaces_registro_cuando_deshabilitado(self, client, settings):
        """GET / hides /registro/ links when ALLOW_PUBLIC_REGISTRATION is False."""
        settings.ALLOW_PUBLIC_REGISTRATION = False
        response = client.get(reverse('inicio'))
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert f'href="{reverse("registro")}"' not in html

    def test_registro_dev_cc_con_puntos_se_sanitiza(self, client):
        """Dev registering with valid CC containing dots stores clean digits."""
        response = client.post(reverse('registro'), {
            'nombre': 'Dev CC Puntos',
            'tipo_documento': 'cedula',
            'identificacion': '1.020.304.050',
            'email': 'devccpuntos@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'acepta_terminos': 'on',
        })
        assert response.status_code == 302
        user = User.objects.get(email='devccpuntos@test.jobdevs')
        assert user.identificacion == '1020304050'

    def test_registro_dev_ti_valido(self, client):
        """Dev registering with valid 10-digit TI succeeds."""
        response = client.post(reverse('registro'), {
            'nombre': 'Dev TI Valido',
            'tipo_documento': 'ti',
            'identificacion': '1000234567',
            'email': 'devtivalido@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'acepta_terminos': 'on',
        })
        assert response.status_code == 302
        user = User.objects.get(email='devtivalido@test.jobdevs')
        assert user.identificacion == '1000234567'

    def test_registro_dev_cc_invalida_rechazada(self, client):
        """Dev with too-short or alphabetic CC is rejected."""
        for bad_cc in ('12345', '12345ABC'):
            response = client.post(reverse('registro'), {
                'nombre': 'Dev CC Mala',
                'tipo_documento': 'cedula',
                'identificacion': bad_cc,
                'email': f'devccmala_{bad_cc}@test.jobdevs',
                'fecha_nacimiento': '2000-01-01',
                'rol': 'desarrollador',
                'password1': 'TestPass123!',
                'password2': 'TestPass123!',
            })
            assert response.status_code == 200
            assert 'identificacion' in response.context['form'].errors
            assert not User.objects.filter(email=f'devccmala_{bad_cc}@test.jobdevs').exists()

    def test_registro_empresa_ti_rechazada(self, client):
        """Empresa registering with TI is rejected."""
        response = client.post(reverse('registro'), {
            'nombre': 'Empresa TI',
            'tipo_documento': 'ti',
            'identificacion': '1000234567',
            'email': 'empresati@test.jobdevs',
            'fecha_nacimiento': '1990-01-01',
            'rol': 'empresa',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 200
        assert 'tipo_documento' in response.context['form'].errors
        assert not User.objects.filter(email='empresati@test.jobdevs').exists()

    def test_registro_empresa_nit_dv_invalido_rechazada(self, client):
        """Empresa with invalid DIAN NIT DV is rejected."""
        response = client.post(reverse('registro'), {
            'nombre': 'Empresa NIT Malo',
            'tipo_documento': 'nit',
            'identificacion': '899.999.034-9',
            'email': 'empresanitmalo@test.jobdevs',
            'fecha_nacimiento': '1990-01-01',
            'rol': 'empresa',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert response.status_code == 200
        assert 'identificacion' in response.context['form'].errors
        assert not User.objects.filter(email='empresanitmalo@test.jobdevs').exists()

    def test_registro_empresa_con_cc_valida_aceptada(self, client):
        """Empresa registering with valid CC is accepted."""
        response = client.post(reverse('registro'), {
            'nombre': 'Empresa Persona Natural',
            'tipo_documento': 'cedula',
            'identificacion': '79.123.456',
            'email': 'empresacc@test.jobdevs',
            'fecha_nacimiento': '1990-01-01',
            'rol': 'empresa',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'acepta_terminos': 'on',
        })
        assert response.status_code == 302
        user = User.objects.get(email='empresacc@test.jobdevs')
        assert user.identificacion == '79123456'
        assert user.rol == 'empresa'

    def test_registro_sin_aceptar_terminos_es_rechazado_y_no_crea_usuario_ni_log(self, client):
        """POST /registro/ sin acepta_terminos falla validación y no crea usuario ni LogAuditoria."""
        users_before = User.objects.count()
        logs_before = LogAuditoria.objects.count()

        response = client.post(reverse('registro'), {
            'username': 'sinterminos',
            'nombre': 'Sin Terminos',
            'tipo_documento': 'cedula',
            'identificacion': '1020304099',
            'email': 'sinterminos@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })

        assert response.status_code == 200
        assert 'acepta_terminos' in response.context['form'].errors
        assert User.objects.count() == users_before
        assert LogAuditoria.objects.count() == logs_before
        assert not User.objects.filter(email='sinterminos@test.jobdevs').exists()

    def test_registro_con_aceptacion_legal_registra_auditoria(self, client):
        """POST /registro/ con acepta_terminos crea el usuario y registra la aceptación en LogAuditoria."""
        response = client.post(reverse('registro'), {
            'username': 'conterminos',
            'nombre': 'Con Terminos',
            'tipo_documento': 'cedula',
            'identificacion': '1020304088',
            'email': 'conterminos@test.jobdevs',
            'fecha_nacimiento': '2000-01-01',
            'rol': 'desarrollador',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'acepta_terminos': 'on',
        })

        assert response.status_code == 302
        user = User.objects.get(email='conterminos@test.jobdevs')
        log = LogAuditoria.objects.filter(
            usuario=user,
            tabla_afectada='usuarios',
            registro_id=user.id,
        ).first()
        assert log is not None
        accion_lower = log.accion.lower()
        assert 'condiciones del servicio' in accion_lower
        assert 'privacidad' in accion_lower
        assert 'cookies' in accion_lower

    def test_registro_incluye_checkbox_y_enlaces_legales(self, client):
        """GET /registro/ muestra el checkbox acepta_terminos y enlaces a las 3 páginas legales en nueva pestaña."""
        response = client.get(reverse('registro'))
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert 'name="acepta_terminos"' in html
        assert 'target="_blank"' in html
        assert 'rel="noopener noreferrer"' in html
        for url_name in ('legal_condiciones', 'legal_privacidad', 'legal_cookies'):
            assert f'href="{reverse(url_name)}"' in html

    def test_landing_footer_incluye_enlaces_legales(self, client):
        """GET / incluye enlaces en el footer a las 3 páginas legales."""
        response = client.get(reverse('inicio'))
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        for url_name in ('legal_condiciones', 'legal_privacidad', 'legal_cookies'):
            assert f'href="{reverse(url_name)}"' in html


class TestPaginasLegales:
    """Tests for the 3 public legal pages (ES & EN)."""

    def test_legal_condiciones_publica_y_completa(self, client):
        response = client.get(reverse('legal_condiciones'))
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert 'Condiciones del servicio' in html
        assert 'Ley 527 de 1999' in html
        assert 'Modo Piloto' in html
        assert 'Medellín' in html
        assert 'Marco legal completo de Jobdevs' not in html
        assert 'legal-crosslinks' not in html
        assert 'href="/en/legal/condiciones/"' in html
        assert f'href="{reverse("legal_privacidad")}"' in html
        assert f'href="{reverse("legal_cookies")}"' in html

    def test_legal_privacidad_publica_y_completa(self, client):
        response = client.get(reverse('legal_privacidad'))
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert 'Política de privacidad' in html
        assert 'Ley 1581 de 2012' in html
        assert 'Decreto 1377 de 2013' in html
        assert 'Tarjeta de Identidad' in html
        assert 'Marco legal completo de Jobdevs' not in html
        assert 'legal-crosslinks' not in html
        assert 'href="/en/legal/privacidad/"' in html
        assert f'href="{reverse("legal_condiciones")}"' in html
        assert f'href="{reverse("legal_cookies")}"' in html

    def test_legal_cookies_publica_y_completa(self, client):
        response = client.get(reverse('legal_cookies'))
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert 'Política de cookies' in html
        assert 'sessionid' in html
        assert 'csrftoken' in html
        assert 'django_language' in html
        assert 'jobdevs-theme' in html
        assert 'Marco legal completo de Jobdevs' not in html
        assert 'legal-crosslinks' not in html
        assert 'href="/en/legal/cookies/"' in html
        assert f'href="{reverse("legal_condiciones")}"' in html
        assert f'href="{reverse("legal_privacidad")}"' in html

    def test_legal_condiciones_en_ingles(self, client):
        response = client.get('/en/legal/condiciones/')
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert '<html lang="en">' in html
        assert 'Terms of Service' in html
        assert 'Law 527 of 1999' in html
        assert 'Pilot Mode' in html
        assert 'escrow' in html.lower()
        assert 'permanent deletion' in html.lower()
        assert 'Marco legal completo de Jobdevs' not in html
        assert 'legal-crosslinks' not in html
        assert 'href="/legal/condiciones/"' in html
        assert 'href="/en/legal/privacidad/"' in html
        assert 'href="/en/legal/cookies/"' in html

    def test_legal_privacidad_en_ingles(self, client):
        response = client.get('/en/legal/privacidad/')
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert '<html lang="en">' in html
        assert 'Privacy Policy' in html
        assert 'Law 1581 of 2012' in html
        assert 'Decree 1377 of 2013' in html
        assert 'Identity Card' in html
        assert 'Marco legal completo de Jobdevs' not in html
        assert 'legal-crosslinks' not in html
        assert 'href="/legal/privacidad/"' in html
        assert 'href="/en/legal/condiciones/"' in html
        assert 'href="/en/legal/cookies/"' in html

    def test_legal_cookies_en_ingles(self, client):
        response = client.get('/en/legal/cookies/')
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert '<html lang="en">' in html
        assert 'Cookie Policy' in html
        assert 'sessionid' in html
        assert 'csrftoken' in html
        assert 'django_language' in html
        assert 'jobdevs-theme' in html
        assert 'Marco legal completo de Jobdevs' not in html
        assert 'legal-crosslinks' not in html
        assert 'href="/legal/cookies/"' in html
        assert 'href="/en/legal/condiciones/"' in html
        assert 'href="/en/legal/privacidad/"' in html
