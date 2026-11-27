/**
 * ============================================================
 * JobDevs - Dashboard Empresa: UI Core Barrel
 * Re-exports utilities, navigation & animations, attaches
 * global window.* contracts, and initializes UI core listeners.
 * ============================================================
 */

import {
  onReady,
  loadI18n,
  t,
  csrfTokenActual,
  escaparHtml,
  EASE_OUT_EXPO,
  prefersReducedMotion,
  mostrarToastCorp,
  THEME_STORAGE_KEY,
  obtenerTemaActual,
  actualizarBotonTema,
  toggleEmpresaTheme,
  switchEmpresaIdioma,
  cerrarSesionConSpinner,
} from './ui_utils.js';

import {
  toggleSidebar,
  closeSidebar,
  toggleSidebarCollapse,
  toggleChatContextSidebar,
  ejecutarSwitchTabDOM,
  switchTab,
  toggleNotifPopover,
  closeNotifPopover,
  toggleUserMenu,
  closeUserMenu,
  limpiarNotificacionesAjax,
} from './ui_navigation.js';

import {
  animarTextoNumericoCorp,
  animarSeccionCorp,
  initChatListResizer,
  initDialogFocusTrap,
} from './ui_animations.js';

export {
  onReady,
  loadI18n,
  t,
  csrfTokenActual,
  escaparHtml,
  EASE_OUT_EXPO,
  prefersReducedMotion,
  mostrarToastCorp,
  obtenerTemaActual,
  actualizarBotonTema,
  toggleEmpresaTheme,
  switchEmpresaIdioma,
  cerrarSesionConSpinner,
  toggleSidebar,
  closeSidebar,
  toggleSidebarCollapse,
  toggleChatContextSidebar,
  ejecutarSwitchTabDOM,
  switchTab,
  toggleNotifPopover,
  closeNotifPopover,
  toggleUserMenu,
  closeUserMenu,
  limpiarNotificacionesAjax,
  animarTextoNumericoCorp,
  animarSeccionCorp,
  initChatListResizer,
  initDialogFocusTrap,
};

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
