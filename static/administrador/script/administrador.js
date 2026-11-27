/**
 * ============================================================
 * JobDevs - Panel Administrador (ES Module Orchestrator)
 * ============================================================
 */

import {
  onReady,
  initUiCore,
  showSection,
  closeSidebar,
  closeAdminUserDropdown,
} from './modules/ui_core.js';
import { initUsuariosVerificaciones } from './modules/usuarios_verificaciones.js';
import { initAuditoriaReportes } from './modules/auditoria_reportes.js';

onReady(function () {
  initUiCore();
  initUsuariosVerificaciones();
  initAuditoriaReportes();

  // Tecla Escape global para modales, drawer móvil y menú desplegable
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;

    closeAdminUserDropdown();

    const sidebar = document.querySelector('.sidebar');
    if (sidebar && sidebar.classList.contains('is-open')) {
      closeSidebar();
    }

    const openModals = document.querySelectorAll('.modal-overlay.open');
    if (!openModals.length) return;
    openModals.forEach((m) => {
      if (m.id === 'adminGenericConfirmModal') {
        const cancelBtn = document.getElementById('admConfCancel');
        if (cancelBtn) cancelBtn.click();
        else m.classList.remove('open');
      } else {
        m.classList.remove('open');
      }
    });
  });

  // Restaurar sección desde query param (?section=...)
  const sectionParam = new URLSearchParams(window.location.search).get('section');
  if (sectionParam) {
    showSection(sectionParam);
  }

  // Inicializar íconos Lucide
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
