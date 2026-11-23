/**
 * Lógica específica para el Dashboard de Desarrollador
 * (Manejado por Django y tabs.js)
 */

document.addEventListener("DOMContentLoaded", function () {
    // Inicialización específica si fuera necesaria
});

// ═══════════════════════════════════════════════
// MODO CLARO / OSCURO (comparte preferencia con la landing)
// ═══════════════════════════════════════════════
var DEV_THEME_STORAGE_KEY = 'jobdevs-theme';

function devTemaActual() {
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
}

function actualizarBotonTemaDev(tema) {
  var btn = document.getElementById('devThemeToggle');
  if (btn) {
    btn.setAttribute('aria-pressed', tema === 'light' ? 'true' : 'false');
    btn.setAttribute('aria-label', 'Cambiar entre tema oscuro y claro');
    btn.title = tema === 'light' ? 'Cambiar a tema oscuro' : 'Cambiar a tema claro';
  }
  var dropdownLabel = document.getElementById('devDropdownThemeLabel');
  if (dropdownLabel) {
    dropdownLabel.textContent = tema === 'light' ? 'Tema Oscuro' : 'Tema Claro';
  }
}

function toggleDevTheme() {
  var nuevoTema = devTemaActual() === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', nuevoTema);
  try {
    localStorage.setItem(DEV_THEME_STORAGE_KEY, nuevoTema);
  } catch (e) {}
  actualizarBotonTemaDev(nuevoTema);
}

document.addEventListener('DOMContentLoaded', function () {
  actualizarBotonTemaDev(devTemaActual());

  // Si el usuario no ha elegido manualmente, seguir la preferencia del sistema.
  if (window.matchMedia) {
    var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    var handleSystemThemeChange = function (e) {
      var guardado = null;
      try { guardado = localStorage.getItem(DEV_THEME_STORAGE_KEY); } catch (err) {}
      if (guardado === 'light' || guardado === 'dark') return;
      var tema = e.matches ? 'dark' : 'light';
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
});

// Función para previsualizar foto de perfil antes de subir (opcional)
function previewFoto(event) {
    const reader = new FileReader();
    reader.onload = function() {
        const output = document.getElementById('fotoPerfil');
        output.src = reader.result;
    };
    reader.readAsDataURL(event.target.files[0]);
}

function verSeccion(id, btn) {
  if (id === 'perfil') {
    abrirModalPerfilDev();
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
function animarContadorKpi(el, durationMs) {
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

function animarKpisDashboard() {
  const kpis = document.querySelectorAll('.dev-card .kpi-num, #devChartKpiVal');
  kpis.forEach(function (el) {
    animarContadorKpi(el);
  });
}

window.animarContadorKpi = animarContadorKpi;
window.animarKpisDashboard = animarKpisDashboard;
document.addEventListener('DOMContentLoaded', function () {
  animarKpisDashboard();
});

window.abrirModalNuevaDisputaDev = function () {
  const m = document.getElementById('modalNuevaDisputa');
  if (m) {
    m.hidden = false;
    m.style.display = 'flex';
    m.classList.add('is-open');
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }
};

window.cerrarModalNuevaDisputaDev = function () {
  const m = document.getElementById('modalNuevaDisputa');
  if (m) {
    m.hidden = true;
    m.style.display = 'none';
    m.classList.remove('is-open');
  }
};
window.abrirModalDisputa = window.abrirModalNuevaDisputaDev;
window.cerrarModalDisputa = window.cerrarModalNuevaDisputaDev;
let _modalKeydownListener = null;

function _setupModalFocusTrap(modal, onEscapeCallback) {
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

function _cleanupModalFocusTrap() {
  if (_modalKeydownListener) {
    document.removeEventListener('keydown', _modalKeydownListener);
    _modalKeydownListener = null;
  }
}

window.abrirModalPerfilDev = function () {
  const modal = document.getElementById('modalEditarPerfilDev');
  if (!modal) return;
  _perfilModalLastFocus = document.activeElement;
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
  const closeBtn = modal.querySelector('.jdm-close, input:not([type="hidden"]), button');
  if (closeBtn) closeBtn.focus();
  _setupModalFocusTrap(modal, window.cerrarModalPerfilDev);
};

window.cerrarModalPerfilDev = function () {
  const modal = document.getElementById('modalEditarPerfilDev');
  if (!modal || modal.hidden) return;
  _cleanupModalFocusTrap();
  modal.hidden = true;
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  if (_perfilModalLastFocus && typeof _perfilModalLastFocus.focus === 'function') {
    _perfilModalLastFocus.focus();
  }
  _perfilModalLastFocus = null;
};

// Manejo AJAX del guardado de perfil para evitar recarga de pantalla
document.addEventListener('DOMContentLoaded', function () {
  const formPerfil = document.getElementById('formPerfilDev');
  if (!formPerfil) return;

  formPerfil.addEventListener('submit', async function (e) {
    e.preventDefault();
    const btnSubmit = document.getElementById('btnGuardarPerfilDev');
    const textoOriginal = btnSubmit ? btnSubmit.innerHTML : '';

    // Limpiar errores previos
    formPerfil.querySelectorAll('.jd-error-dinamico').forEach(el => el.remove());
    formPerfil.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = '<span class="jd-spinner-sm" style="display:inline-block; width:14px; height:14px; border:2px solid currentColor; border-right-color:transparent; border-radius:50%; animation:spin 0.6s linear infinite; vertical-align:middle; margin-right:6px;"></span> Guardando…';
    }

    try {
      const formData = new FormData(formPerfil);
      const response = await fetch(formPerfil.action || window.location.href, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json'
        },
        body: formData
      });

      const data = await response.json().catch(() => null);

      if (response.ok && data && data.ok) {
        cerrarModalPerfilDev();
        if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
          window.JobDevsToast.mostrar({
            tipo: 'success',
            mensaje: data.mensaje || 'Perfil actualizado con éxito',
            duracion: 3500
          });
        }
        // Actualizar visualmente avatar en todos los componentes del dashboard
        if (data.foto_url) {
          const freshUrl = data.foto_url.includes('?') ? (data.foto_url + '&t=' + Date.now()) : (data.foto_url + '?t=' + Date.now());
          const imgHtml = '<img src="' + freshUrl + '" alt="Foto de perfil">';

          // 1. Avatar en el modal de perfil
          const avatarModal = document.getElementById('perfilModalAvatar');
          if (avatarModal) avatarModal.innerHTML = imgHtml;

          // 2. Avatar en el chip de usuario (barra superior)
          const chipAvatar = document.getElementById('devUserChipAvatar') || document.querySelector('.user-chip .user-avatar');
          if (chipAvatar) chipAvatar.innerHTML = imgHtml;

          // 3. Avatar en la cabecera del menú desplegable
          const dropdownAvatar = document.getElementById('devUserDropdownAvatar') || document.querySelector('.user-dropdown-header .user-dropdown-avatar');
          if (dropdownAvatar) dropdownAvatar.innerHTML = imgHtml;
        }

        if (data.nombre) {
          const chipName = document.getElementById('devUserChipName') || document.querySelector('.user-chip .user-name');
          if (chipName) chipName.textContent = data.nombre;

          const dropdownName = document.getElementById('devUserDropdownName') || document.querySelector('.user-dropdown-meta .user-dropdown-name');
          if (dropdownName) dropdownName.textContent = data.nombre;

          const modalName = document.querySelector('.perfil-hero-details .perfil-hero-name-row strong');
          if (modalName) modalName.textContent = data.nombre;
        }
      } else if (data && data.errores) {
        for (const [campo, errs] of Object.entries(data.errores)) {
          const input = formPerfil.querySelector('[name="' + campo + '"]');
          if (input) {
            input.classList.add('is-invalid');
            const parentField = input.closest('.jd-field') || input.parentElement;
            const errDiv = document.createElement('div');
            errDiv.className = 'jd-error jd-error-dinamico';
            errDiv.textContent = Array.isArray(errs) ? errs.join(', ') : String(errs);
            parentField.appendChild(errDiv);
          }
        }
        if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
          window.JobDevsToast.mostrar({
            tipo: 'error',
            mensaje: data.mensaje || 'Por favor revisa los errores en el formulario',
            duracion: 4000
          });
        }
      } else {
        throw new Error('Respuesta inválida');
      }
    } catch (err) {
      if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
        window.JobDevsToast.mostrar({
          tipo: 'error',
          mensaje: 'Error de conexión al guardar el perfil. Intenta nuevamente.',
          duracion: 4000
        });
      }
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = textoOriginal;
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      }
    }
  });
});

