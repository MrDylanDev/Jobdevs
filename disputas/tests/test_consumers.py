"""
Tests unitarios y de integración para DisputaConsumer (SCRUM-189).
Prueba la sala de mediación tripartita WebSocket.
"""

import pytest
from channels.testing import WebsocketCommunicator
from config.asgi import application
from usuarios.models import Usuario
from proyectos.models import Proyecto
from contrataciones.models import Contratacion
from disputas.models import Disputa, MensajeDisputa
from logs.models import LogAuditoria


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestDisputaConsumer:

    async def test_disputa_rechaza_anonimo(self):
        communicator = WebsocketCommunicator(application, "/ws/disputas/1/")
        connected, _ = await communicator.connect()
        assert not connected
        await communicator.disconnect()

    async def test_disputa_rechaza_no_participante(self):
        empresa = await Usuario.objects.acreate(
            username="emp_disp", email="emp_disp@test.com", rol="empresa"
        )
        dev = await Usuario.objects.acreate(
            username="dev_disp", email="dev_disp@test.com", rol="desarrollador"
        )
        ajeno = await Usuario.objects.acreate(
            username="ajeno_disp", email="ajeno_disp@test.com", rol="desarrollador"
        )
        proyecto = await Proyecto.objects.acreate(
            empresa=empresa, titulo="Proyecto Disputa", estado="en_desarrollo"
        )
        contrato = await Contratacion.objects.acreate(
            proyecto=proyecto, empresa=empresa, desarrollador=dev, estado="activa"
        )
        disputa = await Disputa.objects.acreate(
            proyecto=proyecto,
            contratacion=contrato,
            iniciado_por=empresa,
            motivo="Incumplimiento de hitos",
            estado="abierta"
        )

        communicator = WebsocketCommunicator(application, f"/ws/disputas/{disputa.id}/")
        communicator.scope["user"] = ajeno
        connected, _ = await communicator.connect()
        assert not connected
        await communicator.disconnect()

    async def test_disputa_flujo_mediacion_tiempo_real(self):
        empresa = await Usuario.objects.acreate(
            username="emp_med", email="emp_med@test.com", rol="empresa"
        )
        dev = await Usuario.objects.acreate(
            username="dev_med", email="dev_med@test.com", rol="desarrollador"
        )
        admin = await Usuario.objects.acreate(
            username="admin_med", email="admin_med@test.com", rol="administrador"
        )
        proyecto = await Proyecto.objects.acreate(
            empresa=empresa, titulo="Proyecto Mediacion", estado="en_desarrollo"
        )
        contrato = await Contratacion.objects.acreate(
            proyecto=proyecto, empresa=empresa, desarrollador=dev, estado="activa"
        )
        disputa = await Disputa.objects.acreate(
            proyecto=proyecto,
            contratacion=contrato,
            iniciado_por=empresa,
            motivo="Retraso en entrega",
            estado="abierta"
        )

        # Conectar los 3 participantes: Empresa, Dev y Mediador Admin
        comm_emp = WebsocketCommunicator(application, f"/ws/disputas/{disputa.id}/")
        comm_emp.scope["user"] = empresa
        assert (await comm_emp.connect())[0]

        comm_dev = WebsocketCommunicator(application, f"/ws/disputas/{disputa.id}/")
        comm_dev.scope["user"] = dev
        assert (await comm_dev.connect())[0]

        comm_admin = WebsocketCommunicator(application, f"/ws/disputas/{disputa.id}/")
        comm_admin.scope["user"] = admin
        assert (await comm_admin.connect())[0]

        # Admin escribe primero: la disputa debe pasar a 'en_mediacion'
        await comm_admin.send_json_to({"contenido": "Buenas tardes partes, daremos inicio a la mediación."})

        # Verificar recepción por dev
        resp_dev = await comm_dev.receive_json_from()
        assert resp_dev["type"] == "mensaje_disputa"
        assert resp_dev["mensaje"]["contenido"] == "Buenas tardes partes, daremos inicio a la mediación."
        assert resp_dev["mensaje"]["rol_emisor"] == "admin"

        # Verificar recepción por empresa
        resp_emp = await comm_emp.receive_json_from()
        assert resp_emp["type"] == "mensaje_disputa"
        assert resp_emp["mensaje"]["contenido"] == "Buenas tardes partes, daremos inicio a la mediación."

        # Verificar en base de datos
        msg_db = await MensajeDisputa.objects.filter(disputa=disputa).afirst()
        assert msg_db is not None
        assert msg_db.contenido == "Buenas tardes partes, daremos inicio a la mediación."

        # Desconectar
        await comm_emp.disconnect()
        await comm_dev.disconnect()
        await comm_admin.disconnect()

    async def test_envio_websocket_registra_log_auditoria(self):
        """SCRUM-234 (RF 10.2.1): el envío por WebSocket deja traza sin contenido."""
        empresa = await Usuario.objects.acreate(
            username="emp_aud", email="emp_aud@test.com", rol="empresa"
        )
        dev = await Usuario.objects.acreate(
            username="dev_aud", email="dev_aud@test.com", rol="desarrollador"
        )
        proyecto = await Proyecto.objects.acreate(
            empresa=empresa, titulo="Proyecto Auditoria", estado="en_desarrollo"
        )
        contrato = await Contratacion.objects.acreate(
            proyecto=proyecto, empresa=empresa, desarrollador=dev, estado="activa"
        )
        disputa = await Disputa.objects.acreate(
            proyecto=proyecto,
            contratacion=contrato,
            iniciado_por=empresa,
            motivo="Falta de trazabilidad",
            estado="abierta",
        )
        contenido = "TEXTO_CONFIDENCIAL_WS_XYZ"

        communicator = WebsocketCommunicator(application, f"/ws/disputas/{disputa.id}/")
        communicator.scope["user"] = dev
        assert (await communicator.connect())[0]

        await communicator.send_json_to({"contenido": contenido})
        resp = await communicator.receive_json_from()
        assert resp["mensaje"]["contenido"] == contenido

        log = await LogAuditoria.objects.filter(
            tabla_afectada="mensajes_disputa"
        ).afirst()
        assert log is not None
        assert log.registro_id == disputa.id
        assert log.usuario_id == dev.id
        assert "WebSocket" in log.accion
        assert contenido not in (log.accion or "")

        await communicator.disconnect()
