/**
 * JobDevs - Módulo de Tiempo Real y Experiencia Avanzada de Chat [FEAT][CHAT-01]
 * 
 * Características:
 * - Auto-scroll inteligente y fluido hacia el último mensaje.
 * - Soporte para carga asíncrona de imágenes e hidratación reactiva del scroll.
 * - Tarjetas de previsualización enriquecida para repositorios de GitHub y archivos compartidos.
 * - UI optimista con estado "Enviando..." y confirmación de entrega en tiempo real.
 */

(function (window, document) {
  'use strict';

  class ChatRealtimeManager {
    constructor() {
      this.container = document.getElementById('chat-container');
      this.chatForm = document.querySelector('.chat-input-form');
      this.inputField = this.chatForm ? this.chatForm.querySelector('.chat-input-field') : null;
      this.pendingMessages = new Map();
      this.imageObservers = new WeakSet();
      this.mutationObserver = null;
      this.socket = null;
      this.reconnectAttempts = 0;
      this.maxReconnectAttempts = 10;
      this.baseReconnectDelay = 1000;

      if (!this.container) return;

      this.currentUserId = parseInt((this.chatForm && this.chatForm.dataset.userId) || '0', 10);
      this.esGrupal = (this.chatForm && this.chatForm.dataset.esGrupal) === 'true';
      this.proyectoId = (this.chatForm && this.chatForm.dataset.proyectoId) || '';
      this.receptorId = (this.chatForm && this.chatForm.dataset.receptorId) || '';

      this.init();
    }

    init() {
      // Punto de inicio de la inicialización de listeners y conexión
      console.log('[ChatRealtime] Inicializando gestor en tiempo real');
      this.setupImageAndMutationObservers();
      this.hydrateExistingMessages();
      this.setupFormSubmit();
      this.connectWebSocket();
      this.scrollToBottom(true, false);
    }

    /**
     * Establece la conexión WebSocket con Django Channels y gestiona eventos.
     */
    connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
      let wsPath = '';

      if (this.esGrupal && this.proyectoId) {
        wsPath = `/ws/chat/grupal/${this.proyectoId}/`;
      } else if (this.receptorId) {
        wsPath = `/ws/chat/${this.receptorId}/`;
        if (this.proyectoId) {
          wsPath += `?proyecto_id=${this.proyectoId}`;
        }
      }

      if (!wsPath) return;

      this.socket = new WebSocket(protocol + window.location.host + wsPath);

      this.socket.onopen = () => {
        console.log('[ChatRealtime] WebSocket conectado exitosamente');
        this.reconnectAttempts = 0;
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'mensaje' && data.mensaje) {
            this.handleIncomingMessage(data.mensaje);
          } else if (data.error) {
            console.warn('[ChatRealtime] Error desde el servidor:', data.error);
            if (data.client_msg_id && this.pendingMessages.has(data.client_msg_id)) {
              this.markMessageFailed(data.client_msg_id, data.error);
            }
          }
        } catch (err) {
          console.error('[ChatRealtime] Error deserializando mensaje recibido:', err);
        }
      };

      this.socket.onclose = (event) => {
        console.warn(`[ChatRealtime] WebSocket cerrado (código: ${event.code})`);
        this.markAllPendingMessagesFailed('Conexión cerrada');
        if (event.code === 4401 || event.code === 4403) return;

        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          const delay = Math.min(30000, this.baseReconnectDelay * Math.pow(1.5, this.reconnectAttempts));
          this.reconnectAttempts++;
          setTimeout(() => this.connectWebSocket(), delay);
        }
      };

      this.socket.onerror = (err) => {
        console.error('[ChatRealtime] Excepción en WebSocket:', err);
        this.markAllPendingMessagesFailed('Error en WebSocket');
      };
    }

    /**
     * Procesa un mensaje emitido por el WebSocket en tiempo real.
     */
    handleIncomingMessage(msg) {
      const isMine = msg.remitente_id === this.currentUserId;

      if (isMine) {
        // Buscar burbuja optimista pendiente correspondiente
        let matchedBubble = null;

        // 1. Reconciliación primaria y exacta mediante client_msg_id
        if (msg.client_msg_id && this.pendingMessages.has(msg.client_msg_id)) {
          const entry = this.pendingMessages.get(msg.client_msg_id);
          if (entry && entry.timer) clearTimeout(entry.timer);
          matchedBubble = entry.bubble || entry;
          this.pendingMessages.delete(msg.client_msg_id);
        } else if (!msg.client_msg_id) {
          // Fallback solo si el backend no devolvió client_msg_id: buscar la primera burbuja pendiente con igual contenido
          const pendingBubbles = this.container.querySelectorAll('.message-bubble.message-pending');
          for (let b of pendingBubbles) {
            const txt = b.querySelector('.message-content-text');
            if (txt && txt.textContent.trim() === (msg.contenido || '').trim()) {
              matchedBubble = b;
              const pendingId = b.dataset.clientMsgId;
              if (pendingId && this.pendingMessages.has(pendingId)) {
                const entry = this.pendingMessages.get(pendingId);
                if (entry && entry.timer) clearTimeout(entry.timer);
                this.pendingMessages.delete(pendingId);
              }
              break;
            }
          }
        }

        if (matchedBubble) {
          this.markMessageDelivered(matchedBubble, msg);
          return;
        }
      }

      // Si no es un mensaje optimista propio, creamos la burbuja recibida
      this.renderReceivedMessage(msg, isMine);
    }

    /**
     * Marca un mensaje pendiente como fallido tras timeout o error de socket,
     * permitiendo reintentar el envío o recuperar el texto al input.
     */
    markMessageFailed(clientMsgId, reason) {
      const entry = this.pendingMessages.get(clientMsgId);
      if (!entry) return;

      if (entry.timer) {
        clearTimeout(entry.timer);
        entry.timer = null;
      }

      const bubble = entry.bubble || entry;
      if (!bubble) return;

      bubble.classList.remove('message-pending');
      bubble.classList.add('message-failed');

      const statusNode = bubble.querySelector('.message-status');
      if (statusNode) {
        statusNode.innerHTML = `
          <span class="status-failed-badge" title="${this.escapeHtml(reason || 'Error al enviar')}">
            <span>&#9888;</span> Falló el envío
          </span>
          <button type="button" class="chat-btn-action chat-btn-retry" title="Reintentar envío">&#8635; Reintentar</button>
          <button type="button" class="chat-btn-action chat-btn-recover" title="Recuperar texto en el campo">&#8617; Recuperar</button>
        `;

        const retryBtn = statusNode.querySelector('.chat-btn-retry');
        if (retryBtn) {
          retryBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.retrySendMessage(clientMsgId);
          });
        }

        const recoverBtn = statusNode.querySelector('.chat-btn-recover');
        if (recoverBtn) {
          recoverBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.recoverMessageText(clientMsgId);
          });
        }
      }
    }

    /**
     * Reintenta el envío de un mensaje previamente fallido vía WebSocket.
     */
    retrySendMessage(clientMsgId) {
      const entry = this.pendingMessages.get(clientMsgId);
      if (!entry) return;

      const bubble = entry.bubble || entry;
      const texto = entry.texto;

      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        bubble.classList.remove('message-failed');
        bubble.classList.add('message-pending');

        const statusNode = bubble.querySelector('.message-status');
        if (statusNode) {
          statusNode.innerHTML = `
            <span class="status-spinner"></span>
            <span class="status-text-pending">Reintentando...</span>
          `;
        }

        if (entry.timer) clearTimeout(entry.timer);
        entry.timer = setTimeout(() => {
          this.markMessageFailed(clientMsgId, 'Tiempo de espera agotado al reintentar');
        }, 12000);

        try {
          this.socket.send(JSON.stringify({
            contenido: texto,
            client_msg_id: clientMsgId
          }));
        } catch (err) {
          console.error('[ChatRealtime] Error en reintento de envío:', err);
          this.markMessageFailed(clientMsgId, 'Error en reintento');
        }
      } else {
        console.warn('[ChatRealtime] Socket cerrado al reintentar; reconectando...');
        this.connectWebSocket();
        const badge = bubble.querySelector('.status-failed-badge');
        if (badge) {
          badge.textContent = 'Reconectando... Vuelve a pulsar Reintentar';
        }
      }
    }

    /**
     * Recupera el texto de un mensaje fallido hacia el textarea/input y elimina la burbuja fallida.
     */
    recoverMessageText(clientMsgId) {
      const entry = this.pendingMessages.get(clientMsgId);
      if (!entry) return;

      const bubble = entry.bubble || entry;
      const texto = entry.texto;

      if (entry.timer) clearTimeout(entry.timer);
      this.pendingMessages.delete(clientMsgId);

      if (this.inputField) {
        this.inputField.value = texto;
        this.inputField.focus();
      }

      if (bubble && bubble.parentNode) {
        bubble.remove();
      }
    }

    /**
     * Marca todos los mensajes en cola como fallidos (e.g. desconexión abrupta).
     */
    markAllPendingMessagesFailed(reason) {
      for (const [id] of this.pendingMessages.entries()) {
        this.markMessageFailed(id, reason);
      }
    }

    /**
     * Actualiza una burbuja pendiente a estado 'Entregado' con doble check visual.
     */
    markMessageDelivered(bubble, msg) {
      if (!bubble) return;

      bubble.classList.remove('message-pending');
      bubble.classList.remove('message-failed');
      bubble.classList.add('message-delivered');

      if (msg && msg.fecha_envio) {
        const timeNode = bubble.querySelector('.message-time');
        if (timeNode) timeNode.textContent = msg.fecha_envio;
      }

      const statusNode = bubble.querySelector('.message-status');
      if (statusNode) {
        statusNode.innerHTML = `
          <span class="status-check-delivered" title="Entregado">&#10003;&#10003;</span>
          <span class="status-text-delivered">Entregado</span>
        `;
      }
    }

    /**
     * Renderiza un mensaje nuevo recibido desde el socket.
     */
    renderReceivedMessage(msg, isMine) {
      if (!this.container) return;

      const placeholder = this.container.querySelector('div[style*="text-align:center"]');
      if (placeholder) placeholder.remove();

      const bubble = document.createElement('div');
      bubble.className = `message-bubble ${isMine ? 'message-sent' : 'message-received'}`;

      if (msg.es_grupal && !isMine) {
        const sender = document.createElement('div');
        sender.className = 'message-sender-name';
        const rolLabel = msg.remitente_rol === 'empresa' ? 'Empresa' : 'Dev';
        sender.textContent = `${msg.remitente_nombre || 'Usuario'} (${rolLabel})`;
        bubble.appendChild(sender);
      }

      const contentNode = document.createElement('div');
      contentNode.className = 'message-content-text';
      contentNode.textContent = msg.contenido || '';
      bubble.appendChild(contentNode);

      // Inyectar previews para el mensaje entrante
      this.enhanceMessageWithPreviews(bubble);

      // Meta fila
      const metaRow = document.createElement('div');
      metaRow.className = 'message-meta-row';

      const timeSpan = document.createElement('span');
      timeSpan.className = 'message-time';
      timeSpan.textContent = msg.fecha_envio || '';
      metaRow.appendChild(timeSpan);

      if (isMine) {
        const statusSpan = document.createElement('span');
        statusSpan.className = 'message-status';
        statusSpan.innerHTML = `
          <span class="status-check-delivered" title="Entregado">&#10003;&#10003;</span>
          <span class="status-text-delivered">Entregado</span>
        `;
        metaRow.appendChild(statusSpan);
      }

      bubble.appendChild(metaRow);
      this.container.appendChild(bubble);

      // Auto-scroll suave inteligente hacia el nuevo mensaje
      this.scrollToBottom(isMine, true);
    }

    /**
     * Normaliza los metadatos de mensajes preexistentes renderizados en la carga inicial.
     */
    normalizeMessageMeta(bubble) {
      if (!bubble) return;
      const existingTime = bubble.querySelector('.message-time');
      if (!existingTime) return;

      // Si ya está agrupado en meta-row, omitir
      if (bubble.querySelector('.message-meta-row')) return;

      const metaRow = document.createElement('div');
      metaRow.className = 'message-meta-row';

      const isSent = bubble.classList.contains('message-sent');
      existingTime.parentNode.insertBefore(metaRow, existingTime);
      metaRow.appendChild(existingTime);

      if (isSent) {
        bubble.classList.add('message-delivered');
        const statusSpan = document.createElement('span');
        statusSpan.className = 'message-status';
        statusSpan.innerHTML = `
          <span class="status-check-delivered" title="Entregado">&#10003;&#10003;</span>
          <span class="status-text-delivered">Entregado</span>
        `;
        metaRow.appendChild(statusSpan);
      }
    }
    setupFormSubmit() {
      if (!this.chatForm || !this.inputField) return;

      this.chatForm.addEventListener('submit', (e) => {
        const texto = this.inputField.value.trim();
        if (!texto) return;

        // Si el WebSocket está conectado, gestionamos el envío en tiempo real con UI optimista
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          e.preventDefault();

          const clientMsgId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 7);
          const bubble = this.renderOptimisticMessage(texto, clientMsgId);
          
          const timeoutId = setTimeout(() => {
            this.markMessageFailed(clientMsgId, 'Tiempo de espera agotado');
          }, 12000);

          this.pendingMessages.set(clientMsgId, {
            bubble: bubble,
            texto: texto,
            clientMsgId: clientMsgId,
            timer: timeoutId
          });

          try {
            this.socket.send(JSON.stringify({
              contenido: texto,
              client_msg_id: clientMsgId
            }));
          } catch (err) {
            console.error('[ChatRealtime] Error enviando mensaje por socket:', err);
            this.markMessageFailed(clientMsgId, 'Error al enviar por socket');
          }

          this.inputField.value = '';
          this.inputField.focus();
        }
        // Si no está disponible el socket, permite el fallback HTTP normal del formulario
      });
    }

    /**
     * Renderiza una burbuja con indicador sutil de 'Enviando...' de inmediato en el chat.
     */
    renderOptimisticMessage(texto, clientMsgId) {
      if (!this.container) return null;

      // Remover placeholder de vacío si existe
      const placeholder = this.container.querySelector('div[style*="text-align:center"]');
      if (placeholder) placeholder.remove();

      const bubble = document.createElement('div');
      bubble.className = 'message-bubble message-sent message-pending';
      bubble.dataset.clientMsgId = clientMsgId;

      const contentNode = document.createElement('div');
      contentNode.className = 'message-content-text';
      contentNode.textContent = texto;
      bubble.appendChild(contentNode);

      // Inyectar previews visuales (GitHub / Archivos / Imágenes)
      this.enhanceMessageWithPreviews(bubble);

      // Meta fila con hora y estado Enviando...
      const metaRow = document.createElement('div');
      metaRow.className = 'message-meta-row';

      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const timeStr = `${hours}:${minutes}`;

      metaRow.innerHTML = `
        <span class="message-time">${timeStr}</span>
        <span class="message-status">
          <span class="status-spinner"></span>
          <span class="status-text-pending">Enviando...</span>
        </span>
      `;

      bubble.appendChild(metaRow);
      this.container.appendChild(bubble);

      // Scroll suave hacia el mensaje enviado
      this.scrollToBottom(true, true);

      return bubble;
    }

    /**
     * Procesa los mensajes existentes en el DOM inicial para inyectar previews
     * y normalizar indicadores de entrega.
     */
    hydrateExistingMessages() {
      if (!this.container) return;
      const bubbles = this.container.querySelectorAll('.message-bubble');
      bubbles.forEach((bubble) => {
        this.enhanceMessageWithPreviews(bubble);
        this.normalizeMessageMeta(bubble);
      });
    }

    /**
     * Analiza el texto del mensaje y genera tarjetas interactivas si contiene
     * enlaces a repositorios de GitHub.
     * @param {HTMLElement} bubble
     */
    enhanceMessageWithPreviews(bubble) {
      if (!bubble || bubble.dataset.hasPreviews === 'true') return;

      const text = bubble.innerText || bubble.textContent || '';
      
      // 1. Patrón para repositorios GitHub: https://github.com/owner/repo
      const ghPattern = /https?:\/\/(?:www\.)?github\.com\/([a-zA-Z0-9_\-\.]+)\/([a-zA-Z0-9_\-\.]+)(?:\/[^\s<>"']*)?/i;
      const ghMatch = text.match(ghPattern);

      if (ghMatch) {
        const fullUrl = ghMatch[0];
        const owner = ghMatch[1];
        let repo = ghMatch[2];
        if (repo.endsWith('.git')) repo = repo.slice(0, -4);

        const card = this.createGitHubCard(fullUrl, owner, repo);
        this.insertPreviewCardIntoBubble(bubble, card);
        bubble.dataset.hasPreviews = 'true';
        return;
      }

      // 2. Patrón para imágenes compartidas
      const imgPattern = /https?:\/\/[^\s<>"']+\.(?:png|jpe?g|webp|gif|svg)(?:\?[^\s<>"']*)?/i;
      const imgMatch = text.match(imgPattern);

      if (imgMatch) {
        const imgCard = this.createImagePreviewCard(imgMatch[0]);
        this.insertPreviewCardIntoBubble(bubble, imgCard);
        bubble.dataset.hasPreviews = 'true';
        return;
      }

      // 3. Patrón para archivos compartidos (PDF, ZIP, DOC, etc.)
      const filePattern = /https?:\/\/[^\s<>"']+\.(?:pdf|zip|rar|docx?|xlsx?|tar\.gz)(?:\?[^\s<>"']*)?/i;
      const fileMatch = text.match(filePattern);

      if (fileMatch) {
        const fileCard = this.createFilePreviewCard(fileMatch[0]);
        this.insertPreviewCardIntoBubble(bubble, fileCard);
        bubble.dataset.hasPreviews = 'true';
      }
    }

    /**
     * Construye un preview visual de imagen con auto-ajuste y click para ampliar.
     */
    createImagePreviewCard(imageUrl) {
      const wrap = document.createElement('div');
      wrap.className = 'chat-preview-image-wrap';

      const img = document.createElement('img');
      img.className = 'chat-preview-image';
      img.src = imageUrl;
      img.alt = 'Adjunto compartido';
      img.loading = 'lazy';

      img.addEventListener('click', () => {
        window.open(imageUrl, '_blank', 'noopener,noreferrer');
      });

      this.attachImageListeners(img);
      wrap.appendChild(img);
      return wrap;
    }

    /**
     * Construye la tarjeta visual para archivos compartidos (PDF, ZIP, etc.).
     */
    createFilePreviewCard(fileUrl) {
      const card = document.createElement('a');
      card.className = 'chat-preview-card file-card';
      card.href = fileUrl;
      card.target = '_blank';
      card.rel = 'noopener noreferrer';

      let fileName = 'archivo_adjunto';
      try {
        const parsed = new URL(fileUrl);
        const parts = parsed.pathname.split('/');
        fileName = decodeURIComponent(parts[parts.length - 1] || fileName);
      } catch (e) {
        fileName = fileUrl.split('/').pop() || fileName;
      }

      const extMatch = fileName.match(/\.([0-9a-z]+)(?:[\?#]|$)/i);
      const ext = extMatch ? extMatch[1].toUpperCase() : 'DOC';

      card.innerHTML = `
        <div class="file-card-inner">
          <div class="file-card-icon">${this.escapeHtml(ext)}</div>
          <div class="file-card-info">
            <div class="file-card-name" title="${this.escapeHtml(fileName)}">${this.escapeHtml(fileName)}</div>
            <div class="file-card-meta">Archivo adjunto &bull; Clic para abrir / descargar</div>
          </div>
        </div>
      `;

      return card;
    }

    /**
     * Construye el nodo DOM de una tarjeta visual para repositorio GitHub.
     */
    createGitHubCard(url, owner, repo) {
      const card = document.createElement('a');
      card.className = 'chat-preview-card github-card';
      card.href = url;
      card.target = '_blank';
      card.rel = 'noopener noreferrer';

      const octocatSvg = `
        <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" style="fill:currentColor; flex-shrink:0;">
          <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
        </svg>
      `;

      card.innerHTML = `
        <div class="github-card-header">
          <span class="github-card-tag">
            ${octocatSvg}
            <span>GitHub</span>
          </span>
          <span class="github-card-badge">Repositorio</span>
        </div>
        <div class="github-card-repo">
          <strong>${this.escapeHtml(owner)}</strong> / <span>${this.escapeHtml(repo)}</span>
        </div>
        <div class="github-card-meta">
          <span>Ver código fuente y ramas</span>
        </div>
        <div class="github-card-action">
          <span>Abrir repositorio en GitHub</span>
          <span>&rarr;</span>
        </div>
      `;

      return card;
    }

    /**
     * Inserta la tarjeta de preview en una posición visual adecuada dentro de la burbuja.
     */
    insertPreviewCardIntoBubble(bubble, card) {
      const metaRow = bubble.querySelector('.message-meta-row') || bubble.querySelector('.message-time');
      if (metaRow) {
        bubble.insertBefore(card, metaRow);
      } else {
        bubble.appendChild(card);
      }
    }

    /**
     * Utilidad para sanitizar texto insertado en plantillas HTML.
     */
    escapeHtml(str) {
      if (!str) return '';
      const div = document.createElement('div');
      div.textContent = str;
      return div.innerHTML;
    }

    /**
     * Observa la carga asíncrona de imágenes y mutaciones del DOM para garantizar
     * que el scroll permanezca al final cuando las imágenes terminen de descargarse.
     */
    setupImageAndMutationObservers() {
      if (!this.container) return;

      // 1. Observar imágenes existentes
      this.attachImageListeners(this.container);

      // 2. Observar inserción de nuevos mensajes con imágenes o adjuntos
      if ('MutationObserver' in window) {
        this.mutationObserver = new MutationObserver((mutations) => {
          let hasNewNodes = false;
          mutations.forEach((mutation) => {
            if (mutation.addedNodes && mutation.addedNodes.length > 0) {
              mutation.addedNodes.forEach((node) => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                  hasNewNodes = true;
                  this.attachImageListeners(node);
                }
              });
            }
          });

          if (hasNewNodes) {
            this.scrollToBottom(false, true);
          }
        });

        this.mutationObserver.observe(this.container, {
          childList: true,
          subtree: true
        });
      }

      // 3. ResizeObserver para ajustar dimensiones si el contenedor sufre reflow
      if ('ResizeObserver' in window) {
        const resizeObserver = new ResizeObserver(() => {
          this.scrollToBottom(false, false);
        });
        resizeObserver.observe(this.container);
      }
    }

    /**
     * Asocia manejadores de carga a cualquier <img> no completada dentro de una raíz dada.
     * @param {Element} rootNode
     */
    attachImageListeners(rootNode) {
      if (!rootNode) return;
      const images = rootNode.matches && rootNode.matches('img')
        ? [rootNode]
        : Array.from(rootNode.querySelectorAll ? rootNode.querySelectorAll('img') : []);

      images.forEach((img) => {
        if (this.imageObservers.has(img)) return;
        this.imageObservers.add(img);

        if (!img.complete) {
          const onImgFinish = () => {
            img.removeEventListener('load', onImgFinish);
            img.removeEventListener('error', onImgFinish);
            this.scrollToBottom(false, true);
          };
          img.addEventListener('load', onImgFinish);
          img.addEventListener('error', onImgFinish);
        }
      });
    }

    /**
     * Auto-scroll inteligente y suave hacia el fondo del contenedor de mensajes.
     * @param {boolean} force - Si es true, fuerza el scroll aunque el usuario esté leyendo arriba.
     * @param {boolean} smooth - Si es true, realiza un scroll animado suave; si false, scroll inmediato.
     */
    scrollToBottom(force = false, smooth = true) {
      if (!this.container) return;

      const threshold = 160;
      const distanceFromBottom = this.container.scrollHeight - this.container.scrollTop - this.container.clientHeight;
      const isNearBottom = distanceFromBottom <= threshold;

      if (force || isNearBottom) {
        if (smooth && typeof this.container.scrollTo === 'function') {
          this.container.scrollTo({
            top: this.container.scrollHeight,
            behavior: 'smooth'
          });
        } else {
          this.container.scrollTop = this.container.scrollHeight;
        }
      }
    }
  }

  // Exportar al entorno global
  window.ChatRealtimeManager = ChatRealtimeManager;

  document.addEventListener('DOMContentLoaded', () => {
    if (!window.chatRealtimeInstance && document.getElementById('chat-container')) {
      window.chatRealtimeInstance = new ChatRealtimeManager();
    }
  });
})(window, document);
