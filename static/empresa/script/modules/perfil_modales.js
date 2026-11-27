/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Modales de Perfil,
 * Verificación de Identidad y Sub-tabs de Perfil / Historial
 * ============================================================
 */

import { t } from './ui_utils.js';

// --- Modal de Editar Perfil In-Situ ---

export function abrirModalPerfil() {
  const modal = document.getElementById('modalEditarPerfil');
  if (modal) {
    modal.classList.add('open');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
    if (firstInput) firstInput.focus();
  }
}

export function cerrarModalPerfil() {
  const modal = document.getElementById('modalEditarPerfil');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

// --- Modal de Verificación de Identidad In-Situ ---

export function abrirModalVerificacion(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  const modal = document.getElementById('modalVerificacionEmpresa');
  if (modal) {
    modal.classList.add('open');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
    const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
    if (firstInput) firstInput.focus();
  }
}

export function cerrarModalVerificacion() {
  const modal = document.getElementById('modalVerificacionEmpresa');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

// --- Previsualización de Logo en Modal ---

export function previewLogo(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function (e) {
      const previewBox = document.getElementById('logoPreviewBox');
      if (previewBox) {
        previewBox.innerHTML = '<img src="' + e.target.result + '" alt="' + t('vistaPrevia', 'Vista previa') + '" style="width:100%;height:100%;object-fit:cover;">';
      }
    };
    reader.readAsDataURL(input.files[0]);
  }
}

// --- Sub-tabs de Perfil LinkedIn Style ---

export function switchPerfilSubTab(paneId, btn) {
  const panes = document.querySelectorAll('.linkedin-tab-pane');
  const tabs = document.querySelectorAll('.linkedin-tab-btn');

  panes.forEach(function (p) {
    p.classList.remove('active');
  });

  tabs.forEach(function (tab) {
    tab.classList.remove('active');
  });

  const target = document.getElementById('pane-' + paneId);
  if (target) {
    target.classList.add('active');
  }

  if (btn) {
    btn.classList.add('active');
  }
}

// --- Sub-tabs de Historial (Proyectos / Disputas) ---

export function switchHistorialSubTab(subtabId, btn) {
  const panes = document.querySelectorAll('.history-tab-pane');
  const tabs = document.querySelectorAll('.history-tab-btn');

  panes.forEach(function (p) {
    p.classList.remove('active');
  });

  tabs.forEach(function (tab) {
    tab.classList.remove('active');
  });

  const target = document.getElementById('pane-historial-' + subtabId);
  if (target) {
    target.classList.add('active');
  }

  if (!btn) {
    btn = document.getElementById('btn-historial-' + subtabId);
  }
  if (btn) {
    btn.classList.add('active');
  }

  if (window.history && window.history.replaceState) {
    const url = new URL(window.location);
    url.searchParams.set('subtab', subtabId);
    window.history.replaceState(null, '', url);
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}
