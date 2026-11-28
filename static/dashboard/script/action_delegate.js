/**
 * Declarative event delegation for dashboard actions (CSP-friendly replacement for inline on*=).
 * Supports data-action (click + Enter/Space on role="button"), data-change-action, and data-submit-action.
 */

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
    const el = event.target.closest?.('[data-action]');
    if (el) handleAction(el, event);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const el = event.target.closest?.('[role="button"][data-action]');
    if (!el || event.target !== el) return;
    event.preventDefault();
    el.click();
  });

  document.addEventListener('change', (event) => {
    const el = event.target.closest?.('[data-change-action]');
    if (!el) return;
    if (el.dataset.changeAction === 'sync-create-user-doc') {
      window.syncCreateUserDocField?.();
    }
  });

  document.addEventListener('submit', (event) => {
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
}
