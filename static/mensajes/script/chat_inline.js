/**
 * JobDevs — Chat embebido tipo WhatsApp (ES Module Orchestrator).
 *
 * Convierte un bloque [data-chat-root] en un panel de dos columnas:
 * lista de conversaciones a la izquierda y conversación activa a la derecha,
 * sin recargar ni navegar a otra página.
 *
 * Cada elemento .jd-chat-item declara:
 *   data-url       -> endpoint JSON del historial (GET, solo carga inicial)
 *   data-receptor  -> id del usuario con el que se conversa
 *   data-proyecto  -> id del proyecto (0 = conversación general)
 *
 * La conversación activa se conecta al WebSocket existente de Django Channels
 * (/ws/chat/<receptor_id>/?proyecto_id=<id>) para recibir y enviar mensajes
 * en tiempo real. No se hace polling HTTP. [data-send-url] se conserva solo
 * como fallback puntual si el socket no está disponible al enviar.
 */

import { createChatRenderer } from './modules/chat_renderer.js';
import { createChatWs } from './modules/chat_ws.js';

const ID_TOKEN = '987654321';

function initChat(root) {
  const list = root.querySelector('[data-chat-list]');
  const items = Array.prototype.slice.call(root.querySelectorAll('.jd-chat-item'));
  const empty = root.querySelector('[data-chat-empty]');
  const conv = root.querySelector('[data-chat-conv]');
  const messagesBox = root.querySelector('[data-chat-messages]');
  const nameEl = root.querySelector('[data-chat-name]');
  const subEl = root.querySelector('[data-chat-sub]');
  const avatarEl = root.querySelector('[data-chat-avatar]');
  const form = root.querySelector('[data-chat-form]');
  const input = root.querySelector('[data-chat-input]');
  const sendBtn = root.querySelector('[data-chat-send]');
  const readonlyEl = root.querySelector('[data-chat-readonly]');
  const errorEl = root.querySelector('[data-chat-error]');
  const backBtn = root.querySelector('[data-chat-back]');
  const sendUrl = root.getAttribute('data-send-url');
  const sessionUrl = root.getAttribute('data-session-url');
  const yoId = parseInt(root.getAttribute('data-yo-id') || '0', 10);

  if (!list || !conv || !messagesBox || !form) return;

  const csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
  const csrfToken = csrfInput ? csrfInput.value : '';

  const state = {
    yoId,
    active: null,
    lastMessageId: 0,
    sending: false,
    socket: null,
    socketGeneration: 0,
    socketOpenedForActive: false,
    reconnectAttempts: 0,
    reconnectTimer: null,
    historyLoading: false,
    incomingBuffer: [],
    pendingText: '',
  };

  function updatePreview(item, texto, hora) {
    const preview = item.querySelector('.jd-chat-preview');
    const time = item.querySelector('.jd-chat-time');
    if (preview) preview.textContent = texto;
    if (time && hora) time.textContent = hora;
    if (list && list.firstElementChild !== item) list.prepend(item);
  }

  const renderer = createChatRenderer({
    root,
    empty,
    conv,
    messagesBox,
    nameEl,
    subEl,
    avatarEl,
    form,
    readonlyEl,
    errorEl,
    state,
  });

  const ws = createChatWs({
    root,
    input,
    sessionUrl,
    state,
    renderer,
    onUpdatePreview: updatePreview,
  });

  function selectItem(item) {
    items.forEach(function (el) {
      el.classList.toggle('active', el === item);
      el.setAttribute('aria-current', el === item ? 'true' : 'false');
    });
    state.active = item;
    root.classList.add('is-conv-open');
    renderer.showError('');
    state.pendingText = '';
    state.historyLoading = true;
    state.incomingBuffer = [];
    messagesBox.innerHTML = '<div class="jd-chat-messages-empty">Cargando…</div>';
    state.socketOpenedForActive = false;
    ws.connectSocket(item);
    renderer.load(item).then(function () {
      if (state.active !== item) return;
      state.historyLoading = false;
      ws.flushIncomingBuffer();
    });
  }

  function convUrl(receptorId, proyectoId) {
    const esProyecto = proyectoId && String(proyectoId) !== '0';
    const tpl = root.getAttribute(
      esProyecto ? 'data-url-proyecto' : 'data-url-general'
    );
    if (!tpl) return null;
    if (esProyecto) {
      return tpl.replace(ID_TOKEN, receptorId).replace(ID_TOKEN, proyectoId);
    }
    return tpl.replace(ID_TOKEN, receptorId);
  }

  function bindItem(item) {
    item.addEventListener('click', function () {
      selectItem(item);
    });
  }

  function ensureItem(receptorId, proyectoId, nombre) {
    const proyecto = String(proyectoId || '0');
    const selector =
      '.jd-chat-item[data-receptor="' + receptorId +
      '"][data-proyecto="' + proyecto + '"]';
    const existente = root.querySelector(selector);
    if (existente) return existente;

    const url = convUrl(receptorId, proyecto);
    if (!url) return null;

    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'jd-chat-item';
    item.setAttribute('data-url', url);
    item.setAttribute('data-receptor', receptorId);
    item.setAttribute('data-proyecto', proyecto);
    item.innerHTML =
      '<span class="jd-chat-avatar"></span>' +
      '<span class="jd-chat-item-body">' +
      '<span class="jd-chat-item-top"><span class="jd-chat-name"></span></span>' +
      '<span class="jd-chat-preview">Conversación abierta</span></span>';

    const texto = (nombre || 'Conversación').trim();
    item.querySelector('.jd-chat-name').textContent = texto;
    item.querySelector('.jd-chat-avatar').textContent =
      texto.charAt(0).toUpperCase();

    bindItem(item);
    items.push(item);
    list.prepend(item);
    const vacio = root.querySelector('.jd-chat-list-empty');
    if (vacio) vacio.hidden = true;
    return item;
  }

  function openInline(receptorId, proyectoId, nombre) {
    const seccion = root.closest('.seccion-v, .section-v');
    if (seccion) {
      const activa =
        seccion.classList.contains('active') ||
        seccion.classList.contains('activa');
      if (!activa) {
        const nav = document.querySelector(
          '.nav-item[onclick*="' + seccion.id + '"]'
        );
        if (nav) nav.click();
      }
    }

    const item = ensureItem(receptorId, proyectoId, nombre);
    if (!item) return false;
    selectItem(item);
    return true;
  }

  window.JdChat = { open: openInline };

  items.forEach(bindItem);

  if (backBtn) {
    backBtn.addEventListener('click', function () {
      root.classList.remove('is-conv-open');
      state.active = null;
      state.historyLoading = false;
      state.incomingBuffer = [];
      state.pendingText = '';
      state.socketOpenedForActive = false;
      ws.closeSocket();
    });
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!state.active || state.sending) return;

    const texto = (input.value || '').trim();
    if (!texto) return;

    renderer.showError('');

    // Canal principal: WebSocket de Django Channels.
    if (state.socket && state.socket.readyState === WebSocket.OPEN) {
      try {
        state.pendingText = texto;
        state.socket.send(JSON.stringify({ contenido: texto }));
        input.value = '';
        input.focus();
      } catch (err) {
        state.pendingText = '';
        renderer.showError('No se pudo enviar el mensaje por el canal en tiempo real.');
      }
      return;
    }

    // Fallback puntual si el socket aún no está disponible. No es polling.
    if (!sendUrl) {
      renderer.showError('Sin conexión en tiempo real. Reintenta en unos segundos.');
      return;
    }

    state.sending = true;
    if (sendBtn) sendBtn.disabled = true;

    const requested = state.active;
    const payload = {
      receptor_id: parseInt(requested.getAttribute('data-receptor'), 10),
      proyecto_id: parseInt(requested.getAttribute('data-proyecto') || '0', 10),
      contenido: texto,
    };

    fetch(sendUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) throw new Error(data.error || 'No se pudo enviar.');
          return data;
        });
      })
      .then(function (data) {
        if (state.active !== requested) return;
        renderer.appendMessage(data.mensaje);
        input.value = '';
        renderer.scrollToBottom(true);
        updatePreview(requested, data.mensaje.contenido, data.mensaje.hora);
      })
      .catch(function (err) {
        renderer.showError(err.message || 'Error al enviar el mensaje.');
      })
      .finally(function () {
        state.sending = false;
        if (sendBtn) sendBtn.disabled = false;
        input.focus();
      });
  });

  document.addEventListener('visibilitychange', function () {
    if (document.hidden || !state.active) return;
    if (!state.socket || state.socket.readyState === WebSocket.CLOSED) {
      ws.connectSocket(state.active);
    }
  });
}

document.addEventListener('click', function (event) {
  const trigger = event.target.closest
    ? event.target.closest('[data-chat-open]')
    : null;
  if (!trigger) return;
  if (!window.JdChat || typeof window.JdChat.open !== 'function') return;
  event.preventDefault();
  window.JdChat.open(
    trigger.getAttribute('data-receptor'),
    trigger.getAttribute('data-proyecto'),
    trigger.getAttribute('data-nombre')
  );
});

function bootstrapChat() {
  Array.prototype.slice
    .call(document.querySelectorAll('[data-chat-root]'))
    .forEach(initChat);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrapChat);
} else {
  bootstrapChat();
}