// ═══════════════════════════════════════════════
// FILTRADO DE DISPUTAS EN TIEMPO REAL (SIN RECARGA)
// ═══════════════════════════════════════════════
window.filtrarDisputasEnTiempoReal = function (event, estado, btn) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  const parent = btn ? btn.closest('.disputas-filtros') : null;
  if (parent && btn) {
    parent.querySelectorAll('.btn').forEach(function (b) {
      b.classList.remove('btn-primary');
      b.classList.add('btn-secondary');
    });
    btn.classList.add('btn-primary');
    btn.classList.remove('btn-secondary');
  }

  const serverFiltradas = document.querySelector('[data-testid="disputas-filtradas"]');
  if (serverFiltradas) {
    serverFiltradas.style.display = 'none';
  }

  const cardActivas = document.getElementById('cardDisputasActivas');
  const cardResueltas = document.getElementById('cardDisputasResueltas');
  const emptyMsg = document.getElementById('disputasClienteVacio');

  let totalVisibles = 0;
  let activasVisibles = 0;
  let resueltasVisibles = 0;

  const rows = document.querySelectorAll('.disputa-row-item');
  rows.forEach(function (r) {
    const rowEstado = r.getAttribute('data-disputa-row-estado') || '';
    const match = (estado === 'todos' || !estado || rowEstado === estado);
    r.style.display = match ? '' : 'none';
    if (match) {
      totalVisibles++;
      if (rowEstado === 'abierta' || rowEstado === 'en_mediacion') activasVisibles++;
      if (rowEstado === 'resuelta' || rowEstado === 'cancelada') resueltasVisibles++;
    }
  });

  if (cardActivas) {
    cardActivas.style.display = (estado === 'todos' || activasVisibles > 0) ? '' : 'none';
  }
  if (cardResueltas) {
    cardResueltas.style.display = (estado === 'todos' || resueltasVisibles > 0) ? '' : 'none';
  }
  if (emptyMsg) {
    emptyMsg.style.display = (estado !== 'todos' && totalVisibles === 0) ? 'block' : 'none';
  }

  if (window.history && window.history.replaceState) {
    const url = new URL(window.location);
    url.searchParams.set('seccion', 'disputas');
    if (estado && estado !== 'todos') {
      url.searchParams.set('estado', estado);
    } else {
      url.searchParams.delete('estado');
    }
    window.history.replaceState(null, '', url);
  }

  return false;
};

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const modal = document.getElementById('modalEditarPerfilDev');
    if (modal && !modal.hidden) {
      cerrarModalPerfilDev();
    }
  }
});

window.toggleChatContextSidebarDev = function () {
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
};

window.switchContratosSubTab = function (tabId, btn) {
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
};

window.switchHistorialTab = function (tabId, btn) {
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
};

window.abrirModalCancelacionDev = function () {
  const modal = document.getElementById('modalCancelacionDev');
  if (!modal) return;
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
  const focusTarget = modal.querySelector('select, button, [tabindex]:not([tabindex="-1"])');
  if (focusTarget) focusTarget.focus();
  _setupModalFocusTrap(modal, window.cerrarModalCancelacionDev);
};

