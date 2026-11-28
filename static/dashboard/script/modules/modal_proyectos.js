/**
 * JobDevs — Modales de Dashboard: Contratos Digitales y Calificación de Empresa
 */

import {
  escapeHtml,
  abrirModal,
  cerrarModal,
  setModalObligatorio,
  setHeader,
  setContent,
  setFooter,
} from './modal_core.js';

// ─────────────────────────────────────────────────────────────
// 1. CONTRATO DIGITAL (HTMX partial)
// ─────────────────────────────────────────────────────────────
let activeContratoTrigger = null;
let contratoHooksInit = false;

function hidratarContratoModal(container) {
  if (!container) return;
  const metaEl = container.querySelector('.jdm-contrato-partial');
  if (metaEl) {
    setHeader(
      metaEl.dataset.modalKicker || 'ACUERDO LEGAL DE CONTRATACIÓN',
      metaEl.dataset.modalTitle || 'Contrato Digital',
      metaEl.dataset.modalSubtitle || ''
    );
  }
}

function initContratoHooks() {
  if (contratoHooksInit) return;
  contratoHooksInit = true;

  document.addEventListener('htmx:afterSwap', function (event) {
    const target = event && event.detail && event.detail.target;
    if (target && target.id === 'jdmBody' && target.querySelector('.jdm-contrato-partial')) {
      hidratarContratoModal(target);
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    }
  });

  document.addEventListener('jobdevs:contrato-actualizado', function (event) {
    const detail = (event && event.detail) || {};
    if (activeContratoTrigger && (detail.firmado_desarrollador || detail.esta_firmado)) {
      activeContratoTrigger.innerHTML = '<i data-lucide="file-signature"></i> Ver Contrato';
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    }
  });
}

export async function cargarContratoDigital(url, triggerBtn) {
  initContratoHooks();
  activeContratoTrigger = triggerBtn || null;
  abrirModal('');
  setHeader('ACUERDO LEGAL DE CONTRATACIÓN', 'Cargando contrato…');

  try {
    const fetchUrl = url + (url.indexOf('?') === -1 ? '?' : '&') + 'jdm=1';
    const res = await fetch(fetchUrl, {
      headers: { 'HX-Request': 'true' },
      credentials: 'same-origin',
    });
    const html = await res.text();
    if (!res.ok || !html || !html.includes('jdm-contrato-partial')) {
      throw new Error('No se pudo obtener el contrato (respuesta inesperada del servidor).');
    }

    setContent(html);
    setFooter('');
    const bodyEl = document.getElementById('jdmBody');
    hidratarContratoModal(bodyEl);
    if (window.htmx && typeof window.htmx.process === 'function' && bodyEl) {
      window.htmx.process(bodyEl);
    }
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  } catch (err) {
    setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
    setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
  }
}

// ─────────────────────────────────────────────────────────────
// 4. CALIFICAR EMPRESA (HTMX partial)
// ─────────────────────────────────────────────────────────────
const RATING_CAPTIONS = [
  '',
  '1/5 - Muy insatisfactorio',
  '2/5 - Regular',
  '3/5 - Aceptable',
  '4/5 - Muy bueno',
  '5/5 - Excelente',
];

let activeCalificarTrigger = null;
let calificarHooksInit = false;

