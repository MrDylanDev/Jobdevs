/**
 * ============================================================
 * JobDevs - Panel Administrador: Filtros y Búsqueda de
 * Usuarios, Proyectos, Explorar Catálogo y Quick Search
 * ============================================================
 */

import {
  getCSRFToken,
  debounce,
  escapeAdminHtml,
  escapeAdminJs,
} from './ui_core.js';

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

export function _renderUsersTableRows(users, roleFilter) {
  const table = document.getElementById('usersTable');
  const tbody = table ? table.querySelector('tbody') : null;
  if (!table || !tbody) return;

  const currentUserId = String(table.dataset.currentUserId || '');
  const toggleTpl = table.dataset.toggleUrlTemplate || '/administrador/usuario/0/toggle/';
  const csrfToken = getCSRFToken();
  const roleLabels = {
    desarrollador: 'Desarrollador',
    empresa: 'Empresa',
    administrador: 'Administrador',
  };

  const filtered = roleFilter ? users.filter((u) => u.rol === roleFilter) : users;

  if (!filtered.length) {
    tbody.innerHTML =
      '<tr><td colspan="6"><div class="empty-state" style="padding:36px;"><i data-lucide="users"></i><p>No se encontraron usuarios</p></div></td></tr>';
  } else {
    tbody.innerHTML = filtered
      .map((u) => {
        const isActive = u.estado === 'activo';
        const displayName = u.nombre || u.username || '';
        const initial = (displayName.trim().charAt(0) || '?').toUpperCase();
        const rolLabel = roleLabels[u.rol] || u.rol || '';
        const toggleUrl = toggleTpl.replace('/0/', '/' + u.id + '/');
        const isSelf = currentUserId && String(u.id) === currentUserId;

        let actionsHtml = '';
        if (isSelf) {
          actionsHtml = '<span style="color:var(--text-muted);font-size:12px;">Tu cuenta</span>';
        } else if (u.rol === 'administrador') {
          actionsHtml = '<span style="color:var(--text-muted);font-size:12px;">Protegido</span>';
        } else {
          const jsName = escapeAdminJs(displayName);
          const jsRol = escapeAdminJs(rolLabel);
          const jsUser = escapeAdminJs(u.username || '');
          actionsHtml =
            `<div class="user-actions-group">` +
              `<form action="${escapeAdminHtml(toggleUrl)}" method="POST" style="display:inline;" class="form-toggle-usuario">` +
                `<input type="hidden" name="csrfmiddlewaretoken" value="${escapeAdminHtml(csrfToken)}">` +
                `<button type="button" class="user-icon-btn ${isActive ? 'is-active' : ''}" ` +
                  `onclick="openToggleUserConfirmModal(this, '${escapeAdminHtml(jsName)}', '${escapeAdminHtml(jsRol)}', ${isActive ? 'true' : 'false'})" ` +
                  `title="${isActive ? 'Suspender usuario' : 'Reactivar usuario'}">` +
                  `<i data-lucide="${isActive ? 'toggle-right' : 'toggle-left'}"></i>` +
                `</button>` +
              `</form>` +
              `<button type="button" class="user-icon-btn" onclick="openEditUserModal(${Number(u.id)})" title="Editar">` +
                `<i data-lucide="pencil"></i>` +
              `</button>` +
              `<button type="button" class="user-icon-btn is-danger" onclick="deleteUser(${Number(u.id)}, '${escapeAdminHtml(jsUser)}')" title="Eliminar">` +
                `<i data-lucide="trash-2"></i>` +
              `</button>` +
            `</div>`;
        }

        const statusHtml = isActive
          ? '<span class="status-pill status-pill--active"><i class="status-dot"></i>Activo</span>'
          : '<span class="status-pill status-pill--inactive"><i class="status-dot"></i>Suspendido</span>';
        let fechaRegistro = '';
        let fechaDisplay = '—';
        if (u.date_joined) {
          const parsedDate = new Date(u.date_joined);
          if (!Number.isNaN(parsedDate.getTime())) {
            fechaRegistro = new Intl.DateTimeFormat('en-CA', {
              timeZone: 'America/Bogota',
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
            }).format(parsedDate);
            const parts = new Intl.DateTimeFormat('es-CO', {
              timeZone: 'America/Bogota',
              day: '2-digit',
              month: 'short',
              year: 'numeric',
            }).formatToParts(parsedDate);
            const day = parts.find((p) => p.type === 'day')?.value || '';
            const rawMonth = (parts.find((p) => p.type === 'month')?.value || '').replace(/\.$/, '');
            const month = rawMonth ? rawMonth.charAt(0).toUpperCase() + rawMonth.slice(1) : '';
            const year = parts.find((p) => p.type === 'year')?.value || '';
            fechaDisplay = `${day} ${month} ${year}`.trim() || fechaRegistro;
          } else {
            fechaRegistro = String(u.date_joined).slice(0, 10);
            fechaDisplay = fechaRegistro || '—';
          }
        }

        return (
          `<tr data-username="${escapeAdminHtml(u.username || '')}" data-nombre="${escapeAdminHtml(u.nombre || '')}" ` +
            `data-email="${escapeAdminHtml(u.email || '')}" data-rol="${escapeAdminHtml(u.rol || '')}" ` +
            `data-active="${isActive ? 'active' : 'inactive'}" data-id="${escapeAdminHtml(u.id)}" ` +
            `data-fecha-registro="${escapeAdminHtml(fechaRegistro)}">` +
            `<td><div class="user-cell"><div class="user-cell-avatar">${escapeAdminHtml(initial)}</div>` +
              `<div><div class="user-cell-username">${escapeAdminHtml(displayName)}</div>` +
              `<div class="user-cell-handle">@${escapeAdminHtml(u.username || '')}</div></div></div></td>` +
            `<td class="user-cell-email">${escapeAdminHtml(u.email || '')}</td>` +
            `<td>${escapeAdminHtml(rolLabel)}</td>` +
            `<td>${statusHtml}</td>` +
            `<td class="user-cell-date">${escapeAdminHtml(fechaDisplay)}</td>` +
            `<td style="text-align:right; white-space:nowrap;">${actionsHtml}</td>` +
          `</tr>`
        );
      })
      .join('');
  }

  const countEl = document.getElementById('usersResultCount');
  if (countEl) {
    countEl.textContent = `Mostrando ${filtered.length} usuarios`;
  }
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

let _usersFilterController = null;

export async function filterUsers() {
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
  if (status === 'active') params.set('estado', 'activo');
  if (fechaDesde) params.set('fecha_desde', fechaDesde);
  if (fechaHasta) params.set('fecha_hasta', fechaHasta);

  if (_usersFilterController) {
    try {
      _usersFilterController.abort();
    } catch (e) {}
  }
  _usersFilterController = typeof AbortController !== 'undefined' ? new AbortController() : null;

  try {
    const queryStr = params.toString();
    const url = apiUrl + (queryStr ? '?' + queryStr : '');
    const response = await fetch(url, {
      headers: { Accept: 'application/json' },
      signal: _usersFilterController ? _usersFilterController.signal : undefined,
    });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const payload = await response.json();
    let users = Array.isArray(payload)
      ? payload
      : Array.isArray(payload.usuarios)
        ? payload.usuarios
        : [];
    if (status === 'inactive') {
      users = users.filter((u) => u.estado !== 'activo');
    }
    _renderUsersTableRows(users, role);
  } catch (err) {
    if (err && err.name === 'AbortError') return;
    filterUsersClientSide();
  }
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
