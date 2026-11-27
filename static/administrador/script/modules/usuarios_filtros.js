/**
 * ============================================================
 * JobDevs - Panel Administrador: Filtros y Búsqueda de
 * Usuarios, Proyectos, Explorar Catálogo y Quick Search
 * ============================================================
 */

import { debounce } from './ui_core.js';

// --- Users & Projects Search & Filter (SCRUM-408) ---

export function filterUsersClientSide() {
  const search = (document.getElementById('userSearch')?.value || '').toLowerCase().trim();
  const role = document.getElementById('userRoleFilter')?.value || '';
  const status = document.getElementById('userStatusFilter')?.value || '';
  const fechaDesde = document.querySelector('[data-testid="filtro-fecha-desde"]')?.value || '';
  const fechaHasta = document.querySelector('[data-testid="filtro-fecha-hasta"]')?.value || '';

  const rows = document.querySelectorAll('#usersTable tbody tr');
  let visible = 0;
  rows.forEach((row) => {
    if (row.querySelector('.empty-state')) return;
    const estadoText = row.dataset.active === 'active' ? 'activo' : 'inactivo suspendido';
    const text = [
      row.dataset.username || '',
      row.dataset.nombre || '',
      row.dataset.email || '',
      row.dataset.rol || '',
    ]
      .join(' ')
      .toLowerCase();
    const escapedSearch = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const matchEstadoSearch = search
      ? new RegExp('(^|\\s)' + escapedSearch + '(\\s|$)').test(estadoText)
      : false;
    const matchSearch = !search || text.includes(search) || matchEstadoSearch;
    const matchRole = role ? row.dataset.rol === role : row.dataset.rol !== 'administrador';
    const matchStatus = !status || row.dataset.active === status;
    const fechaRegistro = row.dataset.fechaRegistro || '';
    const matchFechaDesde = !fechaDesde || (fechaRegistro && fechaRegistro >= fechaDesde);
    const matchFechaHasta = !fechaHasta || (fechaRegistro && fechaRegistro <= fechaHasta);
    const show = matchSearch && matchRole && matchStatus && matchFechaDesde && matchFechaHasta;
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  const countEl = document.getElementById('usersResultCount');
  if (countEl) {
    countEl.textContent = `Mostrando ${visible} de ${rows.length} usuarios`;
  }
}

export function _renderUsersTableRows() {}

export function filterUsers() {
  const table = document.getElementById('usersTable');
  const apiUrl = table?.dataset.apiUsuariosUrl || '/api/';
  const search = (document.getElementById('userSearch')?.value || '').trim();
  const role = document.getElementById('userRoleFilter')?.value || '';
  const status = document.getElementById('userStatusFilter')?.value || '';
  const fechaDesde = document.querySelector('[data-testid="filtro-fecha-desde"]')?.value || '';
  const fechaHasta = document.querySelector('[data-testid="filtro-fecha-hasta"]')?.value || '';

  const params = new URLSearchParams();
  if (search) params.set('q', search);
  if (role) params.set('rol', role);
  if (status) params.set('estado', status);
  if (fechaDesde) params.set('fecha_desde', fechaDesde);
  if (fechaHasta) params.set('fecha_hasta', fechaHasta);

  if (window.htmx && typeof window.htmx.ajax === 'function') {
    const queryStr = params.toString();
    const url = apiUrl + (queryStr ? '?' + queryStr : '');
    window.htmx.ajax('GET', url, {
      target: '#usersTableBody',
      swap: 'innerHTML',
    });
    return;
  }

  filterUsersClientSide();
}

export function filterProjects() {
  const search = (document.getElementById('projectSearch')?.value || '').toLowerCase().trim();
  const estado = document.getElementById('projectEstadoFilter')?.value || '';

  const rows = document.querySelectorAll('#projectsSection .data-table tbody tr');
  let visible = 0;
  rows.forEach((row) => {
    const text = [
      row.dataset.titulo || '',
      row.dataset.empresa || '',
      row.dataset.estado || '',
    ]
      .join(' ')
      .toLowerCase();
    const matchSearch = !search || text.includes(search);
    const matchEstado = !estado || row.dataset.estado === estado;
    const show = matchSearch && matchEstado;
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  const countEl = document.getElementById('projectsResultCount');
  if (countEl) {
    countEl.textContent = `Mostrando ${visible} de ${rows.length} proyectos`;
  }
}

export const debouncedFilterUsers = debounce(filterUsers, 300);
export const debouncedFilterProjects = debounce(filterProjects, 300);

export function setAdminProjectEstadoPill(estado, btn) {
  const sel = document.getElementById('projectEstadoFilter');
  if (sel) sel.value = estado;
  document.querySelectorAll('.project-estado-pill').forEach((b) => {
    b.classList.remove('is-active');
  });
  if (btn) btn.classList.add('is-active');
  filterProjects();
}

export function setAdminUserRolePill(rol, btn) {
  const sel = document.getElementById('userRoleFilter');
  if (sel) sel.value = rol;
  document.querySelectorAll('.users-role-pill').forEach((b) => {
    b.classList.remove('is-active');
  });
  if (btn) btn.classList.add('is-active');
  filterUsers();
}

export function switchUsersTab(tab, btn) {
  const dir = document.getElementById('usersTabDirectorio');
  const des = document.getElementById('usersTabDesempeno');
  if (!dir || !des) return;
  const isDir = tab === 'directorio';
  dir.hidden = !isDir;
  des.hidden = isDir;
  document.querySelectorAll('#usersSection .admin-tab-btn').forEach((b) => {
    b.classList.remove('is-active');
    b.setAttribute('aria-selected', 'false');
  });
  if (btn) {
    btn.classList.add('is-active');
    btn.setAttribute('aria-selected', 'true');
  }
}

// --- Explorar Catálogo (Admin) ---

export function filterAdminExplore() {
  const searchInput = document.getElementById('adminExploreSearch');
  const catSelect = document.getElementById('adminExploreCategory');
  const estadoSelect = document.getElementById('adminExploreEstado');
  if (!searchInput) return;

  const q = (searchInput.value || '').toLowerCase().trim();
  const cat = (catSelect ? catSelect.value : '').toLowerCase().trim();
  const estado = (estadoSelect ? estadoSelect.value : '').toLowerCase().trim();

  const cards = document.querySelectorAll('.admin-explore-card');
  let visibleCount = 0;

  cards.forEach((card) => {
    const titulo = card.getAttribute('data-titulo') || '';
    const desc = card.getAttribute('data-desc') || '';
    const empresa = card.getAttribute('data-empresa') || '';
    const tipo = card.getAttribute('data-tipo') || '';
    const cardEstado = card.getAttribute('data-estado') || '';

    const matchesQ = !q || titulo.includes(q) || desc.includes(q) || empresa.includes(q);
    const matchesCat = !cat || tipo === cat;
    const matchesEstado = !estado || cardEstado === estado;

    if (matchesQ && matchesCat && matchesEstado) {
      card.style.display = 'flex';
      visibleCount++;
    } else {
      card.style.display = 'none';
    }
  });

  const noMatches = document.getElementById('adminExploreNoMatches');
  if (noMatches) {
    noMatches.style.display = visibleCount === 0 && cards.length > 0 ? 'block' : 'none';
  }
  const badge = document.getElementById('adminExploreCountBadge');
  if (badge) {
    badge.textContent = visibleCount + ' PROYECTOS';
  }
}

export function resetAdminExploreFilters() {
  const searchInput = document.getElementById('adminExploreSearch');
  const catSelect = document.getElementById('adminExploreCategory');
  const estadoSelect = document.getElementById('adminExploreEstado');
  if (searchInput) searchInput.value = '';
  if (catSelect) catSelect.value = '';
  if (estadoSelect) estadoSelect.value = '';
  filterAdminExplore();
}

// --- Quick Search: Verificaciones & Disputas ---

export function filterAdminQuickSearch(inputId, tbodySelector) {
  const input = document.getElementById(inputId);
  const q = (input ? input.value : '').toLowerCase().trim();
  const rows = document.querySelectorAll(tbodySelector + ' tr');
  rows.forEach((row) => {
    if (
      row.querySelector('.empty-state') ||
      (row.children.length === 1 && row.children[0].hasAttribute('colspan'))
    ) {
      return;
    }
    const text = (row.textContent || '').toLowerCase();
    row.style.display = !q || text.includes(q) ? '' : 'none';
  });
}

// --- Filters Initialization ---

export function initUsuariosFiltros() {
  const exploreSearch = document.getElementById('adminExploreSearch');
  const exploreCat = document.getElementById('adminExploreCategory');
  const exploreEstado = document.getElementById('adminExploreEstado');
  if (exploreSearch) exploreSearch.addEventListener('input', filterAdminExplore);
  if (exploreCat) exploreCat.addEventListener('change', filterAdminExplore);
  if (exploreEstado) exploreEstado.addEventListener('change', filterAdminExplore);

  filterUsersClientSide();
  filterProjects();
}
