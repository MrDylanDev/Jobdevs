/**
 * JobDevs — Renderizado DOM y utilidades de formato del chat embebido.
 */

export function dosDigitos(valor) {
  return valor < 10 ? '0' + valor : String(valor);
}

export function escapeHtml(val) {
  if (val == null) return '';
  return String(val)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function fechaDeHoy() {
  const hoy = new Date();
  return (
    dosDigitos(hoy.getDate()) +
    '/' +
    dosDigitos(hoy.getMonth() + 1) +
    '/' +
    hoy.getFullYear()
  );
}

export function createChatRenderer({
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
}) {
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
      const distance =
        messagesBox.scrollHeight - messagesBox.scrollTop - messagesBox.clientHeight;
      if (distance > 120) return;
    }
    messagesBox.scrollTop = messagesBox.scrollHeight;
  }

  function emptyState() {
    const wrap = document.createElement('div');
    wrap.className = 'jd-chat-messages-empty';
    const icon = document.createElement('i');
    icon.setAttribute('data-lucide', 'message-circle');
    wrap.appendChild(icon);
    wrap.appendChild(
      document.createTextNode('Aún no hay mensajes. Escribe el primero.')
    );
    return wrap;
  }

  function appendMessage(msg) {
    if (!msg || !msg.id || msg.id <= state.lastMessageId) return;
    state.lastMessageId = msg.id;

    const placeholder = messagesBox.querySelector('.jd-chat-messages-empty');
    if (placeholder) placeholder.remove();

    const fecha = msg.fecha || fechaDeHoy();
    const lastDay = messagesBox.getAttribute('data-last-day');
    if (lastDay !== fecha) {
      const day = document.createElement('div');
      day.className = 'jd-msg-day';
      day.textContent = fecha;
      messagesBox.appendChild(day);
      messagesBox.setAttribute('data-last-day', fecha);
    }

    const bubble = document.createElement('div');
    bubble.className = 'jd-msg ' + (msg.es_propio ? 'jd-msg-out' : 'jd-msg-in');
    bubble.appendChild(document.createTextNode(msg.contenido));

    const time = document.createElement('div');
    time.className = 'jd-msg-time';
    time.textContent = msg.hora || '';
    bubble.appendChild(time);

    messagesBox.appendChild(bubble);
  }

  function renderAvatarImg(container, fotoUrl, nombre, inicial) {
    container.innerHTML = '';
    const img = document.createElement('img');
    img.src = fotoUrl;
    img.alt = nombre || '';
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.borderRadius = '50%';
    img.style.objectFit = 'cover';
    img.onerror = function () {
      container.textContent = inicial || '?';
    };
    container.appendChild(img);
  }

  function render(data) {
    if (data.yo_id) {
      state.yoId = parseInt(data.yo_id, 10) || state.yoId;
    }

    if (typeof data.mensajes_no_leidos === 'number') {
      const badges = document.querySelectorAll('[data-mensajes-badge]');
      Array.prototype.slice.call(badges).forEach(function (el) {
        if (data.mensajes_no_leidos > 0) {
          el.textContent = String(data.mensajes_no_leidos);
          el.hidden = false;
          el.style.display = '';
        } else {
          el.textContent = '0';
          el.hidden = true;
          el.style.display = 'none';
        }
      });
    }

    messagesBox.innerHTML = '';
    messagesBox.removeAttribute('data-last-day');
    state.lastMessageId = 0;

    if (!data.mensajes || !data.mensajes.length) {
      messagesBox.appendChild(emptyState());
    } else {
      data.mensajes.forEach(appendMessage);
    }

    if (nameEl) nameEl.textContent = data.receptor.nombre;
    if (avatarEl) {
      if (data.receptor.foto_url) {
        renderAvatarImg(
          avatarEl,
          data.receptor.foto_url,
          data.receptor.nombre,
          data.receptor.inicial
        );
      } else {
        avatarEl.textContent = data.receptor.inicial;
      }
    }
    if (subEl) {
      subEl.textContent = data.proyecto
        ? data.receptor.rol + ' · ' + data.proyecto.titulo
        : data.receptor.rol;
    }

    const puedeEscribir = data.puede_escribir !== false;
    form.hidden = !puedeEscribir;
    if (readonlyEl) readonlyEl.hidden = puedeEscribir;

    const contextPanel = root.querySelector('[data-chat-context]');
    const contextTitle = root.querySelector('[data-context-project-title]');
    const contextBadge = root.querySelector('[data-context-project-badge]');
    const contextEmpresa = root.querySelector('[data-context-project-empresa]');
    const contextDesc = root.querySelector('[data-context-project-desc]');
    const contextMeta = root.querySelector('[data-context-project-meta]');
    if (contextPanel) {
      if (data.proyecto) {
        root.classList.add('has-context');
        const isCollapsed = root.classList.contains('is-context-collapsed');
        contextPanel.style.display = isCollapsed ? 'none' : 'flex';
        if (contextTitle) contextTitle.textContent = data.proyecto.titulo;
        if (contextBadge) {
          contextBadge.textContent = data.proyecto.estado_label || 'En Desarrollo';
        }
        if (contextEmpresa) {
          const empName =
            data.proyecto.empresa_nombre || (data.receptor ? data.receptor.nombre : '');
          const empSpan = contextEmpresa.querySelector('span');
          if (empSpan) empSpan.textContent = empName;
          else contextEmpresa.textContent = empName;
        }
        if (contextDesc) contextDesc.textContent = data.proyecto.descripcion || '';
        if (contextMeta) {
          contextMeta.innerHTML = '';
          if (data.proyecto.tipo_solucion) {
            contextMeta.innerHTML +=
              '<div><strong style="color:var(--fg, #fff);">Tipo:</strong> ' +
              escapeHtml(data.proyecto.tipo_solucion) +
              '</div>';
          }
          if (data.proyecto.modalidad) {
            contextMeta.innerHTML +=
              '<div><strong style="color:var(--fg, #fff);">Modalidad:</strong> ' +
              escapeHtml(data.proyecto.modalidad) +
              '</div>';
          }
        }
      } else {
        contextPanel.style.display = 'none';
        root.classList.remove('has-context');
      }
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    }

    scrollToBottom(true);
  }

  function load(item) {
    const url = item.getAttribute('data-url');
    if (!url) return Promise.resolve();
    const requested = item;

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
        if (requested !== state.active) return data;
        const nombreItem = requested.querySelector('.jd-chat-name');
        const avatarItem = requested.querySelector('.jd-chat-avatar');
        if (nombreItem) nombreItem.textContent = data.receptor.nombre;
        if (avatarItem) {
          if (data.receptor.foto_url) {
            renderAvatarImg(
              avatarItem,
              data.receptor.foto_url,
              data.receptor.nombre,
              data.receptor.inicial
            );
          } else if (!avatarItem.querySelector('img') && !avatarItem.querySelector('i')) {
            avatarItem.textContent = data.receptor.inicial;
          }
        }
        render(data);
        if (empty) empty.hidden = true;
        conv.classList.add('is-open');
        return data;
      })
      .catch(function (err) {
        if (requested !== state.active) return;
        showError(err.message || 'Error al cargar la conversación.');
      });
  }

  return {
    showError,
    scrollToBottom,
    emptyState,
    appendMessage,
    renderAvatarImg,
    render,
    load,
  };
}
