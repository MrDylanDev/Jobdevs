/* ─────────────────────────────────────────────────────────────
   Modal compartido "Ver proyecto" — admin, empresa y desarrollador.
   Intercepta enlaces [data-ver-proyecto], consulta la ficha JSON y la
   pinta sin abandonar el dashboard. Sin dependencias externas.
   ───────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var modal = null;
  var lastFocus = null;
  var controller = null;

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function safeIcon(name) {
    return /^fa-[a-z0-9- ]+$/i.test(name || '') ? name : 'fa-solid fa-circle-info';
  }

  function estadoClass(estado) {
    var permitidos = ['publicado', 'en_desarrollo', 'en_revision', 'finalizado', 'rechazado', 'inactivo', 'en_disputa', 'pendiente', 'completado', 'cancelada'];
    return permitidos.indexOf(estado) !== -1 ? 'is-' + estado : '';
  }

  function ensureModal() {
    if (modal) return modal;

    modal = document.createElement('div');
    modal.className = 'jdp-modal';
    modal.id = 'jdpModal';
    modal.hidden = true;
    modal.innerHTML =
      '<div class="jdp-backdrop" data-jdp-close></div>' +
      '<div class="jdp-card" role="dialog" aria-modal="true" aria-labelledby="jdpTitulo">' +
        '<header class="jdp-header">' +
          '<div style="min-width:0;">' +
            '<div class="jdp-kicker">// Ficha del proyecto</div>' +
            '<h2 class="jdp-title" id="jdpTitulo">Cargando proyecto…</h2>' +
            '<div class="jdp-sub" data-jdp-sub></div>' +
          '</div>' +
          '<button type="button" class="jdp-close" data-jdp-close aria-label="Cerrar">&times;</button>' +
        '</header>' +
        '<div class="jdp-body" data-jdp-body aria-live="polite">' +
          '<div class="jdp-loading"><i class="fa-solid fa-circle-notch fa-spin"></i><span>Consultando la ficha del proyecto…</span></div>' +
        '</div>' +
        '<footer class="jdp-footer" data-jdp-footer hidden></footer>' +
      '</div>';

    document.body.appendChild(modal);
    modal.addEventListener('click', function (event) {
      if (event.target.closest('[data-jdp-close]')) {
        event.preventDefault();
        cerrar();
      }
    });
    document.addEventListener('keydown', onKeydown);
    return modal;
  }

  function onKeydown(event) {
    if (!modal || modal.hidden) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      cerrar();
      return;
    }
    if (event.key !== 'Tab') return;
    var focusables = Array.prototype.slice.call(
      modal.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')
    ).filter(function (el) { return el.offsetParent !== null; });
    if (!focusables.length) return;
    var first = focusables[0];
    var last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function abrir(enlace) {
    lastFocus = document.activeElement;
    ensureModal();
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    var body = modal.querySelector('[data-jdp-body]');
    var footer = modal.querySelector('[data-jdp-footer]');
    var titulo = modal.querySelector('#jdpTitulo');
    var sub = modal.querySelector('[data-jdp-sub]');
    body.scrollTop = 0;
