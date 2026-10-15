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
            username='msg1', email='msg1@test.teir',
            nombre='Msg1', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        dev2 = User.objects.create_user(
            username='msg2', email='msg2@test.teir',
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
            username='m1', email='m1@test.teir',
            nombre='M1', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        dev2 = User.objects.create_user(
            username='m2', email='m2@test.teir',
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
            username='m3', email='m3@test.teir',
            nombre='M3', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        msg = Mensaje.objects.create(
            remitente=dev1, contenido='Grupo',
        )
        assert 'GRUPO' in str(msg)


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


class TestAutorizacionMensajeria:
    """Tests de seguridad y autorización según auditoría SCRUM-160."""

    @pytest.fixture
    def escenario(self, db):
        empresa = User.objects.create_user(
            username='empresa_chat', email='emp_chat@test.teir',
            nombre='Empresa Chat', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='dev_chat', email='dev_chat@test.teir',
            nombre='Dev Chat', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        dev_ajeno = User.objects.create_user(
            username='dev_ajeno', email='dev_ajeno@test.teir',
            nombre='Dev Ajeno', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        admin = User.objects.create_user(
            username='admin_chat', email='admin_chat@test.teir',
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