window.cerrarModalCancelacionDev = function () {
  const modal = document.getElementById('modalCancelacionDev');
  if (!modal) return;
  _cleanupModalFocusTrap();
  modal.hidden = true;
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
};

window.actualizarActionCancelacion = function (selectEl) {
  const form = document.getElementById('formProponerCancelacionDev');
  if (form && selectEl && selectEl.value) {
    form.action = '/contrataciones/cancelar/' + selectEl.value + '/';
  }
};

function initChatListResizerDev() {
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

// ═══════════════════════════════════════════════
// FILTRADO DINÁMICO: Explorar Proyectos (Dev)
// ═══════════════════════════════════════════════
function filterDevExplore() {
  const searchInput = document.getElementById('devExploreSearch');
  const catSelect = document.getElementById('devExploreCategory');
  const prioSelect = document.getElementById('devExplorePriority');
  if (!searchInput) return;

  const q = (searchInput.value || '').toLowerCase().trim();
  const cat = (catSelect ? catSelect.value : '').toLowerCase().trim();
  const prio = (prioSelect ? prioSelect.value : '').toLowerCase().trim();

  const cards = document.querySelectorAll('.dev-explore-card');
  let visibleCount = 0;

  cards.forEach(card => {
    const titulo = card.getAttribute('data-titulo') || '';
    const desc = card.getAttribute('data-desc') || '';
    const empresa = card.getAttribute('data-empresa') || '';
    const tipo = card.getAttribute('data-tipo') || '';
    const prioridad = card.getAttribute('data-prioridad') || '';

    const matchesQ = !q || titulo.includes(q) || desc.includes(q) || empresa.includes(q);
    const matchesCat = !cat || tipo === cat;
    const matchesPrio = !prio || prioridad === prio;

    if (matchesQ && matchesCat && matchesPrio) {
      card.style.display = 'flex';
      visibleCount++;
    } else {
      card.style.display = 'none';
    }
  });

  const noMatches = document.getElementById('devExploreNoMatches');
  if (noMatches) {
    noMatches.style.display = (visibleCount === 0 && cards.length > 0) ? 'block' : 'none';
  }
  const badge = document.getElementById('devExploreCountBadge');
  if (badge) {
    badge.textContent = visibleCount + ' DISPONIBLES';
  }
}

function resetDevExploreFilters() {
  const searchInput = document.getElementById('devExploreSearch');
  const catSelect = document.getElementById('devExploreCategory');
  const prioSelect = document.getElementById('devExplorePriority');
  if (searchInput) searchInput.value = '';
  if (catSelect) catSelect.value = '';
  if (prioSelect) prioSelect.value = '';
  filterDevExplore();
}

document.addEventListener("DOMContentLoaded", function () {
  const search = document.getElementById('devExploreSearch');
  const cat = document.getElementById('devExploreCategory');
  const prio = document.getElementById('devExplorePriority');
  if (search) search.addEventListener('input', filterDevExplore);
  if (cat) cat.addEventListener('change', filterDevExplore);
  if (prio) prio.addEventListener('change', filterDevExplore);

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});

window.addEventListener('load', function() {
  const s = new URLSearchParams(window.location.search).get('section');
  if (s) verSeccion(s);
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});

// ═══════════════════════════════════════════════
// SECCIÓN INICIAL DESDE QUERY (?seccion=)
// ═══════════════════════════════════════════════
// El token oculto puede quedar desfasado si la cookie csrftoken rotó
// (login en otra pestaña, reinicio con otra SECRET_KEY o botón atrás).
// Sincronizarlo evita el 403 "CSRF token from POST incorrect".
function leerCookie(nombre) {
  const par = document.cookie
    .split('; ')
    .find((item) => item.startsWith(nombre + '='));
  return par ? decodeURIComponent(par.slice(nombre.length + 1)) : '';
}

function sincronizarCsrf(scope) {
  const token = leerCookie('csrftoken');
  if (!token) return;
  (scope || document).querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach((input) => {
    input.value = token;
  });
}

document.addEventListener('DOMContentLoaded', () => {
  sincronizarCsrf();
  initChatListResizerDev();
  const params = new URLSearchParams(window.location.search);
  const hash = (window.location.hash || '').replace('#', '');
  const inicial = document.body.getAttribute('data-seccion-inicial') || '';
  const seccion = params.get('seccion') || (inicial && inicial !== 'inicio' ? inicial : '') || (hash && document.getElementById(hash) ? hash : '');
  if (seccion === 'perfil') {
    abrirModalPerfilDev();
  } else if (seccion && document.getElementById(seccion)) {
    verSeccion(seccion, null);
  } else {
    const activa = document.querySelector('.seccion-v.activa');
    if (activa && activa.id === 'centro-chat') {
      document.body.classList.add('is-chat-active');
      const mw = document.querySelector('.main-wrapper');
      if (mw) mw.classList.add('is-chat-active');
    }
  }
  if (params.get('verificacion') === '1') {
    abrirVerificacion();
  }

  const inputFotoPerfil = document.getElementById('id_foto_perfil');
  const avatarContainer = document.getElementById('perfilModalAvatar');
  if (inputFotoPerfil && avatarContainer) {
    inputFotoPerfil.addEventListener('change', () => {
      const file = inputFotoPerfil.files && inputFotoPerfil.files[0];
      if (!file || !file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = () => {
        avatarContainer.classList.remove('is-previewing');
        avatarContainer.innerHTML = '';
        const img = document.createElement('img');
        img.src = reader.result;
        img.alt = 'Vista previa de foto de perfil';
        avatarContainer.appendChild(img);
        void avatarContainer.offsetWidth;
        avatarContainer.classList.add('is-previewing');
      };
      reader.readAsDataURL(file);
    });
  }

  const formPerfilDev = document.getElementById('formPerfilDev');
  const btnGuardarPerfilDev = document.getElementById('btnGuardarPerfilDev');
  if (formPerfilDev && btnGuardarPerfilDev) {
    formPerfilDev.addEventListener('submit', () => {
      if (btnGuardarPerfilDev.disabled) return;
      btnGuardarPerfilDev.disabled = true;
      btnGuardarPerfilDev.setAttribute('aria-busy', 'true');
      btnGuardarPerfilDev.innerHTML = '<i data-lucide="loader-2" class="jd-spin"></i><span>Guardando...</span>';
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    });
  }
});

// ═══════════════════════════════════════════════
// MODAL FLOTANTE: VERIFICACIÓN SENA
// ═══════════════════════════════════════════════
function abrirVerificacion() {
  const modal = document.getElementById('modalVerificacion');
  if (!modal) return;
  sincronizarCsrf(modal);
  modal.classList.add('is-open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  const focusTarget = modal.querySelector('.jd-tab.active, .jd-input, .jd-modal-close');
  if (focusTarget) focusTarget.focus({ preventScroll: true });
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
  _setupModalFocusTrap(modal, cerrarVerificacion);
}

function cerrarVerificacion() {
  const modal = document.getElementById('modalVerificacion');
  if (!modal) return;
  _cleanupModalFocusTrap();
  modal.classList.remove('is-open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    cerrarVerificacion();
    cerrarPostulacion();
  }
});

document.addEventListener('click', (event) => {
  if (event.target.closest('[data-cerrar-verificacion]')) {
    cerrarVerificacion();
  }
});

// Pestañas del modal
document.addEventListener('click', (event) => {
  const tab = event.target.closest('[data-verificacion-tab]');
  if (!tab) return;
  const modal = tab.closest('#modalVerificacion');
  if (!modal) return;
  const id = tab.getAttribute('data-verificacion-tab');
  modal.querySelectorAll('[data-verificacion-tab]').forEach((t) => {
    const activo = t === tab;
    t.classList.toggle('active', activo);
    t.setAttribute('aria-selected', activo ? 'true' : 'false');
  });
  modal.querySelectorAll('[data-verificacion-panel]').forEach((p) => {
    p.classList.toggle('active', p.getAttribute('data-verificacion-panel') === id);
  });
});

// Envío AJAX del formulario de verificación
function limpiarErroresVerificacion(form) {
  form.querySelectorAll('.jd-error').forEach((el) => { el.textContent = ''; });
  form.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
  const feedback = document.querySelector('[data-verificacion-feedback]');
  if (feedback) {
    feedback.hidden = true;
    feedback.classList.remove('is-error');
    feedback.textContent = '';
  }
}

function mostrarFeedbackVerificacion(mensaje, esError) {
  const feedback = document.querySelector('[data-verificacion-feedback]');
  if (!feedback) return;
  feedback.textContent = mensaje || '';
  feedback.hidden = !mensaje;
  feedback.classList.toggle('is-error', !!esError);
}

document.addEventListener('submit', async (event) => {
  const form = event.target.closest('[data-verificacion-form]');
  if (!form) return;
  event.preventDefault();
  limpiarErroresVerificacion(form);
  sincronizarCsrf(form);

  const submit = form.querySelector('button[type="submit"]');
  const textoOriginal = submit ? submit.innerHTML : '';
  if (submit) {
    submit.disabled = true;
    submit.innerHTML = '<i data-lucide="loader-2"></i> Enviando...';
  }

  try {
    const csrf = leerCookie('csrftoken');
    const response = await fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        ...(csrf ? { 'X-CSRFToken': csrf } : {}),
      },
      credentials: 'same-origin',
    });

    const texto = await response.text();
    let data = null;
    try {
      data = JSON.parse(texto);
    } catch (error) {
      data = null;
    }

    if (!data) {
      if (response.status === 403) {
        mostrarFeedbackVerificacion(
          'Tu token de seguridad expiró. Recargando la página para continuar…',
          true
        );
        setTimeout(() => window.location.reload(), 1200);
        return;
      }
      throw new Error('Respuesta inesperada del servidor');
    }

    if (data.ok) {
      mostrarFeedbackVerificacion(data.mensaje || 'Solicitud enviada.', false);
      setTimeout(() => {
        const base = window.location.pathname;
        window.location.href = base + '?seccion=inicio&verificacion=1';
      }, 1100);
      return;
    }

    Object.entries(data.errores || {}).forEach(([campo, mensaje]) => {
      const errorEl = form.querySelector(`[data-error-para="${campo}"]`);
      if (errorEl) errorEl.textContent = mensaje;
      const input = form.querySelector(`[name="${campo}"]`);
      if (input) input.classList.add('is-invalid');
    });
    mostrarFeedbackVerificacion(
      data.mensaje || 'Revisa los campos marcados.',
      true
    );
    const primerError = form.querySelector('.is-invalid');
    if (primerError) primerError.focus({ preventScroll: true });
  } catch (error) {
    mostrarFeedbackVerificacion(
      'No pudimos enviar la solicitud. Revisa tu conexión e inténtalo de nuevo.',
      true
    );
  } finally {
    if (submit) {
      submit.disabled = false;
      submit.innerHTML = textoOriginal;
    }
  }
});

