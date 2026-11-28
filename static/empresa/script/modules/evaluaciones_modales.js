/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Modales de Disputas,
 * Calificaciones, Valoraciones y Filtros en Tiempo Real
 * ============================================================
 */

import { t, escaparHtml } from './ui_utils.js';

// --- Helpers HTMX para Modales de Disputas y Calificaciones ---

function _refrescarIconos(root) {
  if (!window.lucide || typeof window.lucide.createIcons !== 'function') return;
  if (root && root.nodeType === 1) {
    try {
      window.lucide.createIcons({ root: root });
      return;
    } catch (e) {
      // Fallback al escaneo completo
    }
  }
  window.lucide.createIcons();
}

function _enlazarControlesDisputa(container) {
  if (!container) return;
  const form = container.querySelector('#form-disputa');
  if (!form) {
    _refrescarIconos(container);
    return;
  }

  const textarea = form.querySelector('#motivo');
  const charCount = form.querySelector('#char-count');
  if (textarea && charCount) {
    const syncCounter = function () {
      charCount.textContent = String((textarea.value || '').trim().length);
    };
    textarea.addEventListener('input', syncCounter);
    syncCounter();
  }

  const disputaChecks = form.querySelectorAll('#confirma_intento_previo, #confirma_gravedad, #acepta_sanciones');
  const disputaSubmitBtn = form.querySelector('#btn-submit-disputa');
  if (disputaChecks.length > 0 && disputaSubmitBtn) {
    const syncDisputaSubmit = function () {
      const allChecked = Array.prototype.every.call(disputaChecks, function (cb) { return cb.checked; });
      disputaSubmitBtn.disabled = !allChecked;
    };
    disputaChecks.forEach(function (cb) { cb.addEventListener('change', syncDisputaSubmit); });
    syncDisputaSubmit();
  }

  _refrescarIconos(container);
}

function _cargarPartialHtmx(actionUrl, targetId, bodyEl, errorHtml, onFallbackLoaded) {
  if (window.htmx && typeof window.htmx.ajax === 'function') {
    window.htmx.ajax('GET', actionUrl, { target: '#' + targetId, swap: 'innerHTML' }).catch(function () {
      bodyEl.innerHTML = errorHtml;
      _refrescarIconos(bodyEl);
    });
    return;
  }

  fetch(actionUrl, {
    headers: { 'HX-Request': 'true', 'Accept': 'text/html' },
    credentials: 'same-origin',
  })
    .then(function (res) {
      if (!res.ok) throw new Error('Error al cargar partial.');
      return res.text();
    })
    .then(function (html) {
      bodyEl.innerHTML = html;
      if (typeof onFallbackLoaded === 'function') {
        onFallbackLoaded(bodyEl);
      } else {
        _refrescarIconos(bodyEl);
      }
    })
    .catch(function () {
      bodyEl.innerHTML = errorHtml;
      _refrescarIconos(bodyEl);
    });
}

if (!window.__jobdevsEvalModalesHtmxInit) {
  window.__jobdevsEvalModalesHtmxInit = true;

  document.addEventListener('htmx:afterSwap', function (event) {
    const target = event && event.detail && event.detail.target;
    if (!target) return;
    if (target.id === 'modalDisputaBody') {
      _enlazarControlesDisputa(target);
    } else if (target.id === 'modalCalificarBody') {
      _refrescarIconos(target);
    }
  });

  document.addEventListener('jobdevs:disputa-creada', function (event) {
    const detail = (event && event.detail) || {};
    const targetTab = detail.reload_hash || 'desarrollo';
    cerrarModalDisputa();
    if (typeof window.switchTab === 'function') {
      window.switchTab(targetTab);
    }
    window.location.hash = '#' + targetTab;
    if (window.JobDevsHTMX && typeof window.JobDevsHTMX.refreshSections === 'function') {
      window.JobDevsHTMX.refreshSections(['#' + targetTab, '#disputas', '#desarrollo', '#inicio']);
    }
  });

  document.addEventListener('jobdevs:calificacion-guardada', function (event) {
    const detail = (event && event.detail) || {};
    const targetTab = detail.reload_hash || 'historial';
    cerrarModalCalificar();
    if (typeof window.switchTab === 'function') {
      window.switchTab(targetTab);
    }
    window.location.hash = '#' + targetTab;
    if (window.JobDevsHTMX && typeof window.JobDevsHTMX.refreshSections === 'function') {
      window.JobDevsHTMX.refreshSections(['#' + targetTab, '#historial', '#inicio']);
    }
  });
}

