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

  function adminNotify(msg, isError) {
    if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
      window.JobDevsSSE.mostrarToast({ tipo: isError !== false ? 'alerta' : 'info', mensaje: msg });
      return;
    }
    if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
      window.JobDevsToast.mostrar({ tipo: isError !== false ? 'error' : 'success', mensaje: msg });
      return;
    }
    if (typeof window.jdToast === 'function') {
      window.jdToast(msg, isError !== false);
      return;
    }
    const t = document.createElement('div');
    t.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;background:#0a0a0a;color:#fff;border:1px solid rgba(255,255,255,0.15);border-left:3px solid ' + (isError !== false ? '#ef4444' : '#00e676') + ';padding:12px 16px;border-radius:8px;font-size:13px;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,0.5);transition:opacity 0.3s;';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 4000);
  }
  window.adminNotify = adminNotify;

  function adminConfirm(opts) {
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
          '<div class="modal-box" style="max-width:440px;">' +
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
      btnOk.textContent = opts.textoConfirmar || 'Confirmar';
      btnOk.className = 'btn ' + (opts.peligro === false ? 'btn-primary' : 'btn-danger');
      modal.classList.add('open');

      function cleanup(res) {
        modal.classList.remove('open');
        btnOk.onclick = null;
        btnCancel.onclick = null;
        modal.onclick = null;
        resolve(res);
      }
      btnOk.onclick = () => cleanup(true);
      btnCancel.onclick = () => cleanup(false);
      modal.onclick = (e) => { if (e.target === modal) cleanup(false); };
    });
  }
  window.adminConfirm = adminConfirm;

    try {
      const response = await fetch('/api/crear/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify(data)
      });
      const result = await response.json();
      if (response.ok) { window.location.href = '?section=usersSection'; }
      else { adminNotify(result.error || 'Error al crear usuario.'); }
    } catch (e) { adminNotify("Error de red."); }
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
      } else { adminNotify(user.error || "No se pudo cargar el usuario."); }
    } catch (e) { adminNotify("Error de conexión."); }
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
      else { const result = await response.json(); adminNotify(result.error || 'Error al actualizar.'); }
    } catch (e) { adminNotify("Error de red."); }
  });

  async function deleteUser(id, username) {
    const ok = await adminConfirm({
      titulo: 'Eliminar usuario permanentemente',
      mensaje: `¿Estás SEGURO de que deseas eliminar permanentemente al usuario ${username}? Esta acción no se puede deshacer.`,
      textoConfirmar: 'Eliminar usuario',
      peligro: true
    });
    if (ok) {
      try {
        const response = await fetch(`/api/${id}/eliminar/`, {
          method: 'DELETE',
          headers: { 'X-CSRFToken': getCSRFToken() }
        });
        if (response.ok) { window.location.href = '?section=usersSection'; }
        else { const result = await response.json(); adminNotify(result.error || 'No se pudo eliminar.'); }
      } catch (e) { adminNotify("Error de red."); }
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
    ].join(' ').toLowerCase();
    const escapedSearch = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const matchEstadoSearch = search ? new RegExp('(^|\\s)' + escapedSearch + '(\\s|$)').test(estadoText) : false;
    const matchSearch = !search || text.includes(search) || matchEstadoSearch;
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
  const ok = await window.adminConfirm({
    titulo: `${verb.charAt(0).toUpperCase() + verb.slice(1)} usuarios`,
    mensaje: `¿Confirmas que deseas ${verb} ${ids.length} usuario(s) seleccionado(s)?`,
    textoConfirmar: `${verb.charAt(0).toUpperCase() + verb.slice(1)} (${ids.length})`,
    peligro: action !== 'activate'
  });
  if (!ok) return;

  try {
    const response = await fetch('/api/bulk-toggle/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
      body: JSON.stringify({ ids: ids, action: action })
    });
    if (response.ok) { window.location.reload(); }
    else { const r = await response.json(); window.adminNotify(r.error || 'Error'); }
  } catch (e) { window.adminNotify('Error de red'); }
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

  modal.classList.add('open');
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
function _syncAdminDrawerAria(isOpen) {
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
  _syncAdminDrawerAria(isOpen);
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
  _syncAdminDrawerAria(false);
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
