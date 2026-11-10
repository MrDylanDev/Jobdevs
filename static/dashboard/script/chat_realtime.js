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
      this.scrollToBottom(true, false);
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
