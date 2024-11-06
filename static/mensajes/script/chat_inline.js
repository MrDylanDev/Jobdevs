/**
 * JobDevs — Chat embebido tipo WhatsApp.
 *
 * Convierte un bloque [data-chat-root] en un panel de dos columnas:
 * lista de conversaciones a la izquierda y conversación activa a la derecha,
 * sin recargar ni navegar a otra página.
 *
 * Cada elemento .jd-chat-item declara:
 *   data-url       -> endpoint JSON del historial (GET)
 *   data-receptor  -> id del usuario con el que se conversa
 *   data-proyecto  -> id del proyecto (0 = conversación general)
 *
 * El envío se hace por POST a [data-send-url] con JSON.
 */
(function () {
  'use strict';

  var POLL_MS = 5000;
  var ID_TOKEN = '987654321';

  function initChat(root) {
    var list = root.querySelector('[data-chat-list]');
    var items = Array.prototype.slice.call(root.querySelectorAll('.jd-chat-item'));
    var empty = root.querySelector('[data-chat-empty]');
    var conv = root.querySelector('[data-chat-conv]');
    var messagesBox = root.querySelector('[data-chat-messages]');
    var nameEl = root.querySelector('[data-chat-name]');
    var subEl = root.querySelector('[data-chat-sub]');
    var avatarEl = root.querySelector('[data-chat-avatar]');
    var form = root.querySelector('[data-chat-form]');
    var input = root.querySelector('[data-chat-input]');
    var sendBtn = root.querySelector('[data-chat-send]');
    var readonlyEl = root.querySelector('[data-chat-readonly]');
    var errorEl = root.querySelector('[data-chat-error]');
    var backBtn = root.querySelector('[data-chat-back]');
    var sendUrl = root.getAttribute('data-send-url');

    if (!list || !conv || !messagesBox || !form) return;

    var csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
    var csrfToken = csrfInput ? csrfInput.value : '';
    var active = null;
    var lastMessageId = 0;
    var pollTimer = null;
    var sending = false;

    function showError(text) {
      if (!errorEl) return;
      errorEl.textContent = text || '';
      errorEl.hidden = !text;
      if (text) {
        window.clearTimeout(showError._timer);
        showError._timer = window.setTimeout(function () {
          errorEl.hidden = true;
        }, 6000);
      }
    }

    function scrollToBottom(force) {
      if (!force) {
        var distance =
          messagesBox.scrollHeight - messagesBox.scrollTop - messagesBox.clientHeight;
        if (distance > 120) return;
      }
      messagesBox.scrollTop = messagesBox.scrollHeight;
    }

    function emptyState() {
      var wrap = document.createElement('div');
      wrap.className = 'jd-chat-messages-empty';
      var icon = document.createElement('i');
      icon.className = 'fa fa-comments';
      wrap.appendChild(icon);
      wrap.appendChild(
        document.createTextNode('Aún no hay mensajes. Escribe el primero.')
      );
      return wrap;
    }

    function appendMessage(msg) {
      if (!msg || !msg.id || msg.id <= lastMessageId) return;
      lastMessageId = msg.id;

      var placeholder = messagesBox.querySelector('.jd-chat-messages-empty');
      if (placeholder) placeholder.remove();

      var lastDay = messagesBox.getAttribute('data-last-day');
      if (lastDay !== msg.fecha) {
        var day = document.createElement('div');
        day.className = 'jd-msg-day';
        day.textContent = msg.fecha;
        messagesBox.appendChild(day);
        messagesBox.setAttribute('data-last-day', msg.fecha);
      }

      var bubble = document.createElement('div');
      bubble.className = 'jd-msg ' + (msg.es_propio ? 'jd-msg-out' : 'jd-msg-in');
      bubble.appendChild(document.createTextNode(msg.contenido));

      var time = document.createElement('div');
      time.className = 'jd-msg-time';
      time.textContent = msg.hora;
      bubble.appendChild(time);

      messagesBox.appendChild(bubble);
    }

    function render(data) {
      messagesBox.innerHTML = '';
      messagesBox.removeAttribute('data-last-day');
      lastMessageId = 0;

      if (!data.mensajes || !data.mensajes.length) {
        messagesBox.appendChild(emptyState());
      } else {
        data.mensajes.forEach(appendMessage);
      }

      if (nameEl) nameEl.textContent = data.receptor.nombre;
      if (avatarEl) avatarEl.textContent = data.receptor.inicial;
