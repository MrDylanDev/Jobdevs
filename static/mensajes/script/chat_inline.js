/**
 * JobDevs — Chat embebido tipo WhatsApp.
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
(function () {
  'use strict';

  var ID_TOKEN = '987654321';
  var WS_RECONNECT_BASE_MS = 1000;
  var WS_RECONNECT_MAX_MS = 30000;
  var WS_RECONNECT_MAX_ATTEMPTS = 10;

  function dosDigitos(valor) {
    return valor < 10 ? '0' + valor : String(valor);
  }

  function fechaDeHoy() {
    var hoy = new Date();
    return (
      dosDigitos(hoy.getDate()) +
      '/' +
      dosDigitos(hoy.getMonth() + 1) +
      '/' +
      hoy.getFullYear()
    );
  }

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
    var sessionUrl = root.getAttribute('data-session-url');
    var yoId = parseInt(root.getAttribute('data-yo-id') || '0', 10);

    if (!list || !conv || !messagesBox || !form) return;

    var csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
    var csrfToken = csrfInput ? csrfInput.value : '';
    var active = null;
    var lastMessageId = 0;
    var sending = false;
    var socket = null;
    var socketGeneration = 0;
    var socketOpenedForActive = false;
    var reconnectAttempts = 0;
    var reconnectTimer = null;
    var historyLoading = false;
    var incomingBuffer = [];
    var pendingText = '';

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
      icon.setAttribute('data-lucide', 'message-circle');
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

      var fecha = msg.fecha || fechaDeHoy();
      var lastDay = messagesBox.getAttribute('data-last-day');
      if (lastDay !== fecha) {
        var day = document.createElement('div');
        day.className = 'jd-msg-day';
        day.textContent = fecha;
        messagesBox.appendChild(day);
        messagesBox.setAttribute('data-last-day', fecha);
      }

      var bubble = document.createElement('div');
      bubble.className = 'jd-msg ' + (msg.es_propio ? 'jd-msg-out' : 'jd-msg-in');
      bubble.appendChild(document.createTextNode(msg.contenido));

      var time = document.createElement('div');
      time.className = 'jd-msg-time';
      time.textContent = msg.hora || '';
      bubble.appendChild(time);

      messagesBox.appendChild(bubble);
    }

    function render(data) {
      if (data.yo_id) {
        yoId = parseInt(data.yo_id, 10) || yoId;
      }

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

    function load(item) {
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
          var nombreItem = requested.querySelector('.jd-chat-name');
          var avatarItem = requested.querySelector('.jd-chat-avatar');
          if (nombreItem) nombreItem.textContent = data.receptor.nombre;
          if (avatarItem && !avatarItem.querySelector('i')) {
            avatarItem.textContent = data.receptor.inicial;
          }
          render(data);
          if (empty) empty.hidden = true;
          conv.classList.add('is-open');
          return data;
        })
        .catch(function (err) {
          if (requested !== active) return;
          showError(err.message || 'Error al cargar la conversación.');
        });
    }

    function wsUrl(item) {
      var receptor = parseInt(item.getAttribute('data-receptor'), 10);
      if (!receptor) return null;

      var proyecto = parseInt(item.getAttribute('data-proyecto') || '0', 10);
      var protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
      var path = '/ws/chat/' + receptor + '/';
      if (proyecto) path += '?proyecto_id=' + proyecto;
      return protocol + window.location.host + path;
    }

    function clearReconnectTimer() {
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    }

    function refreshHistory(item) {
      var url = item.getAttribute('data-url');
      if (!url || item !== active) return Promise.resolve();

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
          if (item !== active) return;
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
      socketGeneration += 1;
      clearReconnectTimer();
      reconnectAttempts = 0;
      if (socket) {
        var old = socket;
        socket = null;
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
      if (item !== active || generation !== socketGeneration) return;
      if (reconnectAttempts >= WS_RECONNECT_MAX_ATTEMPTS) {
        showError(
          'Se perdió la conexión en tiempo real. Recarga la página para reconectar.'
        );
        return;
      }

      var delay = Math.min(
        WS_RECONNECT_MAX_MS,
        WS_RECONNECT_BASE_MS * Math.pow(1.5, reconnectAttempts)
      );
      reconnectAttempts += 1;
      clearReconnectTimer();
      reconnectTimer = window.setTimeout(function () {
        if (item === active && generation === socketGeneration) {
          openSocket(item, generation);
        }
      }, delay);
    }

    function openSocket(item, generation) {
      var url = wsUrl(item);
      if (!url) {
        showError('No se pudo construir la conexión en tiempo real.');
        return;
      }

      var ws;
      try {
        ws = new WebSocket(url);
      } catch (err) {
        scheduleReconnect(item, generation);
        return;
      }

      socket = ws;

      ws.onopen = function () {
        if (generation !== socketGeneration) return;
        var wasReconnect = socketOpenedForActive;
        socketOpenedForActive = true;
        reconnectAttempts = 0;
        clearReconnectTimer();
        if (wasReconnect && !historyLoading) {
          refreshHistory(item);
        }
      };

      ws.onmessage = function (event) {
        if (generation !== socketGeneration) return;

        var data;
        try {
          data = JSON.parse(event.data);
        } catch (err) {
          return;
        }

        if (data.error) {
          if (pendingText && !input.value) input.value = pendingText;
          pendingText = '';
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
        if (generation !== socketGeneration) return;
        socket = null;

        if (item !== active) return;
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
          if (generation !== socketGeneration || item !== active) return;
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
      openSocket(item, socketGeneration);
    }

    function normalizarMensaje(msg) {
      return {
        id: msg.id,
        contenido: msg.contenido,
        hora: msg.fecha_envio || msg.hora || '',
        fecha: msg.fecha || fechaDeHoy(),
        remitente_nombre: msg.remitente_nombre || '',
        es_propio: msg.remitente_id === yoId,
      };
    }

    function notificarMensajeEntrante(msg) {
      if (!msg || msg.es_propio) return;

      var api = window.JobDevsToast;
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
      if (!active || !msg || !msg.id) return;
      var normalizado = normalizarMensaje(msg);
      appendMessage(normalizado);
      scrollToBottom(false);
      updatePreview(active, normalizado.contenido, normalizado.hora);
      if (normalizado.es_propio) {
        pendingText = '';
      } else {
        notificarMensajeEntrante(normalizado);
      }
    }

    function handleIncoming(msg) {
      if (historyLoading) {
        incomingBuffer.push(msg);
        return;
      }
      processIncoming(msg);
    }

    function flushIncomingBuffer() {
      var pendientes = incomingBuffer;
      incomingBuffer = [];
      pendientes.forEach(processIncoming);
    }

    function selectItem(item) {
      items.forEach(function (el) {
        el.classList.toggle('active', el === item);
        el.setAttribute('aria-current', el === item ? 'true' : 'false');
      });
      active = item;
      root.classList.add('is-conv-open');
      showError('');
      pendingText = '';
      historyLoading = true;
      incomingBuffer = [];
      messagesBox.innerHTML = '<div class="jd-chat-messages-empty">Cargando…</div>';
      socketOpenedForActive = false;
      connectSocket(item);
      load(item).then(function () {
        if (active !== item) return;
        historyLoading = false;
        flushIncomingBuffer();
      });
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
      return true;
    }

    window.JdChat = { open: openInline };

    items.forEach(bindItem);

    if (backBtn) {
      backBtn.addEventListener('click', function () {
        root.classList.remove('is-conv-open');
        active = null;
        historyLoading = false;
        incomingBuffer = [];
        pendingText = '';
        socketOpenedForActive = false;
        closeSocket();
      });
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (!active || sending) return;

      var texto = (input.value || '').trim();
      if (!texto) return;

      showError('');

      // Canal principal: WebSocket de Django Channels.
      if (socket && socket.readyState === WebSocket.OPEN) {
        try {
          pendingText = texto;
          socket.send(JSON.stringify({ contenido: texto }));
          input.value = '';
          input.focus();
        } catch (err) {
          pendingText = '';
          showError('No se pudo enviar el mensaje por el canal en tiempo real.');
        }
        return;
      }

      // Fallback puntual si el socket aún no está disponible. No es polling.
      if (!sendUrl) {
        showError('Sin conexión en tiempo real. Reintenta en unos segundos.');
        return;
      }

      sending = true;
      if (sendBtn) sendBtn.disabled = true;

      var requested = active;
      var payload = {
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
          if (active !== requested) return;
          appendMessage(data.mensaje);
          input.value = '';
          scrollToBottom(true);
          updatePreview(requested, data.mensaje.contenido, data.mensaje.hora);
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
      if (document.hidden || !active) return;
      if (!socket || socket.readyState === WebSocket.CLOSED) {
        connectSocket(active);
      }
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
