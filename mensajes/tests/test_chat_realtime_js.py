"""Regresiones del cliente JS del chat en tiempo real (chat_realtime.js) [FEAT][CHAT-01].

Verifica la correcta integración de:
- Identificador de mensaje de cliente (clientMsgId) y su eco en el socket.
- Manejo de fallos en UI optimista (estados de error, reintento y recuperación de texto).
- Reconciliación determinista sin falsos positivos por duplicidad de texto.
"""

from pathlib import Path
from django.conf import settings


def _chat_realtime_source():
    return (
        Path(settings.BASE_DIR)
        / 'static'
        / 'dashboard'
        / 'script'
        / 'chat_realtime.js'
    ).read_text(encoding='utf-8')


def _chat_css_source():
    return (
        Path(settings.BASE_DIR)
        / 'static'
        / 'dashboard'
        / 'css'
        / 'chat.css'
    ).read_text(encoding='utf-8')


class TestChatRealtimeCliente:

    def test_genera_y_envia_client_msg_id(self):
        source = _chat_realtime_source()
        assert 'client_msg_id' in source
        assert 'clientMsgId' in source
        assert 'this.pendingMessages' in source

    def test_reconciliacion_exacta_por_client_msg_id(self):
        source = _chat_realtime_source()
        assert 'msg.client_msg_id' in source
        assert 'this.pendingMessages.has(msg.client_msg_id)' in source
        assert 'this.pendingMessages.delete' in source

    def test_manejo_de_fallos_y_estado_fallido(self):
        source = _chat_realtime_source()
        assert 'markMessageFailed' in source
        assert 'message-failed' in source
        assert 'markAllPendingMessagesFailed' in source

    def test_acciones_de_reintento_y_recuperacion_de_texto(self):
        source = _chat_realtime_source()
        assert 'retrySendMessage' in source
        assert 'recoverMessageText' in source
        assert 'chat-btn-retry' in source
        assert 'chat-btn-recover' in source
        assert 'Reintentar' in source
        assert 'Recuperar' in source

    def test_captura_errores_del_servidor_y_cierre_de_socket(self):
        source = _chat_realtime_source()
        assert 'data.client_msg_id' in source
        assert 'onclose' in source
        assert 'onerror' in source

    def test_estilos_css_para_mensajes_fallidos(self):
        css = _chat_css_source()
        assert '.message-failed' in css
        assert '.status-failed-badge' in css
        assert '.chat-btn-retry' in css
        assert '.chat-btn-recover' in css