// ═══════════════════════════════════════════════
// MODAL FLOTANTE: POSTULACIÓN A PROYECTO
// ═══════════════════════════════════════════════
let postulacionUrl = '';
let postulacionCard = null;

function setTextoPostulacion(modal, selector, valor) {
  const el = modal.querySelector(selector);
  if (el) el.textContent = valor;
}

function abrirPostulacion(btn) {
  const modal = document.getElementById('modalPostulacion');
  if (!modal || !btn) return;

  postulacionUrl = btn.getAttribute('data-url') || '';
  postulacionCard = btn.closest('.project-card');

  setTextoPostulacion(modal, '[data-postulacion-tipo]', btn.dataset.tipo || 'Proyecto');
  setTextoPostulacion(modal, '[data-postulacion-prioridad]', btn.dataset.prioridad || '—');
  setTextoPostulacion(modal, '[data-postulacion-titulo]', btn.dataset.titulo || 'Proyecto');
  setTextoPostulacion(modal, '[data-postulacion-empresa]', btn.dataset.empresa || '');
  setTextoPostulacion(modal, '[data-postulacion-vacantes]', btn.dataset.vacantes || '0');
  setTextoPostulacion(modal, '[data-postulacion-cierre]', btn.dataset.cierre || 'Sin límite');
  setTextoPostulacion(modal, '[data-postulacion-descripcion]', btn.dataset.descripcion || '');

  const form = modal.querySelector('[data-postulacion-form]');
  if (form) form.reset();
  mostrarFeedbackPostulacion('', false);
  const btnVerificar = modal.querySelector('[data-ir-verificacion]');
  if (btnVerificar) btnVerificar.hidden = true;

  sincronizarCsrf(modal);
  modal.classList.add('is-open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';

  const first = modal.querySelector('#id_post_carta');
  if (first) first.focus({ preventScroll: true });
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
  _setupModalFocusTrap(modal, cerrarPostulacion);
}

function cerrarPostulacion() {
  const modal = document.getElementById('modalPostulacion');
  if (!modal) return;
  _cleanupModalFocusTrap();
  modal.classList.remove('is-open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

function mostrarFeedbackPostulacion(mensaje, esError) {
  const feedback = document.querySelector('[data-postulacion-feedback]');
  if (!feedback) return;
  feedback.textContent = mensaje || '';
  feedback.hidden = !mensaje;
  feedback.classList.toggle('is-error', !!esError);
}

function mostrarToast(mensaje) {
  if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
    window.JobDevsToast.mostrar({
      tipo: 'success',
      mensaje: mensaje,
      duracion: 4200,
    });
  }
}

function actualizarContadorExplorar() {
  const badge = document.getElementById('devExploreCountBadge');
  if (!badge) return;
  const actual = parseInt((badge.textContent || '').replace(/[^\d]/g, ''), 10);
  if (Number.isNaN(actual)) return;
  badge.textContent = `${Math.max(0, actual - 1)} DISPONIBLES`;
}

function escapeHtml(val) {
  if (val == null) return '';
  return String(val)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function insertarPostulacionActiva(post) {
  const contenedorVigentes = document.querySelector('[data-testid="postulaciones-vigentes"]');
  if (!contenedorVigentes) return;

  const postList = contenedorVigentes.querySelector('.post-list');
  if (!postList) return;

  // Si había un empty state ("No tienes postulaciones vigentes"), removerlo
  const emptyState = postList.querySelector('.cockpit-empty-state, .empty-state');
  if (emptyState) {
    emptyState.remove();
  }

  const p = post.proyecto || {};
  const inicial = (p.empresa_nombre || 'E').slice(0, 1).toUpperCase();
  const avatarHtml = p.empresa_logo
    ? '<img src="' + escapeHtml(p.empresa_logo) + '" alt="' + escapeHtml(p.empresa_nombre) + '">'
    : inicial;

  const cardHtml = `
    <article class="post-row-compact" style="animation: devFade 0.3s ease;">
      <!-- Línea 1: Empresa + Fecha a la izquierda | Estado a la derecha -->
      <div class="post-compact-line-1">
        <div class="post-compact-empresa">
          <div class="post-compact-avatar">
            ${avatarHtml}
          </div>
          <div class="post-compact-meta">
            <a href="${escapeHtml(p.detalle_empresa_url || '#')}" data-abrir-empresa data-url="${escapeHtml(p.detalle_empresa_url || '#')}" class="post-compact-empresa-link" title="Ver perfil institucional">
              <span>${escapeHtml(p.empresa_nombre || '')}</span>
              <i data-lucide="arrow-up-right" style="width:11px; height:11px; opacity:0.6;"></i>
            </a>
            <span class="post-compact-date">· Postulado el ${escapeHtml(post.fecha || 'Hoy')} (hace instantes)</span>
          </div>
        </div>

        <div class="post-status-pill">
          <span class="post-status-dot is-pendiente"></span>
          <span class="post-status-text">${escapeHtml(post.estado_display || 'Pendiente de evaluación')}</span>
        </div>
      </div>

      <!-- Línea 2: Título + Tags a la izquierda | Botón Ver a la derecha -->
      <div class="post-compact-line-2">
        <div class="post-compact-project-info">
          <h3 class="post-compact-title">${escapeHtml(p.titulo || '')}</h3>
          <div class="post-tags-row">
            <span class="post-tag"><i data-lucide="layers"></i> ${escapeHtml(p.tipo_solucion || '')}</span>
            <span class="post-tag"><i data-lucide="map-pin"></i> ${escapeHtml(p.modalidad || '')}</span>
            <span class="post-tag" style="color:var(--text-muted); border-style:dashed;">
              <i data-lucide="clock" style="color:var(--text-muted);"></i> Esperando contrato
            </span>
          </div>
        </div>

        <div class="post-actions-group">
          <button type="button" class="btn-cockpit" data-ver-proyecto data-url="${escapeHtml(p.detalle_proyecto_url || '#')}" title="Ver proyecto">
            <i data-lucide="eye"></i>
            <span>Ver</span>
          </button>
        </div>
      </div>
    </article>
  `;

  // Insertar al inicio de la lista
  postList.insertAdjacentHTML('afterbegin', cardHtml);

  // Actualizar el contador de postulaciones vigentes ("X en curso")
  const badgeCount = contenedorVigentes.querySelector('.label-section .badge');
  if (badgeCount) {
    const cards = postList.querySelectorAll('.post-row-compact');
    badgeCount.textContent = cards.length + ' en curso';
  }

  // Actualizar tarjeta de métrica en Inicio si existe
  const cardMetrica = document.querySelector('.dev-card[onclick*="postulaciones"] .dev-card-val');
  if (cardMetrica) {
    const numEl = cardMetrica.querySelector('.kpi-num') || cardMetrica;
    const valActual = parseInt((numEl.getAttribute('data-target-val') || numEl.textContent).trim(), 10) || 0;
    const nuevoVal = valActual + 1;
    numEl.removeAttribute('data-target-val');
    numEl.textContent = nuevoVal;
    animarContadorKpi(numEl);
  }

  // Renderizar iconos de Lucide en la nueva tarjeta
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

document.addEventListener('click', (event) => {
  const abrir = event.target.closest('[data-abrir-postulacion]');
  if (abrir) {
    event.preventDefault();
    abrirPostulacion(abrir);
    return;
  }

  if (event.target.closest('[data-cerrar-postulacion]')) {
    cerrarPostulacion();
    return;
  }

  if (event.target.closest('[data-ir-verificacion]')) {
    cerrarPostulacion();
    abrirVerificacion();
  }
});

document.addEventListener('submit', async (event) => {
  const form = event.target.closest('[data-postulacion-form]');
  if (!form) return;
  event.preventDefault();

  const modal = form.closest('#modalPostulacion');
  const carta = form.querySelector('[name="carta"]');
  if (carta && !carta.value.trim()) {
    mostrarFeedbackPostulacion('La carta de presentación es obligatoria.', true);
    carta.focus({ preventScroll: true });
    return;
  }
  if (!postulacionUrl) return;

  sincronizarCsrf(form);
  const submit = form.querySelector('[data-postulacion-submit]');
  const textoOriginal = submit ? submit.innerHTML : '';
  if (submit) {
    submit.disabled = true;
    submit.innerHTML = '<i data-lucide="loader-2"></i> Enviando...';
  }
  mostrarFeedbackPostulacion('', false);

  try {
    const csrf = leerCookie('csrftoken');
    const response = await fetch(postulacionUrl, {
      method: 'POST',
      body: new FormData(form),
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        ...(csrf ? { 'X-CSRFToken': csrf } : {}),
      },
      credentials: 'same-origin',
    });

    const texto = await response.text();
    let data = null;
    try {
      data = JSON.parse(texto);
    } catch (error) {
      data = null;
    }

    if (!data) {
      if (response.status === 403) {
        mostrarFeedbackPostulacion(
          'Tu token de seguridad expiró. Recargando la página para continuar…',
          true
        );
        setTimeout(() => window.location.reload(), 1200);
        return;
      }
      throw new Error('Respuesta inesperada del servidor');
    }

    if (data.ok) {
      cerrarPostulacion();
      if (postulacionCard) {
        postulacionCard.remove();
        postulacionCard = null;
        actualizarContadorExplorar();
      }
      mostrarToast(data.mensaje || '¡Postulación enviada!');
      if (data.postulacion) {
        insertarPostulacionActiva(data.postulacion);
      }
      return;
    }

    const btnVerificar = modal ? modal.querySelector('[data-ir-verificacion]') : null;
    if (btnVerificar) btnVerificar.hidden = !data.requiere_verificacion;
    mostrarFeedbackPostulacion(data.mensaje || 'No se pudo enviar la postulación.', true);
  } catch (error) {
    mostrarFeedbackPostulacion(
      'No pudimos enviar tu postulación. Revisa tu conexión e inténtalo de nuevo.',
      true
    );
  } finally {
    if (submit) {
      submit.disabled = false;
      submit.innerHTML = textoOriginal;
    }
  }
});

// ═══════════════════════════════════════════════
// DRAWER MÓVIL ACCESIBLE (SCRUM-411)
// ═══════════════════════════════════════════════
function _syncDevDrawerAria(isOpen) {
  const toggleBtn = document.querySelector('.mobile-menu-toggle');
  if (!toggleBtn) return;
  toggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  toggleBtn.setAttribute('aria-label', isOpen ? 'Cerrar menú de navegación' : 'Abrir menú de navegación');
}

function toggleSidebar() {
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

function closeSidebar() {
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

document.addEventListener('DOMContentLoaded', () => {
  const backdrop = document.getElementById('sidebarBackdrop');
  if (backdrop) backdrop.addEventListener('click', closeSidebar);
  document.querySelectorAll('.sidebar .nav-item').forEach((item) => {
    item.addEventListener('click', () => {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const sidebar = document.querySelector('.sidebar');
      if (sidebar && sidebar.classList.contains('is-open')) closeSidebar();
    }
  });
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) closeSidebar();
  });
});

// ═══════════════════════════════════════════════
// MENÚ DESPLEGABLE DE USUARIO (NAVBAR / TOPBAR)
// ═══════════════════════════════════════════════
window.toggleUserMenu = function (e) {
  if (e) e.stopPropagation();
  const menu = document.getElementById('userDropdownMenu');
  const btn = document.getElementById('userMenuBtn');
  if (!menu) return;

  const isOpen = menu.style.display === 'block' || menu.classList.contains('is-open');
  if (isOpen) {
    window.closeUserMenu();
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
};

window.closeUserMenu = function () {
  const menu = document.getElementById('userDropdownMenu');
  const btn = document.getElementById('userMenuBtn');
  if (menu) {
    menu.style.display = 'none';
    menu.classList.remove('is-open');
  }
  if (btn) {
    btn.setAttribute('aria-expanded', 'false');
  }
};

window.cerrarSesionConSpinner = function (event, el) {
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
};

// ═══════════════════════════════════════════════
// COLAPSO DEL SIDEBAR (DESKTOP SOLO ICONOS)
// ═══════════════════════════════════════════════
window.toggleSidebarCollapse = function () {
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
};

document.addEventListener('DOMContentLoaded', function () {
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
});

// Cerrar dropdown al hacer click afuera o presionar Escape
document.addEventListener('click', function (e) {
  const userWrapper = document.querySelector('.user-dropdown-wrapper');
  if (userWrapper && !userWrapper.contains(e.target)) {
    window.closeUserMenu();
  }
});

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    window.closeUserMenu();
  }
});

// Cerrar Pop-up de Contrato Pendiente
window.cerrarPopupContrato = function (id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.opacity = '0';
    el.style.transform = 'translateY(15px)';
    el.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 200);
  }
};

