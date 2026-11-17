function showSection(id, btn) {
    document.querySelectorAll('.section-v').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    const target = document.getElementById(id);
    if (target) target.classList.add('active');
    if (!btn) {
      btn = Array.from(document.querySelectorAll('.nav-item[onclick]')).find(b => (b.getAttribute('onclick') || '').indexOf("('" + id + "'") !== -1);
    }
    if (btn) btn.classList.add('active');
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  // Crud lógica
  function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
  }

  function closeModal(id) {
    document.getElementById(id).classList.remove('open');
  }

  function openCreateUserModal() {
    document.getElementById('createUserForm').reset();
    document.getElementById('createUserModal').classList.add('open');
  }

  document.getElementById('createUserForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const data = {
      username: document.getElementById('create-username').value,
      email: document.getElementById('create-email').value,
      password: document.getElementById('create-password').value,
      rol: document.getElementById('create-rol').value
    };

    try {
      const response = await fetch('/api/crear/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify(data)
      });
      const result = await response.json();
      if (response.ok) { window.location.href = '?section=usersSection'; }
      else { alert(result.error); }
    } catch (e) { alert("Error de red."); }
  });

  async function openEditUserModal(id) {
    try {
      const response = await fetch(`/api/${id}/`);
      const user = await response.json();
      if (response.ok) {
        document.getElementById('edit-id').value = user.id;
        document.getElementById('edit-email').value = user.email;
        document.getElementById('edit-nombre').value = user.nombre || '';
        document.getElementById('edit-rol').value = user.rol;
        document.getElementById('editUserModal').classList.add('open');
      } else { alert(user.error || "No se pudo cargar el usuario."); }
    } catch (e) { alert("Error de conexión."); }
  }

  document.getElementById('editUserForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const id = document.getElementById('edit-id').value;
    const data = {
      email: document.getElementById('edit-email').value,
      nombre: document.getElementById('edit-nombre').value,
      rol: document.getElementById('edit-rol').value
    };

    try {
      const response = await fetch(`/api/${id}/actualizar/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify(data)
      });
      if (response.ok) { window.location.href = '?section=usersSection'; }
      else { const result = await response.json(); alert(result.error); }
    } catch (e) { alert("Error de red."); }
  });

  async function deleteUser(id, username) {
    if (confirm(`¿Estás SEGURO de que deseas eliminar permanentemente al usuario ${username}? Esta acción no se puede deshacer.`)) {
      try {
        const response = await fetch(`/api/${id}/eliminar/`, {
          method: 'DELETE',
          headers: { 'X-CSRFToken': getCSRFToken() }
        });
        if (response.ok) { window.location.href = '?section=usersSection'; }
        else { const result = await response.json(); alert(result.error); }
      } catch (e) { alert("Error de red."); }
    }
  }

  window.onload = function() {
    const s = new URLSearchParams(window.location.search).get('section');
    if (s) showSection(s);
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    const search = document.getElementById('adminExploreSearch');
    const cat = document.getElementById('adminExploreCategory');
    const estado = document.getElementById('adminExploreEstado');
    if (search) search.addEventListener('input', filterAdminExplore);
    if (cat) cat.addEventListener('change', filterAdminExplore);
    if (estado) estado.addEventListener('change', filterAdminExplore);

    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  });

// ═══════════════════════════════════════════════
// FILTRADO DINÁMICO: Explorar Catálogo (Admin)
// ═══════════════════════════════════════════════
function filterAdminExplore() {
  const searchInput = document.getElementById('adminExploreSearch');
  const catSelect = document.getElementById('adminExploreCategory');
  const estadoSelect = document.getElementById('adminExploreEstado');
  if (!searchInput) return;

  const q = (searchInput.value || '').toLowerCase().trim();
  const cat = (catSelect ? catSelect.value : '').toLowerCase().trim();
  const estado = (estadoSelect ? estadoSelect.value : '').toLowerCase().trim();

  const cards = document.querySelectorAll('.admin-explore-card');
  let visibleCount = 0;

  cards.forEach(card => {
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
    noMatches.style.display = (visibleCount === 0 && cards.length > 0) ? 'block' : 'none';
  }
  const badge = document.getElementById('adminExploreCountBadge');
  if (badge) {
    badge.textContent = visibleCount + ' PROYECTOS';
  }
}

function resetAdminExploreFilters() {
  const searchInput = document.getElementById('adminExploreSearch');
  const catSelect = document.getElementById('adminExploreCategory');
  const estadoSelect = document.getElementById('adminExploreEstado');
  if (searchInput) searchInput.value = '';
  if (catSelect) catSelect.value = '';
  if (estadoSelect) estadoSelect.value = '';
  filterAdminExplore();
}

// ═══════════════════════════════════════════════
// SEARCH & FILTER: Users & Projects (SCRUM-408)
// ═══════════════════════════════════════════════
function debounce(fn, delay = 300) {
  let timer = null;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

function filterUsers() {
  const search = (document.getElementById('userSearch')?.value || '').toLowerCase().trim();
  const role = document.getElementById('userRoleFilter')?.value || '';
  const status = document.getElementById('userStatusFilter')?.value || '';

  const rows = document.querySelectorAll('#usersTable tbody tr');
  let visible = 0;
  rows.forEach(row => {
    const estadoText = row.dataset.active === 'active' ? 'activo' : 'inactivo suspendido';
    const text = [
      row.dataset.username || '',
      row.dataset.nombre || '',
      row.dataset.email || '',
      row.dataset.rol || '',
      estadoText,
    ].join(' ').toLowerCase();
    const matchSearch = !search || text.includes(search);
    const matchRole = !role || row.dataset.rol === role;
    const matchStatus = !status || row.dataset.active === status;
    const show = matchSearch && matchRole && matchStatus;
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  const countEl = document.getElementById('usersResultCount');
  if (countEl) {
    countEl.textContent = `Mostrando ${visible} de ${rows.length} usuarios`;
  }
  updateBulkActions();
}

function filterProjects() {
  const search = (document.getElementById('projectSearch')?.value || '').toLowerCase().trim();
  const estado = document.getElementById('projectEstadoFilter')?.value || '';

  const rows = document.querySelectorAll('#projectsSection .data-table tbody tr');
  let visible = 0;
  rows.forEach(row => {
    const text = [
      row.dataset.titulo || '',
      row.dataset.empresa || '',
      row.dataset.estado || '',
    ].join(' ').toLowerCase();
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

const debouncedFilterUsers = debounce(filterUsers, 300);
const debouncedFilterProjects = debounce(filterProjects, 300);

document.addEventListener('DOMContentLoaded', () => {
  filterUsers();
  filterProjects();
});

// ═══════════════════════════════════════════════
// BULK ACTIONS: Users
// ═══════════════════════════════════════════════
function toggleAllUsers(checkbox) {
  document.querySelectorAll('.user-checkbox').forEach(cb => {
    const row = cb.closest('tr');
    if (row.style.display !== 'none') cb.checked = checkbox.checked;
  });
  updateBulkActions();
}

function updateBulkActions() {
  const checked = document.querySelectorAll('.user-checkbox:checked');
  const bar = document.getElementById('bulkActions');
  const count = document.getElementById('bulkCount');
  bar.style.display = checked.length > 0 ? 'flex' : 'none';
  count.textContent = checked.length + ' seleccionado' + (checked.length !== 1 ? 's' : '');
}

async function bulkToggleUsers(action) {
  const ids = Array.from(document.querySelectorAll('.user-checkbox:checked')).map(cb => cb.value);
  if (!ids.length) return;
  const verb = action === 'activate' ? 'activar' : 'suspender';
  if (!confirm(`¿${verb.charAt(0).toUpperCase() + verb.slice(1)} ${ids.length} usuario(s)?`)) return;

  try {
    const response = await fetch('/api/bulk-toggle/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
      body: JSON.stringify({ ids: ids, action: action })
    });
    if (response.ok) { window.location.reload(); }
    else { const r = await response.json(); alert(r.error || 'Error'); }
  } catch (e) { alert('Error de red'); }
}

// ═══════════════════════════════════════════════
// MODAL DOBLE CONFIRMACIÓN TOGGLE USUARIO (SCRUM-407)
// ═══════════════════════════════════════════════
let _pendingToggleUserForm = null;

function openToggleUserConfirmModal(btn, nombre, rol, isActive) {
  _pendingToggleUserForm = btn ? btn.closest('form') : null;
  const modal = document.getElementById('toggleUserConfirmModal');
  if (!modal || !_pendingToggleUserForm) return;

  const titleEl = document.getElementById('toggleConfirmTitle');
  const msgEl = document.getElementById('toggleConfirmMessage');
  const nameEl = document.getElementById('toggleConfirmUserName');
  const roleEl = document.getElementById('toggleConfirmUserRole');
  const submitBtn = document.getElementById('toggleConfirmSubmitBtn');

  if (nameEl) nameEl.textContent = nombre || 'Usuario';
  if (roleEl) roleEl.textContent = rol || '—';

  if (isActive) {
    if (titleEl) titleEl.textContent = 'Confirmar suspensión de usuario';
    if (msgEl) msgEl.textContent = '¿Estás seguro de que deseas suspender el acceso de esta cuenta a la plataforma?';
    if (submitBtn) {
      submitBtn.textContent = 'Suspender usuario';
      submitBtn.className = 'btn btn-danger';
    }
  } else {
    if (titleEl) titleEl.textContent = 'Confirmar reactivación de usuario';
    if (msgEl) msgEl.textContent = '¿Estás seguro de que deseas reactivar el acceso de esta cuenta a la plataforma?';
    if (submitBtn) {
      submitBtn.textContent = 'Reactivar usuario';
      submitBtn.className = 'btn btn-success';
    }
  }

  modal.classList.add('active');
}

function confirmToggleUserAction() {
  if (_pendingToggleUserForm) {
    const form = _pendingToggleUserForm;
    _pendingToggleUserForm = null;
    closeModal('toggleUserConfirmModal');
    form.submit();
  }
}

// ═══════════════════════════════════════════════
// DRAWER MÓVIL ACCESIBLE (SCRUM-411)
// ═══════════════════════════════════════════════
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (sidebar) sidebar.classList.toggle('is-open');
  if (backdrop) backdrop.classList.toggle('is-open');
}

function closeSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (sidebar) sidebar.classList.remove('is-open');
  if (backdrop) backdrop.classList.remove('is-open');
}

document.addEventListener('DOMContentLoaded', () => {
  const backdrop = document.getElementById('sidebarBackdrop');
  if (backdrop) backdrop.addEventListener('click', closeSidebar);
  document.querySelectorAll('.sidebar .nav-item').forEach((item) => {
    item.addEventListener('click', () => {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });
});
