"""
Consumers asíncronos de Django Channels para la app mensajes (SCRUM-189).
Maneja conexiones WebSocket para:
- ChatGrupalConsumer: Chat de equipo/espacio de trabajo de un proyecto.
- ChatDirectoConsumer: Mensajería 1:1 directa (con o sin proyecto asociado).
"""

import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from .models import Mensaje
from . import services
from .policies import puede_participar_en_chat_grupal, puede_comunicarse
from proyectos.models import Proyecto
from usuarios.models import Usuario

logger = logging.getLogger(__name__)


class ChatGrupalConsumer(AsyncJsonWebsocketConsumer):
    """Maneja WebSocket para salas grupales de proyecto ws/chat/grupal/<proyecto_id>/"""

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            # Aceptar primero permite que el navegador reciba el código 4401
            # en vez de un fallo de handshake genérico (1006).
            await self.accept()
            await self.close(code=4401)
            return

        self.proyecto_id = self.scope["url_route"]["kwargs"]["proyecto_id"]
        self.room_group_name = f"chat_grupal_{self.proyecto_id}"

        # Verificar permisos de acceso al proyecto
        autorizado, error_msg = await self._verificar_acceso()
        if not autorizado:
            # Aceptar primero permite que el navegador reciba el código 4403
            # en vez de un fallo de handshake genérico (1006).
            await self.accept()
            await self.close(code=4403)
            return

        # Unirse al grupo en Channel Layer
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive_json(self, content):
        """Recibe mensaje del cliente: {"contenido": "..."}"""
        texto = content.get("contenido", "").strip()
        if not texto:
            await self.send_json({"error": "El mensaje no puede estar vacío."})
            return

        try:
            mensaje_data = await self._guardar_mensaje(texto)
        except (PermissionDenied, ValidationError) as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            await self.send_json({"error": msg})
            return
        except Exception as exc:
            await self.send_json({"error": "Error al procesar el mensaje."})
            return

        # Broadcast al grupo
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "mensaje": mensaje_data,
            }
        )

    async def chat_message(self, event):
        """Manejador del broadcast"""
        await self.send_json({
            "type": "mensaje",
            "mensaje": event["mensaje"]
        })

    @database_sync_to_async
    def _verificar_acceso(self):
        try:
            proyecto = Proyecto.objects.get(id=self.proyecto_id)
            if not puede_participar_en_chat_grupal(self.user, proyecto):
                return False, "No tienes permiso para participar en este chat."
            return True, None
        except Proyecto.DoesNotExist:
            return False, "Proyecto no encontrado."

    @database_sync_to_async
    def _guardar_mensaje(self, texto):
        proyecto = Proyecto.objects.get(id=self.proyecto_id)
        msg = services.enviar_mensaje_grupal(self.user, proyecto, texto)
        return {
            "id": msg.id,
            "remitente_id": self.user.id,
            "remitente_nombre": self.user.nombre or self.user.username,
            "remitente_rol": self.user.rol,
            "contenido": msg.contenido,
            "fecha_envio": msg.fecha_envio.strftime("%H:%M"),
            "es_grupal": True,
        }


class ChatDirectoConsumer(AsyncJsonWebsocketConsumer):
    """Maneja WebSocket para chat 1:1 ws/chat/<receptor_id>/"""

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            # Aceptar primero permite que el navegador reciba el código 4401
            # en vez de un fallo de handshake genérico (1006).
            await self.accept()
            await self.close(code=4401)
            return

        self.receptor_id = self.scope["url_route"]["kwargs"]["receptor_id"]

        # Obtener query param proyecto_id si existe
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        proyecto_id_val = None
        for param in query_string.split("&"):
            if param.startswith("proyecto_id="):
                val = param.split("=")[1]
                if val.isdigit() and int(val) > 0:
                    proyecto_id_val = int(val)
        self.proyecto_id = proyecto_id_val

        # Verificar permisos
        autorizado, error_msg = await self._verificar_acceso()
        if not autorizado:
            # Aceptar primero permite que el navegador reciba el código 4403
            # en vez de un fallo de handshake genérico (1006).
            await self.accept()
            await self.close(code=4403)
            return

        # Generar nombre determinista de sala para los 2 usuarios: menor_id + mayor_id (+ proyecto si aplica)
        ids = sorted([self.user.id, self.receptor_id])
        proy_suffix = f"_proy_{self.proyecto_id}" if self.proyecto_id else "_general"
        self.room_group_name = f"chat_directo_{ids[0]}_{ids[1]}{proy_suffix}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive_json(self, content):
        """Recibe mensaje del cliente: {"contenido": "..."}"""
        texto = content.get("contenido", "").strip()
        if not texto:
            await self.send_json({"error": "El mensaje no puede estar vacío."})
            return

        try:
            mensaje_data = await self._guardar_mensaje(texto)
        except (PermissionDenied, ValidationError) as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            await self.send_json({"error": msg})
            return
        except Exception as exc:
            await self.send_json({"error": "Error al procesar el mensaje."})
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "mensaje": mensaje_data,
            }
        )

    async def chat_message(self, event):
        mensaje = event["mensaje"]
        # Entregar primero: un fallo transitorio de BD no debe cortar el
        # mensaje en tiempo real.
        await self.send_json({
            "type": "mensaje",
            "mensaje": mensaje
        })
        # Si el conectado es el receptor, la conversación está abierta:
        # marcamos el mensaje como leído sin necesidad de polling HTTP.
        if mensaje.get("receptor_id") == self.user.id:
            try:
                await self._marcar_leido(mensaje.get("id"))
            except Exception:
                logger.exception(
                    "No se pudo marcar como leído el mensaje %s",
                    mensaje.get("id"),
                )

    @database_sync_to_async
    def _marcar_leido(self, mensaje_id):
        if not mensaje_id:
            return
        Mensaje.objects.filter(
            id=mensaje_id,
            receptor=self.user,
            leido=False,
        ).update(leido=True)

    @database_sync_to_async
    def _verificar_acceso(self):
        if self.user.id == self.receptor_id:
            return False, "No puedes chatear contigo mismo."
        try:
            receptor = Usuario.objects.get(id=self.receptor_id)
            proyecto = Proyecto.objects.get(id=self.proyecto_id) if self.proyecto_id else None
            if not puede_comunicarse(self.user, receptor, proyecto):
                return False, "No tienes autorización para comunicarte con este usuario."
            return True, None
        except Usuario.DoesNotExist:
            return False, "Usuario receptor no encontrado."
        except Proyecto.DoesNotExist:
            return False, "Proyecto no encontrado."

    @database_sync_to_async
    def _guardar_mensaje(self, texto):
        receptor = Usuario.objects.get(id=self.receptor_id)
        proyecto = Proyecto.objects.get(id=self.proyecto_id) if self.proyecto_id else None
        titulo = f"Chat: {proyecto.titulo if proyecto else 'General'}"
        msg = services.enviar_mensaje(
            remitente=self.user,
            receptor=receptor,
            contenido=texto,
            proyecto=proyecto,
            titulo=titulo
        )
        fecha_local = timezone.localtime(msg.fecha_envio)
        return {
            "id": msg.id,
            "remitente_id": self.user.id,
            "remitente_nombre": self.user.nombre or self.user.username,
            "remitente_rol": self.user.rol,
            "receptor_id": self.receptor_id,
            "proyecto_id": self.proyecto_id,
            "contenido": msg.contenido,
            "fecha_envio": fecha_local.strftime("%H:%M"),
            "fecha": fecha_local.strftime("%d/%m/%Y"),
            "es_grupal": False,
        }
