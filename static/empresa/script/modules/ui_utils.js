/**
 * ============================================================
 * JobDevs - Dashboard Empresa: UI Shared Utilities, Theme,
 * Language Switcher & Logout Helpers
 * ============================================================
 */

// --- Shared Utilities ---

export function onReady(fn) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fn, { once: true });
  } else {
    fn();
  }
}

let _i18nCache = null;

export function loadI18n() {
  if (_i18nCache !== null) return _i18nCache;
  try {
    const el = document.getElementById('empresa-i18n');
    _i18nCache = el ? JSON.parse(el.textContent) : {};
  } catch (e) {
    _i18nCache = {};
  }
  return _i18nCache;
}

export function t(key, fallback) {
  const dict = loadI18n();
  return (dict && dict[key]) || fallback;
}

export function csrfTokenActual() {
  const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (input && input.value) return input.value;
  const coincidencia = document.cookie.match(/csrftoken=([^;]+)/);
  return coincidencia ? coincidencia[1] : '';
}

export function escaparHtml(valor) {
  return String(valor === null || valor === undefined ? '' : valor)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export const EASE_OUT_EXPO = 'cubic-bezier(0.16, 1, 0.3, 1)';

export function prefersReducedMotion() {
  return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
}

// --- Toast Corporativo ---

export function mostrarToastCorp(mensaje, esError) {
  const toast = document.getElementById('corpToast');
  if (!toast) return;
  const span = toast.querySelector('span');
  if (span) span.textContent = mensaje;
  toast.classList.toggle('is-error', !!esError);
  toast.classList.add('show');
  setTimeout(function () {
    toast.classList.remove('show');
    toast.classList.remove('is-error');
  }, 3500);
}

// --- Modo Claro / Oscuro ---

export const THEME_STORAGE_KEY = 'jobdevs-theme';

export function obtenerTemaActual() {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
}

export function actualizarBotonTema(tema) {
  const btn = document.getElementById('empresaThemeToggle');
  if (!btn) return;
  btn.setAttribute('aria-pressed', tema === 'dark' ? 'true' : 'false');
  btn.setAttribute('aria-label', tema === 'dark' ? t('cambiarTemaClaro', 'Cambiar a tema claro') : t('cambiarTemaOscuro', 'Cambiar a tema oscuro'));
  const label = document.getElementById('empresaThemeLabel');
  if (label) {
    label.textContent = tema === 'dark' ? t('temaOscuroLabel', 'Tema oscuro') : t('temaClaroLabel', 'Tema claro');
  }
}

export function toggleEmpresaTheme() {
  const temaActual = obtenerTemaActual();
  const nuevoTema = temaActual === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', nuevoTema);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, nuevoTema);
  } catch (e) {}
  actualizarBotonTema(nuevoTema);
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// --- Idioma & Cierre de Sesión ---

export function switchEmpresaIdioma(event, el) {
  if (!el || !el.href) return;
  if (event) event.preventDefault();
  el.classList.add('is-switching');
  const wrapper = document.querySelector('.main-wrapper');
  if (wrapper) wrapper.classList.add('is-lang-switching');
  const targetUrl = new URL(el.href, window.location.origin);
  const activeSec = document.querySelector('.seccion-v.activa, .section-v.activa');
  const currentHash = window.location.hash || (activeSec && activeSec.id ? '#' + activeSec.id : '');
  const params = new URLSearchParams(window.location.search);
  if (!params.get('section') && activeSec && activeSec.id) {
    params.set('section', activeSec.id);
  }
  const qs = params.toString();
  const finalHref = targetUrl.pathname + (qs ? '?' + qs : '') + currentHash;
  setTimeout(function () {
    if (typeof window.closeUserMenu === 'function') {
      window.closeUserMenu();
    }
    window.location.href = finalHref;
  }, 110);
}

export function cerrarSesionConSpinner(event, el) {
  if (!el || !el.href) return;
  if (event) event.preventDefault();
  if (typeof window.closeUserMenu === 'function') {
    window.closeUserMenu();
  }
  const overlay = document.getElementById('logoutSpinnerOverlay');
  if (overlay) {
    overlay.style.display = 'flex';
    overlay.setAttribute('aria-hidden', 'false');
  }
  setTimeout(function () {
    window.location.href = el.href;
  }, 350);
}
