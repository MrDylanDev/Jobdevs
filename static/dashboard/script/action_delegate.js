/**
 * Declarative event delegation for JobDevs (strict-CSP replacement for inline on*= handlers).
 * Zero eval / zero new Function. Only explicitly allowlisted functions can be invoked.
 */

const ALLOWED_CALLS = new Set([
  // Built-in safe actions
  '__noop',
  '__print',
  '__navigate',
  // Shared shell / navigation / modals
  'toggleSidebar',
  'toggleSidebarCollapse',
  'toggleUserMenu',
  'closeUserMenu',
  'cerrarSesionConSpinner',
  'closeModal',
  'switchModuloTab',
  'toggleFormularioRevision',
  'validarRechazoAvance',
  // Admin dashboard
  'showSection',
  'toggleAdminUserDropdown',
  'closeAdminUserDropdown',
  'toggleAdminTheme',
  'resetAdminExploreFilters',
  'setAdminProjectEstadoPill',
  'debouncedFilterProjects',
  'filterProjects',
  'openCategoryModal',
  'toggleCategory',
  'switchAdminLineChart',
  'switchUsersTab',
  'openCreateUserModal',
  'setAdminUserRolePill',
  'debouncedFilterUsers',
  'filterUsers',
  'filterAdminQuickSearch',
  'openToggleUserConfirmModal',
  'openEditUserModal',
  'deleteUser',
  'confirmToggleUserAction',
  'syncCreateUserDocField',
  // Developer dashboard
  'verSeccion',
  'toggleDevTheme',
  'abrirModalPerfilDev',
  'abrirVerificacion',
  'cerrarModalCancelacionDev',
  'actualizarActionCancelacion',
  'abrirModalNuevaDisputaDev',
  'cerrarModalPerfilDev',
  'cerrarModalNuevaDisputaDev',
  'switchHistorialTab',
  'toggleChatContextSidebarDev',
  'switchContratosSubTab',
  'abrirModalCancelacionDev',
  'resetDevExploreFilters',
  'cerrarPopupContrato',
  'cambiarMetricaGrafica',
  // Disputas
  'filtrarDisputasEnTiempoReal',
  'abrirModalDisputa',
  'switchDisputasSubTab',
  'cerrarModalDisputa',
  // Empresa dashboard & public profile
  'switchPublicPerfilTab',
  'switchTab',
  'toggleNotifPopover',
  'limpiarNotificacionesAjax',
  'abrirModalVerificacion',
  'toggleEmpresaTheme',
  'switchEmpresaIdioma',
  'cerrarModalBienvenida',
  'empezarConvocatoriaDesdeBienvenida',
  'cerrarModalPerfil',
  'previewLogo',
  'cerrarModalTodasValoraciones',
  'filtrarPorEstrellasModal',
  'cerrarModalVerificacion',
  'cerrarModal',
  'toggleCiudadProyecto',
  'cerrarModalContrato',
  'cerrarModalEditarProyecto',
  'cerrarDrawerCandidatos',
  'cerrarModalCalificar',
  'cerrarModalConfirmarRetiro',
  'ejecutarRetiroConfirmado',
  'toggleChatContextSidebar',
  'abrirModalContrato',
  'abrirChatEnCentro',
  'abrirDrawerCandidatos',
  'abrirModalCalificar',
  'seleccionarMetricaLedger',
  'seleccionarPeriodoLedger',
  'filtrarHistorialEnTiempoReal',
  'abrirModal',
  'filtrarOfertasPorModalidad',
  'filtrarOfertasEnTiempoReal',
  'filtrarResenasModal',
  'abrirModalEditarProyecto',
  'abrirModalPerfil',
  'switchPerfilSubTab',
  'seleccionarMetricaInicio',
  'seleccionarPeriodoInicio',
  // Postulaciones & proyectos
  'seleccionarCandidato',
  'toggleCiudadEditar',
]);

function resolveArgToken(val, el, event) {
  if (typeof val !== 'string') return val;
  if (val === '$event') return event;
  if (val === '$el') return el;
  if (val === '$href') return el.href || el.getAttribute?.('href') || '';
  if (val === '$dataUrl') return el.getAttribute?.('data-url') || '';
  if (val.startsWith('$id:')) return document.getElementById(val.slice(4));
  if (val === '$num:0') return 0;
  if (val.startsWith('$num:')) return Number(val.slice(5));
  if (val === '$bool:true') return true;
  if (val === '$bool:false') return false;
  return val;
}

function readIndexedArgs(el, prefix, event) {
  const args = [];
  for (let i = 0; i < 20; i += 1) {
    const attr = el.getAttribute?.(`${prefix}${i}`);
    if (attr === null || attr === undefined) break;
    args.push(resolveArgToken(attr, el, event));
  }
  return args;
}

function readCallArgs(el, jsonAttr, indexedPrefix, event) {
  const rawJson = el.getAttribute?.(jsonAttr);
  if (rawJson) {
    try {
      const parsed = JSON.parse(rawJson);
      if (Array.isArray(parsed)) {
        return parsed.map((item) => resolveArgToken(item, el, event));
      }
    } catch {
      return [];
    }
  }
  return readIndexedArgs(el, indexedPrefix, event);
}

function invokeAllowed(fnName, args) {
  if (!fnName || !ALLOWED_CALLS.has(fnName)) return undefined;
  if (fnName === '__noop') return undefined;
  if (fnName === '__print') {
    window.print?.();
    return undefined;
  }
  if (fnName === '__navigate') {
    if (args[0]) window.location.assign(args[0]);
    return undefined;
  }
  const fn = window[fnName];
  if (typeof fn === 'function') {
    return fn(...args);
  }
  return undefined;
}

