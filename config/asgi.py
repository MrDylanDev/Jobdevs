"""
ASGI config for JobDevs (TEIR).

Expone la aplicación ASGI compatible con HTTP y WebSockets mediante Django Channels.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Inicializar Django ASGI antes de importar consumers y routing
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings
import config.routing

ws_router = URLRouter(config.routing.websocket_urlpatterns)

# En tests (DEBUG o TESTING=True), no rechazar websockets por origen localhost/testserver
if getattr(settings, 'TESTING', False) or getattr(settings, 'DEBUG', False):
    ws_app = AuthMiddlewareStack(ws_router)
else:
    ws_app = AllowedHostsOriginValidator(AuthMiddlewareStack(ws_router))

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": ws_app,
})
