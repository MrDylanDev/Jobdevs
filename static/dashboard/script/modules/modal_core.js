/**
 * JobDevs — Modales de Dashboard: Core compartido
 * Utilidades HTML/CSRF/fetch, toasts, modal de confirmación, modal base y onReady.
 */

export function onReady(fn) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fn, { once: true });
  } else {
    fn();
  }
}

export function escapeHtml(str) {
  return String(str == null ? '' : str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function leerCookie(nombre) {
  const match = document.cookie
    .split('; ')
    .find(function (item) { return item.indexOf(nombre + '=') === 0; });
  return match ? decodeURIComponent(match.slice(nombre.length + 1)) : '';
}

export async function parseJsonResponse(res, fallbackMsg) {
  const ct = res.headers.get('content-type') || '';
  if (!ct.includes('application/json')) {
    throw new Error(fallbackMsg || 'Respuesta inesperada del servidor.');
  }
  return await res.json();
}

export function getCsrfToken() {
  const cookie = leerCookie('csrftoken');
  if (cookie) return cookie;
  const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
  return input ? input.value : '';
}

export function mostrarToast(mensaje, esError) {
  if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
    window.JobDevsToast.mostrar({
      tipo: esError ? 'error' : 'success',
      mensaje: mensaje,
      duracion: 4500,
    });
    return;
  }
  if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
    window.JobDevsSSE.mostrarToast({
      tipo: esError ? 'alerta' : 'info',
      mensaje: mensaje,
    });
    return;
  }
  if (typeof window.mostrarToast === 'function' && window.mostrarToast !== mostrarToast) {
    window.mostrarToast(mensaje, esError);
    return;
  }
  // Fallback Toast Flotante Personalizado
  const t = document.createElement('div');
  t.className = 'jobdevs-toast-fallback ' + (esError ? 'is-error' : 'is-success');
  t.textContent = mensaje;
  document.body.appendChild(t);
  setTimeout(function () {
    t.style.opacity = '0';
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
  }, 4000);
}

// ─────────────────────────────────────────────────────────────
// Modal Personalizado de Confirmación In-Situ (Reemplaza window.confirm)
// ─────────────────────────────────────────────────────────────
let confirmEl = null;

function ensureConfirmModal() {
  if (confirmEl) return confirmEl;
  confirmEl = document.createElement('div');
  confirmEl.id = 'jdmConfirmModal';
  confirmEl.className = 'jdm-modal jdm-confirm-overlay';
  confirmEl.hidden = true;
  confirmEl.style.zIndex = '2350';
  confirmEl.innerHTML =
    '<div class="jdm-backdrop" data-jdm-confirm-cancel></div>' +
    '<div class="jdm-card jdm-confirm-card" role="alertdialog" aria-modal="true" aria-labelledby="jdmConfirmTitle" aria-describedby="jdmConfirmMsg" style="max-width:460px;">' +
      '<header class="jdm-header" style="padding:18px 22px 14px;">' +
        '<div style="min-width:0;flex:1;">' +
          '<div class="jdm-kicker" id="jdmConfirmKicker">CONFIRMACIÓN REQUERIDA</div>' +
          '<h2 class="jdm-title" id="jdmConfirmTitle" style="font-size:17px;">¿Deseas continuar?</h2>' +
        '</div>' +
        '<button type="button" class="jdm-close" data-jdm-confirm-cancel aria-label="Cerrar">&times;</button>' +
      '</header>' +
      '<div class="jdm-body" style="padding:18px 22px;">' +
        '<p id="jdmConfirmMsg" style="margin:0;font-size:13.5px;line-height:1.6;"></p>' +
      '</div>' +
      '<footer class="jdm-footer" style="padding:14px 22px;display:flex;justify-content:flex-end;gap:10px;">' +
        '<button type="button" class="jdm-btn jdm-btn-secondary" id="jdmConfirmBtnCancel" data-jdm-confirm-cancel>Cancelar</button>' +
        '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmConfirmBtnOk">Confirmar</button>' +
      '</footer>' +
    '</div>';
  document.body.appendChild(confirmEl);
  return confirmEl;
}

export function confirmarAccion(opciones) {
  const opts = typeof opciones === 'string' ? { mensaje: opciones } : (opciones || {});
  const modal = ensureConfirmModal();
  const titleEl = document.getElementById('jdmConfirmTitle');
  const kickerEl = document.getElementById('jdmConfirmKicker');
  const msgEl = document.getElementById('jdmConfirmMsg');
  const btnOk = document.getElementById('jdmConfirmBtnOk');
  const btnCancel = document.getElementById('jdmConfirmBtnCancel');

  if (kickerEl) kickerEl.textContent = opts.kicker || (opts.peligro ? 'ACCIÓN CRÍTICA' : 'CONFIRMACIÓN REQUERIDA');
  if (titleEl) titleEl.textContent = opts.titulo || '¿Confirmar esta acción?';
  if (msgEl) msgEl.textContent = opts.mensaje || '¿Estás seguro de que deseas continuar?';
  if (btnOk) {
    btnOk.textContent = opts.textoConfirmar || 'Confirmar';
    btnOk.className = 'jdm-btn ' + (opts.peligro ? 'jdm-btn-danger' : 'jdm-btn-primary');
  }
  if (btnCancel) {
    btnCancel.textContent = opts.textoCancelar || 'Cancelar';
  }

  modal.hidden = false;

  return new Promise(function (resolve) {
    function limpiar(resultado) {
      modal.hidden = true;
      modal.removeEventListener('click', onClick);
      document.removeEventListener('keydown', onKey, true);
      resolve(resultado);
    }

    function onClick(e) {
      if (e.target.closest('#jdmConfirmBtnOk')) {
        e.preventDefault();
        limpiar(true);
      } else if (e.target.closest('[data-jdm-confirm-cancel]')) {
        e.preventDefault();
        limpiar(false);
      }
    }

    function onKey(e) {
      if (e.key === 'Escape' && !modal.hidden) {
        e.preventDefault();
        e.stopPropagation();
        limpiar(false);
      }
    }

    modal.addEventListener('click', onClick);
    document.addEventListener('keydown', onKey, true);
    if (btnOk) btnOk.focus();
  });
}

