/**
 * JobDevs — Modales de Dashboard: Avances, Entregables y Disputas (HTMX)
 * Carga partials HTML renderizados en Django dentro de #jdmModal (modal_core.js).
 */

import {
  escapeHtml,
  confirmarAccion,
  abrirModal,
  cerrarModal,
  setHeader,
  setContent,
  setFooter,
} from './modal_core.js';

const FOOTER_CERRAR = '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>';

function refreshIcons() {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

function hydrateHeaderFromBody(defaultKicker) {
  const metaEl = document.querySelector('#jdmBody [data-modal-title]');
  if (!metaEl) return null;
  setHeader(
    metaEl.dataset.modalKicker || defaultKicker || '',
    metaEl.dataset.modalTitle || '',
    metaEl.dataset.modalSubtitle || ''
  );
  return metaEl;
}

function scrollDisputaChat() {
  const chatBox = document.getElementById('jdmDisputaChat');
  if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
}

function enlazarControlesAbrirDisputa(container) {
  if (!container) return;
  const form = container.querySelector('#jdmFormNuevaDisputa, #form-disputa');
  if (!form) return;

  const textarea = form.querySelector('[name="motivo"]');
  const charCount = form.querySelector('#char-count');
  if (textarea && charCount) {
    const syncCounter = function () {
      charCount.textContent = String((textarea.value || '').trim().length);
    };
    textarea.addEventListener('input', syncCounter);
    syncCounter();
  }

  const categoriaSel = form.querySelector('#jdmCatDisputa, [name="categoria"]');
  const gravedadInput = form.querySelector('[name="confirma_gravedad"]');
  const gravedadRow = gravedadInput ? gravedadInput.closest('label') : null;
  const checks = form.querySelectorAll(
    '[name="confirma_intento_previo"], [name="confirma_gravedad"], [name="acepta_sanciones"]'
  );
  const submitBtn = form.querySelector('#jdmBtnConfirmarDisputa, #btn-submit-disputa');

  const syncEstado = function () {
    const esFuerzaMayor = Boolean(categoriaSel && categoriaSel.value === 'fuerza_mayor');
    if (gravedadInput) {
      gravedadInput.disabled = esFuerzaMayor;
      gravedadInput.required = !esFuerzaMayor;
      if (esFuerzaMayor) {
        gravedadInput.removeAttribute('required');
        gravedadInput.checked = false;
      } else {
        gravedadInput.setAttribute('required', '');
      }
    }
    if (gravedadRow) {
      gravedadRow.style.display = esFuerzaMayor ? 'none' : '';
    }
    if (submitBtn && checks.length) {
      const allChecked = Array.prototype.every.call(checks, function (cb) {
        return cb.disabled || cb.checked;
      });
      submitBtn.disabled = !allChecked;
    }
  };

  if (categoriaSel) categoriaSel.addEventListener('change', syncEstado);
  checks.forEach(function (cb) { cb.addEventListener('change', syncEstado); });
  syncEstado();
}

function initHtmxModalListeners() {
  if (window.__jobdevsModalDisputasAvancesInit) return;
  window.__jobdevsModalDisputasAvancesInit = true;

  document.addEventListener('htmx:afterSwap', function (event) {
    const target = event && event.detail && event.detail.target;
    if (!target || target.id !== 'jdmBody') return;
    hydrateHeaderFromBody();
    scrollDisputaChat();
    enlazarControlesAbrirDisputa(target);
    refreshIcons();
  });

  document.addEventListener('htmx:confirm', function (event) {
    const elt = event && event.detail && event.detail.elt;
    if (!elt || elt.id !== 'jdmFormResolverDisputa') return;
    event.preventDefault();
    confirmarAccion({
      kicker: 'RESOLUCIÓN ARBITRAL VINCULANTE',
      titulo: 'Confirmar Emisión de Dictamen',
      mensaje: event.detail.question || '¿Confirmas la emisión definitiva de esta resolución arbitral?',
      textoConfirmar: 'Emitir Resolución',
      peligro: true,
    }).then(function (confirmado) {
      if (confirmado) event.detail.issueRequest(true);
    });
  });

  function cerrarYRecargar() {
    cerrarModal();
    setTimeout(function () { window.location.reload(); }, 900);
  }

  document.addEventListener('jobdevs:avance-registrado', cerrarYRecargar);
  document.addEventListener('jobdevs:disputa-resuelta', cerrarYRecargar);
  document.addEventListener('jobdevs:disputa-creada', function () {
    const modal = document.getElementById('jdmModal');
    if (modal && !modal.hidden) {
      cerrarYRecargar();
    }
  });
}

async function cargarPartialJdm(url, config) {
  initHtmxModalListeners();
  abrirModal(config.cardClass || '');
  setHeader(config.loadingKicker, config.loadingTitle, config.loadingSubtitle || '');

  try {
    const res = await fetch(url, {
      headers: { 'HX-Request': 'true', 'Accept': 'text/html' },
      credentials: 'same-origin',
    });
    const html = await res.text();
    if (!res.ok) {
      if (html && html.includes('jdm-error')) {
        setContent(html);
        setFooter(FOOTER_CERRAR);
        return;
      }
      throw new Error(config.errorMsg);
    }
    if (!html) {
      throw new Error(config.errorMsg);
    }

    setContent(html);
    const bodyEl = document.getElementById('jdmBody');
    if (bodyEl && window.htmx && typeof window.htmx.process === 'function') {
      window.htmx.process(bodyEl);
    }

    const metaEl = hydrateHeaderFromBody(config.loadingKicker);
    if (typeof config.onLoaded === 'function') {
      config.onLoaded(bodyEl, metaEl);
    } else {
      setFooter(config.footerHtml !== undefined ? config.footerHtml : FOOTER_CERRAR);
    }
    refreshIcons();
  } catch (err) {
    setContent(
      '<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' +
        escapeHtml((err && err.message) || config.errorMsg) +
      '</span></div>'
    );
    setFooter(FOOTER_CERRAR);
  }
}

// ─────────────────────────────────────────────────────────────
// 2. VER AVANCES & HISTORIAL
// ─────────────────────────────────────────────────────────────
export async function cargarAvances(url) {
  return cargarPartialJdm(url, {
    cardClass: 'jdm-card-lg',
    loadingKicker: 'HISTORIAL DE ENTREGAS',
    loadingTitle: 'Cargando avances…',
    errorMsg: 'No se pudieron obtener los avances.',
    onLoaded: function (_bodyEl, metaEl) {
      let footerBtns = '';
      if (metaEl && metaEl.dataset.puedeRegistrar === 'true' && metaEl.dataset.registrarUrl) {
        footerBtns +=
          '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmBtnIrRegistrar" data-url-registrar="' +
          escapeHtml(metaEl.dataset.registrarUrl) +
          '"><i data-lucide="pen"></i> Registrar Nuevo Avance</button>';
      }
      footerBtns += FOOTER_CERRAR;
      setFooter(footerBtns);

      const btnIrReg = document.getElementById('jdmBtnIrRegistrar');
      if (btnIrReg) {
        btnIrReg.addEventListener('click', function () {
          cargarFormularioAvance(btnIrReg.getAttribute('data-url-registrar'));
        });
      }
    },
  });
}

// ─────────────────────────────────────────────────────────────
// 3. REGISTRAR AVANCE FORMULARIO
// ─────────────────────────────────────────────────────────────
export async function cargarFormularioAvance(url) {
  return cargarPartialJdm(url, {
    cardClass: '',
    loadingKicker: 'GESTIÓN DE ENTREGABLES',
    loadingTitle: 'Registrar Avance Técnico',
    loadingSubtitle: 'Cargando hitos pendientes…',
    errorMsg: 'No se pudieron consultar los hitos.',
    footerHtml:
      '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cancelar</button>' +
      '<button type="submit" form="jdmFormAvance" class="jdm-btn jdm-btn-primary" id="jdmBtnEnviarAvance"><i data-lucide="upload-cloud"></i> Registrar Avance</button>',
  });
}

// ─────────────────────────────────────────────────────────────
// 6. SALA DE DISPUTA & EXPEDIENTE
// ─────────────────────────────────────────────────────────────
export async function cargarSalaDisputa(url) {
  return cargarPartialJdm(url, {
    cardClass: 'jdm-card-lg',
    loadingKicker: 'DISPUTAS // SALA DE MEDIACIÓN',
    loadingTitle: 'Cargando expediente arbitral…',
    errorMsg: 'No se pudo obtener el expediente de disputa.',
    onLoaded: function () {
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar Expediente</button>');
      scrollDisputaChat();
    },
  });
}

// ─────────────────────────────────────────────────────────────
// 7. ABRIR DISPUTA FORMULARIO
// ─────────────────────────────────────────────────────────────
export async function cargarFormularioAbrirDisputa(url) {
  const jdmUrl = url + (url.indexOf('?') !== -1 ? '&' : '?') + 'jdm=1';
  return cargarPartialJdm(jdmUrl, {
    cardClass: '',
    loadingKicker: 'ARBITRAJE CONTRACTUAL',
    loadingTitle: 'Consultando proyecto…',
    errorMsg: 'No se pudo consultar el proyecto.',
    onLoaded: function (bodyEl) {
      setFooter('');
      enlazarControlesAbrirDisputa(bodyEl);
    },
  });
}
