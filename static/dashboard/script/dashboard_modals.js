/**
 * JobDevs — Sistema de Modales Integrados en Dashboards (ES Module Orchestrator)
 * Controla Contratos, Avances, Calificaciones, Empresas, Desarrolladores y Disputas sin redirecciones.
 */

import {
  onReady,
  mostrarToast,
  confirmarAccion,
  cerrarModal,
  initConfirmFormInterceptor,
} from './modules/modal_core.js';
import {
  cargarDetalleEmpresa,
  cargarDetalleDesarrollador,
} from './modules/modal_perfil.js';
import {
  cargarContratoDigital,
  cargarCalificarEmpresa,
} from './modules/modal_proyectos.js';
import {
  cargarAvances,
  cargarFormularioAvance,
  cargarSalaDisputa,
  cargarFormularioAbrirDisputa,
} from './modules/modal_disputas_avances.js';

// Exponer API global inmediatamente al cargar el módulo
window.JdConfirm = confirmarAccion;
window.jdToast = mostrarToast;
window.JdDashboardModals = {
  abrirContrato: cargarContratoDigital,
  abrirAvances: cargarAvances,
  abrirRegistrarAvance: cargarFormularioAvance,
  abrirCalificar: cargarCalificarEmpresa,
  abrirEmpresa: cargarDetalleEmpresa,
  abrirDesarrollador: cargarDetalleDesarrollador,
  abrirSalaDisputa: cargarSalaDisputa,
  abrirFormularioDisputa: cargarFormularioAbrirDisputa,
  confirmar: confirmarAccion,
  cerrar: cerrarModal,
  toast: mostrarToast,
};

onReady(function () {
  // Event Delegation Global
  document.addEventListener('click', function (e) {
    // 1. Contrato Digital
    const btnContrato = e.target.closest('[data-abrir-contrato]');
    if (btnContrato) {
      e.preventDefault();
      const urlContrato = btnContrato.getAttribute('data-url') || btnContrato.getAttribute('href');
      if (urlContrato) cargarContratoDigital(urlContrato, btnContrato);
      return;
    }

    // 2. Avances / Historial
    const btnAvances = e.target.closest('[data-abrir-avances]');
    if (btnAvances) {
      e.preventDefault();
      const urlAvances = btnAvances.getAttribute('data-url') || btnAvances.getAttribute('href');
      if (urlAvances) cargarAvances(urlAvances);
      return;
    }

    // 3. Registrar Avance
    const btnRegAvance = e.target.closest('[data-abrir-registrar-avance]');
    if (btnRegAvance) {
      e.preventDefault();
      const urlRegAvance = btnRegAvance.getAttribute('data-url') || btnRegAvance.getAttribute('href');
      if (urlRegAvance) cargarFormularioAvance(urlRegAvance);
      return;
    }

    // 4. Calificar Empresa
    const btnCalificar = e.target.closest('[data-abrir-calificar]');
    if (btnCalificar) {
      e.preventDefault();
      const urlCalificar = btnCalificar.getAttribute('data-url') || btnCalificar.getAttribute('href');
      if (urlCalificar) cargarCalificarEmpresa(urlCalificar, btnCalificar);
      return;
    }

    // 5. Detalle Empresa
    const btnEmpresa = e.target.closest('[data-abrir-empresa]');
    if (btnEmpresa) {
      e.preventDefault();
      const urlEmpresa = btnEmpresa.getAttribute('data-url') || btnEmpresa.getAttribute('href');
      if (urlEmpresa) cargarDetalleEmpresa(urlEmpresa);
      return;
    }

    // 5B. Detalle Desarrollador
    const btnDev = e.target.closest('[data-abrir-desarrollador]');
    if (btnDev) {
      e.preventDefault();
      const urlDev = btnDev.getAttribute('data-url') || btnDev.getAttribute('href');
      if (typeof window.cerrarModalPerfilDev === 'function') {
        window.cerrarModalPerfilDev();
      }
      if (urlDev) cargarDetalleDesarrollador(urlDev);
      return;
    }

    // 6. Sala de Disputa
    const btnDisputa = e.target.closest('[data-abrir-sala-disputa]');
    if (btnDisputa) {
      e.preventDefault();
      const urlDisputa = btnDisputa.getAttribute('data-url') || btnDisputa.getAttribute('href');
      if (urlDisputa) cargarSalaDisputa(urlDisputa);
      return;
    }

    // 7. Formulario Abrir Disputa
    const btnAbrirDisp = e.target.closest('[data-abrir-formulario-disputa]');
    if (btnAbrirDisp) {
      e.preventDefault();
      const urlAbrir = btnAbrirDisp.getAttribute('data-url') || btnAbrirDisp.getAttribute('href');
      if (urlAbrir) cargarFormularioAbrirDisputa(urlAbrir);
      return;
    }
  });

  // Interceptor global para formularios con data-confirm
  initConfirmFormInterceptor();
});