// ─────────────────────────────────────────────────────────────
// Modal Base Manager
// ─────────────────────────────────────────────────────────────
let modalEl = null;
let lastFocusEl = null;

export function ensureModal() {
  if (modalEl) return modalEl;

  modalEl = document.createElement('div');
  modalEl.id = 'jdmModal';
  modalEl.className = 'jdm-modal';
  modalEl.hidden = true;
  modalEl.innerHTML =
    '<div class="jdm-backdrop" data-jdm-close></div>' +
    '<div class="jdm-card" id="jdmCard" role="dialog" aria-modal="true" aria-labelledby="jdmTitulo">' +
      '<header class="jdm-header">' +
        '<div style="min-width:0;flex:1;">' +
          '<div class="jdm-kicker" id="jdmKicker">// ACCIÓN</div>' +
          '<h2 class="jdm-title" id="jdmTitulo">Cargando…</h2>' +
          '<div class="jdm-sub" id="jdmSub"></div>' +
        '</div>' +
        '<button type="button" class="jdm-close" data-jdm-close aria-label="Cerrar">&times;</button>' +
      '</header>' +
      '<div class="jdm-body" id="jdmBody" aria-live="polite">' +
        '<div class="jdm-loading"><i data-lucide="loader-2"></i><span>Cargando información…</span></div>' +
      '</div>' +
      '<footer class="jdm-footer" id="jdmFooter" hidden></footer>' +
    '</div>';

  document.body.appendChild(modalEl);

  modalEl.addEventListener('click', function (e) {
    if (modalEl.dataset.obligatorio === 'true') return;
    if (e.target.closest('[data-jdm-close]')) {
      e.preventDefault();
      cerrarModal();
    }
  });

  document.addEventListener('keydown', function (e) {
    if (!modalEl || modalEl.hidden) return;
    if (e.key === 'Escape') {
      if (modalEl.dataset.obligatorio === 'true') {
        e.preventDefault();
        return;
      }
      e.preventDefault();
      cerrarModal();
    }
  });

  return modalEl;
}

export function setModalObligatorio(esObligatorio) {
  if (!modalEl) return;
  modalEl.dataset.obligatorio = esObligatorio ? 'true' : 'false';
  const closeBtn = modalEl.querySelector('.jdm-close');
  if (closeBtn) closeBtn.style.display = esObligatorio ? 'none' : 'flex';
}

export function abrirModal(cardClass) {
  lastFocusEl = document.activeElement;
  ensureModal();
  const card = document.getElementById('jdmCard');
  card.className = 'jdm-card' + (cardClass ? ' ' + cardClass : '');
  modalEl.hidden = false;
  document.body.style.overflow = 'hidden';

  const body = document.getElementById('jdmBody');
  const footer = document.getElementById('jdmFooter');
  body.scrollTop = 0;
  body.innerHTML = '<div class="jdm-loading"><i data-lucide="loader-2"></i><span>Cargando información…</span></div>';
  footer.hidden = true;
  footer.innerHTML = '';
}

export function cerrarModal(forzar) {
  if (!modalEl) return;
  if (!forzar && modalEl.dataset.obligatorio === 'true') return;
  modalEl.dataset.obligatorio = 'false';
  modalEl.hidden = true;
  document.body.style.overflow = '';
  const closeBtn = modalEl.querySelector('.jdm-close');
  if (closeBtn) closeBtn.style.display = 'flex';
  if (lastFocusEl && typeof lastFocusEl.focus === 'function') {
    try { lastFocusEl.focus(); } catch (err) {}
  }
}

export function setHeader(kicker, titulo, sub) {
  const k = document.getElementById('jdmKicker');
  const t = document.getElementById('jdmTitulo');
  const s = document.getElementById('jdmSub');
  if (k) k.textContent = kicker || '';
  if (t) t.textContent = titulo || '';
  if (s) {
    s.textContent = sub || '';
    s.style.display = sub ? 'block' : 'none';
  }
}

export function setContent(html) {
  const b = document.getElementById('jdmBody');
  if (b) b.innerHTML = html;
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function setFooter(html) {
  const f = document.getElementById('jdmFooter');
  if (!f) return;
  if (html) {
    f.innerHTML = html;
    f.hidden = false;
  } else {
    f.innerHTML = '';
    f.hidden = true;
  }
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// Interceptor global para formularios con data-confirm (reemplaza onsubmit="return confirm(...)")
export function initConfirmFormInterceptor() {
  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (!form || !form.hasAttribute('data-confirm')) return;
    if (form.dataset.confirmed === 'true') {
      form.dataset.confirmed = '';
      return;
    }
    e.preventDefault();
    e.stopPropagation();

    const msg = form.getAttribute('data-confirm');
    const title = form.getAttribute('data-confirm-title') || 'Confirmar acción';
    const danger = form.getAttribute('data-confirm-danger') !== 'false';

    confirmarAccion({
      titulo: title,
      mensaje: msg,
      peligro: danger
    }).then(function (ok) {
      if (ok) {
        form.dataset.confirmed = 'true';
        if (typeof form.requestSubmit === 'function') {
          form.requestSubmit();
        } else {
          form.submit();
        }
      }
    });
  }, true);
}
