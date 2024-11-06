/**
 * JobDevs — Sistema de Modales Integrados en Dashboards
 * Controla Contratos, Avances, Calificaciones, Empresas y Disputas sin redirecciones.
 */
(function () {
  'use strict';

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function leerCookie(nombre) {
    var match = document.cookie
      .split('; ')
      .find(function (item) { return item.indexOf(nombre + '=') === 0; });
    return match ? decodeURIComponent(match.slice(nombre.length + 1)) : '';
  }

  function getCsrfToken() {
    var cookie = leerCookie('csrftoken');
    if (cookie) return cookie;
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : '';
  }

  function mostrarToast(mensaje, esError) {
    var toast = document.getElementById('jdmToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'jdmToast';
      toast.className = 'jdm-toast';
      toast.setAttribute('role', 'status');
      document.body.appendChild(toast);
    }
    toast.innerHTML = '<i class="fa-solid ' + (esError ? 'fa-circle-exclamation' : 'fa-circle-check') + '"></i><span>' + escapeHtml(mensaje) + '</span>';
    toast.style.borderColor = esError ? '#ef4444' : '#00e676';
    toast.style.color = esError ? '#f87171' : '#69f0ae';
    toast.classList.add('is-visible');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(function () {
      toast.classList.remove('is-visible');
    }, 4500);
  }

  // ─────────────────────────────────────────────────────────────
  // Modal Base Manager
  // ─────────────────────────────────────────────────────────────
  var modalEl = null;
  var lastFocusEl = null;

  function ensureModal() {
    if (modalEl) return modalEl;

    modalEl = document.createElement('div');
    modalEl.id = 'jdmModal';
    modalEl.className = 'jdm-modal';
    modalEl.hidden = true;
    modalEl.innerHTML =
      '<div class="jdm-backdrop" data-jdm-close></div>' +
      '<div class="jdm-card" id="jdmCard" role="dialog" aria-modal="true" aria-labelledby="jdmTitulo">' +
        '<header class="jdm-header">' +
          '<div style="min-width:0;flex:1;">' +
            '<div class="jdm-kicker" id="jdmKicker">// ACCIÓN</div>' +
            '<h2 class="jdm-title" id="jdmTitulo">Cargando…</h2>' +
            '<div class="jdm-sub" id="jdmSub"></div>' +
          '</div>' +
          '<button type="button" class="jdm-close" data-jdm-close aria-label="Cerrar">&times;</button>' +
        '</header>' +
        '<div class="jdm-body" id="jdmBody" aria-live="polite">' +
          '<div class="jdm-loading"><i class="fa-solid fa-circle-notch"></i><span>Cargando información…</span></div>' +
        '</div>' +
        '<footer class="jdm-footer" id="jdmFooter" hidden></footer>' +
      '</div>';

    document.body.appendChild(modalEl);

    modalEl.addEventListener('click', function (e) {
      if (e.target.closest('[data-jdm-close]')) {
        e.preventDefault();
        cerrarModal();
      }
    });

    document.addEventListener('keydown', function (e) {
      if (!modalEl || modalEl.hidden) return;
      if (e.key === 'Escape') {
        e.preventDefault();
        cerrarModal();
      }
    });

    return modalEl;
  }

  function abrirModal(cardClass) {
    lastFocusEl = document.activeElement;
    ensureModal();
    var card = document.getElementById('jdmCard');
    card.className = 'jdm-card' + (cardClass ? ' ' + cardClass : '');
    modalEl.hidden = false;
    document.body.style.overflow = 'hidden';

    var body = document.getElementById('jdmBody');
    var footer = document.getElementById('jdmFooter');
    body.scrollTop = 0;
    body.innerHTML = '<div class="jdm-loading"><i class="fa-solid fa-circle-notch"></i><span>Cargando información…</span></div>';
    footer.hidden = true;
    footer.innerHTML = '';
  }

  function cerrarModal() {
    if (!modalEl) return;
    modalEl.hidden = true;
