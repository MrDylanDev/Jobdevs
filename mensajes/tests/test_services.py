"""Tests unitarios de los servicios de envío de mensajes (SCRUM-156, Fase 2)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from contrataciones.models import Contratacion
from mensajes.models import Mensaje
from mensajes.services import enviar_mensaje, enviar_mensaje_grupal
from notificaciones.models import Notificacion
from proyectos.models import Proyecto

User = get_user_model()


@pytest.fixture
def proyecto(empresa_user):
    return Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto Mensajes', descripcion='D',
        tipo_solucion='sitio_web', estado='en_desarrollo',
    )


@pytest.fixture
def contratacion(proyecto, empresa_user, desarrollador_user):
    return Contratacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, empresa=empresa_user, estado='activa',
    )


@pytest.fixture
def dev_ajeno(db):
    return User.objects.create_user(
        username='dev_ajeno_msg', email='dev_ajeno_msg@test.jobdevs',
        nombre='Dev Ajeno', rol='desarrollador', estado='activo',
        password='TestPass123!',
    )


class TestEnviarMensaje:

    def test_crea_mensaje_y_notificacion(self, empresa_user, desarrollador_user, contratacion):
        mensaje = enviar_mensaje(
            remitente=empresa_user,
            receptor=desarrollador_user,
            contenido='  Hola equipo  ',
            proyecto=contratacion.proyecto,
            titulo='Saludo',
        )

        assert mensaje.contenido == 'Hola equipo'
        assert mensaje.titulo == 'Saludo'
        assert Mensaje.objects.filter(id=mensaje.id).exists()
        assert Notificacion.objects.filter(
            usuario=desarrollador_user, tipo='mensaje', proyecto=contratacion.proyecto
        ).exists()

    def test_rechaza_contenido_vacio(self, empresa_user, desarrollador_user, contratacion):
        with pytest.raises(ValidationError) as exc:
            enviar_mensaje(empresa_user, desarrollador_user, '   ', contratacion.proyecto)

        assert 'no puede estar vacío' in str(exc.value)
        assert not Mensaje.objects.exists()

    def test_rechaza_contenido_demasiado_largo(self, empresa_user, desarrollador_user, contratacion):
        with pytest.raises(ValidationError) as exc:
            enviar_mensaje(empresa_user, desarrollador_user, 'x' * 2001, contratacion.proyecto)

        assert '2000 caracteres' in str(exc.value)

    def test_rechaza_proyecto_finalizado(self, empresa_user, desarrollador_user, contratacion):
        proyecto = contratacion.proyecto
        proyecto.estado = 'finalizado'
        proyecto.save()

        with pytest.raises(ValidationError) as exc:
            enviar_mensaje(empresa_user, desarrollador_user, 'Hola', proyecto)

        assert 'proyectos finalizados' in str(exc.value)

    def test_permission_denied_sin_relacion(self, empresa_user, dev_ajeno):
        with pytest.raises(PermissionDenied):
            enviar_mensaje(empresa_user, dev_ajeno, 'Hola')

        assert not Mensaje.objects.exists()

    def test_permission_denied_al_hablar_consigo_mismo(self, empresa_user):
        with pytest.raises(PermissionDenied):
            enviar_mensaje(empresa_user, empresa_user, 'Hola')


class TestEnviarMensajeGrupal:

    def test_publica_mensaje_y_notifica_al_equipo(
        self, empresa_user, desarrollador_user, contratacion
    ):
        mensaje = enviar_mensaje_grupal(desarrollador_user, contratacion.proyecto, 'Hola equipo')

        assert mensaje.receptor is None
        assert mensaje.proyecto_id == contratacion.proyecto_id
        assert Notificacion.objects.filter(
            usuario=empresa_user, tipo='mensaje', proyecto=contratacion.proyecto
        ).exists()
        # El remitente no se auto-notifica
        assert not Notificacion.objects.filter(usuario=desarrollador_user).exists()

    def test_permission_denied_para_ajeno(self, dev_ajeno, contratacion):
        with pytest.raises(PermissionDenied):
            enviar_mensaje_grupal(dev_ajeno, contratacion.proyecto, 'Hola')

        assert not Mensaje.objects.exists()

    def test_rechaza_proyecto_finalizado(self, desarrollador_user, contratacion):
        proyecto = contratacion.proyecto
        proyecto.estado = 'finalizado'
        proyecto.save()

        with pytest.raises(ValidationError) as exc:
            enviar_mensaje_grupal(desarrollador_user, proyecto, 'Hola')

        assert 'proyectos finalizados' in str(exc.value)
