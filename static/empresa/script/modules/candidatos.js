/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Candidatos Drawer & Chat Integration
 * ============================================================
 */

import { t, ejecutarSwitchTabDOM } from './ui_core.js';
import { abrirModalContrato } from './contratos_hitos.js';

export function _limpiarCacheDrawerCandidatos() {
  // Mantenido por compatibilidad de contrato global; HTMX siempre consulta estado fresco del servidor.
}

function bindDrawerCandidateLinks(container) {
  if (!container) return;
  container.querySelectorAll('.drawer-candidates-body a').forEach(function (link) {
    if (link.hasAttribute('data-abrir-desarrollador') || link.hasAttribute('hx-get')) {
      return;
    }
    const href = link.getAttribute('href') || '';
    const coincidenciaContrato = href.match(/contrato-digital\/(\d+)\/?/);
    if (coincidenciaContrato) {
      link.removeAttribute('target');
      link.setAttribute('rel', 'noopener');
      if (!link.dataset.contratoBound) {
        link.dataset.contratoBound = '1';
        link.addEventListener('click', function (ev) {
          abrirModalContrato(ev, coincidenciaContrato[1]);
        });
      }
      return;
    }
    link.setAttribute('target', '_blank');
    link.setAttribute('rel', 'noopener');
  });
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function abrirDrawerCandidatos(event, url, titulo) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  window._ultimoUrlCandidatos = url;

  const drawer = document.getElementById('drawerCandidatos');
  const titleEl = document.getElementById('drawerProjectTitle');
  const contentEl = document.getElementById('drawerContent');

  if (titleEl) titleEl.textContent = titulo || t('candidatosPostulados', 'Candidatos Postulados');
  if (drawer) {
    drawer.classList.add('is-open');
    document.body.style.overflow = 'hidden';
  }

  if (!contentEl) return;

  contentEl.innerHTML = '<div class="drawer-loading"><i data-lucide="loader-circle" class="corp-spin"></i><p>' + t('cargandoPostulaciones', 'Cargando postulaciones y perfiles de candidatos...') + '</p></div>';
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }

  if (window.htmx && typeof window.htmx.ajax === 'function') {
    window.htmx.ajax('GET', url, { target: '#drawerContent', swap: 'innerHTML' }).catch(function () {
      contentEl.innerHTML = '<div class="activity-empty" style="padding:40px 20px;"><i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i><p>' + t('errorVistaPrevia', 'No se pudo cargar la vista previa in-situ.') + '</p></div>';
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    });
    return;
  }

  fetch(url, { headers: { 'HX-Request': 'true', 'Accept': 'text/html' }, credentials: 'same-origin' })
    .then(function (res) {
      if (!res.ok) throw new Error(t('errorConsultarCandidatos', 'Error al consultar candidatos'));
      return res.text();
    })
    .then(function (html) {
      contentEl.innerHTML = html;
      bindDrawerCandidateLinks(contentEl);
    })
    .catch(function () {
      contentEl.innerHTML = '<div class="activity-empty" style="padding:40px 20px;"><i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i><p>' + t('errorVistaPrevia', 'No se pudo cargar la vista previa in-situ.') + '</p></div>';
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    });
}

export function cerrarDrawerCandidatos() {
  const drawer = document.getElementById('drawerCandidatos');
  if (drawer) {
    drawer.classList.remove('is-open');
    document.body.style.overflow = '';
  }
}

export function abrirChatEnCentro(event, receptorId, proyectoId) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  ejecutarSwitchTabDOM('centro-chat');
  try {
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, '', '#centro-chat');
    }
  } catch (e) {}

  const list = document.querySelector('#centro-chat [data-chat-list]');
  if (!list) return;
  const selectorExacto = '.jd-chat-item[data-receptor="' + String(receptorId) + '"][data-proyecto="' + String(proyectoId) + '"]';
  const item = list.querySelector(selectorExacto) || list.querySelector('.jd-chat-item[data-receptor="' + String(receptorId) + '"]');
  if (item) {
    item.click();
  }
}

// --- Global Window Contracts ---

window._limpiarCacheDrawerCandidatos = _limpiarCacheDrawerCandidatos;
window.abrirDrawerCandidatos = abrirDrawerCandidatos;
window.cerrarDrawerCandidatos = cerrarDrawerCandidatos;
window.abrirChatEnCentro = abrirChatEnCentro;

// --- DOM Initialization ---

export function initCandidatos() {
  const drawerCandidatos = document.getElementById('drawerCandidatos');
  if (drawerCandidatos) {
    drawerCandidatos.addEventListener('click', function (e) {
      if (e.target === drawerCandidatos) {
        cerrarDrawerCandidatos();
      }
    });
  }

  document.addEventListener('htmx:afterSwap', function (event) {
    const target = event && event.detail && event.detail.target;
    if (!target || target.id !== 'drawerContent') return;
    const xhr = event.detail.xhr;
    if (xhr && xhr.responseURL) {
      window._ultimoUrlCandidatos = xhr.responseURL;
    }
    bindDrawerCandidateLinks(target);
  });
}
