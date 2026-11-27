/**
 * ============================================================
 * JobDevs - Dashboard Desarrollador (ES Module Orchestrator)
 * ============================================================
 */

import {
  onReady,
  initUiCore,
  verSeccion,
  closeSidebar,
  closeUserMenu,
} from './modules/ui_core.js';
import {
  initProyectosPostulaciones,
  cerrarPostulacion,
} from './modules/proyectos_postulaciones.js';
import {
  initPerfilVerificacion,
  abrirModalPerfilDev,
  cerrarModalPerfilDev,
  abrirVerificacion,
  cerrarVerificacion,
} from './modules/perfil_verificacion.js';
import { initContratosDisputas } from './modules/contratos_disputas.js';
import { initAnalytics } from './modules/analytics.js';

onReady(function () {
  initUiCore();
  initProyectosPostulaciones();
  initPerfilVerificacion();
  initContratosDisputas();
  initAnalytics();

  // Manejadores globales de tecla Escape
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;

    const modalPerfil = document.getElementById('modalEditarPerfilDev');
    if (modalPerfil && !modalPerfil.hidden) {
      cerrarModalPerfilDev();
    }

    cerrarVerificacion();
    cerrarPostulacion();

    const sidebar = document.querySelector('.sidebar');
    if (sidebar && sidebar.classList.contains('is-open')) {
      closeSidebar();
    }

    closeUserMenu();
  });

  // Enrutamiento inicial desde URL (?section=, ?seccion=, hash, data-seccion-inicial, ?verificacion=1)
  const params = new URLSearchParams(window.location.search);
  const hash = (window.location.hash || '').replace('#', '');
  const inicial = document.body.getAttribute('data-seccion-inicial') || '';
  const seccion = params.get('section')
    || params.get('seccion')
    || (inicial && inicial !== 'inicio' ? inicial : '')
    || (hash && document.getElementById(hash) ? hash : '');

  if (seccion === 'perfil') {
    abrirModalPerfilDev();
  } else if (seccion && document.getElementById(seccion)) {
    verSeccion(seccion, null);
  } else {
    const activa = document.querySelector('.seccion-v.activa');
    if (activa && activa.id === 'centro-chat') {
      document.body.classList.add('is-chat-active');
      const mw = document.querySelector('.main-wrapper');
      if (mw) mw.classList.add('is-chat-active');
    }
  }

  if (params.get('verificacion') === '1') {
    abrirVerificacion();
  }

  // Inicializar íconos Lucide
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});

// Garantizar re-render de Lucide si el evento load aún no ha ocurrido
if (document.readyState !== 'complete') {
  window.addEventListener('load', function () {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  });
}
