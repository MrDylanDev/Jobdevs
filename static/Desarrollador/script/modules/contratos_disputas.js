/**
 * Módulo Contratos & Disputas — Dashboard Desarrollador
 * Modales de disputa, filtrado en tiempo real de disputas,
 * modal de cancelación de contratos y pop-up de contrato pendiente.
 */

import {
  _setupModalFocusTrap,
  _cleanupModalFocusTrap,
} from './ui_core.js';

// ═══════════════════════════════════════════════
// MODAL DE DISPUTAS
// ═══════════════════════════════════════════════
export function abrirModalNuevaDisputaDev() {
  const m = document.getElementById('modalNuevaDisputa');
  if (m) {
    m.hidden = false;
    m.style.display = 'flex';
    m.classList.add('is-open');
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }
}

export function cerrarModalNuevaDisputaDev() {
  const m = document.getElementById('modalNuevaDisputa');
  if (m) {
    m.hidden = true;
    m.style.display = 'none';
    m.classList.remove('is-open');
  }
}

export const abrirModalDisputa = abrirModalNuevaDisputaDev;
export const cerrarModalDisputa = cerrarModalNuevaDisputaDev;

// ═══════════════════════════════════════════════
// FILTRADO DE DISPUTAS EN TIEMPO REAL (SIN RECARGA)
// ═══════════════════════════════════════════════
export function filtrarDisputasEnTiempoReal(event, estado, btn) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  const parent = btn ? btn.closest('.disputas-filtros') : null;
  if (parent && btn) {
    parent.querySelectorAll('.btn').forEach(function (b) {
      b.classList.remove('btn-primary');
      b.classList.add('btn-secondary');
    });
    btn.classList.add('btn-primary');
    btn.classList.remove('btn-secondary');
  }

  const serverFiltradas = document.querySelector('[data-testid="disputas-filtradas"]');
  if (serverFiltradas) {
    serverFiltradas.style.display = 'none';
  }

  const cardActivas = document.getElementById('cardDisputasActivas');
  const cardResueltas = document.getElementById('cardDisputasResueltas');
  const emptyMsg = document.getElementById('disputasClienteVacio');

  let totalVisibles = 0;
  let activasVisibles = 0;
  let resueltasVisibles = 0;

  const rows = document.querySelectorAll('.disputa-row-item');
  rows.forEach(function (r) {
    const rowEstado = r.getAttribute('data-disputa-row-estado') || '';
    const match = (estado === 'todos' || !estado || rowEstado === estado);
    r.style.display = match ? '' : 'none';
    if (match) {
      totalVisibles++;
      if (rowEstado === 'abierta' || rowEstado === 'en_mediacion') activasVisibles++;
      if (rowEstado === 'resuelta' || rowEstado === 'cancelada') resueltasVisibles++;
    }
  });

  if (cardActivas) {
    cardActivas.style.display = (estado === 'todos' || activasVisibles > 0) ? '' : 'none';
  }
  if (cardResueltas) {
    cardResueltas.style.display = (estado === 'todos' || resueltasVisibles > 0) ? '' : 'none';
  }
  if (emptyMsg) {
    emptyMsg.style.display = (estado !== 'todos' && totalVisibles === 0) ? 'block' : 'none';
  }

  if (window.history && window.history.replaceState) {
    const url = new URL(window.location);
    url.searchParams.set('seccion', 'disputas');
    if (estado && estado !== 'todos') {
      url.searchParams.set('estado', estado);
    } else {
      url.searchParams.delete('estado');
    }
    window.history.replaceState(null, '', url);
  }

  return false;
}

// ═══════════════════════════════════════════════
// MODAL DE CANCELACIÓN DE CONTRATO
// ═══════════════════════════════════════════════
export function abrirModalCancelacionDev() {
  const modal = document.getElementById('modalCancelacionDev');
  if (!modal) return;
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
  const focusTarget = modal.querySelector('select, button, [tabindex]:not([tabindex="-1"])');
  if (focusTarget) focusTarget.focus();
  _setupModalFocusTrap(modal, cerrarModalCancelacionDev);
}

export function cerrarModalCancelacionDev() {
  const modal = document.getElementById('modalCancelacionDev');
  if (!modal) return;
  _cleanupModalFocusTrap();
  modal.hidden = true;
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

export function actualizarActionCancelacion(selectEl) {
  const form = document.getElementById('formProponerCancelacionDev');
  if (form && selectEl && selectEl.value) {
    form.action = '/contrataciones/cancelar/' + selectEl.value + '/';
  }
}

// ═══════════════════════════════════════════════
// POP-UP DE CONTRATO PENDIENTE
// ═══════════════════════════════════════════════
export function cerrarPopupContrato(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.opacity = '0';
    el.style.transform = 'translateY(15px)';
    el.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 200);
  }
}

// Exponer en window para manejadores inline HTML y scripts hermanos
window.abrirModalNuevaDisputaDev = abrirModalNuevaDisputaDev;
window.cerrarModalNuevaDisputaDev = cerrarModalNuevaDisputaDev;
window.abrirModalDisputa = abrirModalDisputa;
window.cerrarModalDisputa = cerrarModalDisputa;
window.filtrarDisputasEnTiempoReal = filtrarDisputasEnTiempoReal;
window.abrirModalCancelacionDev = abrirModalCancelacionDev;
window.cerrarModalCancelacionDev = cerrarModalCancelacionDev;
window.actualizarActionCancelacion = actualizarActionCancelacion;
window.cerrarPopupContrato = cerrarPopupContrato;

export function initContratosDisputas() {
  // Manejadores registrados vía window.* y atributos inline HTML
}
