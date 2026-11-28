/**
 * Módulo Proyectos & Postulaciones — Dashboard Desarrollador
 * Filtrado dinámico de Explorar Proyectos y modal HTMX de postulaciones.
 */

import {
  sincronizarCsrf,
  animarContadorKpi,
  _setupModalFocusTrap,
  _cleanupModalFocusTrap,
} from './ui_core.js';
import { abrirVerificacion } from './perfil_verificacion.js';

// ═══════════════════════════════════════════════
// FILTRADO DINÁMICO: Explorar Proyectos (Dev)
// ═══════════════════════════════════════════════
export function filterDevExplore() {
  const searchInput = document.getElementById('devExploreSearch');
  const catSelect = document.getElementById('devExploreCategory');
  const prioSelect = document.getElementById('devExplorePriority');
  if (!searchInput) return;

  const q = (searchInput.value || '').toLowerCase().trim();
  const cat = (catSelect ? catSelect.value : '').toLowerCase().trim();
  const prio = (prioSelect ? prioSelect.value : '').toLowerCase().trim();

  const cards = document.querySelectorAll('#devExploreGrid .dev-explore-card');

  cards.forEach(card => {
    const titulo = card.getAttribute('data-titulo') || '';
    const desc = card.getAttribute('data-desc') || '';
    const empresa = card.getAttribute('data-empresa') || '';
    const tipo = card.getAttribute('data-tipo') || '';
    const prioridad = card.getAttribute('data-prioridad') || '';

    const matchesQ = !q || titulo.includes(q) || desc.includes(q) || empresa.includes(q);
    const matchesCat = !cat || tipo === cat;
    const matchesPrio = !prio || prioridad === prio;

    if (matchesQ && matchesCat && matchesPrio) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });
}

export function resetDevExploreFilters() {
  const searchInput = document.getElementById('devExploreSearch');
  const catSelect = document.getElementById('devExploreCategory');
  const prioSelect = document.getElementById('devExplorePriority');
  if (searchInput) searchInput.value = '';
  if (catSelect) catSelect.value = '';
  if (prioSelect) prioSelect.value = '';
  filterDevExplore();
}

// ═══════════════════════════════════════════════
// MODAL FLOTANTE: POSTULACIÓN A PROYECTO
// ═══════════════════════════════════════════════
let postulacionUrl = '';
let postulacionCard = null;

function setTextoPostulacion(modal, selector, valor) {
  const el = modal.querySelector(selector);
  if (el) el.textContent = valor;
}

