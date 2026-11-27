/**
 * Módulo UI Core — Dashboard Desarrollador
 * Helpers base (onReady, CSRF, toasts, escapeHtml), tema claro/oscuro,
 * navegación de secciones/subpestañas, KPIs count-up, focus trap,
 * chat sidebar/resizer, drawer móvil, colapso de sidebar y menú de usuario.
 */

// ═══════════════════════════════════════════════
// HELPERS BASE
// ═══════════════════════════════════════════════
export function onReady(fn) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fn, { once: true });
  } else {
    fn();
  }
}

// El token oculto puede quedar desfasado si la cookie csrftoken rotó
// (login en otra pestaña, reinicio con otra SECRET_KEY o botón atrás).
// Sincronizarlo evita el 403 "CSRF token from POST incorrect".
export function leerCookie(nombre) {
  const par = document.cookie
    .split('; ')
    .find((item) => item.startsWith(nombre + '='));
  return par ? decodeURIComponent(par.slice(nombre.length + 1)) : '';
}

export function sincronizarCsrf(scope) {
  const token = leerCookie('csrftoken');
  if (!token) return;
  (scope || document).querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach((input) => {
    input.value = token;
  });
}

export function mostrarToast(mensaje) {
  if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
    window.JobDevsToast.mostrar({
      tipo: 'success',
      mensaje: mensaje,
      duracion: 4200,
    });
  }
}

