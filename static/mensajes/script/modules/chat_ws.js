/**
 * JobDevs — Ciclo de vida WebSocket, reconexión y buffer de mensajes entrantes.
 */

import { fechaDeHoy } from './chat_renderer.js';

const WS_RECONNECT_BASE_MS = 1000;
const WS_RECONNECT_MAX_MS = 30000;
const WS_RECONNECT_MAX_ATTEMPTS = 10;

export function wsUrl(item) {
  const receptor = parseInt(item.getAttribute('data-receptor'), 10);
  if (!receptor) return null;

  const proyecto = parseInt(item.getAttribute('data-proyecto') || '0', 10);
  const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
  let path = '/ws/chat/' + receptor + '/';
  if (proyecto) path += '?proyecto_id=' + proyecto;
  return protocol + window.location.host + path;
}

export function createChatWs({
  root,
  input,
  sessionUrl,
  state,
  renderer,
  onUpdatePreview,
}) {
  const { appendMessage, scrollToBottom, showError } = renderer;

  function clearReconnectTimer() {
    if (state.reconnectTimer) {
      window.clearTimeout(state.reconnectTimer);
      state.reconnectTimer = null;
    }
  }

  function refreshHistory(item) {
    const url = item.getAttribute('data-url');
    if (!url || item !== state.active) return Promise.resolve();

    return fetch(url, {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) throw new Error(data.error || 'No se pudo actualizar.');
          return data;
        });
      })
      .then(function (data) {
        if (item !== state.active) return;
        (data.mensajes || []).forEach(appendMessage);
        scrollToBottom(false);
      })
      .catch(function () {
        // Un fallo de historial no debe bloquear la reconexión.
      });
  }

  function verificarSesion() {
    if (!sessionUrl) return Promise.resolve(true);
    return fetch(sessionUrl, {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
      .then(function (res) {
        if (res.status === 401 || res.status === 403) return false;
        return true;
      })
      .catch(function () {
        // Sin red no podemos distinguir sesión expirada de caída temporal.
        return true;
      });
  }

  function closeSocket() {
    state.socketGeneration += 1;
    clearReconnectTimer();
    state.reconnectAttempts = 0;
    if (state.socket) {
      const old = state.socket;
      state.socket = null;
      old.onopen = null;
      old.onmessage = null;
      old.onerror = null;
      old.onclose = null;
      try {
        old.close(1000, 'cambio de conversación');
      } catch (err) {
        // El socket ya estaba cerrado.
      }
    }
  }

  function scheduleReconnect(item, generation) {
    if (item !== state.active || generation !== state.socketGeneration) return;
    if (state.reconnectAttempts >= WS_RECONNECT_MAX_ATTEMPTS) {
      showError(
        'Se perdió la conexión en tiempo real. Recarga la página para reconectar.'
      );
      return;
    }

    const delay = Math.min(
      WS_RECONNECT_MAX_MS,
      WS_RECONNECT_BASE_MS * Math.pow(1.5, state.reconnectAttempts)
    );
    state.reconnectAttempts += 1;
    clearReconnectTimer();
    state.reconnectTimer = window.setTimeout(function () {
      if (item === state.active && generation === state.socketGeneration) {
        openSocket(item, generation);
      }
    }, delay);
  }

  function normalizarMensaje(msg) {
    return {
      id: msg.id,
      contenido: msg.contenido,
      hora: msg.fecha_envio || msg.hora || '',
      fecha: msg.fecha || fechaDeHoy(),
      remitente_nombre: msg.remitente_nombre || '',
      es_propio: msg.remitente_id === state.yoId,
    };
  }

  function notificarMensajeEntrante(msg) {
    if (!msg || msg.es_propio) return;

    let api = window.JobDevsToast;
    if (!api || typeof api.mostrar !== 'function') {
      if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
        api = { mostrar: window.JobDevsSSE.mostrarToast };
      } else {
        return;
      }
    }

    api.mostrar({
      tipo: 'mensaje',
      titulo: msg.remitente_nombre || 'Nuevo mensaje',
      mensaje: msg.contenido,
      duracion: 5000,
      origen: 'ws',
      onClick: function () {
        if (root.scrollIntoView) {
          root.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        if (input && input.focus) {
          input.focus({ preventScroll: true });
        }
      },
    });
  }

  function processIncoming(msg) {
    if (!state.active || !msg || !msg.id) return;
    const normalizado = normalizarMensaje(msg);
    appendMessage(normalizado);
    scrollToBottom(false);
    onUpdatePreview(state.active, normalizado.contenido, normalizado.hora);
    if (normalizado.es_propio) {
      state.pendingText = '';
    } else {
      notificarMensajeEntrante(normalizado);
    }
  }

  function handleIncoming(msg) {
    if (state.historyLoading) {
      state.incomingBuffer.push(msg);
      return;
    }
    processIncoming(msg);
  }

  function flushIncomingBuffer() {
    const pendientes = state.incomingBuffer;
    state.incomingBuffer = [];
    pendientes.forEach(processIncoming);
  }

  function openSocket(item, generation) {
    const url = wsUrl(item);
    if (!url) {
      showError('No se pudo construir la conexión en tiempo real.');
      return;
    }

    let ws;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      scheduleReconnect(item, generation);
      return;
    }

    state.socket = ws;

    ws.onopen = function () {
      if (generation !== state.socketGeneration) return;
      const wasReconnect = state.socketOpenedForActive;
      state.socketOpenedForActive = true;
      state.reconnectAttempts = 0;
      clearReconnectTimer();
      if (wasReconnect && !state.historyLoading) {
        refreshHistory(item);
      }
    };

    ws.onmessage = function (event) {
      if (generation !== state.socketGeneration) return;

      let data;
      try {
        data = JSON.parse(event.data);
      } catch (err) {
        return;
      }

      if (data.error) {
        if (state.pendingText && !input.value) input.value = state.pendingText;
        state.pendingText = '';
        showError(data.error);
        return;
      }

      if (data.type === 'mensaje' && data.mensaje) {
        handleIncoming(data.mensaje);
      }
    };

    ws.onerror = function () {
      // onclose se encarga de la reconexión.
    };

    ws.onclose = function (event) {
      if (generation !== state.socketGeneration) return;
      state.socket = null;

      if (item !== state.active) return;
      if (event.code === 4401) {
        showError('Tu sesión expiró. Recarga la página para reconectar.');
        return;
      }
      if (event.code === 4403) {
        showError('No tienes permiso para esta conversación.');
        return;
      }
      // Si el cierre no trae un código de aplicación (p. ej. 1006),
      // comprobamos la sesión antes de seguir reintentando.
      verificarSesion().then(function (sesionValida) {
        if (generation !== state.socketGeneration || item !== state.active) return;
        if (!sesionValida) {
          showError('Tu sesión expiró. Recarga la página para reconectar.');
          return;
        }
        scheduleReconnect(item, generation);
      });
    };
  }

  function connectSocket(item) {
    closeSocket();
    if (!item) return;
    openSocket(item, state.socketGeneration);
  }

  return {
    wsUrl,
    clearReconnectTimer,
    refreshHistory,
    verificarSesion,
    closeSocket,
    scheduleReconnect,
    openSocket,
    connectSocket,
    normalizarMensaje,
    notificarMensajeEntrante,
    processIncoming,
    handleIncoming,
    flushIncomingBuffer,
  };
}
