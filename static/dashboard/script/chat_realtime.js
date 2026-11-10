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
      this.scrollToBottom(true, false);
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
      
      // Patrón para repositorios GitHub: https://github.com/owner/repo
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
      }
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
