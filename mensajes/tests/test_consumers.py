"""
Tests unitarios y de integración para Consumers de Mensajes (SCRUM-189).
Prueba ChatGrupalConsumer y ChatDirectoConsumer usando WebsocketCommunicator.
"""

from unittest.mock import patch

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from config.asgi import application
from usuarios.models import Usuario
from proyectos.models import Proyecto
from contrataciones.models import Contratacion
from mensajes.models import Mensaje
from mensajes.consumers import ChatDirectoConsumer


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestChatConsumers:

    async def test_chat_grupal_rechaza_anonimo(self):
        communicator = WebsocketCommunicator(application, "/ws/chat/grupal/1/")
        connected, _ = await communicator.connect()
        # El consumer acepta y cierra con 4401 para que el navegador pueda
        # distinguir sesión expirada de un fallo de red (1006).
        assert connected
        event = await communicator.receive_output()
        assert event["type"] == "websocket.close"
        assert event["code"] == 4401

    async def test_chat_grupal_rechaza_usuario_sin_permiso(self):
        # Crear usuario ajeno y proyecto
        empresa = await Usuario.objects.acreate(
            username="empresa_chat", email="empresa@chat.com", rol="empresa"
        )
        ajeno = await Usuario.objects.acreate(
            username="ajeno_chat", email="ajeno@chat.com", rol="desarrollador"
        )
        proyecto = await Proyecto.objects.acreate(
            empresa=empresa, titulo="Proyecto Chat Test", estado="en_desarrollo"
        )

        communicator = WebsocketCommunicator(application, f"/ws/chat/grupal/{proyecto.id}/")
        communicator.scope["user"] = ajeno
        connected, _ = await communicator.connect()
        assert connected
        event = await communicator.receive_output()
        assert event["type"] == "websocket.close"
        assert event["code"] == 4403

    async def test_chat_grupal_flujo_exitoso(self):
        empresa = await Usuario.objects.acreate(
            username="empresa_ok", email="empresa_ok@chat.com", rol="empresa"
        )
        dev = await Usuario.objects.acreate(
            username="dev_ok", email="dev_ok@chat.com", rol="desarrollador"
        )
        proyecto = await Proyecto.objects.acreate(
            empresa=empresa, titulo="Proyecto Colaborativo", estado="en_desarrollo"
        )
        await Contratacion.objects.acreate(
            proyecto=proyecto, empresa=empresa, desarrollador=dev, estado="activa"
        )

        # Conectar comunicador de empresa
        comm_empresa = WebsocketCommunicator(application, f"/ws/chat/grupal/{proyecto.id}/")
        comm_empresa.scope["user"] = empresa
        connected_empresa, _ = await comm_empresa.connect()
        assert connected_empresa

        # Conectar comunicador de dev
        comm_dev = WebsocketCommunicator(application, f"/ws/chat/grupal/{proyecto.id}/")
        comm_dev.scope["user"] = dev
        connected_dev, _ = await comm_dev.connect()
        assert connected_dev

        # Empresa envía mensaje grupal
        await comm_empresa.send_json_to({"contenido": "Hola equipo, bienvenidos al proyecto!"})

        # Ambos reciben el broadcast
        resp_empresa = await comm_empresa.receive_json_from()
        assert resp_empresa["type"] == "mensaje"
        assert resp_empresa["mensaje"]["contenido"] == "Hola equipo, bienvenidos al proyecto!"
        assert resp_empresa["mensaje"]["remitente_id"] == empresa.id

        resp_dev = await comm_dev.receive_json_from()
        assert resp_dev["type"] == "mensaje"
        assert resp_dev["mensaje"]["contenido"] == "Hola equipo, bienvenidos al proyecto!"

        # Verificar persistencia en base de datos
        mensaje_db = await Mensaje.objects.filter(proyecto=proyecto, receptor__isnull=True).afirst()
        assert mensaje_db is not None
        assert mensaje_db.contenido == "Hola equipo, bienvenidos al proyecto!"

        await comm_empresa.disconnect()
        await comm_dev.disconnect()

    async def test_chat_directo_rechaza_chatear_consigo_mismo(self):
        user = await Usuario.objects.acreate(
            username="self_chat", email="self@chat.com", rol="desarrollador"
        )
        communicator = WebsocketCommunicator(application, f"/ws/chat/{user.id}/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected
        event = await communicator.receive_output()
        assert event["type"] == "websocket.close"
        assert event["code"] == 4403

    async def test_chat_directo_flujo_exitoso(self):
        empresa = await Usuario.objects.acreate(
            username="empresa_dir", email="empresa_dir@chat.com", rol="empresa"
        )
        dev = await Usuario.objects.acreate(
            username="dev_dir", email="dev_dir@chat.com", rol="desarrollador"
        )
        proyecto = await Proyecto.objects.acreate(
            empresa=empresa, titulo="Proyecto 1 a 1", estado="en_desarrollo"
        )
        await Contratacion.objects.acreate(
            proyecto=proyecto, empresa=empresa, desarrollador=dev, estado="activa"
        )

        # Conectar comunicador para chat directo
        comm_dev = WebsocketCommunicator(
            application, f"/ws/chat/{empresa.id}/?proyecto_id={proyecto.id}"
        )
        comm_dev.scope["user"] = dev
        connected_dev, _ = await comm_dev.connect()
        assert connected_dev

        comm_emp = WebsocketCommunicator(
            application, f"/ws/chat/{dev.id}/?proyecto_id={proyecto.id}"
        )
        comm_emp.scope["user"] = empresa
        connected_emp, _ = await comm_emp.connect()
        assert connected_emp

        # Dev envía mensaje a empresa
        await comm_dev.send_json_to({"contenido": "Mensaje directo privado para la empresa."})

        resp_emp = await comm_emp.receive_json_from()
        assert resp_emp["type"] == "mensaje"
        assert resp_emp["mensaje"]["contenido"] == "Mensaje directo privado para la empresa."
        assert resp_emp["mensaje"]["remitente_id"] == dev.id
        assert resp_emp["mensaje"]["receptor_id"] == empresa.id
        assert resp_emp["mensaje"]["proyecto_id"] == proyecto.id
        assert resp_emp["mensaje"]["fecha"]

        # El receptor está conectado: el mensaje se marca leído sin polling.
        mensaje_db = await Mensaje.objects.filter(
            remitente=dev, receptor=empresa
        ).afirst()
        assert mensaje_db is not None
        assert mensaje_db.leido is True

        await comm_dev.disconnect()
        await comm_emp.disconnect()

    async def test_chat_directo_entrega_aunque_falle_marcar_leido(self):
        empresa = await Usuario.objects.acreate(
            username="empresa_mr", email="empresa_mr@chat.com", rol="empresa"
        )
        dev = await Usuario.objects.acreate(
            username="dev_mr", email="dev_mr@chat.com", rol="desarrollador"
        )
        proyecto = await Proyecto.objects.acreate(
            empresa=empresa, titulo="Proyecto Mark Read", estado="en_desarrollo"
        )
        await Contratacion.objects.acreate(
            proyecto=proyecto, empresa=empresa, desarrollador=dev, estado="activa"
        )

        comm_dev = WebsocketCommunicator(
            application, f"/ws/chat/{empresa.id}/?proyecto_id={proyecto.id}"
        )
        comm_dev.scope["user"] = dev
        assert (await comm_dev.connect())[0]

        comm_emp = WebsocketCommunicator(
            application, f"/ws/chat/{dev.id}/?proyecto_id={proyecto.id}"
        )
        comm_emp.scope["user"] = empresa
        assert (await comm_emp.connect())[0]

        async def _marcar_leido_falla(self, mensaje_id):
            raise RuntimeError("BD caída")

        with patch.object(
            ChatDirectoConsumer, "_marcar_leido", _marcar_leido_falla
        ):
            await comm_dev.send_json_to({
                "contenido": "El mensaje debe entregarse igual."
            })
            resp_emp = await comm_emp.receive_json_from()

        assert resp_emp["type"] == "mensaje"
        assert resp_emp["mensaje"]["contenido"] == "El mensaje debe entregarse igual."
        mensaje_db = await Mensaje.objects.filter(
            remitente=dev, receptor=empresa
        ).afirst()
        assert mensaje_db is not None
        assert mensaje_db.leido is False

        await comm_dev.disconnect()
        await comm_emp.disconnect()
