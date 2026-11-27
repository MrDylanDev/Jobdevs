/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Sidebar, Tabs, Notifications
 * Popover & User Menu Navigation
 * ============================================================
 */

import { t, csrfTokenActual, prefersReducedMotion, mostrarToastCorp } from './ui_utils.js';
import { animarSeccionCorp } from './ui_animations.js';

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
