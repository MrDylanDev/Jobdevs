/**
 * ============================================================
 * JobDevs - Panel Administrador: UI Core, Navigation, Theme,
 * Sidebar/Drawer, User Dropdown, Toasts, Modals & Shared Helpers
 * ============================================================
 */

// --- Shared Utilities ---

export function onReady(fn) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fn, { once: true });
  } else {
    fn();
  }
}

export function getCSRFToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

export function debounce(fn, delay = 300) {
  let timer = null;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

export function escapeAdminHtml(val) {
  return String(val == null ? '' : val)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function escapeAdminJs(val) {
  return String(val == null ? '' : val)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'");
}

// --- Section Navigation & Hooks ---

const _sectionHooks = [];

export function registerSectionHook(fn) {
  if (typeof fn === 'function') {
    _sectionHooks.push(fn);
  }
}

export function showSection(id, btn) {
  document.querySelectorAll('.section-v').forEach((s) => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach((b) => b.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('active');
  let activeBtn = btn;
  if (!activeBtn) {
    activeBtn = Array.from(document.querySelectorAll('.nav-item[onclick]')).find(
      (b) => (b.getAttribute('onclick') || '').indexOf("('" + id + "'") !== -1
    );
  }
  if (activeBtn) activeBtn.classList.add('active');

  _sectionHooks.forEach((hook) => {
    try {
      hook(id, activeBtn);
    } catch (e) {
      console.error(e);
    }
  });

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// --- Modals ---

export function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

// --- Toasts & Notifications ---

export function adminNotify(msg, typeOrIsError) {
  let type = 'error';
  if (typeOrIsError === false || typeOrIsError === 'success') {
    type = 'success';
  } else if (typeOrIsError === 'warning') {
    type = 'warning';
  } else if (typeOrIsError === 'info') {
    type = 'info';
  }
  const isErr = type === 'error';

  if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
    window.JobDevsSSE.mostrarToast({ tipo: isErr ? 'error' : 'success', mensaje: msg });
    return;
  }
  if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
    window.JobDevsToast.mostrar({ tipo: type, mensaje: msg });
    return;
  }
  if (typeof window.jdToast === 'function') {
    window.jdToast(msg, isErr);
    return;
  }

  const borderColors = {
    success: 'var(--accent, #16a34a)',
    error: 'var(--danger, #ef4444)',
    warning: 'var(--warning, #f59e0b)',
    info: 'var(--info, #38bdf8)',
  };
  const t = document.createElement('div');
  t.style.cssText =
    'position:fixed;bottom:24px;right:24px;z-index:9999;background:var(--bg-card, #141619);' +
    'color:var(--text-primary, #ffffff);border:1px solid var(--border, rgba(255,255,255,0.14));' +
    'border-left:3px solid ' + (borderColors[type] || borderColors.error) + ';' +
    'padding:12px 16px;border-radius:8px;font-size:13px;font-weight:600;' +
    'box-shadow:0 8px 24px rgba(0,0,0,0.22);transition:opacity 0.3s;';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    setTimeout(() => t.remove(), 300);
  }, 4000);
}

export function queueAdminToast(msg, type) {
  try {
    sessionStorage.setItem(
      'admin_pending_toast',
      JSON.stringify({ msg: msg, type: type || 'success' })
    );
  } catch (e) {}
}

export function flushQueuedAdminToast() {
  try {
    const raw = sessionStorage.getItem('admin_pending_toast');
    if (raw) {
      sessionStorage.removeItem('admin_pending_toast');
      const parsed = JSON.parse(raw);
      if (parsed && parsed.msg) {
        adminNotify(parsed.msg, parsed.type || 'success');
      }
    }
  } catch (e) {}
}

// --- Confirmation Modal ---

export function adminConfirm(opts) {
  return new Promise((resolve) => {
    if (typeof window.JdConfirm === 'function') {
      window.JdConfirm(opts).then(resolve);
      return;
    }
    let modal = document.getElementById('adminGenericConfirmModal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'adminGenericConfirmModal';
      modal.className = 'modal-overlay';
      modal.innerHTML =
        '<div class="modal-box">' +
          '<button type="button" class="modal-close-btn" id="admConfClose" aria-label="Cerrar">&times;</button>' +
          '<h3 id="admConfTitle" style="margin-bottom:10px; font-size:18px;">Confirmar acción</h3>' +
          '<p id="admConfMsg" style="font-size:13.5px; color:var(--text-secondary); line-height:1.5; margin-bottom:18px;"></p>' +
          '<div style="display:flex; gap:10px; justify-content:flex-end;">' +
            '<button type="button" class="btn btn-secondary" id="admConfCancel">Cancelar</button>' +
            '<button type="button" class="btn btn-danger" id="admConfOk">Confirmar</button>' +
          '</div>' +
        '</div>';
      document.body.appendChild(modal);
    }
    document.getElementById('admConfTitle').textContent = opts.titulo || 'Confirmar acción';
    document.getElementById('admConfMsg').textContent = opts.mensaje || '¿Deseas continuar?';
    const btnOk = document.getElementById('admConfOk');
    const btnCancel = document.getElementById('admConfCancel');
    const btnClose = document.getElementById('admConfClose');
    btnOk.textContent = opts.textoConfirmar || 'Confirmar';
    btnOk.className = 'btn ' + (opts.peligro === false ? 'btn-primary' : 'btn-danger');
    modal.classList.add('open');

    function cleanup(res) {
      modal.classList.remove('open');
      btnOk.onclick = null;
      btnCancel.onclick = null;
      if (btnClose) btnClose.onclick = null;
      modal.onclick = null;
      resolve(res);
    }
    btnOk.onclick = () => cleanup(true);
    btnCancel.onclick = () => cleanup(false);
    if (btnClose) btnClose.onclick = () => cleanup(false);
    modal.onclick = (e) => {
      if (e.target === modal) cleanup(false);
    };
  });
}

// --- Mobile Drawer & Desktop Sidebar Collapse (SCRUM-411) ---

function _syncAdminDrawerAria(isOpen) {
  const toggleBtn = document.querySelector('.mobile-menu-toggle');
  if (!toggleBtn) return;
  toggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  toggleBtn.setAttribute(
    'aria-label',
    isOpen ? 'Cerrar menú de navegación' : 'Abrir menú de navegación'
  );
}

export function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const isOpen = sidebar ? sidebar.classList.toggle('is-open') : false;
  if (backdrop) backdrop.classList.toggle('is-open', isOpen);
  _syncAdminDrawerAria(isOpen);
  if (isOpen && sidebar) {
    const firstFocusable = sidebar.querySelector('.nav-item, a, button');
    if (firstFocusable) firstFocusable.focus();
  } else if (!isOpen) {
    const toggleBtn = document.querySelector('.mobile-menu-toggle');
    if (toggleBtn) toggleBtn.focus();
  }
}

