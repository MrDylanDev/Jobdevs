/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Widgets de Bienvenida, Chat,
 * Roadmap, Revisiones y Modalidad de Proyecto
 * ============================================================
 */

import { abrirModal } from './proyectos.js';

export function cerrarModalBienvenida() {
  const chk = document.getElementById('chkNoVolverAMostrarBienvenida');
  if (chk && chk.checked) {
    try { localStorage.setItem('jobdevs_bienvenida_no_mostrar', '1'); } catch (e) {}
  }
  const modal = document.getElementById('modalBienvenidaEmpresa');
  if (modal) {
    modal.style.display = 'none';
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }
}

export function empezarConvocatoriaDesdeBienvenida() {
  cerrarModalBienvenida();
  abrirModal();
}

export function filtrarChatsEnLista(inp) {
  const q = (inp.value || '').toLowerCase().trim();
  document.querySelectorAll('.jd-chat-items .jd-chat-item').forEach(function (item) {
    const text = item.textContent.toLowerCase();
    item.style.display = text.indexOf(q) !== -1 ? 'flex' : 'none';
  });
}

export function switchRoadmapProyecto(proyId, btnEl) {
  document.querySelectorAll('.roadmap-project-tab').forEach(function (b) {
    b.style.background = 'transparent';
    b.style.color = 'var(--corp-slate-600)';
    b.classList.remove('active');
  });
  if (btnEl) {
    btnEl.style.background = 'var(--corp-surface)';
    btnEl.style.color = 'var(--corp-brand)';
    btnEl.classList.add('active');
  }
  document.querySelectorAll('.roadmap-project-view').forEach(function (v) {
    v.style.display = 'none';
  });
  const target = document.getElementById('roadmap-view-' + proyId);
  if (target) {
    target.style.display = 'block';
  }
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function toggleFormularioRevision(avanceId) {
  const formEl = document.getElementById('form-revision-' + avanceId);
  if (formEl) {
    formEl.style.display = (formEl.style.display === 'none' || formEl.style.display === '') ? 'block' : 'none';
  }
}

export function toggleCiudadProyecto(selectEl, groupTargetId) {
  const grp = document.getElementById(groupTargetId);
  const inp = grp ? grp.querySelector('input') : null;
  if (!grp) return;
  if (selectEl.value === 'presencial' || selectEl.value === 'hibrido') {
    grp.style.display = 'block';
    if (inp) inp.required = true;
  } else {
    grp.style.display = 'none';
    if (inp) {
      inp.required = false;
      inp.value = '';
    }
  }
}

// --- Global Window Contracts ---

window.cerrarModalBienvenida = cerrarModalBienvenida;
window.empezarConvocatoriaDesdeBienvenida = empezarConvocatoriaDesdeBienvenida;
window.filtrarChatsEnLista = filtrarChatsEnLista;
window.switchRoadmapProyecto = switchRoadmapProyecto;
window.toggleFormularioRevision = toggleFormularioRevision;
window.toggleCiudadProyecto = toggleCiudadProyecto;

// --- DOM Initialization ---

export function initDashboardWidgets() {
  const layout = document.querySelector('.app-layout');
  const esCuentaNueva = layout && layout.getAttribute('data-es-cuenta-nueva') === '1';
  if (!esCuentaNueva) return;
  try {
    if (localStorage.getItem('jobdevs_bienvenida_no_mostrar') !== '1') {
      const modal = document.getElementById('modalBienvenidaEmpresa');
      if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      }
    }
  } catch (e) {}
}
