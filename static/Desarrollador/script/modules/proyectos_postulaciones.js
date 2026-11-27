/**
 * Módulo Proyectos & Postulaciones — Dashboard Desarrollador
 * Filtrado dinámico de Explorar Proyectos y modal/envío AJAX de postulaciones.
 */

import {
  leerCookie,
  sincronizarCsrf,
  mostrarToast,
  escapeHtml,
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

  const cards = document.querySelectorAll('.dev-explore-card');

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
  if (form) form.reset();
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

export function insertarPostulacionActiva(post) {
  const contenedorVigentes = document.querySelector('[data-testid="postulaciones-vigentes"]');
  if (!contenedorVigentes) return;

  const postList = contenedorVigentes.querySelector('.post-list');
  if (!postList) return;

  // Si había un empty state ("No tienes postulaciones vigentes"), removerlo
  const emptyState = postList.querySelector('.cockpit-empty-state, .empty-state');
  if (emptyState) {
    emptyState.remove();
  }

  const p = post.proyecto || {};
  const inicial = (p.empresa_nombre || 'E').slice(0, 1).toUpperCase();
  const avatarHtml = p.empresa_logo
    ? '<img src="' + escapeHtml(p.empresa_logo) + '" alt="' + escapeHtml(p.empresa_nombre) + '">'
    : inicial;

  const cardHtml = `
    <article class="post-row-compact" style="animation: devFade 0.3s ease;">
      <!-- Línea 1: Empresa + Fecha a la izquierda | Estado a la derecha -->
      <div class="post-compact-line-1">
        <div class="post-compact-empresa">
          <div class="post-compact-avatar">
            ${avatarHtml}
          </div>
          <div class="post-compact-meta">
            <a href="${escapeHtml(p.detalle_empresa_url || '#')}" data-abrir-empresa data-url="${escapeHtml(p.detalle_empresa_url || '#')}" class="post-compact-empresa-link" title="Ver perfil institucional">
              <span>${escapeHtml(p.empresa_nombre || '')}</span>
              <i data-lucide="arrow-up-right" style="width:11px; height:11px; opacity:0.6;"></i>
            </a>
            <span class="post-compact-date">· Postulado el ${escapeHtml(post.fecha || 'Hoy')} (hace instantes)</span>
          </div>
        </div>

        <div class="post-status-pill">
          <span class="post-status-dot is-pendiente"></span>
          <span class="post-status-text">${escapeHtml(post.estado_display || 'Pendiente de evaluación')}</span>
        </div>
      </div>

      <!-- Línea 2: Título + Tags a la izquierda | Botón Ver a la derecha -->
      <div class="post-compact-line-2">
        <div class="post-compact-project-info">
          <h3 class="post-compact-title">${escapeHtml(p.titulo || '')}</h3>
          <div class="post-tags-row">
            <span class="post-tag"><i data-lucide="layers"></i> ${escapeHtml(p.tipo_solucion || '')}</span>
            <span class="post-tag"><i data-lucide="map-pin"></i> ${escapeHtml(p.modalidad || '')}</span>
            <span class="post-tag" style="color:var(--text-muted); border-style:dashed;">
              <i data-lucide="clock" style="color:var(--text-muted);"></i> Esperando contrato
            </span>
          </div>
        </div>

        <div class="post-actions-group">
          <button type="button" class="btn-cockpit" data-ver-proyecto data-url="${escapeHtml(p.detalle_proyecto_url || '#')}" title="Ver proyecto">
            <i data-lucide="eye"></i>
            <span>Ver</span>
          </button>
        </div>
      </div>
    </article>
  `;

  // Insertar al inicio de la lista
  postList.insertAdjacentHTML('afterbegin', cardHtml);

  // Actualizar el contador de postulaciones vigentes ("X en curso")
  const badgeCount = contenedorVigentes.querySelector('.label-section .badge');
  if (badgeCount) {
    const cards = postList.querySelectorAll('.post-row-compact');
    badgeCount.textContent = cards.length + ' en curso';
  }

  // Actualizar tarjeta de métrica en Inicio si existe
  const cardMetrica = document.querySelector('.dev-card[onclick*="postulaciones"] .dev-card-val');
  if (cardMetrica) {
    const numEl = cardMetrica.querySelector('.kpi-num') || cardMetrica;
    const valActual = parseInt((numEl.getAttribute('data-target-val') || numEl.textContent).trim(), 10) || 0;
    const nuevoVal = valActual + 1;
    numEl.removeAttribute('data-target-val');
    numEl.textContent = nuevoVal;
    animarContadorKpi(numEl);
  }

  // Renderizar iconos de Lucide en la nueva tarjeta
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

  document.addEventListener('submit', async (event) => {
    const form = event.target.closest('[data-postulacion-form]');
    if (!form) return;
    event.preventDefault();

    const modal = form.closest('#modalPostulacion');
    const carta = form.querySelector('[name="carta"]');
    if (carta && !carta.value.trim()) {
      mostrarFeedbackPostulacion('La carta de presentación es obligatoria.', true);
      carta.focus({ preventScroll: true });
      return;
    }
    if (!postulacionUrl) return;

    sincronizarCsrf(form);
    const submit = form.querySelector('[data-postulacion-submit]');
    const textoOriginal = submit ? submit.innerHTML : '';
    if (submit) {
      submit.disabled = true;
      submit.innerHTML = '<i data-lucide="loader-2"></i> Enviando...';
    }
    mostrarFeedbackPostulacion('', false);

    try {
      const csrf = leerCookie('csrftoken');
      const response = await fetch(postulacionUrl, {
        method: 'POST',
        body: new FormData(form),
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          ...(csrf ? { 'X-CSRFToken': csrf } : {}),
        },
        credentials: 'same-origin',
      });

      const texto = await response.text();
      let data = null;
      try {
        data = JSON.parse(texto);
      } catch (error) {
        data = null;
      }

      if (!data) {
        if (response.status === 403) {
          mostrarFeedbackPostulacion(
            'Tu token de seguridad expiró. Recargando la página para continuar…',
            true
          );
          setTimeout(() => window.location.reload(), 1200);
          return;
        }
        throw new Error('Respuesta inesperada del servidor');
      }

      if (data.ok) {
        cerrarPostulacion();
        if (postulacionCard) {
          postulacionCard.remove();
          postulacionCard = null;
        }
        mostrarToast(data.mensaje || '¡Postulación enviada!');
        if (data.postulacion) {
          insertarPostulacionActiva(data.postulacion);
        }
        return;
      }

      const btnVerificar = modal ? modal.querySelector('[data-ir-verificacion]') : null;
      if (btnVerificar) btnVerificar.hidden = !data.requiere_verificacion;
      mostrarFeedbackPostulacion(data.mensaje || 'No se pudo enviar la postulación.', true);
    } catch (error) {
      mostrarFeedbackPostulacion(
        'No pudimos enviar tu postulación. Revisa tu conexión e inténtalo de nuevo.',
        true
      );
    } finally {
      if (submit) {
        submit.disabled = false;
        submit.innerHTML = textoOriginal;
      }
    }
  });
}
