/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Contratos Digitales & Hitos
 * (Expediente Contractual HTMX, Firma Electrónica y Rechazo de Avances)
 * ============================================================
 */

import {
  t,
  mostrarToastCorp,
  prefersReducedMotion,
  EASE_OUT_EXPO,
} from './ui_core.js';

function endpointContratoDigital(contratoId) {
  const seccion = document.getElementById('contratos');
  let base = seccion ? (seccion.getAttribute('data-contrato-endpoint') || '') : '';
  if (!base) base = '/contrataciones/contrato-digital/0/';
  return base.replace(/0\/$/, '') + contratoId + '/';
}

function refrescarIconos(root) {
  if (!window.lucide || typeof window.lucide.createIcons !== 'function') return;
  if (root && root.nodeType === 1) {
    try {
      window.lucide.createIcons({ root: root });
      return;
    } catch (e) {
      // Fallback al escaneo completo
    }
  }
  window.lucide.createIcons();
}

function animarExpedienteContrato(container, contratoId) {
  if (!container || prefersReducedMotion()) return;
  const paper = container.querySelector('.contract-doc-paper');
  if (paper && typeof paper.animate === 'function') {
    paper.animate(
      [
        { opacity: 0, transform: 'translateY(10px) scale(0.99)' },
        { opacity: 1, transform: 'translateY(0) scale(1)' },
      ],
      { duration: 260, easing: EASE_OUT_EXPO, fill: 'backwards' }
    );
  }

  const esRecienFirmado = contratoId && String(window._recienFirmadoContratoId) === String(contratoId);
  if (esRecienFirmado) {
    window._recienFirmadoContratoId = null;
    const sellos = container.querySelectorAll('.contract-sign-done, .hash-pill, .contract-estado-badge');
    sellos.forEach(function (sello, idx) {
      if (typeof sello.animate === 'function') {
        sello.animate(
          [
            { opacity: 0.2, transform: 'scale(1.12)' },
            { opacity: 1, transform: 'scale(1)' },
          ],
          {
            duration: 380,
            delay: idx * 55,
            easing: EASE_OUT_EXPO,
            fill: 'backwards',
          }
        );
      }
    });

    const fila = document.querySelector('[data-contrato-row="' + contratoId + '"]');
    if (fila && typeof fila.animate === 'function') {
      fila.animate(
        [
          { backgroundColor: 'var(--corp-brand-light)' },
          { backgroundColor: 'transparent' },
        ],
        { duration: 900, easing: EASE_OUT_EXPO }
      );
    }
  }
}

function sincronizarTituloModalContrato(container) {
  if (!container) return;
  const paper = container.querySelector('.contract-doc-paper');
  const tituloSpan = document.querySelector('#contratoModalTitulo span');
  if (paper && tituloSpan && paper.dataset.modalTitle) {
    tituloSpan.textContent = paper.dataset.modalTitle;
  }
}

function pintarEstadoFilaContrato(contrato) {
  if (!contrato || !contrato.id) return;
  const fila = document.querySelector('[data-contrato-row="' + contrato.id + '"]');
  if (!fila) return;
  const mapa = [
    { rol: 'firma-empresa', firmado: contrato.firmado_empresa, etiqueta: t('etiquetaEmpresa', 'Empresa') },
    { rol: 'firma-dev', firmado: contrato.firmado_desarrollador, etiqueta: t('etiquetaDev', 'Dev') },
  ];
  mapa.forEach(function (item) {
    const badge = fila.querySelector('[data-role="' + item.rol + '"]');
    if (!badge) return;
    badge.classList.toggle('is-signed', !!item.firmado);
    badge.classList.toggle('is-pending', !item.firmado);
    const span = badge.querySelector('span');
    if (span) span.textContent = item.etiqueta + ': ' + (item.firmado ? t('firmado', 'Firmado') : t('pendiente', 'Pendiente'));
    const icono = badge.querySelector('.lucide, svg, [data-lucide]');
    if (icono && icono.parentNode) {
      const nuevoIcono = document.createElement('i');
      nuevoIcono.setAttribute('data-lucide', item.firmado ? 'check-circle-2' : 'clock');
      icono.parentNode.replaceChild(nuevoIcono, icono);
    }
  });
  const estadoBadge = fila.querySelector('[data-role="estado-contrato"]');
  if (estadoBadge) {
    estadoBadge.className = 'contract-estado-badge estado-' + contrato.estado;
    estadoBadge.textContent = contrato.estado_display;
  }
  const montoEl = fila.querySelector('.contrato-monto');
  if (montoEl && contrato.monto_formateado) {
    montoEl.textContent = contrato.monto_formateado;
  }
  const hashPill = fila.querySelector('[data-role="hash-contrato"]');
  if (hashPill) {
    hashPill.textContent = contrato.hash_contrato ? contrato.hash_contrato.slice(0, 12) + '…' : t('sinSello', 'Sin sello');
  }
  refrescarIconos(fila);
}

