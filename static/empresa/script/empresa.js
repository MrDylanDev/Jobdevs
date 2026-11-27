/**
 * ============================================================
 * JobDevs - Dashboard Empresa (ES Module Orchestrator)
 * ============================================================
 */

import {
  onReady,
  initUiCore,
  switchTab,
  closeNotifPopover,
  closeUserMenu,
  closeSidebar,
} from './modules/ui_core.js';
import { initDatepicker } from './modules/datepicker.js';
import {
  initProyectos,
  cerrarModal,
  cerrarModalEditarProyecto,
  cerrarModalConfirmarRetiro,
} from './modules/proyectos.js';
import {
  initCandidatos,
  cerrarDrawerCandidatos,
  abrirChatEnCentro,
} from './modules/candidatos.js';
import {
  initContratosHitos,
  cerrarModalContrato,
} from './modules/contratos_hitos.js';
import {
  initPerfilEvaluaciones,
  abrirModalCalificar,
  cerrarModalPerfil,
  cerrarModalTodasValoraciones,
  cerrarModalVerificacion,
  cerrarModalCalificar,
  switchHistorialSubTab,
} from './modules/perfil_evaluaciones.js';
import { initAnalytics } from './modules/analytics.js';
import { initLedgerChart } from './modules/ledger_chart.js';
import {
  initDashboardWidgets,
  cerrarModalBienvenida,
} from './modules/dashboard_widgets.js';

onReady(function () {
  initUiCore();
  initDatepicker();
  initProyectos();
  initCandidatos();
  initContratosHitos();
  initPerfilEvaluaciones();
  initAnalytics();
  initLedgerChart();
  initDashboardWidgets();

  // Tecla Escape global para modales, drawers, popovers y menús contextuales
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      cerrarModal();
      cerrarModalPerfil();
      cerrarModalEditarProyecto();
      cerrarModalConfirmarRetiro();
      cerrarModalTodasValoraciones();
      cerrarModalContrato();
      cerrarModalVerificacion();
      cerrarModalCalificar();
      cerrarModalBienvenida();
      cerrarDrawerCandidatos();
      closeNotifPopover();
      closeUserMenu();
      closeSidebar();
      document.querySelectorAll('.dev-more-actions[open]').forEach(function (det) {
        det.removeAttribute('open');
      });
    }
  });

  // Restaurar pestaña activa y parámetros de URL
  const params = new URLSearchParams(window.location.search);
  const calificarProyectoId = params.get('calificar_proyecto');
  if (calificarProyectoId) {
    const btnCalificar = document.querySelector('a[href$="/finalizar/' + calificarProyectoId + '/"]');
    const urlCalificar = btnCalificar ? btnCalificar.href : ('/proyectos/finalizar/' + calificarProyectoId + '/');
    abrirModalCalificar(null, urlCalificar, '');
    params.delete('calificar_proyecto');
    if (window.history && window.history.replaceState) {
      const cleanQs = params.toString();
      window.history.replaceState(null, '', window.location.pathname + (cleanQs ? '?' + cleanQs : '') + (window.location.hash || ''));
    }
  }

  const hash = window.location.hash ? window.location.hash.substring(1) : null;
  const sectionParam = params.get('section');
  const chatReceptor = params.get('chat_receptor');
  const chatProyecto = params.get('chat_proyecto') || '0';
  const initialTab = chatReceptor ? 'centro-chat' : (hash || sectionParam || 'inicio');

  switchTab(initialTab);

  if (chatReceptor) {
    params.delete('chat_receptor');
    params.delete('chat_proyecto');
    if (window.history && window.history.replaceState) {
      const cleanQs = params.toString();
      window.history.replaceState(null, '', window.location.pathname + (cleanQs ? '?' + cleanQs : '') + '#centro-chat');
    }
    setTimeout(function () {
      abrirChatEnCentro(null, chatReceptor, chatProyecto);
    }, 0);
  }

  // Restaurar subpestaña de historial si aplica
  const subtabParam = params.get('subtab');
  if (subtabParam === 'disputas' || hash === 'historial-disputas') {
    switchHistorialSubTab('disputas');
  }

  // Inicializar íconos Lucide
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