// --- Modal de Disputas ---

export function abrirModalDisputa(event, actionUrl, titulo) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  document.querySelectorAll('.dev-more-actions[open]').forEach(function (d) {
    d.removeAttribute('open');
  });

  // Si se invoca sin URL (botón "Iniciar Nueva Disputa"), abrir selector de proyecto
  if (!actionUrl) {
    const selectorModal = document.getElementById('modalNuevaDisputa');
    if (selectorModal) {
      selectorModal.classList.add('open');
      selectorModal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
    }
    return;
  }

  const modal = document.getElementById('modalReportarDisputa');
  const subtituloEl = document.getElementById('modalDisputaSubtitulo');
  const bodyEl = document.getElementById('modalDisputaBody');
  if (!modal || !bodyEl) return;

  if (subtituloEl) subtituloEl.textContent = titulo || '';
  bodyEl.innerHTML = '<div class="drawer-loading" style="padding:36px 16px;"><i data-lucide="loader-circle" class="corp-spin"></i><p>' + escaparHtml(t('cargandoFormularioDisputa', 'Cargando formulario de mediación...')) + '</p></div>';

  modal.classList.add('open');
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  _refrescarIconos(bodyEl);

  const errorHtml = '<div class="activity-empty" style="padding:36px 16px;"><i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i><p>No se pudo cargar el formulario de disputa.</p></div>';
  _cargarPartialHtmx(actionUrl, 'modalDisputaBody', bodyEl, errorHtml, _enlazarControlesDisputa);
}

export function cerrarModalDisputa() {
  ['modalReportarDisputa', 'modalNuevaDisputa'].forEach(function (id) {
    const m = document.getElementById(id);
    if (m) {
      m.classList.remove('open');
      m.style.display = 'none';
    }
  });
  document.body.style.overflow = '';
}

// --- Modal Profesional de Calificar Equipo (100% in-situ) ---

export function cerrarModalCalificar() {
  const modal = document.getElementById('modalCalificarEquipo');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

export function abrirModalCalificar(event, actionUrl, titulo) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  const modal = document.getElementById('modalCalificarEquipo');
  const subEl = document.getElementById('modalCalificarSubtitulo');
  const bodyEl = document.getElementById('modalCalificarBody');
  if (!modal || !bodyEl || !actionUrl) return;

  if (subEl) subEl.textContent = titulo || '';
  bodyEl.innerHTML = '<div class="drawer-loading" style="padding:36px 16px;"><div class="corp-spinner"></div><p>' + escaparHtml(t('cargandoCalificacion', 'Cargando formulario de calificación...')) + '</p></div>';

  modal.classList.add('open');
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';

  const errorHtml = '<div class="drawer-loading" style="padding:28px 16px;"><p style="color:var(--corp-danger);">' + escaparHtml(t('errorCargarCalificacion', 'No se pudo cargar el formulario de calificación.')) + '</p></div>';
  _cargarPartialHtmx(actionUrl, 'modalCalificarBody', bodyEl, errorHtml);
}

// --- Modal de Todas las Valoraciones y Reseñas ---

window._filtroEstrellasActual = 0;
window._filtroTextoActual = '';

