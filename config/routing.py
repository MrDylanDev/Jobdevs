"""
WebSocket routing for JobDevs (TEIR)
Enruta las conexiones WebSocket a sus respectivos consumers:
- ws/chat/grupal/<proyecto_id>/ -> Sala grupal de proyecto
- ws/chat/<receptor_id>/ (opcional ?proyecto_id=) -> Chat 1:1 directo
- ws/disputas/<disputa_id>/ -> Sala de mediación tripartita
"""

from django.urls import re_path, path
from mensajes import consumers as mensajes_consumers
from disputas import consumers as disputas_consumers

websocket_urlpatterns = [
    path('ws/chat/grupal/<int:proyecto_id>/', mensajes_consumers.ChatGrupalConsumer.as_asgi()),
    path('ws/chat/<int:receptor_id>/', mensajes_consumers.ChatDirectoConsumer.as_asgi()),
    path('ws/disputas/<int:disputa_id>/', disputas_consumers.DisputaConsumer.as_asgi()),
]
