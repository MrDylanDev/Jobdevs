"""Regresiones del cliente JS del chat embebido (panel tipo WhatsApp).

El chat inline debe usar el WebSocket de Django Channels para la conversación
activa y no debe volver a introducir polling HTTP con setInterval.
"""

import re
from pathlib import Path

from django.conf import settings

CHAT_SCRIPT_DIR = Path(settings.BASE_DIR) / 'static' / 'mensajes' / 'script'
CHAT_FILES = (
    CHAT_SCRIPT_DIR / 'chat_inline.js',
    CHAT_SCRIPT_DIR / 'modules' / 'chat_renderer.js',
    CHAT_SCRIPT_DIR / 'modules' / 'chat_ws.js',
)
CHAT_TEMPLATES = (
    Path(settings.BASE_DIR) / 'templates' / 'empresa' / 'empresa.html',
    Path(settings.BASE_DIR) / 'templates' / 'administrador' / 'Administrador.html',
    Path(settings.BASE_DIR) / 'templates' / 'Desarrollador' / 'Desarrollador.html',
)


def _chat_inline_source():
    partes = []
    for path in CHAT_FILES:
        assert path.exists(), f'Falta archivo modular de chat: {path}'
        partes.append(path.read_text(encoding='utf-8'))
    return '\n'.join(partes)


class TestChatInlineCliente:

    def test_no_usa_polling_http(self):
        source = _chat_inline_source()
        assert 'POLL_MS' not in source
        assert 'setInterval' not in source

    def test_usa_websocket_de_channels(self):
        source = _chat_inline_source()
        assert 'new WebSocket' in source
        assert '/ws/chat/' in source
        assert 'proyecto_id=' in source

    def test_refresca_historial_tras_reconexion(self):
        source = _chat_inline_source()
        assert 'refreshHistory' in source
        assert 'wasReconnect' in source
        assert 'socketOpenedForActive' in source

    def test_verifica_sesion_por_http(self):
        source = _chat_inline_source()
        assert 'data-session-url' in source
        assert 'verificarSesion' in source
        assert 'api/sesion' in source or 'sessionUrl' in source

    def test_actualiza_badge_sidebar_al_renderizar_conversacion(self):
        source = _chat_inline_source()
        inicio_render = source.index('function render(data)')
        siguiente = re.search(r'\n\s+function ', source[inicio_render + 1:])
        assert siguiente is not None
        fin_render = inicio_render + 1 + siguiente.start()
        cuerpo_render = source[inicio_render:fin_render]
        assert "typeof data.mensajes_no_leidos === 'number'" in cuerpo_render
        assert "document.querySelectorAll('[data-mensajes-badge]')" in cuerpo_render

    def test_templates_cargan_chat_inline_como_es_module(self):
        esperado = '<script type="module" src="{% static \'mensajes/script/chat_inline.js\' %}?v=20261121_v10"></script>'
        for tpl in CHAT_TEMPLATES:
            html = tpl.read_text(encoding='utf-8')
            assert esperado in html, f'{tpl} debe cargar chat_inline.js con type="module" y cache-busting'
