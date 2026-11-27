/**
 * ============================================================
 * JobDevs - Dashboard Empresa: UI Core, Theme, Navigation,
 * Animations, Popovers, Sidebar, Focus Trap & Shared Helpers
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

let _i18nCache = null;

function loadI18n() {
  if (_i18nCache !== null) return _i18nCache;
  try {
    const el = document.getElementById('empresa-i18n');
    _i18nCache = el ? JSON.parse(el.textContent) : {};
  } catch (e) {
    _i18nCache = {};
  }
  return _i18nCache;
}

export function t(key, fallback) {
  const dict = loadI18n();
  return (dict && dict[key]) || fallback;
}

export function csrfTokenActual() {
  const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (input && input.value) return input.value;
  const coincidencia = document.cookie.match(/csrftoken=([^;]+)/);
  return coincidencia ? coincidencia[1] : '';
}

export function escaparHtml(valor) {
  return String(valor === null || valor === undefined ? '' : valor)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export const EASE_OUT_EXPO = 'cubic-bezier(0.16, 1, 0.3, 1)';

export function prefersReducedMotion() {
  return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
}

// --- Toast Corporativo ---

export function mostrarToastCorp(mensaje, esError) {
  const toast = document.getElementById('corpToast');
  if (!toast) return;
  const span = toast.querySelector('span');
  if (span) span.textContent = mensaje;
  toast.classList.toggle('is-error', !!esError);
  toast.classList.add('show');
  setTimeout(function () {
    toast.classList.remove('show');
    toast.classList.remove('is-error');
  }, 3500);
}

// --- Modo Claro / Oscuro ---

const THEME_STORAGE_KEY = 'jobdevs-theme';

function obtenerTemaActual() {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
}

function actualizarBotonTema(tema) {
  const btn = document.getElementById('empresaThemeToggle');
  if (!btn) return;
  btn.setAttribute('aria-pressed', tema === 'dark' ? 'true' : 'false');
  btn.setAttribute('aria-label', tema === 'dark' ? t('cambiarTemaClaro', 'Cambiar a tema claro') : t('cambiarTemaOscuro', 'Cambiar a tema oscuro'));
  const label = document.getElementById('empresaThemeLabel');
  if (label) {
    label.textContent = tema === 'dark' ? t('temaOscuroLabel', 'Tema oscuro') : t('temaClaroLabel', 'Tema claro');
  }
}

export function toggleEmpresaTheme() {
  const temaActual = obtenerTemaActual();
  const nuevoTema = temaActual === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', nuevoTema);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, nuevoTema);
  } catch (e) {}
  actualizarBotonTema(nuevoTema);
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// --- Idioma & Cierre de Sesión ---

export function switchEmpresaIdioma(event, el) {
  if (!el || !el.href) return;
  if (event) event.preventDefault();
  el.classList.add('is-switching');
  const wrapper = document.querySelector('.main-wrapper');
  if (wrapper) wrapper.classList.add('is-lang-switching');
  const targetUrl = new URL(el.href, window.location.origin);
  const activeSec = document.querySelector('.seccion-v.activa, .section-v.activa');
  const currentHash = window.location.hash || (activeSec && activeSec.id ? '#' + activeSec.id : '');
  const params = new URLSearchParams(window.location.search);
  if (!params.get('section') && activeSec && activeSec.id) {
    params.set('section', activeSec.id);
  }
  const qs = params.toString();
  const finalHref = targetUrl.pathname + (qs ? '?' + qs : '') + currentHash;
  setTimeout(function () {
    closeUserMenu();
    window.location.href = finalHref;
  }, 110);
}

export function cerrarSesionConSpinner(event, el) {
  if (!el || !el.href) return;
  if (event) event.preventDefault();
  closeUserMenu();
  const overlay = document.getElementById('logoutSpinnerOverlay');
  if (overlay) {
    overlay.style.display = 'flex';
    overlay.setAttribute('aria-hidden', 'false');
  }
  setTimeout(function () {
    window.location.href = el.href;
  }, 350);
}

// --- Sidebar Móvil (Drawer) y Colapso ---

export function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (sidebar) sidebar.classList.toggle('is-open');
  if (backdrop) backdrop.classList.toggle('is-open');
}

export function closeSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (sidebar) sidebar.classList.remove('is-open');
  if (backdrop) backdrop.classList.remove('is-open');
}

export function toggleSidebarCollapse() {
  const sidebar = document.querySelector('.sidebar');
  if (!sidebar) return;
  const isCollapsed = sidebar.classList.toggle('is-collapsed');
  try {
    localStorage.setItem('sidebar_collapsed', isCollapsed ? '1' : '0');
  } catch (e) {}

  const btn = document.getElementById('sidebarCollapseBtn');
  if (btn) {
    btn.title = isCollapsed ? t('expandirSidebar', 'Expandir menú lateral') : t('colapsarSidebar', 'Colapsar menú (solo iconos)');
    btn.innerHTML = '<i data-lucide="' + (isCollapsed ? 'panel-left-open' : 'panel-left-close') + '"></i>';
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function toggleChatContextSidebar() {
  const chat = document.querySelector('#centro-chat .jd-chat');
  if (!chat) return;
  const isCollapsed = chat.classList.toggle('is-context-collapsed');
  try {
    localStorage.setItem('chat_context_collapsed', isCollapsed ? '1' : '0');
  } catch (e) {}

  const btn = document.getElementById('chatContextToggleBtn');
  if (btn) {
    btn.title = isCollapsed ? t('mostrarContextoProyecto', 'Mostrar contexto del proyecto') : t('ocultarContextoProyecto', 'Ocultar contexto del proyecto');
    btn.innerHTML = '<i data-lucide="' + (isCollapsed ? 'panel-right-open' : 'panel-right-close') + '"></i>';
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// --- Tab Switching & URL Persistence ---

let _initialTabReady = false;

export function ejecutarSwitchTabDOM(id, btn) {
  const sections = document.querySelectorAll('.seccion-v, .section-v');
  const navItems = document.querySelectorAll('.nav-item');

  sections.forEach(function (sec) {
    sec.classList.remove('activa', 'active');
  });

  navItems.forEach(function (item) {
    item.classList.remove('active');
  });

  const targetSection = document.getElementById(id);
  if (targetSection) {
    targetSection.classList.add('activa');
  }

  // Gestionar modo de pantalla completa para el chat (elimina paddings de carta)
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    if (id === 'centro-chat') {
      mainContent.classList.add('is-chat-active');
    } else {
      mainContent.classList.remove('is-chat-active');
    }
  }

  // Identificar botón activo
  if (!btn) {
    btn = Array.from(document.querySelectorAll('.nav-item')).find(function (el) {
      const onclickAttr = el.getAttribute('onclick') || '';
      const dataTarget = el.getAttribute('data-tab') || '';
      return onclickAttr.indexOf("'" + id + "'") !== -1 ||
             onclickAttr.indexOf('"' + id + '"') !== -1 ||
             dataTarget === id;
    });
  }

  if (btn) {
    btn.classList.add('active');
  }

  // Actualizar URL hash y section param de forma limpia sin saltos de scroll
  if (window.history && window.history.replaceState) {
    const url = new URL(window.location);
    url.hash = id;
    url.searchParams.set('section', id);
    window.history.replaceState(null, '', url);
  }

  // Cerrar sidebar en móviles tras seleccionar pestaña
  closeSidebar();

  if (targetSection) {
    animarSeccionCorp(targetSection);
  }
}

export function switchTab(id, btn) {
  if (!id) return;
  if (id === 'reputacion') id = 'inicio';
  if (id === 'historial-disputas') id = 'disputas';

  const targetSection = document.getElementById(id);
  const yaActiva = targetSection && targetSection.classList.contains('activa');

  if (
    _initialTabReady &&
    !yaActiva &&
    typeof document.startViewTransition === 'function' &&
    !prefersReducedMotion()
  ) {
    try {
      document.startViewTransition(function () {
        ejecutarSwitchTabDOM(id, btn);
      });
    } catch (e) {
      ejecutarSwitchTabDOM(id, btn);
    }
  } else {
    ejecutarSwitchTabDOM(id, btn);
  }
  _initialTabReady = true;
}

// --- Motor Nativo de Micro-Animaciones (WAAPI + rAF) ---

export function animarTextoNumericoCorp(el) {
  if (!el || prefersReducedMotion()) return;
  const raw = (el.textContent || '').trim();
  if (!raw) return;

  // Extraer el primer bloque numérico con separadores de miles/decimales
  const match = raw.match(/^([^0-9\-]*)(-?[0-9][0-9.,]*)(.*)$/);
  if (!match) return;

  const prefix = match[1];
  const numStr = match[2];
  const suffix = match[3];

  // Ignorar fechas o rangos como "1-2" o "2026"
  if (suffix.indexOf('/') === 0 && numStr.length <= 2 && suffix.indexOf('5.0') === -1) return;

  let clean = numStr;
  let sepMiles = '';
  let sepDec = '.';
  let decimals = 0;

  if (numStr.indexOf('.') !== -1 && numStr.indexOf(',') !== -1) {
    if (numStr.lastIndexOf(',') > numStr.lastIndexOf('.')) {
      sepMiles = '.';
      sepDec = ',';
      decimals = numStr.length - numStr.lastIndexOf(',') - 1;
      clean = numStr.replace(/\./g, '').replace(',', '.');
    } else {
      sepMiles = ',';
      sepDec = '.';
      decimals = numStr.length - numStr.lastIndexOf('.') - 1;
      clean = numStr.replace(/,/g, '');
    }
  } else if ((numStr.match(/\./g) || []).length > 1) {
    sepMiles = '.';
    clean = numStr.replace(/\./g, '');
  } else if ((numStr.match(/,/g) || []).length > 1) {
    sepMiles = ',';
    clean = numStr.replace(/,/g, '');
  } else if (numStr.indexOf('.') !== -1) {
    const afterDot = numStr.split('.')[1] || '';
    if (afterDot.length === 3 && raw.indexOf('$') !== -1) {
      sepMiles = '.';
      clean = numStr.replace(/\./g, '');
    } else {
      sepDec = '.';
      decimals = afterDot.length;
    }
  } else if (numStr.indexOf(',') !== -1) {
    const afterComma = numStr.split(',')[1] || '';
    if (afterComma.length === 3 && raw.indexOf('$') !== -1) {
      sepMiles = ',';
      clean = numStr.replace(/,/g, '');
    } else {
      sepDec = ',';
      decimals = afterComma.length;
      clean = numStr.replace(',', '.');
    }
  }

  const targetVal = parseFloat(clean);
  if (!isFinite(targetVal) || targetVal === 0) return;

  if (el._corpTickerRaf) {
    cancelAnimationFrame(el._corpTickerRaf);
  }

  el.style.fontVariantNumeric = 'tabular-nums';
  const duration = 460;
  const startTime = performance.now();

  function formatNum(val) {
    const fixed = val.toFixed(decimals);
    const parts = fixed.split('.');
    let intPart = parts[0];
    if (sepMiles) {
      intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, sepMiles);
    }
    return decimals > 0 ? intPart + sepDec + parts[1] : intPart;
  }

  function tick(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = targetVal * eased;
    el.textContent = prefix + formatNum(current) + suffix;
    if (progress < 1) {
      el._corpTickerRaf = requestAnimationFrame(tick);
    } else {
      el.textContent = raw;
      el._corpTickerRaf = null;
    }
  }

  el._corpTickerRaf = requestAnimationFrame(tick);
}

export function animarSeccionCorp(sectionEl) {
  if (!sectionEl || prefersReducedMotion()) return;

  // 1. Entrada escalonada rápida (stagger <= 150ms) en tarjetas visibles
  const cardSelector = [
    '.kpi-card-corp',
    '.command-section-card',
    '.command-financial-card',
    '.command-trust-card',
    '.offer-card-corp',
    '.dev-card-corp',
    '.contract-card-corp',
    '.ledger-metric-card',
    '.ledger-chart-card',
    '.distribution-card-corp',
    '.disputas-kpi-card',
    '.disputas-case-card',
    '.linkedin-profile-card',
    '.linkedin-content-card'
  ].join(', ');

  const cards = Array.prototype.filter.call(sectionEl.querySelectorAll(cardSelector), function (el) {
    return el.offsetParent !== null;
  });

  cards.forEach(function (card, idx) {
    if (typeof card.animate === 'function') {
      card.animate(
        [
          { opacity: 0, transform: 'translateY(8px)' },
          { opacity: 1, transform: 'translateY(0)' }
        ],
        {
          duration: 240,
          delay: Math.min(idx * 24, 150),
          easing: EASE_OUT_EXPO,
          fill: 'backwards'
        }
      );
    }
  });

  // 2. Contadores numéricos (tabular-nums)
  const numSelector = '.kpi-card-value, .ledger-metric-val, .financial-card-escrow-amount, .disputas-kpi-val, .stat-number';
  sectionEl.querySelectorAll(numSelector).forEach(function (numEl) {
    if (numEl.offsetParent !== null) {
      animarTextoNumericoCorp(numEl);
    }
  });

  // 3. Barras de progreso horizontales
  sectionEl.querySelectorAll('[role="progressbar"] > div, .distribution-bar-track > div, .rep-histo-fill').forEach(function (bar, idx) {
    if (bar.offsetParent !== null && typeof bar.animate === 'function') {
      bar.style.transformOrigin = 'left center';
      bar.animate(
        [
          { transform: 'scaleX(0)' },
          { transform: 'scaleX(1)' }
        ],
        {
          duration: 420,
          delay: Math.min(idx * 30, 120),
          easing: EASE_OUT_EXPO,
          fill: 'backwards'
        }
      );
    }
  });

  // 4. Trazado de curvas SVG en la sección activa (ej. Curva de Hitos o Ledger)
  sectionEl.querySelectorAll('svg path[stroke]:not([stroke="none"])').forEach(function (pathEl) {
    if (typeof pathEl.getTotalLength === 'function' && typeof pathEl.animate === 'function') {
      try {
        const len = pathEl.getTotalLength();
        if (len > 10) {
          pathEl.style.strokeDasharray = len + ' ' + len;
          pathEl.animate(
            [
              { strokeDashoffset: len },
              { strokeDashoffset: 0 }
            ],
            { duration: 500, easing: EASE_OUT_EXPO, fill: 'forwards' }
          );
        }
      } catch (err) {}
    }
  });
}

// --- Notificaciones Popover & Limpieza ---

export function toggleNotifPopover(event) {
  if (event) event.stopPropagation();
  const popover = document.getElementById('notifPopover');
  const btn = document.querySelector('.notif-btn');
  if (popover) {
    const open = popover.classList.toggle('is-open');
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
}

export function closeNotifPopover() {
  const popover = document.getElementById('notifPopover');
  const btn = document.querySelector('.notif-btn');
  if (popover) {
    popover.classList.remove('is-open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }
}

// --- Menú Desplegable de Usuario (Topbar) ---

export function toggleUserMenu(e) {
  if (e) e.stopPropagation();
  const menu = document.getElementById('userDropdownMenu');
  const btn = document.getElementById('userMenuBtn');
  if (!menu) return;

  const isOpen = menu.style.display === 'block' || menu.classList.contains('is-open');
  if (isOpen) {
    closeUserMenu();
  } else {
    closeNotifPopover();
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

export function limpiarNotificacionesAjax(event, form) {
  if (event) event.preventDefault();
  const btn = form.querySelector('button[type="submit"]');
  const oldHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = t('limpiando', 'Limpiando...');
  }

  const formData = new FormData(form);
  fetch(form.action, {
    method: 'POST',
    body: formData,
    headers: {
      'Accept': 'application/json',
      'X-CSRFToken': csrfTokenActual(),
    },
  })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      // Vaciar la lista del popover
      const popoverBody = document.getElementById('notifPopoverBody');
      if (popoverBody) {
        popoverBody.innerHTML = '<div class="notif-popover-empty"><i data-lucide="bell-off"></i><span>' + t('sinNotificaciones', 'No hay notificaciones') + '</span></div>';
      }
      // Ocultar badge de la campana
      const notifBadge = document.querySelector('.notif-btn .notif-badge');
      if (notifBadge) {
        notifBadge.style.display = 'none';
      }
      // Ocultar botón de limpiar
      if (form) form.style.display = 'none';

      // Mostrar toast
      const toast = document.getElementById('corpToast');
      if (toast) {
        const toastSpan = toast.querySelector('span');
        if (toastSpan) toastSpan.textContent = data.message || t('notifEliminadas', 'Notificaciones eliminadas');
        toast.classList.add('show');
        setTimeout(function () { toast.classList.remove('show'); }, 3000);
      }

      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    })
    .catch(function () {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = oldHtml;
      }
      mostrarToastCorp(t('errorLimpiarNotif', 'Error al limpiar las notificaciones.'), true);
    });
}

// --- Chat List Resizer ---

function initChatListResizer() {
  const chat = document.querySelector('#centro-chat .jd-chat');
  const resizer = document.getElementById('chatListResizer');
  const list = chat ? chat.querySelector('.jd-chat-list') : null;
  if (!chat || !resizer || !list) return;

  // Por defecto el panel de contexto arranca cerrado; solo se abre si el usuario lo dejó abierto
  try {
    const savedCollapsed = localStorage.getItem('chat_context_collapsed');
    const shouldCollapse = savedCollapsed !== '0';
    chat.classList.toggle('is-context-collapsed', shouldCollapse);
    const btn = document.getElementById('chatContextToggleBtn');
    if (btn) {
      btn.title = shouldCollapse ? t('mostrarContextoProyecto', 'Mostrar contexto del proyecto') : t('ocultarContextoProyecto', 'Ocultar contexto del proyecto');
      btn.innerHTML = '<i data-lucide="' + (shouldCollapse ? 'panel-right-open' : 'panel-right-close') + '"></i>';
    }
  } catch (e) {}

  const MIN_WIDTH = 220;
  const MAX_WIDTH = 520;
  const STORAGE_KEY = 'empresa_chat_list_width';

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
      chat.style.setProperty('--jd-chat-list-width', clampWidth(saved) + 'px');
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

// --- Dialog / Drawer Focus Trap & Focus Restoration ---

function initDialogFocusTrap() {
  const focusRestoreMap = new WeakMap();
  let lastUserTrigger = null;
  const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  document.addEventListener('pointerdown', function (e) {
    if (e.target && !e.target.closest('[role="dialog"].open, [role="dialog"].is-open')) {
      const cand = e.target.closest('button, a, [role="button"], [tabindex]:not([tabindex="-1"])');
      lastUserTrigger = cand || null;
    }
  }, true);

  document.addEventListener('keydown', function (e) {
    if ((e.key === 'Enter' || e.key === ' ') && document.activeElement && !document.activeElement.closest('[role="dialog"].open, [role="dialog"].is-open')) {
      lastUserTrigger = document.activeElement;
    }
  }, true);

  function isDialogOpen(el) {
    return el.classList.contains('open') || el.classList.contains('is-open');
  }

  function getFocusable(container) {
    return Array.prototype.filter.call(container.querySelectorAll(FOCUSABLE), function (el) {
      return el.offsetParent !== null;
    });
  }

  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      const target = m.target;
      if (!target || !target.matches || !target.matches('[role="dialog"]')) return;
      if (isDialogOpen(target)) {
        if (!focusRestoreMap.has(target)) {
          const trigger = lastUserTrigger || (document.activeElement && !target.contains(document.activeElement) ? document.activeElement : null);
          lastUserTrigger = null;
          if (trigger) focusRestoreMap.set(target, trigger);
        }
        const items = getFocusable(target);
        if (items.length && !target.contains(document.activeElement)) {
          items[0].focus();
        }
      } else if (focusRestoreMap.has(target)) {
        const prev = focusRestoreMap.get(target);
        focusRestoreMap.delete(target);
        if (prev && typeof prev.focus === 'function' && prev.isConnected) {
          prev.focus();
        }
      }
    });
  });

  document.querySelectorAll('[role="dialog"].modal-overlay, [role="dialog"].drawer-overlay').forEach(function (dlg) {
    observer.observe(dlg, { attributes: true, attributeFilter: ['class'] });
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab') return;
    const allOpen = document.querySelectorAll('[role="dialog"].open, [role="dialog"].is-open');
    const activeDialog = allOpen.length ? allOpen[allOpen.length - 1] : null;
    if (!activeDialog) return;
    const items = getFocusable(activeDialog);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && (document.activeElement === first || !activeDialog.contains(document.activeElement))) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });
}

// --- Global Window Contracts ---

window.toggleEmpresaTheme = toggleEmpresaTheme;
window.switchEmpresaIdioma = switchEmpresaIdioma;
window.cerrarSesionConSpinner = cerrarSesionConSpinner;
window.switchTab = switchTab;
window.animarTextoNumericoCorp = animarTextoNumericoCorp;
window.animarSeccionCorp = animarSeccionCorp;
window.toggleNotifPopover = toggleNotifPopover;
window.closeNotifPopover = closeNotifPopover;
window.toggleUserMenu = toggleUserMenu;
window.closeUserMenu = closeUserMenu;
window.limpiarNotificacionesAjax = limpiarNotificacionesAjax;
window.toggleSidebar = toggleSidebar;
window.closeSidebar = closeSidebar;
window.toggleSidebarCollapse = toggleSidebarCollapse;
window.toggleChatContextSidebar = toggleChatContextSidebar;
window.mostrarToastCorp = mostrarToastCorp;

// --- DOM Initialization ---

export function initUiCore() {
  initChatListResizer();
  initDialogFocusTrap();

  // Backdrop de sidebar móvil
  const backdrop = document.getElementById('sidebarBackdrop');
  if (backdrop) {
    backdrop.addEventListener('click', closeSidebar);
  }
  document.querySelectorAll('.sidebar .nav-item').forEach(function (item) {
    item.addEventListener('click', function () {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });

  // Cerrar popovers y menús contextuales al hacer click fuera
  document.addEventListener('click', function (e) {
    const wrapper = document.querySelector('.notif-wrapper');
    if (wrapper && !wrapper.contains(e.target)) {
      closeNotifPopover();
    }

    const userWrapper = document.querySelector('.user-dropdown-wrapper');
    if (userWrapper && !userWrapper.contains(e.target)) {
      closeUserMenu();
    }

    document.querySelectorAll('.dev-more-actions[open]').forEach(function (det) {
      if (!det.contains(e.target)) det.removeAttribute('open');
    });
  });

  // Restaurar estado de colapso del sidebar en desktop
  try {
    if (localStorage.getItem('sidebar_collapsed') === '1' && window.innerWidth > 768) {
      const sidebar = document.querySelector('.sidebar');
      if (sidebar) {
        sidebar.classList.add('is-collapsed');
        const btn = document.getElementById('sidebarCollapseBtn');
        if (btn) {
          btn.title = t('expandirSidebar', 'Expandir menú lateral');
          const icon = btn.querySelector('[data-lucide], .lucide');
          if (icon) icon.setAttribute('data-lucide', 'panel-left-open');
        }
      }
    }
  } catch (e) {}

  // Inicializar estado del botón de tema claro/oscuro
  actualizarBotonTema(obtenerTemaActual());

  // Escuchar cambios de preferencia del sistema
  if (window.matchMedia) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemThemeChange = function (e) {
      let guardado = null;
      try { guardado = localStorage.getItem(THEME_STORAGE_KEY); } catch (err) {}
      if (guardado === 'light' || guardado === 'dark') return;
      const tema = e.matches ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', tema);
      actualizarBotonTema(tema);
    };
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleSystemThemeChange);
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleSystemThemeChange);
    }
  }

  // Animación de segmentos de dona y leyenda al desplegar details en Inicio
  document.querySelectorAll('details.command-collapse-corp').forEach(function (det) {
    det.addEventListener('toggle', function () {
      if (!det.open || prefersReducedMotion()) return;
      det.querySelectorAll('.donut-segment-slice').forEach(function (slice, idx) {
        const targetDash = slice.getAttribute('stroke-dasharray');
        if (targetDash && typeof slice.animate === 'function') {
          slice.animate(
            [
              { strokeDasharray: '0 238.76', opacity: 0.3 },
              { strokeDasharray: targetDash, opacity: 1 }
            ],
            {
              duration: 460,
              delay: idx * 45,
              easing: EASE_OUT_EXPO,
              fill: 'backwards'
            }
          );
        }
      });
      det.querySelectorAll('.donut-legend-item').forEach(function (item, idx) {
        if (typeof item.animate === 'function') {
          item.animate(
            [
              { opacity: 0, transform: 'translateX(-6px)' },
              { opacity: 1, transform: 'translateX(0)' }
            ],
            {
              duration: 240,
              delay: Math.min(idx * 30, 150),
              easing: EASE_OUT_EXPO,
              fill: 'backwards'
            }
          );
        }
      });
    });
  });
}