// ═══════════════════════════════════════════════
// GRÁFICA DE ACTIVIDAD COCKPIT DEV (VANILLA SVG)
// ═══════════════════════════════════════════════
(function () {
  var devChartState = {
    metric: 'hitos',
    data: null,
    prevCoords: null,
    rafId: null
  };

  var SVG_W = 680;
  var PAD_L = 36;
  var PAD_R = 20;
  var PAD_T = 20;
  var PAD_B = 30;
  var PLOT_H = 200 - PAD_T - PAD_B;

  function buildSmoothPath(pts) {
    if (!pts.length) return '';
    if (pts.length === 1) return 'M ' + pts[0].x.toFixed(2) + ' ' + pts[0].y.toFixed(2);
    var d = 'M ' + pts[0].x.toFixed(2) + ' ' + pts[0].y.toFixed(2);
    for (var i = 0; i < pts.length - 1; i++) {
      var p0 = pts[i === 0 ? i : i - 1];
      var p1 = pts[i];
      var p2 = pts[i + 1];
      var p3 = pts[i + 2 < pts.length ? i + 2 : i + 1];
      var cp1x = p1.x + (p2.x - p0.x) / 6;
      var cp1y = p1.y + (p2.y - p0.y) / 6;
      var cp2x = p2.x - (p3.x - p1.x) / 6;
      var cp2y = p2.y - (p3.y - p1.y) / 6;
      var minY = Math.min(p1.y, p2.y);
      var maxY = Math.max(p1.y, p2.y);
      cp1y = Math.max(PAD_T, Math.min(PAD_T + PLOT_H, Math.max(minY - 8, Math.min(maxY + 8, cp1y))));
      cp2y = Math.max(PAD_T, Math.min(PAD_T + PLOT_H, Math.max(minY - 8, Math.min(maxY + 8, cp2y))));
      d += ' C ' + cp1x.toFixed(2) + ' ' + cp1y.toFixed(2) + ', ' + cp2x.toFixed(2) + ' ' + cp2y.toFixed(2) + ', ' + p2.x.toFixed(2) + ' ' + p2.y.toFixed(2);
    }
    return d;
  }

  function buildAreaPath(pts, lineD) {
    if (!pts.length || !lineD) return '';
    var baseY = (PAD_T + PLOT_H).toFixed(2);
    return lineD + ' L ' + pts[pts.length - 1].x.toFixed(2) + ' ' + baseY + ' L ' + pts[0].x.toFixed(2) + ' ' + baseY + ' Z';
  }

  function computeCoords(puntos, metric) {
    var maxVal = 1;
    for (var i = 0; i < puntos.length; i++) {
      var v = puntos[i][metric] || 0;
      if (v > maxVal) maxVal = v;
    }
    var niceMax = metric === 'calificacion' ? 5 : (maxVal <= 2 ? 3 : Math.ceil(maxVal * 1.25));
    var plotW = SVG_W - PAD_L - PAD_R;
    var n = puntos.length;
    var coords = [];
    for (var j = 0; j < n; j++) {
      var val = puntos[j][metric] || 0;
      var x = n === 1 ? PAD_L + plotW / 2 : PAD_L + (j / (n - 1)) * plotW;
      var y = PAD_T + PLOT_H - (val / niceMax) * PLOT_H;
      coords.push({ x: x, y: y, valor: val, etiqueta: puntos[j].etiqueta, fecha: puntos[j].fecha });
    }
    return { coords: coords, niceMax: niceMax };
  }

  function showTooltip(evt, pt, label) {
    var tip = document.getElementById('devChartTooltip');
    var wrap = tip ? tip.parentElement : null;
    if (!tip || !wrap) return;
    document.getElementById('tipPeriodo').textContent = pt.fecha || pt.etiqueta;

    var numEl = document.getElementById('tipMonto');
    var descEl = document.getElementById('tipDesc');
    if (devChartState.metric === 'calificacion') {
      if (pt.valor > 0) {
        numEl.textContent = Number(pt.valor).toFixed(1);
        descEl.textContent = '★ de calificación promedio';
      } else {
        numEl.textContent = '0.0';
        descEl.textContent = 'sin valoraciones en el mes';
      }
    } else {
      numEl.textContent = String(pt.valor);
      descEl.textContent = label;
    }

    tip.style.display = 'block';
    var rect = wrap.getBoundingClientRect();
    var left = (evt.clientX - rect.left);
    var top = (evt.clientY - rect.top) - 10;
    if (left + 140 > rect.width) left = Math.max(8, left - 150);
    if (top < 30) top = 30;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }

  function hideTooltip() {
    var tip = document.getElementById('devChartTooltip');
    if (tip) tip.style.display = 'none';
  }

  function renderChart(mode) {
    if (!devChartState.data || !devChartState.data.length) return;
    var metric = devChartState.metric;
    var computed = computeCoords(devChartState.data, metric);
    var niceMax = computed.niceMax;
    var coords = computed.coords;

    var gridG = document.getElementById('devChartGrid');
    var yG = document.getElementById('devChartYAxis');
    var xG = document.getElementById('devChartXAxis');
    var dotsG = document.getElementById('devChartDots');
    var linePath = document.getElementById('devChartLinePath');
    var areaPath = document.getElementById('devChartAreaPath');

    if (!linePath || !areaPath || !gridG) return;

    var ns = 'http://www.w3.org/2000/svg';
    gridG.innerHTML = '';
    yG.innerHTML = '';
    xG.innerHTML = '';
    dotsG.innerHTML = '';

    // Eje Y y líneas horizontales
    var ticks = [0, Math.round(niceMax / 2), niceMax];
    for (var t = 0; t < ticks.length; t++) {
      var val = ticks[t];
      var y = PAD_T + PLOT_H - (val / niceMax) * PLOT_H;
      var line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', PAD_L);
      line.setAttribute('x2', SVG_W - PAD_R);
      line.setAttribute('y1', y.toFixed(1));
      line.setAttribute('y2', y.toFixed(1));
      line.setAttribute('class', 'chart-grid-line');
      gridG.appendChild(line);

      var txt = document.createElementNS(ns, 'text');
      txt.setAttribute('x', PAD_L - 8);
      txt.setAttribute('y', (y + 4).toFixed(1));
      txt.setAttribute('text-anchor', 'end');
      txt.setAttribute('class', 'chart-axis-label');
      txt.textContent = String(val);
      yG.appendChild(txt);
    }

    // Eje X
    for (var i = 0; i < coords.length; i++) {
      var xTxt = document.createElementNS(ns, 'text');
      xTxt.setAttribute('x', coords[i].x.toFixed(1));
      xTxt.setAttribute('y', '195');
      xTxt.setAttribute('text-anchor', i === 0 ? 'start' : (i === coords.length - 1 ? 'end' : 'middle'));
      xTxt.setAttribute('class', 'chart-axis-label');
      xTxt.textContent = coords[i].etiqueta;
      xG.appendChild(xTxt);
    }

    // Trazos de curva y área
    var d = buildSmoothPath(coords);
    var isGold = metric === 'calificacion';
    linePath.setAttribute('stroke', isGold ? '#f59e0b' : '#00e676');
    linePath.setAttribute('filter', isGold ? 'url(#goldGlow)' : 'url(#neonGlow)');
    areaPath.setAttribute('fill', isGold ? 'url(#goldAreaGradient)' : 'url(#neonAreaGradient)');
    linePath.setAttribute('d', d);
    areaPath.setAttribute('d', buildAreaPath(coords, d));

    if (mode === 'draw' && typeof linePath.getTotalLength === 'function') {
      var len = linePath.getTotalLength();
      linePath.style.transition = 'none';
      linePath.style.strokeDasharray = len;
      linePath.style.strokeDashoffset = len;
      linePath.getBoundingClientRect();
      linePath.style.transition = 'stroke-dashoffset 550ms cubic-bezier(0.16, 1, 0.3, 1)';
      linePath.style.strokeDashoffset = '0';
    }

    // Puntos interactivos
    var labelText = metric === 'calificacion' ? '★ de calificación promedio' : (metric === 'hitos' ? 'hitos entregados' : 'postulaciones');
    coords.forEach(function (pt) {
      var c = document.createElementNS(ns, 'circle');
      c.setAttribute('cx', pt.x.toFixed(2));
      c.setAttribute('cy', pt.y.toFixed(2));
      c.setAttribute('r', pt.valor > 0 ? '4.5' : '3');
      c.setAttribute('class', 'chart-data-dot');
      c.setAttribute('stroke', isGold ? '#f59e0b' : '#00e676');
      c.setAttribute('tabindex', '0');
      c.addEventListener('mouseenter', function (e) { showTooltip(e, pt, labelText); });
      c.addEventListener('mousemove', function (e) { showTooltip(e, pt, labelText); });
      c.addEventListener('mouseleave', hideTooltip);
      dotsG.appendChild(c);
    });

    devChartState.prevCoords = coords;
  }

  window.cambiarMetricaGrafica = function (metric, btn) {
    devChartState.metric = metric;
    document.querySelectorAll('.cockpit-chart-tab').forEach(function (b) { b.classList.remove('active'); });
    if (btn) btn.classList.add('active');

    var title = document.getElementById('devChartTitle');
    var kpiVal = document.getElementById('devChartKpiVal');
    var kpiLabel = document.getElementById('devChartKpiLabel');
    var rawData = devChartState.data || [];

    if (metric === 'hitos') {
      if (title) title.textContent = 'Evolución de Entregas y Cumplimiento';
      var sumH = rawData.reduce(function (acc, p) { return acc + (p.hitos || 0); }, 0);
      if (kpiVal) {
        kpiVal.removeAttribute('data-target-val');
        kpiVal.textContent = String(sumH);
        animarContadorKpi(kpiVal);
      }
      if (kpiLabel) kpiLabel.textContent = 'Hitos Completados (6m)';
    } else if (metric === 'postulaciones') {
      if (title) title.textContent = 'Ritmo de Postulaciones Enviadas';
      var sumP = rawData.reduce(function (acc, p) { return acc + (p.postulaciones || 0); }, 0);
      if (kpiVal) {
        kpiVal.removeAttribute('data-target-val');
        kpiVal.textContent = String(sumP);
        animarContadorKpi(kpiVal);
      }
      if (kpiLabel) kpiLabel.textContent = 'Postulaciones Totales (6m)';
    } else if (metric === 'calificacion') {
      if (title) title.textContent = 'Evolución de Calificación y Reputación';
      var vals = rawData.map(function (p) { return p.calificacion || 0; }).filter(function (v) { return v > 0; });
      var avg = vals.length ? (vals.reduce(function (a, b) { return a + b; }, 0) / vals.length).toFixed(1) : '5.0';
      if (kpiVal) {
        kpiVal.removeAttribute('data-target-val');
        kpiVal.textContent = avg;
        animarContadorKpi(kpiVal);
      }
      if (kpiLabel) kpiLabel.textContent = 'Promedio Empresas';
    }

    renderChart('draw');
  };

  window.initDevActivityChart = function () {
    var dataEl = document.getElementById('devChartDataScript');
    if (!dataEl) return;
    try {
      devChartState.data = JSON.parse(dataEl.textContent);
    } catch (e) {
      devChartState.data = [];
    }
    renderChart('draw');
  };

  document.addEventListener('DOMContentLoaded', window.initDevActivityChart);
})();