function hidratarCalificarModal(container) {
  if (!container) return;
  const metaEl = container.querySelector('.jdm-calificar-partial');
  if (metaEl) {
    setHeader(
      metaEl.dataset.modalKicker || 'VALORAR EMPRESA',
      metaEl.dataset.modalTitle || '',
      metaEl.dataset.modalSubtitle || ''
    );
    setModalObligatorio(metaEl.dataset.obligatorio === 'true');
  }

  const form = container.querySelector('#jdmFormCalificar');
  if (!form) return;

  const starsWrap = form.querySelector('#jdmStars');
  const stars = form.querySelectorAll('#jdmStars .jdm-star-btn');
  const caption = form.querySelector('#jdmRatingCaption');
  const inputPunt = form.querySelector('#jdmInputPuntuacion');
  const txtComentario = form.querySelector('#jdmComentario');
  const charCount = form.querySelector('#jdmCharCount');
  let puntuacionVal = parseInt(inputPunt && inputPunt.value, 10) || 0;

  function pintarEstrellas(n) {
    stars.forEach(function (s, idx) {
      s.classList.toggle('is-active', (idx + 1) <= n);
    });
  }

  if (puntuacionVal && caption) {
    pintarEstrellas(puntuacionVal);
    caption.textContent = RATING_CAPTIONS[puntuacionVal] || '';
    caption.style.color = '#00e676';
  }

  stars.forEach(function (star) {
    star.addEventListener('click', function () {
      puntuacionVal = parseInt(star.getAttribute('data-val'), 10);
      if (inputPunt) inputPunt.value = puntuacionVal;
      pintarEstrellas(puntuacionVal);
      if (caption) {
        caption.textContent = RATING_CAPTIONS[puntuacionVal] || '';
        caption.style.color = '#00e676';
      }
    });
    star.addEventListener('mouseenter', function () {
      pintarEstrellas(parseInt(star.getAttribute('data-val'), 10));
    });
  });

  if (starsWrap) {
    starsWrap.addEventListener('mouseleave', function () {
      pintarEstrellas(puntuacionVal);
    });
  }

  if (txtComentario && charCount) {
    const actualizarContador = function () {
      const len = txtComentario.value.trim().length;
      charCount.textContent = len + ' / 20 caracteres mínimos';
      charCount.style.color = len >= 20 ? '#00e676' : '#666666';
    };
    txtComentario.addEventListener('input', actualizarContador);
    actualizarContador();
  }
}

function initCalificarHooks() {
  if (calificarHooksInit) return;
  calificarHooksInit = true;

  document.addEventListener('htmx:afterSwap', function (event) {
    const target = event && event.detail && event.detail.target;
    if (target && target.id === 'jdmBody' && target.querySelector('.jdm-calificar-partial')) {
      hidratarCalificarModal(target);
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    }
  });

  document.addEventListener('jobdevs:calificacion-empresa-guardada', function (event) {
    const detail = (event && event.detail) || {};
    cerrarModal(true);
    if (activeCalificarTrigger) {
      activeCalificarTrigger.classList.remove('btn-primary', 'primary');
      activeCalificarTrigger.classList.add('btn-secondary');
      activeCalificarTrigger.innerHTML =
        '<i data-lucide="check-circle-2" style="color:#00e676;"></i> Empresa calificada' +
        (detail.puntuacion ? ' (' + escapeHtml(detail.puntuacion) + '/5)' : '');
      activeCalificarTrigger.disabled = true;
      activeCalificarTrigger = null;
    }
    document.querySelectorAll('.calificar-popup-overlay').forEach(function (popup) {
      popup.remove();
    });
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  });
}

export async function cargarCalificarEmpresa(url, triggerBtn, esObligatorio) {
  initCalificarHooks();
  activeCalificarTrigger = triggerBtn || null;
  abrirModal('jdm-card-sm');
  setModalObligatorio(Boolean(esObligatorio));
  setHeader(
    esObligatorio ? 'EVALUACIÓN OBLIGATORIA' : 'PROYECTO // VALORACIÓN',
    'Cargando calificación…'
  );

  try {
    const fetchUrl = esObligatorio
      ? url + (url.indexOf('?') === -1 ? '?' : '&') + 'obligatorio=1'
      : url;
    const res = await fetch(fetchUrl, {
      headers: { 'HX-Request': 'true' },
      credentials: 'same-origin',
    });
    const html = await res.text();
    if (!html || !html.includes('jdm-calificar-partial')) {
      throw new Error('No se pudo cargar la valoración (respuesta inesperada del servidor).');
    }

    setContent(html);
    setFooter('');
    const bodyEl = document.getElementById('jdmBody');
    hidratarCalificarModal(bodyEl);
    if (window.htmx && typeof window.htmx.process === 'function' && bodyEl) {
      window.htmx.process(bodyEl);
    }
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  } catch (err) {
    setModalObligatorio(false);
    setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
    setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
  }
}