export function closeSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const wasOpen = sidebar ? sidebar.classList.contains('is-open') : false;
  if (sidebar) sidebar.classList.remove('is-open');
  if (backdrop) backdrop.classList.remove('is-open');
  _syncAdminDrawerAria(false);
  if (wasOpen) {
    const toggleBtn = document.querySelector('.mobile-menu-toggle');
    if (toggleBtn) toggleBtn.focus();
  }
}

export function toggleSidebarCollapse() {
  const sidebar = document.querySelector('.sidebar');
  if (!sidebar) return;
  const isCollapsed = sidebar.classList.toggle('is-collapsed');
  try {
    localStorage.setItem('sidebar_collapsed_admin', isCollapsed ? '1' : '0');
  } catch (e) {}

  const btn = document.getElementById('sidebarCollapseBtn');
  if (btn) {
    btn.title = isCollapsed ? 'Expandir menú lateral' : 'Colapsar menú (solo iconos)';
    btn.innerHTML =
      '<i data-lucide="' + (isCollapsed ? 'panel-left-open' : 'panel-left-close') + '"></i>';
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// --- User Dropdown ---

export function toggleAdminUserDropdown(ev) {
  if (ev) ev.stopPropagation();
  const wrap = document.getElementById('adminUserDropdown');
  const menu = document.getElementById('adminUserDropdownMenu');
  const btn = document.getElementById('adminUserDropdownBtn');
  if (!wrap || !menu || !btn) return;
  const willOpen = menu.hidden;
  menu.hidden = !willOpen;
  wrap.classList.toggle('is-open', willOpen);
  btn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
}

export function closeAdminUserDropdown() {
  const wrap = document.getElementById('adminUserDropdown');
  const menu = document.getElementById('adminUserDropdownMenu');
  const btn = document.getElementById('adminUserDropdownBtn');
  if (!wrap || !menu || !btn) return;
  menu.hidden = true;
  wrap.classList.remove('is-open');
  btn.setAttribute('aria-expanded', 'false');
}

// --- Theme Toggle (Dark / Corporate Light) ---

function _syncAdminThemeBtn(theme) {
  const btn = document.getElementById('adminThemeToggle');
  if (!btn) return;
  const isDark = theme === 'dark';
  const labelText = isDark ? 'Tema oscuro' : 'Tema claro';
  const ariaLabel = isDark ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro';
  btn.setAttribute('aria-pressed', isDark ? 'true' : 'false');
  btn.setAttribute('aria-label', ariaLabel);
  btn.title = ariaLabel;
  const label = document.getElementById('adminThemeLabel');
  if (label) {
    label.textContent = labelText;
  }
}

export function toggleAdminTheme() {
  const current =
    document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  const next = current === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  try {
    localStorage.setItem('admin_theme', next);
  } catch (e) {}
  _syncAdminThemeBtn(next);
}

// --- Logout Spinner ---

export function cerrarSesionConSpinner(event, el) {
  if (!el || !el.href) return;
  if (event) event.preventDefault();
  closeAdminUserDropdown();
  const overlay = document.getElementById('logoutSpinnerOverlay');
  if (overlay) {
    overlay.style.display = 'flex';
    overlay.setAttribute('aria-hidden', 'false');
  }
  setTimeout(function () {
    window.location.href = el.href;
  }, 350);
}

// --- Chat List Resizer ---

function initAdminChatResizer() {
  const resizer = document.getElementById('adminChatListResizer');
  const chatEl = document.querySelector('#chatSection .jd-chat');
  if (!resizer || !chatEl) return;

  try {
    const saved = parseInt(localStorage.getItem('jobdevs-admin-chat-list-width') || '', 10);
    if (saved >= 240 && saved <= 520) {
      chatEl.style.setProperty('--jd-chat-list-width', saved + 'px');
    }
  } catch (e) {}

  let startX = 0;
  let startW = 340;

  function onMove(ev) {
    const next = Math.min(520, Math.max(240, Math.round(startW + (ev.clientX - startX))));
    chatEl.style.setProperty('--jd-chat-list-width', next + 'px');
  }

  function onUp() {
    resizer.classList.remove('is-resizing');
    document.body.classList.remove('is-chat-resizing');
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', onUp);
    try {
      const current = parseInt(
        getComputedStyle(chatEl).getPropertyValue('--jd-chat-list-width'),
        10
      );
      if (current >= 240 && current <= 520) {
        localStorage.setItem('jobdevs-admin-chat-list-width', String(current));
      }
    } catch (e) {}
  }

  resizer.addEventListener('pointerdown', function (ev) {
    ev.preventDefault();
    startX = ev.clientX;
    const listEl = chatEl.querySelector('.jd-chat-list');
    startW = listEl ? listEl.getBoundingClientRect().width : 340;
    resizer.classList.add('is-resizing');
    document.body.classList.add('is-chat-resizing');
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  });
}

// --- Module Initializer ---

export function initUiCore() {
  // Expose inline HTML & sibling-script handlers on window
  window.showSection = showSection;
  window.closeModal = closeModal;
  window.adminNotify = adminNotify;
  window.queueAdminToast = queueAdminToast;
  window.adminConfirm = adminConfirm;
  window.toggleSidebar = toggleSidebar;
  window.closeSidebar = closeSidebar;
  window.toggleSidebarCollapse = toggleSidebarCollapse;
  window.toggleAdminUserDropdown = toggleAdminUserDropdown;
  window.closeAdminUserDropdown = closeAdminUserDropdown;
  window.toggleAdminTheme = toggleAdminTheme;
  window.cerrarSesionConSpinner = cerrarSesionConSpinner;

  // Flush queued toast from sessionStorage
  flushQueuedAdminToast();

  // Global form[data-admin-confirm="true"] confirmation interceptor
  document.addEventListener('submit', async function (e) {
    const form = e.target;
    if (!form || !form.matches || !form.matches('form[data-admin-confirm="true"]')) return;
    if (form.dataset.adminConfirmed === 'true') {
      delete form.dataset.adminConfirmed;
      return;
    }
    e.preventDefault();
    const ok = await adminConfirm({
      titulo: form.dataset.confirmTitle || 'Confirmar acción',
      mensaje: form.dataset.confirmMessage || '¿Deseas continuar con esta acción?',
      textoConfirmar: form.dataset.confirmOk || 'Confirmar',
      peligro: form.dataset.confirmDanger === 'true',
    });
    if (ok) {
      form.dataset.adminConfirmed = 'true';
      if (typeof form.requestSubmit === 'function') {
        form.requestSubmit();
      } else {
        HTMLFormElement.prototype.submit.call(form);
      }
    }
  });

  // Mobile drawer backdrop, nav-item auto-close & viewport resize
  const backdrop = document.getElementById('sidebarBackdrop');
  if (backdrop) backdrop.addEventListener('click', closeSidebar);
  document.querySelectorAll('.sidebar .nav-item').forEach((item) => {
    item.addEventListener('click', () => {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) closeSidebar();
  });

  // Restore desktop sidebar collapse state
  try {
    if (localStorage.getItem('sidebar_collapsed_admin') === '1' && window.innerWidth >= 769) {
      const sidebar = document.querySelector('.sidebar');
      if (sidebar) sidebar.classList.add('is-collapsed');
      const btn = document.getElementById('sidebarCollapseBtn');
      if (btn) {
        btn.title = 'Expandir menú lateral';
        btn.innerHTML = '<i data-lucide="panel-left-open"></i>';
      }
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    }
  } catch (e) {}

  // Restore saved theme
  let savedTheme = 'dark';
  try {
    const stored = localStorage.getItem('admin_theme');
    if (stored === 'light' || stored === 'dark') savedTheme = stored;
  } catch (e) {}
  document.documentElement.setAttribute('data-theme', savedTheme);
  _syncAdminThemeBtn(savedTheme);

  // Close user dropdown when clicking outside
  document.addEventListener('click', function (ev) {
    const wrap = document.getElementById('adminUserDropdown');
    if (wrap && !wrap.contains(ev.target)) {
      closeAdminUserDropdown();
    }
  });

  // Resizable chat conversation list
  initAdminChatResizer();
}
