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
      if (subEl) {
        subEl.textContent = data.proyecto
          ? data.receptor.rol + ' · ' + data.proyecto.titulo
          : data.receptor.rol;
      }

      var puedeEscribir = data.puede_escribir !== false;
      form.hidden = !puedeEscribir;
      if (readonlyEl) readonlyEl.hidden = puedeEscribir;

      scrollToBottom(true);
    }

    function load(item, silent) {
      var url = item.getAttribute('data-url');
      if (!url) return Promise.resolve();
      var requested = item;

      return fetch(url, {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
      })
        .then(function (res) {
          return res.json().then(function (data) {
            if (!res.ok) throw new Error(data.error || 'No se pudo cargar.');
            return data;
          });
        })
        .then(function (data) {
          // Evita pintar respuestas antiguas si el usuario cambió de chat.
          if (requested !== active) return data;
          if (requested) {
            var nombreItem = requested.querySelector('.jd-chat-name');
            var avatarItem = requested.querySelector('.jd-chat-avatar');
            if (nombreItem) nombreItem.textContent = data.receptor.nombre;
            if (avatarItem && !avatarItem.querySelector('i')) {
              avatarItem.textContent = data.receptor.inicial;
            }
          }
          render(data);
          if (!silent) {
            if (empty) empty.hidden = true;
            conv.classList.add('is-open');
          }
          return data;
        })
        .catch(function (err) {
          if (requested !== active) return;
          if (!silent) showError(err.message || 'Error al cargar la conversación.');
        });
    }

    function selectItem(item) {
      items.forEach(function (el) {
        el.classList.toggle('active', el === item);
        el.setAttribute('aria-current', el === item ? 'true' : 'false');
      });
      active = item;
      root.classList.add('is-conv-open');
      showError('');
      messagesBox.innerHTML = '<div class="jd-chat-messages-empty">Cargando…</div>';
      load(item, false);
    }

    function startPolling() {
      stopPolling();
      pollTimer = window.setInterval(function () {
        if (!active || document.hidden || sending) return;
        load(active, true);
      }, POLL_MS);
    }

    function stopPolling() {
      if (pollTimer) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
    }

    function updatePreview(item, texto, hora) {
      var preview = item.querySelector('.jd-chat-preview');
      var time = item.querySelector('.jd-chat-time');
      if (preview) preview.textContent = texto;
      if (time && hora) time.textContent = hora;
      if (list && list.firstElementChild !== item) list.prepend(item);
    }

    function convUrl(receptorId, proyectoId) {
      var esProyecto = proyectoId && String(proyectoId) !== '0';
      var tpl = root.getAttribute(
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
        startPolling();
      });
    }

    function ensureItem(receptorId, proyectoId, nombre) {
      var proyecto = String(proyectoId || '0');
      var selector =
        '.jd-chat-item[data-receptor="' + receptorId +
        '"][data-proyecto="' + proyecto + '"]';
      var existente = root.querySelector(selector);
      if (existente) return existente;

      var url = convUrl(receptorId, proyecto);
      if (!url) return null;

      var item = document.createElement('button');
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

      var texto = (nombre || 'Conversación').trim();
      item.querySelector('.jd-chat-name').textContent = texto;
      item.querySelector('.jd-chat-avatar').textContent =
        texto.charAt(0).toUpperCase();

      bindItem(item);
      items.push(item);
      list.prepend(item);
      var vacio = root.querySelector('.jd-chat-list-empty');
      if (vacio) vacio.hidden = true;
      return item;
    }

    function openInline(receptorId, proyectoId, nombre) {
      var seccion = root.closest('.seccion-v, .section-v');
      if (seccion) {
        var activa =
          seccion.classList.contains('active') ||
          seccion.classList.contains('activa');
        if (!activa) {
          var nav = document.querySelector(
            '.nav-item[onclick*="' + seccion.id + '"]'
          );
          if (nav) nav.click();
        }
      }

      var item = ensureItem(receptorId, proyectoId, nombre);
      if (!item) return false;
      selectItem(item);
      startPolling();
      return true;
    }

    window.JdChat = { open: openInline };

    items.forEach(bindItem);

    if (backBtn) {
      backBtn.addEventListener('click', function () {
        root.classList.remove('is-conv-open');
        stopPolling();
      });
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (!active || sending) return;

      var texto = (input.value || '').trim();
      if (!texto) return;

      sending = true;
      if (sendBtn) sendBtn.disabled = true;
      showError('');

      var payload = {
        receptor_id: parseInt(active.getAttribute('data-receptor'), 10),
        proyecto_id: parseInt(active.getAttribute('data-proyecto') || '0', 10),
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
          appendMessage(data.mensaje);
          input.value = '';
          scrollToBottom(true);
          updatePreview(active, data.mensaje.contenido, data.mensaje.hora);
        })
        .catch(function (err) {
          showError(err.message || 'Error al enviar el mensaje.');
        })
        .finally(function () {
          sending = false;
          if (sendBtn) sendBtn.disabled = false;
          input.focus();
        });
    });

    document.addEventListener('visibilitychange', function () {
      if (!document.hidden && active) load(active, true);
    });
  }

  document.addEventListener('click', function (event) {
    var trigger = event.target.closest
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

  document.addEventListener('DOMContentLoaded', function () {
    Array.prototype.slice
      .call(document.querySelectorAll('[data-chat-root]'))
      .forEach(initChat);
  });
})();