export function escapeHtml(val) {
  if (val == null) return '';
  return String(val)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ═══════════════════════════════════════════════
// MODO CLARO / OSCURO (comparte preferencia con la landing)
// ═══════════════════════════════════════════════
export const DEV_THEME_STORAGE_KEY = 'jobdevs-theme';

export function devTemaActual() {
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
}

export function actualizarBotonTemaDev(tema) {
  const btn = document.getElementById('devThemeToggle');
  if (btn) {
    btn.setAttribute('aria-pressed', tema === 'light' ? 'true' : 'false');
    btn.setAttribute('aria-label', 'Cambiar entre tema oscuro y claro');
    btn.title = tema === 'light' ? 'Cambiar a tema oscuro' : 'Cambiar a tema claro';
  }
  const dropdownLabel = document.getElementById('devDropdownThemeLabel');
  if (dropdownLabel) {
    dropdownLabel.textContent = tema === 'light' ? 'Tema Oscuro' : 'Tema Claro';
  }
}

export function toggleDevTheme() {
  const nuevoTema = devTemaActual() === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', nuevoTema);
  try {
    localStorage.setItem(DEV_THEME_STORAGE_KEY, nuevoTema);
  } catch (e) {}
  actualizarBotonTemaDev(nuevoTema);
}

// ═══════════════════════════════════════════════
// NAVEGACIÓN DE SECCIONES Y SUB-PESTAÑAS
// ═══════════════════════════════════════════════
export function switchContratosSubTab(tabId, btn) {
  document.querySelectorAll('#contratos .contratos-pane').forEach(function (p) {
    p.style.display = 'none';
  });
  document.querySelectorAll('#contratos .contratos-subtab-btn').forEach(function (b) {
    b.classList.remove('active');
    b.setAttribute('aria-selected', 'false');
  });
  const target = document.getElementById('contratos-pane-' + tabId);
  if (target) target.style.display = 'block';

  if (!btn) {
    btn = document.getElementById('tabBtnContrato' + tabId.charAt(0).toUpperCase() + tabId.slice(1));
  }
  if (btn) {
    btn.classList.add('active');
    btn.setAttribute('aria-selected', 'true');
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function switchHistorialTab(tabId, btn) {
  document.querySelectorAll('.historial-pane').forEach(function (p) {
    p.style.display = 'none';
  });
  document.querySelectorAll('.historial-tab').forEach(function (b) {
    b.classList.remove('is-active');
    b.setAttribute('aria-selected', 'false');
  });

  const target = document.getElementById('historial-pane-' + tabId);
  if (target) target.style.display = 'block';

  if (!btn) {
    btn = document.getElementById('tabBtnHist' + tabId.charAt(0).toUpperCase() + tabId.slice(1));
  }
  if (btn) {
    btn.classList.add('is-active');
    btn.setAttribute('aria-selected', 'true');
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function verSeccion(id, btn) {
  if (id === 'perfil') {
    if (typeof window.abrirModalPerfilDev === 'function') {
      window.abrirModalPerfilDev();
    }
    return;
  }
  if (id === 'postulaciones') {
    verSeccion('contratos');
    if (typeof window.switchContratosSubTab === 'function') {
      window.switchContratosSubTab('postulaciones');
    }
    return;
  }
  if (id === 'disputas') {
    verSeccion('completados');
    if (typeof window.switchHistorialTab === 'function') {
      window.switchHistorialTab('disputas', document.getElementById('tabBtnHistDisputas'));
    }
    return;
  }
  document.querySelectorAll('.seccion-v').forEach(s => s.classList.remove('activa'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('activa');
  if (!btn) {
    btn = Array.from(document.querySelectorAll('.nav-item[onclick]')).find(b => (b.getAttribute('onclick') || '').indexOf("('" + id + "'") !== -1);
  }
  if (btn) btn.classList.add('active');

  const isChat = (id === 'centro-chat');
  document.body.classList.toggle('is-chat-active', isChat);
  const mainWrapper = document.querySelector('.main-wrapper');
  if (mainWrapper) mainWrapper.classList.toggle('is-chat-active', isChat);

  if (id === 'inicio') {
    animarKpisDashboard();
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// ═══════════════════════════════════════════════
// EFECTO COUNT-UP (SUBIDA DE NÚMEROS) EN KPIS
// ═══════════════════════════════════════════════
export function animarContadorKpi(el, durationMs) {
  if (!el) return;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  const rawText = (el.getAttribute('data-target-val') || el.textContent || '').trim();
  if (!rawText) return;

  if (!el.hasAttribute('data-target-val')) {
    el.setAttribute('data-target-val', rawText);
  }

  const isDecimal = rawText.includes('.');
  const decimals = isDecimal ? (rawText.split('.')[1] || '').length : 0;
  const targetVal = parseFloat(rawText);

  if (isNaN(targetVal) || targetVal <= 0) {
    el.textContent = rawText;
    return;
  }

  if (el._counterRaf) {
    cancelAnimationFrame(el._counterRaf);
  }

  el.style.fontVariantNumeric = 'tabular-nums';
  const duration = durationMs || 800;
  const startTime = performance.now();

  function tick(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = targetVal * eased;

    if (decimals > 0) {
      el.textContent = current.toFixed(decimals);
    } else {
      el.textContent = Math.round(current);
    }

    if (progress < 1) {
      el._counterRaf = requestAnimationFrame(tick);
    } else {
      el.textContent = rawText;
      el._counterRaf = null;
    }
  }

  el.textContent = decimals > 0 ? (0).toFixed(decimals) : '0';
  el._counterRaf = requestAnimationFrame(tick);
}

export function animarKpisDashboard() {
  const kpis = document.querySelectorAll('.dev-card .kpi-num, #devChartKpiVal');
  kpis.forEach(function (el) {
    animarContadorKpi(el);
  });
}

// ═══════════════════════════════════════════════
// FOCUS TRAP PARA MODALES
// ═══════════════════════════════════════════════
let _modalKeydownListener = null;

export function _setupModalFocusTrap(modal, onEscapeCallback) {
  _cleanupModalFocusTrap();

  _modalKeydownListener = function (e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      if (typeof onEscapeCallback === 'function') {
        onEscapeCallback();
      }
      return;
    }

    if (e.key === 'Tab') {
      const focusableSelector = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
      const focusables = Array.from(modal.querySelectorAll(focusableSelector))
        .filter(el => el.offsetWidth > 0 || el.offsetHeight > 0 || el === document.activeElement);

      if (focusables.length === 0) {
        e.preventDefault();
        return;
      }

      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first || !modal.contains(document.activeElement)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last || !modal.contains(document.activeElement)) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  };

  document.addEventListener('keydown', _modalKeydownListener);
}

export function _cleanupModalFocusTrap() {
  if (_modalKeydownListener) {
    document.removeEventListener('keydown', _modalKeydownListener);
    _modalKeydownListener = null;
  }
}

// ═══════════════════════════════════════════════
// CHAT SIDEBAR & RESIZER
// ═══════════════════════════════════════════════
export function toggleChatContextSidebarDev() {
  const chat = document.querySelector('#centro-chat .jd-chat');
  if (!chat) return;
  const isCollapsed = chat.classList.toggle('is-context-collapsed');
  const contextPanel = chat.querySelector('[data-chat-context]');
  if (contextPanel) {
    contextPanel.style.display = isCollapsed ? 'none' : 'flex';
  }
  try {
    localStorage.setItem('chat_context_collapsed_dev', isCollapsed ? '1' : '0');
  } catch (e) {}
  const btn = document.getElementById('chatContextToggleBtn');
  if (btn) {
    btn.title = isCollapsed ? 'Mostrar contexto del proyecto' : 'Ocultar contexto del proyecto';
    btn.innerHTML = '<i data-lucide="' + (isCollapsed ? 'panel-right-open' : 'panel-right-close') + '"></i>';
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }
}

export function initChatListResizerDev() {
  const chat = document.querySelector('#centro-chat .jd-chat');
  const resizer = document.getElementById('chatListResizer');
  const list = chat ? chat.querySelector('.jd-chat-list') : null;
  if (!chat || !resizer || !list) return;

  try {
    const savedCollapsed = localStorage.getItem('chat_context_collapsed_dev');
    const shouldCollapse = savedCollapsed !== '0';
    chat.classList.toggle('is-context-collapsed', shouldCollapse);
    const contextPanel = chat.querySelector('[data-chat-context]');
    if (contextPanel) {
      contextPanel.style.display = shouldCollapse ? 'none' : 'flex';
    }
    const btn = document.getElementById('chatContextToggleBtn');
    if (btn) {
      btn.title = shouldCollapse ? 'Mostrar contexto del proyecto' : 'Ocultar contexto del proyecto';
      btn.innerHTML = '<i data-lucide="' + (shouldCollapse ? 'panel-right-open' : 'panel-right-close') + '"></i>';
    }
  } catch (e) {}

  const MIN_WIDTH = 220;
  const MAX_WIDTH = 520;
  const STORAGE_KEY = 'dev_chat_list_width';

  function clampWidth(px) {
    const chatWidth = chat.getBoundingClientRect().width;
    const hasOpenContext = chat.classList.contains('has-context') && !chat.classList.contains('is-context-collapsed');
    const reservedRight = hasOpenContext ? 620 : 360;
    const dynamicMax = chatWidth > (MIN_WIDTH + reservedRight)
      ? Math.min(MAX_WIDTH, chatWidth - reservedRight)
      : MIN_WIDTH;
    return Math.round(Math.min(Math.max(px, MIN_WIDTH), Math.max(MIN_WIDTH, dynamicMax)));
  }

  try {
    const saved = parseInt(localStorage.getItem(STORAGE_KEY) || '', 10);
    if (Number.isFinite(saved) && saved >= MIN_WIDTH) {
      chat.style.setProperty(
        '--jd-chat-list-width',
        (chat.getBoundingClientRect().width > 0 ? clampWidth(saved) : Math.min(saved, MAX_WIDTH)) + 'px'
      );
    }
  } catch (e) {}

  resizer.addEventListener('pointerdown', function (e) {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    e.preventDefault();

    const startX = e.clientX;
    const startWidth = list.getBoundingClientRect().width;
    resizer.classList.add('is-resizing');
    document.body.classList.add('is-chat-resizing');

    function onMove(ev) {
      const nextWidth = clampWidth(startWidth + (ev.clientX - startX));
      chat.style.setProperty('--jd-chat-list-width', nextWidth + 'px');
    }

    function onUp() {
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerup', onUp);
      document.removeEventListener('pointercancel', onUp);
      resizer.classList.remove('is-resizing');
      document.body.classList.remove('is-chat-resizing');
      try {
        const finalWidth = Math.round(list.getBoundingClientRect().width);
        if (finalWidth >= MIN_WIDTH) {
          localStorage.setItem(STORAGE_KEY, String(finalWidth));
        }
      } catch (err) {}
    }

    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp);
    document.addEventListener('pointercancel', onUp);
  });
}

// ═══════════════════════════════════════════════
// DRAWER MÓVIL ACCESIBLE (SCRUM-411) & COLAPSO SIDEBAR
// ═══════════════════════════════════════════════
export function _syncDevDrawerAria(isOpen) {
  const toggleBtn = document.querySelector('.mobile-menu-toggle');
  if (!toggleBtn) return;
  toggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  toggleBtn.setAttribute('aria-label', isOpen ? 'Cerrar menú de navegación' : 'Abrir menú de navegación');
}

export function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const isOpen = sidebar ? sidebar.classList.toggle('is-open') : false;
  if (backdrop) backdrop.classList.toggle('is-open', isOpen);
  _syncDevDrawerAria(isOpen);
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
  _syncDevDrawerAria(false);
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
    localStorage.setItem('sidebar_collapsed_dev', isCollapsed ? '1' : '0');
  } catch (e) {}

  const btn = document.getElementById('sidebarCollapseBtn');
  if (btn) {
    btn.title = isCollapsed ? 'Expandir menú lateral' : 'Colapsar menú (solo iconos)';
    btn.innerHTML = '<i data-lucide="' + (isCollapsed ? 'panel-left-open' : 'panel-left-close') + '"></i>';
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// ═══════════════════════════════════════════════
// MENÚ DESPLEGABLE DE USUARIO (NAVBAR / TOPBAR)
// ═══════════════════════════════════════════════
export function toggleUserMenu(e) {
  if (e) e.stopPropagation();
  const menu = document.getElementById('userDropdownMenu');
  const btn = document.getElementById('userMenuBtn');
  if (!menu) return;

  const isOpen = menu.style.display === 'block' || menu.classList.contains('is-open');
  if (isOpen) {
    closeUserMenu();
  } else {
    // Cerrar popover de notificaciones si está abierto
    const notifPopover = document.getElementById('notifPopover');
    if (notifPopover) {
      notifPopover.classList.remove('is-open');
      const notifBtn = document.querySelector('.notif-btn');
      if (notifBtn) notifBtn.setAttribute('aria-expanded', 'false');
    }

    menu.style.display = 'block';
    menu.classList.add('is-open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }
}

export function closeUserMenu() {
  const menu = document.getElementById('userDropdownMenu');
  const btn = document.getElementById('userMenuBtn');
  if (menu) {
    menu.style.display = 'none';
    menu.classList.remove('is-open');
  }
  if (btn) {
    btn.setAttribute('aria-expanded', 'false');
  }
}

export function cerrarSesionConSpinner(event, el) {
  if (!el || !el.href) return;
  if (event) event.preventDefault();
  if (typeof window.closeUserMenu === 'function') window.closeUserMenu();
  const overlay = document.getElementById('logoutSpinnerOverlay');
  if (overlay) {
    overlay.style.display = 'flex';
    overlay.setAttribute('aria-hidden', 'false');
  }
  setTimeout(function () {
    window.location.href = el.href;
  }, 350);
}

// Exponer funciones en window para manejadores inline HTML y scripts hermanos
window.mostrarToast = mostrarToast;
window.toggleDevTheme = toggleDevTheme;
window.verSeccion = verSeccion;
window.switchContratosSubTab = switchContratosSubTab;
window.switchHistorialTab = switchHistorialTab;
window.animarContadorKpi = animarContadorKpi;
window.animarKpisDashboard = animarKpisDashboard;
window.toggleChatContextSidebarDev = toggleChatContextSidebarDev;
window.toggleSidebar = toggleSidebar;
window.closeSidebar = closeSidebar;
window.toggleSidebarCollapse = toggleSidebarCollapse;
window.toggleUserMenu = toggleUserMenu;
window.closeUserMenu = closeUserMenu;
window.cerrarSesionConSpinner = cerrarSesionConSpinner;

// ═══════════════════════════════════════════════
// INICIALIZACIÓN UI CORE
// ═══════════════════════════════════════════════
export function initUiCore() {
  // Tema inicial y sincronización con preferencia del sistema
  actualizarBotonTemaDev(devTemaActual());
  if (window.matchMedia) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemThemeChange = function (e) {
      let guardado = null;
      try { guardado = localStorage.getItem(DEV_THEME_STORAGE_KEY); } catch (err) {}
      if (guardado === 'light' || guardado === 'dark') return;
      const tema = e.matches ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', tema);
      actualizarBotonTemaDev(tema);
    };
    handleSystemThemeChange(mediaQuery);
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleSystemThemeChange);
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleSystemThemeChange);
    }
  }

  // Sincronización CSRF, KPIs y resizer del chat
  sincronizarCsrf();
  animarKpisDashboard();
  initChatListResizerDev();

  // Drawer móvil
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

  // Estado persistido del colapso de sidebar en desktop
  try {
    if (localStorage.getItem('sidebar_collapsed_dev') === '1' && window.innerWidth >= 769) {
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

  // Cerrar dropdown de usuario al hacer click afuera
  document.addEventListener('click', function (e) {
    const userWrapper = document.querySelector('.user-dropdown-wrapper');
    if (userWrapper && !userWrapper.contains(e.target)) {
      closeUserMenu();
    }
  });
}
