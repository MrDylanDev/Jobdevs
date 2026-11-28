/**
 * JobDevs — Modales de Dashboard: Perfiles Públicos (Empresa y Desarrollador)
 * Carga los partials HTML renderizados en Django vía HTMX (HX-Request: true).
 */

import {
  escapeHtml,
  abrirModal,
  setHeader,
  setContent,
  setFooter,
} from './modal_core.js';

const FOOTER_CERRAR = '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>';

async function cargarPerfilModal(url, config) {
  abrirModal('');
  setHeader(config.loadingKicker, config.loadingTitle);

  try {
    const res = await fetch(url, {
      headers: { 'HX-Request': 'true' },
      credentials: 'same-origin',
    });
    if (!res.ok) {
      throw new Error(config.errorMsg);
    }
    const html = await res.text();
    if (!html || !html.includes('jdm-perfil-partial')) {
      throw new Error(config.errorMsg);
    }

    setContent(html);
    const metaEl = document.querySelector('#jdmBody [data-modal-title]');
    if (metaEl) {
      setHeader(
        metaEl.dataset.modalKicker || config.defaultKicker,
        metaEl.dataset.modalTitle || '',
        metaEl.dataset.modalSubtitle || ''
      );
    }
    setFooter(FOOTER_CERRAR);
  } catch (err) {
    setHeader(config.defaultKicker, 'No disponible');
    setContent(
      '<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' +
        escapeHtml(err.message || config.errorMsg) +
      '</span></div>'
    );
    setFooter(FOOTER_CERRAR);
  }
}

// ─────────────────────────────────────────────────────────────
// 5. DETALLE EMPRESA
// ─────────────────────────────────────────────────────────────
export async function cargarDetalleEmpresa(url) {
  return cargarPerfilModal(url, {
    loadingKicker: 'PERFIL // INSTITUCIONAL',
    loadingTitle: 'Cargando perfil de empresa…',
    defaultKicker: 'EMPRESA // FICHA INSTITUCIONAL',
    errorMsg: 'No se pudo obtener el perfil de la empresa.',
  });
}

// ─────────────────────────────────────────────────────────────
// 5B. DETALLE PÚBLICO DE DESARROLLADOR (IN-SITU)
// ─────────────────────────────────────────────────────────────
export async function cargarDetalleDesarrollador(url) {
  return cargarPerfilModal(url, {
    loadingKicker: 'TALENTO SENA // PERFIL PÚBLICO',
    loadingTitle: 'Cargando perfil profesional…',
    defaultKicker: 'TALENTO SENA // PERFIL PÚBLICO',
    errorMsg: 'No se pudo obtener el perfil del desarrollador.',
  });
}
