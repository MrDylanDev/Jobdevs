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