function runDeclarativeCall(el, callAttr, argsAttr, indexedPrefix, event) {
  const fnName = el.getAttribute?.(callAttr);
  if (!fnName) return;

  if (el.dataset?.selfOnly === 'true' && event.target !== el) return;
  if (el.dataset?.ifNoHtmx === 'true' && window.htmx) return;
  if (el.dataset?.ifEl && !document.getElementById(el.dataset.ifEl)) return;
  if (el.dataset?.stop === 'true') event.stopPropagation?.();
  if (el.dataset?.prevent === 'true') event.preventDefault?.();

  const args = readCallArgs(el, argsAttr, indexedPrefix, event);
  const res = invokeAllowed(fnName, args);
  if (res === false) {
    event.preventDefault?.();
  }

  const thenFn = el.getAttribute?.('data-then');
  if (thenFn) {
    const thenArgs = readCallArgs(el, 'data-then-args', 'data-then-arg-', event);
    const thenRes = invokeAllowed(thenFn, thenArgs);
    if (thenRes === false) event.preventDefault?.();
  }

  const then2Fn = el.getAttribute?.('data-then2');
  if (then2Fn) {
    const then2Args = readCallArgs(el, 'data-then2-args', 'data-then2-arg-', event);
    const then2Res = invokeAllowed(then2Fn, then2Args);
    if (then2Res === false) event.preventDefault?.();
  }
}

function handleAction(el, event) {
  const action = el.dataset.action;
  if (!action) return;

  if (el.dataset.selfOnly === 'true' && event.target !== el) {
    return;
  }

  if (el.dataset.remove) {
    document.getElementById(el.dataset.remove)?.remove();
  }

  switch (action) {
    case 'close-modal':
      window.closeModal?.(el.dataset.target);
      break;
    case 'confirm-toggle-user':
      window.confirmToggleUserAction?.();
      break;
    case 'ver-seccion':
      window.verSeccion?.(el.dataset.target);
      break;
    case 'cerrar-popup-contrato':
      window.cerrarPopupContrato?.(el.dataset.target);
      break;
    case 'cambiar-metrica-grafica':
      window.cambiarMetricaGrafica?.(el.dataset.metric, el);
      break;
    case 'switch-tab':
      if (el.tagName === 'A') event.preventDefault();
      window.switchTab?.(el.dataset.target);
      if (el.dataset.scrollTo) {
        document.getElementById(el.dataset.scrollTo)?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      }
      break;
    case 'abrir-modal':
      window.abrirModal?.();
      break;
    case 'remove-el':
      document.getElementById(el.dataset.target)?.remove();
      break;
    case 'seleccionar-metrica-inicio':
      window.seleccionarMetricaInicio?.(el.dataset.metric, el);
      break;
    case 'seleccionar-periodo-inicio':
      window.seleccionarPeriodoInicio?.(el.dataset.period, el);
      break;
    case 'toggle-display': {
      const target = document.getElementById(el.dataset.target);
      if (target) {
        target.style.display =
          target.style.display === 'none' || target.style.display === '' ? 'block' : 'none';
      }
      break;
    }
    case 'hide-el': {
      const target = document.getElementById(el.dataset.target);
      if (target) target.style.display = 'none';
      break;
    }
    case 'abrir-chat-centro':
      event.preventDefault();
      window.abrirChatEnCentro?.(event, el.dataset.devId, el.dataset.proyectoId);
      break;
    default:
      break;
  }
}

if (!window.__jobdevsActionDelegateBound) {
  window.__jobdevsActionDelegateBound = true;

  document.addEventListener('click', (event) => {
    const callEl = event.target.closest?.('[data-call]');
    if (callEl) {
      runDeclarativeCall(callEl, 'data-call', 'data-args', 'data-arg-', event);
      return;
    }
    const actionEl = event.target.closest?.('[data-action]');
    if (actionEl) handleAction(actionEl, event);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const el = event.target.closest?.('[role="button"][data-action], [role="button"][data-call]');
    if (!el || event.target !== el) return;
    event.preventDefault();
    el.click();
  });

  document.addEventListener('input', (event) => {
    const el = event.target.closest?.('[data-input-call]');
    if (el) runDeclarativeCall(el, 'data-input-call', 'data-input-args', 'data-input-arg-', event);
  });

  document.addEventListener('change', (event) => {
    const callEl = event.target.closest?.('[data-change-call]');
    if (callEl) {
      runDeclarativeCall(callEl, 'data-change-call', 'data-change-args', 'data-change-arg-', event);
      return;
    }
    const el = event.target.closest?.('[data-change-action]');
    if (!el) return;
    if (el.dataset.changeAction === 'sync-create-user-doc') {
      window.syncCreateUserDocField?.();
    }
  });

  document.addEventListener('submit', (event) => {
    const callForm = event.target.closest?.('form[data-submit-call]');
    if (callForm) {
      runDeclarativeCall(callForm, 'data-submit-call', 'data-submit-args', 'data-submit-arg-', event);
      return;
    }
    const form = event.target.closest?.('form[data-submit-action]');
    if (!form) return;
    if (form.dataset.submitAction === 'validar-rechazo-avance') {
      if (
        typeof window.validarRechazoAvance === 'function' &&
        window.validarRechazoAvance(form, event) === false
      ) {
        event.preventDefault();
      }
    }
  });

  document.addEventListener(
    'error',
    (event) => {
      const target = event.target;
      if (target?.tagName === 'IMG' && target.dataset?.fallbackText && target.parentElement) {
        target.parentElement.textContent = target.dataset.fallbackText;
      }
    },
    true
  );
}
