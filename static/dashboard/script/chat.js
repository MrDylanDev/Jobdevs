/**
 * JobDevs - Cliente WebSocket para Salas de Chat (SCRUM-189)
 * Soporta chat grupal y chat directo 1:1 con reconexión exponencial y fallback HTTP.
 */

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('chat-container');
  const chatForm = document.querySelector('.chat-input-form');
  const inputField = chatForm ? chatForm.querySelector('.chat-input-field') : null;

  if (container) {
    container.scrollTop = container.scrollHeight;
  }

  if (!chatForm || !inputField) return;

  const currentUserId = parseInt(chatForm.dataset.userId || '0', 10);
  const esGrupal = chatForm.dataset.esGrupal === 'true';
  const proyectoId = chatForm.dataset.proyectoId || '';
  const receptorId = chatForm.dataset.receptorId || '';

  // Determinar URL de WebSocket
  const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
  let wsPath = '';

  if (esGrupal && proyectoId) {
    wsPath = `/ws/chat/grupal/${proyectoId}/`;
  } else if (receptorId) {
    wsPath = `/ws/chat/${receptorId}/`;
    if (proyectoId) {
      wsPath += `?proyecto_id=${proyectoId}`;
    }
  }

  if (!wsPath) return;

  let socket = null;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 10;
  const baseReconnectDelay = 1000;

  function connect() {
    socket = new WebSocket(protocol + window.location.host + wsPath);

    socket.onopen = () => {
      console.log('[JobDevs WS] Conectado al chat');
      reconnectAttempts = 0;
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'mensaje' && data.mensaje) {
          appendMessage(data.mensaje);
        } else if (data.error) {
          console.warn('[JobDevs WS Error]:', data.error);
        }
      } catch (err) {
        console.error('[JobDevs WS] Error parseando mensaje', err);
      }
    };

    socket.onclose = (event) => {
      console.warn('[JobDevs WS] Desconectado del chat (código: ' + event.code + ')');
      // No reconectar si fue rechazo por permisos o autenticación
      if (event.code === 4401 || event.code === 4403) return;

      if (reconnectAttempts < maxReconnectAttempts) {
        const delay = Math.min(30000, baseReconnectDelay * Math.pow(1.5, reconnectAttempts));
        reconnectAttempts++;
        setTimeout(connect, delay);
      }
    };

    socket.onerror = (err) => {
      console.error('[JobDevs WS Error]', err);
    };
  }

  function appendMessage(msg) {
    if (!container) return;

    // Remover placeholder de "no hay mensajes" si existe
    const placeholder = container.querySelector('div[style*="text-align:center"]');
    if (placeholder) {
      placeholder.remove();
    }

    const bubble = document.createElement('div');
    bubble.classList.add('message-bubble');

    const isMine = msg.remitente_id === currentUserId;
    bubble.classList.add(isMine ? 'message-sent' : 'message-received');

    if (msg.es_grupal && !isMine) {
      const senderName = document.createElement('div');
      senderName.classList.add('message-sender-name');
      const rolStr = msg.remitente_rol === 'empresa' ? 'Empresa' : 'Dev';
      senderName.textContent = `${msg.remitente_nombre} (${rolStr})`;
      bubble.appendChild(senderName);
    }

    const textNode = document.createTextNode(msg.contenido);
    bubble.appendChild(textNode);

    const timeDiv = document.createElement('div');
    timeDiv.classList.add('message-time');
    timeDiv.textContent = msg.fecha_envio;
    bubble.appendChild(timeDiv);

    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
  }

  // Interceptar submit del formulario
  chatForm.addEventListener('submit', (e) => {
    const texto = inputField.value.trim();
    if (!texto) return;

    // Si el socket está abierto, enviar por WebSocket y cancelar POST
    if (socket && socket.readyState === WebSocket.OPEN) {
      e.preventDefault();
      socket.send(JSON.stringify({ contenido: texto }));
      inputField.value = '';
      inputField.focus();
    }
    // Si no está abierto el WebSocket, permite el submit POST nativo tradicional como fallback
  });

  connect();
});
