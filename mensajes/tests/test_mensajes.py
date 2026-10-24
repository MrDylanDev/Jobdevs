import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from proyectos.models import Proyecto
from postulaciones.models import Postulacion
from contrataciones.models import Contratacion
from mensajes.models import Mensaje

User = get_user_model()


class TestMensajeModel:
    """Tests for Mensaje model."""

    def test_crear_mensaje(self, db):
        """Mensaje links sender and receiver."""
        dev1 = User.objects.create_user(
            username='msg1', email='msg1@test.jobdevs',
            nombre='Msg1', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        dev2 = User.objects.create_user(
            username='msg2', email='msg2@test.jobdevs',
            nombre='Msg2', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        msg = Mensaje.objects.create(
            remitente=dev1, receptor=dev2,
            titulo='Hola', contenido='Mensaje de prueba',
        )
        assert msg.id is not None
        assert msg.leido == False
        assert msg.remitente == dev1
        assert msg.receptor == dev2

    def test_mensaje_str(self, db):
        """__str__ includes sender and receiver."""
        dev1 = User.objects.create_user(
            username='m1', email='m1@test.jobdevs',
            nombre='M1', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        dev2 = User.objects.create_user(
            username='m2', email='m2@test.jobdevs',
            nombre='M2', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        msg = Mensaje.objects.create(
            remitente=dev1, receptor=dev2,
            contenido='Test',
        )
        assert 'm1' in str(msg)
        assert 'm2' in str(msg)

    def test_mensaje_sin_receptor(self, db):
        """Mensaje without receptor shows GRUPO."""
        dev1 = User.objects.create_user(
            username='m3', email='m3@test.jobdevs',
            nombre='M3', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        msg = Mensaje.objects.create(
            remitente=dev1, contenido='Grupo',
        )
        assert 'GRUPO' in str(msg)

    def test_eliminacion_usuario_remitente_preserva_mensaje_set_null(self, db):
        """Auditoría SCRUM-160: Si se elimina el remitente, el mensaje no se destruye en cascada."""
        u1 = User.objects.create_user(username='u_rem', email='u_rem@test.jobdevs', password='Password123!')
        u2 = User.objects.create_user(username='u_rec', email='u_rec@test.jobdevs', password='Password123!')
        msg = Mensaje.objects.create(remitente=u1, receptor=u2, contenido='Mensaje persistente')
        msg_id = msg.id

        u1.delete()
        msg.refresh_from_db()
        assert msg.remitente is None
        assert msg.receptor == u2
        assert 'Usuario Eliminado' in str(msg) or 'u_rec' in str(msg)

    def test_eliminacion_usuario_receptor_preserva_mensaje_set_null(self, db):
        """Auditoría SCRUM-160: Si se elimina el receptor, el remitente conserva su historial enviado."""
        u1 = User.objects.create_user(username='u_rem2', email='u_rem2@test.jobdevs', password='Password123!')
        u2 = User.objects.create_user(username='u_rec2', email='u_rec2@test.jobdevs', password='Password123!')
        msg = Mensaje.objects.create(remitente=u1, receptor=u2, contenido='Mensaje enviado persistente')

        u2.delete()
        msg.refresh_from_db()
        assert msg.remitente == u1
        assert msg.receptor is None
        assert 'Usuario Eliminado' in str(msg) or 'u_rem2' in str(msg)


class TestInbox:
    """Tests for mensajeria_inbox view."""

    def test_inbox_accessible(self, dev_client):
        """Authenticated user can access inbox."""
        response = dev_client.get(reverse('mensajeria_inbox'))
        assert response.status_code == 200

    def test_inbox_blocked_anon(self, client):
        """Anonymous cannot access inbox."""
        response = client.get(reverse('mensajeria_inbox'))
        assert response.status_code == 302


class TestMensajeriaSent:
    """Tests for mensajeria_sent view."""

    def test_sent_accessible(self, dev_client):
        """Authenticated user can view sent messages."""
        response = dev_client.get(reverse('mensajeria_sent'))
        assert response.status_code == 200

    def test_sent_blocked_anon(self, client):
        """Anonymous cannot view sent messages."""
        response = client.get(reverse('mensajeria_sent'))
        assert response.status_code == 302


class TestRedactar:
    """Tests for mensajeria_redactar view."""

    def test_redactar_accessible(self, auth_client):
        """Authenticated user can access message composer."""
        response = auth_client.get(reverse('mensajeria_redactar'))
        assert response.status_code == 200

    def test_redactar_blocked_anon(self, client):
        """Anonymous cannot compose messages."""
        response = client.get(reverse('mensajeria_redactar'))
        assert response.status_code == 302

    def test_redactar_get_con_params_invalidos_no_lanza_500(self, auth_client):
        """Auditoría SCRUM-160: Parámetros GET no numéricos ('para=abc&proyecto=xyz') no deben lanzar 500."""
        response = auth_client.get(reverse('mensajeria_redactar') + '?para=abc&proyecto=xyz')
        assert response.status_code == 200
        assert response.context['para_id'] == 0
        assert response.context['proyecto_pre'] == 0


class TestAutorizacionMensajeria:
    """Tests de seguridad y autorización según auditoría SCRUM-160."""

    @pytest.fixture
    def escenario(self, db):
        empresa = User.objects.create_user(
            username='empresa_chat', email='emp_chat@test.jobdevs',
            nombre='Empresa Chat', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='dev_chat', email='dev_chat@test.jobdevs',
            nombre='Dev Chat', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        dev_ajeno = User.objects.create_user(
            username='dev_ajeno', email='dev_ajeno@test.jobdevs',
            nombre='Dev Ajeno', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        admin = User.objects.create_user(
            username='admin_chat', email='admin_chat@test.jobdevs',
            nombre='Admin Chat', rol='administrador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='Proyecto Chat',
            descripcion='D', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        contratacion = Contratacion.objects.create(
            proyecto=proyecto, empresa=empresa,
            desarrollador=dev, estado='activa',
        )
        return {
            'empresa': empresa,
            'dev': dev,
            'dev_ajeno': dev_ajeno,
            'admin': admin,
            'proyecto': proyecto,
            'contratacion': contratacion,
        }

    def test_sala_chat_rechaza_auto_conversacion(self, client, escenario):
        """No se puede iniciar una conversación con uno mismo."""
        dev = escenario['dev']
        client.force_login(dev)
        response = client.get(reverse('sala_chat_general', args=[dev.id]))
        assert response.status_code == 403

    def test_sala_chat_bloquea_usuario_sin_relacion_contractual(self, client, escenario):
        """Un dev ajeno sin relación con la empresa recibe 403."""
        dev_ajeno = escenario['dev_ajeno']
        empresa = escenario['empresa']
        client.force_login(dev_ajeno)
        response = client.get(reverse('sala_chat_general', args=[empresa.id]))
        assert response.status_code == 403

    def test_sala_chat_permite_si_hay_contratacion(self, client, escenario):
        """Dev con contrato activo con la empresa puede acceder al chat 1:1."""
        dev = escenario['dev']
        empresa = escenario['empresa']
        client.force_login(dev)
        response = client.get(reverse('sala_chat_general', args=[empresa.id]))
        assert response.status_code == 200

    def test_sala_chat_permite_comunicacion_con_admin(self, client, escenario):
        """Cualquier usuario puede comunicarse con un administrador."""
        dev_ajeno = escenario['dev_ajeno']
        admin = escenario['admin']
        client.force_login(dev_ajeno)
        response = client.get(reverse('sala_chat_general', args=[admin.id]))
        assert response.status_code == 200

    def test_sala_chat_grupal_excluye_contrataciones_canceladas(self, client, escenario):
        """Un dev con contratación cancelada pierde acceso a la sala grupal del proyecto."""
        dev = escenario['dev']
        contratacion = escenario['contratacion']
        contratacion.estado = 'cancelada'
        contratacion.save()

        client.force_login(dev)
        response = client.get(reverse('sala_chat_grupal', args=[escenario['proyecto'].id]))
        assert response.status_code == 302
        assert response.url == reverse('inicio')

    def test_mensajeria_redactar_post_rechaza_destinatario_no_permitido(self, client, escenario):
        """En redactar, si se fuerza un receptor sin relación, el POST es rechazado."""
        dev_ajeno = escenario['dev_ajeno']
        empresa = escenario['empresa']
        client.force_login(dev_ajeno)
        response = client.post(reverse('mensajeria_redactar'), {
            'receptor': empresa.id,
            'titulo': 'Intento no autorizado',
            'contenido': 'Hola',
        }, follow=True)
        assert response.status_code == 200
        assert not Mensaje.objects.filter(remitente=dev_ajeno, receptor=empresa).exists()
        content = response.content.decode('utf-8')
        assert 'No tienes autorización' in content or 'no válido' in content


class TestIndicadorMensajesNoLeidos:
    """Pruebas del indicador visual y conteo de mensajes no leídos (SCRUM-313 / HU-D19)."""

    def test_dashboard_empresa_muestra_badge_mensajes_no_leidos(self, auth_client, empresa_user, desarrollador_user):
        """Si la empresa tiene mensajes no leídos, el dashboard muestra el badge con el conteo."""
        # Inicialmente 0
        res = auth_client.get(reverse('dashboard_empresa'))
        assert res.status_code == 200
        assert 'badge-mensajes-no-leidos' not in res.content.decode()

        # Enviar 2 mensajes sin leer
        Mensaje.objects.create(
            remitente=desarrollador_user, receptor=empresa_user, contenido='Hola 1', leido=False
        )
        Mensaje.objects.create(
            remitente=desarrollador_user, receptor=empresa_user, contenido='Hola 2', leido=False
        )

        res = auth_client.get(reverse('dashboard_empresa'))
        assert res.status_code == 200
        html = res.content.decode()
        assert 'badge-mensajes-no-leidos' in html

    def test_dashboard_dev_muestra_badge_mensajes_no_leidos(self, dev_client, empresa_user, desarrollador_user):
        """Si el desarrollador tiene mensajes no leídos, su dashboard muestra el badge."""
        Mensaje.objects.create(
            remitente=empresa_user, receptor=desarrollador_user, contenido='Hola Dev', leido=False
        )
        res = dev_client.get(reverse('dashboard_desarrollador'))
        assert res.status_code == 200
        html = res.content.decode()
        assert 'badge-mensajes-no-leidos' in html

    def test_abrir_chat_marca_leido_y_limpia_badge(self, auth_client, empresa_user, admin_user):
        """Al abrir la sala de chat con el admin, los mensajes se marcan leídos y el badge se limpia."""
        Mensaje.objects.create(
            remitente=admin_user, receptor=empresa_user, contenido='Hola Empresa', leido=False
        )
        res_antes = auth_client.get(reverse('dashboard_empresa'))
        assert 'badge-mensajes-no-leidos' in res_antes.content.decode()

        url_chat = reverse('sala_chat_general', args=[admin_user.id])
        res_chat = auth_client.get(url_chat)
        assert res_chat.status_code == 200

        res_despues = auth_client.get(reverse('dashboard_empresa'))
        assert 'badge-mensajes-no-leidos' not in res_despues.content.decode()


class TestAislamientoSalasChat:
    """Pruebas de aislamiento estricto de salas de chat por proyecto (SCRUM-221 / RF 6.1.3)."""

    def test_sala_chat_proyecto_excluye_mensajes_generales_y_de_otros_proyectos(
        self, client, empresa_user, desarrollador_user
    ):
        proyecto1 = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto 1', descripcion='D1',
            tipo_solucion='sitio_web', estado='en_desarrollo',
        )
        Contratacion.objects.create(
            proyecto=proyecto1, empresa=empresa_user, desarrollador=desarrollador_user, estado='activa'
        )
        proyecto2 = Proyecto.objects.create(
            empresa=empresa_user, titulo='Otro Proyecto', descripcion='D2',
            tipo_solucion='sitio_web', estado='en_desarrollo',
        )
        Contratacion.objects.create(
            proyecto=proyecto2, empresa=empresa_user, desarrollador=desarrollador_user, estado='activa'
        )

        Mensaje.objects.create(
            remitente=empresa_user, receptor=desarrollador_user, proyecto=proyecto1, contenido='Exclusivo Proyecto 1'
        )
        Mensaje.objects.create(
            remitente=empresa_user, receptor=desarrollador_user, proyecto=None, contenido='Mensaje General Sin Proyecto'
        )
        Mensaje.objects.create(
            remitente=empresa_user, receptor=desarrollador_user, proyecto=proyecto2, contenido='Exclusivo Proyecto 2'
        )

        client.force_login(desarrollador_user)
        url_p1 = reverse('sala_chat', args=[empresa_user.id, proyecto1.id])
        res = client.get(url_p1)
        assert res.status_code == 200
        html = res.content.decode()

        assert 'Exclusivo Proyecto 1' in html
        assert 'Mensaje General Sin Proyecto' not in html  # SCRUM-221
        assert 'Exclusivo Proyecto 2' not in html