export function abrirPostulacion(btn) {
  const modal = document.getElementById('modalPostulacion');
  if (!modal || !btn) return;

  postulacionUrl = btn.getAttribute('data-url') || '';
  postulacionCard = btn.closest('.project-card');

  setTextoPostulacion(modal, '[data-postulacion-tipo]', btn.dataset.tipo || 'Proyecto');
  setTextoPostulacion(modal, '[data-postulacion-prioridad]', btn.dataset.prioridad || '—');
  setTextoPostulacion(modal, '[data-postulacion-titulo]', btn.dataset.titulo || 'Proyecto');
  setTextoPostulacion(modal, '[data-postulacion-empresa]', btn.dataset.empresa || '');
  setTextoPostulacion(modal, '[data-postulacion-vacantes]', btn.dataset.vacantes || '0');
  setTextoPostulacion(modal, '[data-postulacion-cierre]', btn.dataset.cierre || 'Sin límite');
  setTextoPostulacion(modal, '[data-postulacion-descripcion]', btn.dataset.descripcion || '');

  const form = modal.querySelector('[data-postulacion-form]');
  if (form) {
    form.reset();
    form.setAttribute('action', postulacionUrl);
    form.setAttribute('hx-post', postulacionUrl);
    if (window.htmx && typeof window.htmx.process === 'function') {
      window.htmx.process(form);
    }
  }
  mostrarFeedbackPostulacion('', false);
  const btnVerificar = modal.querySelector('[data-ir-verificacion]');
  if (btnVerificar) btnVerificar.hidden = true;

  sincronizarCsrf(modal);
  modal.classList.add('is-open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';

  const first = modal.querySelector('#id_post_carta');
  if (first) first.focus({ preventScroll: true });
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
  _setupModalFocusTrap(modal, cerrarPostulacion);
}

export function cerrarPostulacion() {
  const modal = document.getElementById('modalPostulacion');
  if (!modal) return;
  _cleanupModalFocusTrap();
  modal.classList.remove('is-open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

export function mostrarFeedbackPostulacion(mensaje, esError) {
  const feedback = document.querySelector('[data-postulacion-feedback]');
  if (!feedback) return;
  feedback.textContent = mensaje || '';
  feedback.hidden = !mensaje;
  feedback.classList.toggle('is-error', !!esError);
}

function actualizarContadoresPostulacion() {
  const contenedorVigentes = document.querySelector('[data-testid="postulaciones-vigentes"]');
  if (contenedorVigentes) {
    const postList = contenedorVigentes.querySelector('.post-list');
    if (postList) {
      const emptyState = postList.querySelector('.cockpit-empty-state, .empty-state');
      if (emptyState) emptyState.remove();

      const badgeCount = contenedorVigentes.querySelector('.label-section .badge');
      if (badgeCount) {
        const cards = postList.querySelectorAll('.post-row-compact');
        badgeCount.textContent = cards.length + ' en curso';
      }
    }
  }

  const cardMetrica = document.querySelector('.dev-card[onclick*="postulaciones"] .dev-card-val');
  if (cardMetrica) {
    const numEl = cardMetrica.querySelector('.kpi-num') || cardMetrica;
    const valActual = parseInt((numEl.getAttribute('data-target-val') || numEl.textContent).trim(), 10) || 0;
    numEl.removeAttribute('data-target-val');
    numEl.textContent = valActual + 1;
    animarContadorKpi(numEl);
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// Exponer en window para manejadores inline HTML y scripts hermanos
window.filterDevExplore = filterDevExplore;
window.resetDevExploreFilters = resetDevExploreFilters;
window.abrirPostulacion = abrirPostulacion;
window.cerrarPostulacion = cerrarPostulacion;

// ═══════════════════════════════════════════════
// INICIALIZACIÓN PROYECTOS Y POSTULACIONES
// ═══════════════════════════════════════════════
export function initProyectosPostulaciones() {
  const search = document.getElementById('devExploreSearch');
  const cat = document.getElementById('devExploreCategory');
  const prio = document.getElementById('devExplorePriority');
  if (search) search.addEventListener('input', filterDevExplore);
  if (cat) cat.addEventListener('change', filterDevExplore);
  if (prio) prio.addEventListener('change', filterDevExplore);

  document.addEventListener('click', (event) => {
    const abrir = event.target.closest('[data-abrir-postulacion]');
    if (abrir) {
      event.preventDefault();
      abrirPostulacion(abrir);
      return;
    }

    if (event.target.closest('[data-cerrar-postulacion]')) {
      cerrarPostulacion();
      return;
    }

    if (event.target.closest('[data-ir-verificacion]')) {
      cerrarPostulacion();
      abrirVerificacion();
    }
  });

  document.addEventListener('htmx:beforeRequest', (event) => {
    const form = event.target && event.target.closest ? event.target.closest('[data-postulacion-form]') : null;
    if (!form) return;

    const carta = form.querySelector('[name="carta"]');
    if (carta && !carta.value.trim()) {
      event.preventDefault();
      mostrarFeedbackPostulacion('La carta de presentación es obligatoria.', true);
      carta.focus({ preventScroll: true });
      return;
    }
    if (!postulacionUrl) {
      event.preventDefault();
      return;
    }
    sincronizarCsrf(form);
    mostrarFeedbackPostulacion('', false);
  });

  document.addEventListener('jobdevs:postulacion-creada', () => {
    cerrarPostulacion();
    if (postulacionCard) {
      postulacionCard.remove();
      postulacionCard = null;
    }
    actualizarContadoresPostulacion();
  });

  document.addEventListener('htmx:responseError', (event) => {
    const elt = event.detail && event.detail.elt;
    const form = elt && elt.closest ? elt.closest('[data-postulacion-form]') : null;
    if (!form) return;

    const xhr = event.detail.xhr;
    const modal = form.closest('#modalPostulacion');
    const btnVerificar = modal ? modal.querySelector('[data-ir-verificacion]') : null;

    let errData = null;
    const triggerHeader = xhr ? xhr.getResponseHeader('HX-Trigger') : null;
    if (triggerHeader) {
      try {
        const parsed = JSON.parse(triggerHeader);
        errData = parsed && parsed['jobdevs:postulacion-error'] ? parsed['jobdevs:postulacion-error'] : null;
      } catch (e) {
        errData = null;
      }
    }

    if (errData) {
      if (btnVerificar) btnVerificar.hidden = !errData.requiere_verificacion;
      mostrarFeedbackPostulacion(errData.mensaje || 'No se pudo enviar la postulación.', true);
      return;
    }

    if (xhr && xhr.status === 403) {
      const esCsrf = /csrf/i.test(xhr.responseText || '');
      mostrarFeedbackPostulacion(
        esCsrf
          ? 'Tu token de seguridad expiró. Actualizando la página para continuar…'
          : 'No tienes permisos para realizar esta postulación.',
        true
      );
      return;
    }

    mostrarFeedbackPostulacion('No se pudo enviar la postulación. Inténtalo de nuevo.', true);
  });

  document.addEventListener('htmx:sendError', (event) => {
    const elt = event.detail && event.detail.elt;
    if (!elt || !elt.closest || !elt.closest('[data-postulacion-form]')) return;
    mostrarFeedbackPostulacion(
      'No pudimos enviar tu postulación. Revisa tu conexión e inténtalo de nuevo.',
      true
    );
  });
}
