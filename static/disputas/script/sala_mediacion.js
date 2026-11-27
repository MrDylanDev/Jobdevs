document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('disputa-chat-container');
  const form = document.getElementById('disputa-msg-form');
  const textarea = form ? form.querySelector('#contenido') : null;

  if (container) {
    container.scrollTop = container.scrollHeight;
  }

  // Panel de resolución: toggle propio (sin Bootstrap).
  const toggleResolucion = document.getElementById('toggle-resolucion');
  const panelResolucion = document.getElementById('panelResolucion');
  if (toggleResolucion && panelResolucion) {
    const abrir = () => {
      const open = panelResolucion.classList.toggle('open');
      toggleResolucion.setAttribute('aria-expanded', open ? 'true' : 'false');
      const icon = document.getElementById('icon-resolucion');
      if (icon) {
        icon.setAttribute('data-lucide', open ? 'chevron-up' : 'chevron-down');
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      }
    };
    toggleResolucion.addEventListener('click', abrir);
    toggleResolucion.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        abrir();
      }
    });
  }

  if (!form || !textarea) return;

  const disputaId = form.dataset.disputaId;
  const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
  const wsUrl = `${protocol}${window.location.host}/ws/disputas/${disputaId}/`;

  let socket = null;
  let reconnectAttempts = 0;

  function connect() {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('[Disputa WS] Conectado a la sala de mediación #' + disputaId);
      reconnectAttempts = 0;
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'mensaje_disputa' && data.mensaje) {
          appendDisputaMsg(data.mensaje);
        } else if (data.error) {
          console.warn('[Disputa WS Error]:', data.error);
        }
      } catch (err) {
        console.error('[Disputa WS] Error parseando datos', err);
      }
    };

    socket.onclose = (event) => {
      if (event.code === 4401 || event.code === 4403) return;
      if (reconnectAttempts < 8) {
        const delay = Math.min(20000, 1000 * Math.pow(1.5, reconnectAttempts));
        reconnectAttempts++;
        setTimeout(connect, delay);
      }
    };
  }

  function appendDisputaMsg(msg) {
    if (!container) return;
    const emptyMsg = document.getElementById('disputa-empty-msg');
    if (emptyMsg) emptyMsg.remove();

    const box = document.createElement('div');
    box.className = 'disp-msg ';
    let badgeClass = 'badge badge-warning';
    let badgeText = 'Mediador Admin';

    if (msg.rol_emisor === 'empresa') {
      box.className += 'disp-msg-empresa';
      badgeClass = 'badge badge-gray';
      badgeText = 'Empresa';
    } else if (msg.rol_emisor === 'dev') {
      box.className += 'disp-msg-dev';
      badgeClass = 'badge badge-success';
      badgeText = 'Desarrollador';
    } else {
      box.className += 'disp-msg-admin';
    }

    const header = document.createElement('div');
    header.className = 'disp-msg-head';

    const senderSpan = document.createElement('span');
    const senderName = document.createElement('strong');
    senderName.textContent = msg.emisor_nombre;
    senderSpan.appendChild(senderName);
    senderSpan.appendChild(document.createTextNode(' '));

    const badge = document.createElement('span');
    badge.className = badgeClass;
    badge.textContent = badgeText;
    senderSpan.appendChild(badge);

    const timeSpan = document.createElement('span');
    timeSpan.textContent = msg.fecha_envio;

    header.appendChild(senderSpan);
    header.appendChild(timeSpan);

    const bodyDiv = document.createElement('div');
    bodyDiv.className = 'disp-msg-body';
    bodyDiv.textContent = msg.contenido;

    box.appendChild(header);
    box.appendChild(bodyDiv);
    container.appendChild(box);
    container.scrollTop = container.scrollHeight;
  }

  form.addEventListener('submit', (e) => {
    const texto = textarea.value.trim();
    if (!texto) return;

    if (socket && socket.readyState === WebSocket.OPEN) {
      e.preventDefault();
      socket.send(JSON.stringify({ contenido: texto }));
      textarea.value = '';
      textarea.focus();
    }
  });

  connect();
});
