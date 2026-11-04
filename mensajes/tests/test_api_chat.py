"""Tests de la API JSON del chat embebido (panel tipo WhatsApp).

Cubre: historial, marcado de lectura, aislamiento por proyecto, envío,
validaciones y control de permisos.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from contrataciones.models import Contratacion
from mensajes.models import Mensaje
from notificaciones.models import Notificacion
from proyectos.models import Proyecto

User = get_user_model()


@pytest.fixture
def proyecto(empresa_user):
    return Proyecto.objects.create(
        empresa=empresa_user,
        titulo='Proyecto API Chat',
        descripcion='D',
        tipo_solucion='sitio_web',
        estado='en_desarrollo',
    )


@pytest.fixture
def contratacion(proyecto, empresa_user, desarrollador_user):
    return Contratacion.objects.create(
        proyecto=proyecto,
        desarrollador=desarrollador_user,
        empresa=empresa_user,
        estado='activa',
    )


@pytest.fixture
def dev_ajeno(db):
    return User.objects.create_user(
        username='dev_ajeno_api',
        email='dev_ajeno_api@test.jobdevs',
        nombre='Dev Ajeno',
        rol='desarrollador',
        estado='activo',
        password='TestPass123!',
    )


class TestApiConversacion:

    def test_requiere_autenticacion(self, client, desarrollador_user):
        response = client.get(reverse('api_conversacion', args=[desarrollador_user.id]))
        assert response.status_code == 302

    def test_devuelve_historial_y_marca_leido(
        self, client, empresa_user, desarrollador_user, contratacion
    ):
        mensaje = Mensaje.objects.create(
            remitente=empresa_user,
            receptor=desarrollador_user,
            contenido='Hola dev',
            proyecto=contratacion.proyecto,
        )
        client.force_login(desarrollador_user)

        response = client.get(
            reverse(
                'api_conversacion_proyecto',
                args=[empresa_user.id, contratacion.proyecto.id],
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert data['receptor']['id'] == empresa_user.id
        assert data['receptor']['nombre'] == empresa_user.nombre
        assert data['proyecto']['id'] == contratacion.proyecto.id
        assert data['puede_escribir'] is True
        assert len(data['mensajes']) == 1
        assert data['mensajes'][0]['contenido'] == 'Hola dev'
        assert data['mensajes'][0]['es_propio'] is False

        mensaje.refresh_from_db()
        assert mensaje.leido is True

    def test_aisla_por_proyecto(self, client, empresa_user, desarrollador_user, contratacion):
        Mensaje.objects.create(
            remitente=empresa_user,
            receptor=desarrollador_user,
            contenido='Mensaje general',
        )
        Mensaje.objects.create(
            remitente=empresa_user,
            receptor=desarrollador_user,
            contenido='Mensaje del proyecto',
            proyecto=contratacion.proyecto,
        )
        client.force_login(desarrollador_user)

        data = client.get(
            reverse(
                'api_conversacion_proyecto',
                args=[empresa_user.id, contratacion.proyecto.id],
            )
        ).json()

        assert [m['contenido'] for m in data['mensajes']] == ['Mensaje del proyecto']

    def test_rechaza_conversacion_no_autorizada(self, client, desarrollador_user, dev_ajeno):
        client.force_login(desarrollador_user)
        response = client.get(reverse('api_conversacion', args=[dev_ajeno.id]))

        assert response.status_code == 403
        assert 'error' in response.json()

    def test_rechaza_conversacion_consigo_mismo(self, client, desarrollador_user):
        client.force_login(desarrollador_user)
        response = client.get(reverse('api_conversacion', args=[desarrollador_user.id]))

        assert response.status_code == 400

    def test_administrador_puede_abrir_cualquier_chat(self, client, admin_user, dev_ajeno):
        client.force_login(admin_user)
        response = client.get(reverse('api_conversacion', args=[dev_ajeno.id]))

        assert response.status_code == 200
        assert response.json()['mensajes'] == []


class TestApiEnviar:

    def test_envia_mensaje_y_notifica(
        self, client, empresa_user, desarrollador_user, contratacion
    ):
        client.force_login(empresa_user)

        response = client.post(
            reverse('api_enviar'),
            data=json.dumps({
                'receptor_id': desarrollador_user.id,
                'proyecto_id': contratacion.proyecto.id,
                'contenido': '  Hola desde el panel  ',
            }),
            content_type='application/json',
        )

        assert response.status_code == 201
        data = response.json()
        assert data['mensaje']['contenido'] == 'Hola desde el panel'
        assert data['mensaje']['es_propio'] is True

        mensaje = Mensaje.objects.get()
        assert mensaje.remitente == empresa_user
        assert mensaje.receptor == desarrollador_user
        assert mensaje.proyecto == contratacion.proyecto
        assert Notificacion.objects.filter(
            usuario=desarrollador_user, tipo='mensaje'
        ).exists()

    def test_rechaza_contenido_vacio(self, client, empresa_user, desarrollador_user, contratacion):
        client.force_login(empresa_user)

        response = client.post(
            reverse('api_enviar'),
            data=json.dumps({
                'receptor_id': desarrollador_user.id,
                'proyecto_id': contratacion.proyecto.id,
                'contenido': '   ',
            }),
            content_type='application/json',
        )

        assert response.status_code == 400
        assert not Mensaje.objects.exists()

    def test_rechaza_sin_autorizacion(self, client, desarrollador_user, dev_ajeno):
        client.force_login(desarrollador_user)

        response = client.post(
            reverse('api_enviar'),
            data=json.dumps({
                'receptor_id': dev_ajeno.id,
                'contenido': 'No debería enviarse',
            }),
            content_type='application/json',
        )

        assert response.status_code == 403
        assert not Mensaje.objects.exists()

    def test_rechaza_proyecto_finalizado(
        self, client, empresa_user, desarrollador_user, contratacion
    ):
        contratacion.proyecto.estado = 'finalizado'
        contratacion.proyecto.save(update_fields=['estado'])
        client.force_login(empresa_user)

        response = client.post(
            reverse('api_enviar'),
            data=json.dumps({
                'receptor_id': desarrollador_user.id,
                'proyecto_id': contratacion.proyecto.id,
                'contenido': 'Chat cerrado',
            }),
            content_type='application/json',
        )

        assert response.status_code == 400
        assert not Mensaje.objects.exists()

    def test_rechaza_json_invalido(self, client, empresa_user):
        client.force_login(empresa_user)

        response = client.post(
            reverse('api_enviar'),
            data='no-es-json',
            content_type='application/json',
        )

        assert response.status_code == 400

    def test_solo_acepta_post(self, client, empresa_user):
        client.force_login(empresa_user)
        response = client.get(reverse('api_enviar'))

        assert response.status_code == 405