function htmlErrorContrato() {
  return '<div class="activity-empty" style="padding:44px 20px;">' +
    '<i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i>' +
    '<p>' + t('errorContrato', 'No se pudo cargar el expediente contractual. Intenta de nuevo.') + '</p></div>';
}

export function abrirModalContrato(event, contratoId) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  if (!contratoId) return;

  const modal = document.getElementById('modalContratoDigital');
  const bodyEl = document.getElementById('contratoModalBody');
  if (!modal || !bodyEl) return;

  window._contratoAbiertoId = contratoId;
  bodyEl.innerHTML = '<div class="drawer-loading"><i data-lucide="loader-circle" class="corp-spin"></i><p>' + t('cargandoContrato', 'Cargando expediente contractual...') + '</p></div>';
  refrescarIconos(bodyEl);
  modal.classList.add('open');
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';

  const url = endpointContratoDigital(contratoId);
  if (window.htmx && typeof window.htmx.ajax === 'function') {
    window.htmx.ajax('GET', url, { target: '#contratoModalBody', swap: 'innerHTML' }).catch(function () {
      bodyEl.innerHTML = htmlErrorContrato();
      refrescarIconos(bodyEl);
    });
    return;
  }

  fetch(url, {
    headers: { 'HX-Request': 'true' },
    credentials: 'same-origin',
  })
    .then(function (res) {
      if (!res.ok) throw new Error('No se pudo cargar el contrato');
      return res.text();
    })
    .then(function (html) {
      bodyEl.innerHTML = html;
      sincronizarTituloModalContrato(bodyEl);
      refrescarIconos(bodyEl);
      animarExpedienteContrato(bodyEl, contratoId);
    })
    .catch(function () {
      bodyEl.innerHTML = htmlErrorContrato();
      refrescarIconos(bodyEl);
    });
}

export function cerrarModalContrato() {
  const modal = document.getElementById('modalContratoDigital');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
  }
  document.body.style.overflow = '';
  const bodyEl = document.getElementById('contratoModalBody');
  if (bodyEl) {
    bodyEl.innerHTML = '<div class="drawer-loading"><i data-lucide="loader-circle" class="corp-spin"></i><p>' + t('cargandoContrato', 'Cargando expediente contractual...') + '</p></div>';
    refrescarIconos(bodyEl);
  }
  window._contratoAbiertoId = null;
}

export function validarRechazoAvance(form, event) {
  const submitter = event && event.submitter ? event.submitter : document.activeElement;
  if (submitter && submitter.name === 'accion' && submitter.value === 'rechazar') {
    const ta = form.querySelector('textarea[name="comentario"]');
    if (ta && !ta.value.trim()) {
      event.preventDefault();
      const toastEl = document.getElementById('corpToast');
      const msg = (toastEl && toastEl.dataset.msgRechazo) || 'Debes escribir un comentario explicando los ajustes solicitados.';
      let errEl = form.querySelector('.form-error-inline');
      if (!errEl) {
        errEl = document.createElement('div');
        errEl.className = 'form-error-inline';
        errEl.setAttribute('role', 'alert');
        ta.insertAdjacentElement('afterend', errEl);
        ta.addEventListener('input', function () {
          if (ta.value.trim() && errEl.parentNode) errEl.remove();
        });
      }
      errEl.textContent = msg;
      ta.focus();
      mostrarToastCorp(msg, true);
      return false;
    }
  }
  return true;
}

// --- Global Window Contracts ---

window.abrirModalContrato = abrirModalContrato;
window.cerrarModalContrato = cerrarModalContrato;
window.validarRechazoAvance = validarRechazoAvance;

// --- DOM Initialization ---

let contratoHooksInit = false;

export function initContratosHitos() {
  const modalContratoDigital = document.getElementById('modalContratoDigital');
  if (modalContratoDigital) {
    modalContratoDigital.addEventListener('click', function (e) {
      if (e.target === modalContratoDigital) {
        cerrarModalContrato();
      }
    });
  }

  if (contratoHooksInit) return;
  contratoHooksInit = true;

  document.addEventListener('htmx:afterSwap', function (event) {
    const target = event && event.detail && event.detail.target;
    if (!target || target.id !== 'contratoModalBody') return;
    const paper = target.querySelector('.contract-doc-paper');
    const contratoId = (paper && paper.dataset.contratoId) || window._contratoAbiertoId;
    sincronizarTituloModalContrato(target);
    refrescarIconos(target);
    animarExpedienteContrato(target, contratoId);
  });

  document.addEventListener('jobdevs:contrato-actualizado', function (event) {
    const detail = event && event.detail;
    if (!detail) return;
    if (detail.recien_firmado && detail.id) {
      window._recienFirmadoContratoId = String(detail.id);
    }
    pintarEstadoFilaContrato(detail);
  });
}
