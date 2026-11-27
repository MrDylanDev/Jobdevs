/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Perfil y Evaluaciones Barrel
 * Re-exports perfil_modales & evaluaciones_modales, attaches
 * global window.* contracts, and initializes modal backdrops.
 * ============================================================
 */

import {
  abrirModalPerfil,
  cerrarModalPerfil,
  abrirModalVerificacion,
  cerrarModalVerificacion,
  previewLogo,
  switchPerfilSubTab,
  switchHistorialSubTab,
} from './perfil_modales.js';

import {
  abrirModalDisputa,
  cerrarModalDisputa,
  cerrarModalCalificar,
  abrirModalCalificar,
  abrirModalTodasValoraciones,
  cerrarModalTodasValoraciones,
  filtrarResenasModal,
  filtrarPorEstrellasModal,
  _aplicarFiltrosResenas,
  filtrarHistorialEnTiempoReal,
  filtrarDisputasEnTiempoReal,
} from './evaluaciones_modales.js';

export {
  abrirModalPerfil,
  cerrarModalPerfil,
  abrirModalVerificacion,
  cerrarModalVerificacion,
  previewLogo,
  switchPerfilSubTab,
  switchHistorialSubTab,
  abrirModalDisputa,
  cerrarModalDisputa,
  cerrarModalCalificar,
  abrirModalCalificar,
  abrirModalTodasValoraciones,
  cerrarModalTodasValoraciones,
  filtrarResenasModal,
  filtrarPorEstrellasModal,
  _aplicarFiltrosResenas,
  filtrarHistorialEnTiempoReal,
  filtrarDisputasEnTiempoReal,
};

// --- Global Window Contracts ---

window.abrirModalPerfil = abrirModalPerfil;
window.cerrarModalPerfil = cerrarModalPerfil;
window.abrirModalVerificacion = abrirModalVerificacion;
window.cerrarModalVerificacion = cerrarModalVerificacion;
window.previewLogo = previewLogo;
window.switchPerfilSubTab = switchPerfilSubTab;
window.switchHistorialSubTab = switchHistorialSubTab;
window.abrirModalDisputa = abrirModalDisputa;
window.cerrarModalDisputa = cerrarModalDisputa;
window.abrirModalCalificar = abrirModalCalificar;
window.cerrarModalCalificar = cerrarModalCalificar;
window.abrirModalTodasValoraciones = abrirModalTodasValoraciones;
window.cerrarModalTodasValoraciones = cerrarModalTodasValoraciones;
window.filtrarResenasModal = filtrarResenasModal;
window.filtrarPorEstrellasModal = filtrarPorEstrellasModal;
window._aplicarFiltrosResenas = _aplicarFiltrosResenas;
window.filtrarHistorialEnTiempoReal = filtrarHistorialEnTiempoReal;
window.filtrarDisputasEnTiempoReal = filtrarDisputasEnTiempoReal;

// --- DOM Initialization ---

export function initPerfilEvaluaciones() {
  // Backdrop del modal de editar perfil
  const modalPerfil = document.getElementById('modalEditarPerfil');
  if (modalPerfil) {
    modalPerfil.addEventListener('click', function (e) {
      if (e.target === modalPerfil) {
        cerrarModalPerfil();
      }
    });
  }

  // Backdrop del modal de todas las valoraciones
  const modalTodasValoraciones = document.getElementById('modalTodasValoraciones');
  if (modalTodasValoraciones) {
    modalTodasValoraciones.addEventListener('click', function (e) {
      if (e.target === modalTodasValoraciones) {
        cerrarModalTodasValoraciones();
      }
    });
  }

  // Backdrop del modal de verificación de empresa
  const modalVerificacion = document.getElementById('modalVerificacionEmpresa');
  if (modalVerificacion) {
    modalVerificacion.addEventListener('click', function (e) {
      if (e.target === modalVerificacion) {
        cerrarModalVerificacion();
        cerrarModalCalificar();
      }
    });
  }
}