export function abrirModalTodasValoraciones() {
  const modal = document.getElementById('modalTodasValoraciones');
  if (modal) {
    modal.classList.add('open');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    const searchInput = modal.querySelector('input');
    if (searchInput) {
      searchInput.value = '';
      window._filtroTextoActual = '';
      window._filtroEstrellasActual = 0;
      _aplicarFiltrosResenas();
      searchInput.focus();
    }
  }
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function cerrarModalTodasValoraciones() {
  const modal = document.getElementById('modalTodasValoraciones');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

export function filtrarResenasModal(input) {
  window._filtroTextoActual = (input.value || '').toLowerCase().trim();
  _aplicarFiltrosResenas();
}

export function filtrarPorEstrellasModal(stars, btn) {
  window._filtroEstrellasActual = parseInt(stars, 10) || 0;
  const parent = btn.parentElement;
  if (parent) {
    parent.querySelectorAll('.datepicker-preset-pill').forEach(function (b) {
      b.classList.remove('active');
    });
    btn.classList.add('active');
  }
  _aplicarFiltrosResenas();
}

export function _aplicarFiltrosResenas() {
  const items = document.querySelectorAll('#modalResenasFeed .modal-review-item');
  const emptyMsg = document.getElementById('noMatchResenas');
  let visibleCount = 0;

  items.forEach(function (item) {
    const itemStars = parseInt(item.getAttribute('data-stars'), 10) || 0;
    const itemText = item.textContent.toLowerCase();

    let matchStars = true;
    if (window._filtroEstrellasActual === 1) {
      matchStars = (itemStars === 1 || itemStars === 2);
    } else if (window._filtroEstrellasActual > 1) {
      matchStars = (itemStars === window._filtroEstrellasActual);
    }

    let matchText = true;
    if (window._filtroTextoActual) {
      matchText = (itemText.indexOf(window._filtroTextoActual) !== -1);
    }

    if (matchStars && matchText) {
      item.style.display = '';
      visibleCount++;
    } else {
      item.style.display = 'none';
    }
  });

  if (emptyMsg) {
    emptyMsg.style.display = (visibleCount === 0 && items.length > 0) ? 'block' : 'none';
  }
}

// --- Filtrado de Historial en Tiempo Real (Sin recargar página) ---

export function filtrarHistorialEnTiempoReal(event, estado, btn) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  // Actualizar píldora activa
  const parent = btn ? btn.closest('.segmented-filters-corp') : null;
  if (parent && btn) {
    parent.querySelectorAll('.segmented-pill').forEach(function (p) {
      p.classList.remove('is-active');
    });
    btn.classList.add('is-active');
  }

  // Filtrar tarjetas del historial
  const cards = document.querySelectorAll('[data-testid="historial-inactivos"] .history-card-corp');
  let visibleCount = 0;

  cards.forEach(function (card) {
    const cardEstado = card.getAttribute('data-historial-estado') || '';
    if (estado === 'todos' || !estado || cardEstado === estado) {
      card.style.display = '';
      visibleCount++;
    } else {
      card.style.display = 'none';
    }
  });

  // Control del empty state (evitar duplicar si el servidor ya mostró {% empty %})
  const emptyMsg = document.getElementById('historialSinResultados');
  if (emptyMsg) {
    emptyMsg.style.display = (cards.length > 0 && visibleCount === 0) ? 'block' : 'none';
  }

  // Actualizar URL de forma limpia sin recargar
  if (window.history && window.history.replaceState) {
    const url = new URL(window.location);
    url.searchParams.set('section', 'historial');
    url.searchParams.delete('historial_estado');
    url.hash = 'historial';
    window.history.replaceState(null, '', url);
  }
}

// --- Filtrado de Disputas en Tiempo Real (Sin recargar página) ---

export function filtrarDisputasEnTiempoReal(event, estado, btn) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  // Actualizar botón activo
  const parent = btn ? btn.closest('.disputas-filtros') : null;
  if (parent && btn) {
    parent.querySelectorAll('.btn').forEach(function (b) {
      b.classList.remove('btn-primary');
      b.classList.add('btn-secondary');
    });
    btn.classList.add('btn-primary');
    btn.classList.remove('btn-secondary');
  }

  // Ocultar card de disputas-filtradas del servidor si existía
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

  // Actualizar URL sin recargar
  if (window.history && window.history.replaceState) {
    const url = new URL(window.location);
    url.searchParams.set('section', 'disputas');
    if (estado && estado !== 'todos') {
      url.searchParams.set('estado', estado);
    } else {
      url.searchParams.delete('estado');
    }
    url.hash = 'disputas';
    window.history.replaceState(null, '', url);
  }
}
