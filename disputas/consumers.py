"""
Consumer asíncrono de Django Channels para la app disputas (SCRUM-189).
Maneja conexiones WebSocket para la Sala de Mediación Tripartita:
- ws/disputas/<disputa_id>/
"""

import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import Disputa, MensajeDisputa
from .views import ESTADOS_MENSAJERIA, _es_participante, _rol_emisor, _destinatarios_mensaje
from notificaciones.models import Notificacion


class DisputaConsumer(AsyncJsonWebsocketConsumer):
    """Maneja WebSocket para salas de mediación ws/disputas/<disputa_id>/"""

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return

        self.disputa_id = self.scope["url_route"]["kwargs"]["disputa_id"]
        self.room_group_name = f"disputa_mediacion_{self.disputa_id}"

        # Verificar permisos de participación
        autorizado, error_msg = await self._verificar_participante()
        if not autorizado:
            await self.close(code=4403)
            return

        # Unirse al grupo
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

        resultado, error = await self._guardar_mensaje(texto)
        if error:
            await self.send_json({"error": error})
            return

        # Broadcast a todos los miembros de la sala de mediación
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "disputa.message",
                "mensaje": resultado,
            }
        )

    async def disputa_message(self, event):
        """Manejador del broadcast"""
        await self.send_json({
            "type": "mensaje_disputa",
            "mensaje": event["mensaje"]
        })

    @database_sync_to_async
    def _verificar_participante(self):
        try:
            disputa = Disputa.objects.select_related(
                'proyecto__empresa', 'contratacion__desarrollador', 'iniciado_por', 'mediador'
            ).get(id=self.disputa_id)
            if not _es_participante(self.user, disputa):
                return False, "No participas en esta disputa."
            return True, None
        except Disputa.DoesNotExist:
            return False, "Disputa no encontrada."

    @database_sync_to_async
    def _guardar_mensaje(self, texto):
        try:
            with transaction.atomic():
                disputa = Disputa.objects.select_for_update().select_related(
                    'proyecto__empresa', 'contratacion__desarrollador', 'iniciado_por', 'mediador'
                ).get(id=self.disputa_id)

                if not _es_participante(self.user, disputa):
                    return None, "No participas en esta disputa."

                if disputa.estado not in ESTADOS_MENSAJERIA:
                    return None, "La disputa está cerrada: no se pueden enviar nuevos mensajes."

                if self.user.rol == 'administrador' and disputa.estado == 'abierta':
                    disputa.estado = 'en_mediacion'
                    if not disputa.mediador_id:
                        disputa.mediador = self.user
                    disputa.save(update_fields=['estado', 'mediador'])

                msg = MensajeDisputa.objects.create(
                    disputa=disputa,
                    emisor=self.user,
                    contenido=texto
                )

                destinatarios = _destinatarios_mensaje(disputa, self.user)
                if destinatarios:
                    Notificacion.objects.bulk_create([
                        Notificacion(
                            usuario_id=uid,
                            proyecto=disputa.proyecto,
                            tipo='mensaje',
                            mensaje=(
                                f"Nuevo mensaje de {self.user.nombre or self.user.username} en la disputa "
                                f"#{disputa.pk} del proyecto '{disputa.proyecto.titulo}'."
                            ),
                        )
                        for uid in destinatarios
                    ])

                rol = _rol_emisor(self.user, disputa)
                return {
                    "id": msg.id,
                    "emisor_id": self.user.id,
                    "emisor_nombre": self.user.nombre or self.user.username,
                    "rol_emisor": rol,
                    "contenido": msg.contenido,
                    "fecha_envio": msg.fecha_envio.strftime("%d/%m/%Y %H:%M"),
                }, None
        except Disputa.DoesNotExist:
            return None, "Disputa no encontrada."
        except Exception as exc:
            return None, str(exc)
