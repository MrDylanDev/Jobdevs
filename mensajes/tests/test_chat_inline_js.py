"""Regresiones del cliente JS del chat embebido (panel tipo WhatsApp).

El chat inline debe usar el WebSocket de Django Channels para la conversación
activa y no debe volver a introducir polling HTTP con setInterval.
"""

from pathlib import Path

from django.conf import settings


def _chat_inline_source():
    return (
        Path(settings.BASE_DIR)
        / 'static'
        / 'mensajes'
        / 'script'
        / 'chat_inline.js'
    ).read_text(encoding='utf-8')


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
