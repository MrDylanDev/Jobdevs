/**
 * ============================================================
 * JobDevs - Panel Administrador: CRUD de Usuarios y Modal
 * de Doble Confirmación de Suspensión / Reactivación
 * ============================================================
 */

import {
  getCSRFToken,
  closeModal,
  adminNotify,
  queueAdminToast,
  adminConfirm,
} from './ui_core.js';

// --- Users CRUD Modals ---

export function openCreateUserModal() {
  const form = document.getElementById('createUserForm');
  if (form) form.reset();
  syncCreateUserDocField();
  const modal = document.getElementById('createUserModal');
  if (modal) modal.classList.add('open');
}

export function syncCreateUserDocField() {
  const rol = document.getElementById('create-rol')?.value || 'empresa';
  const tipoGrp = document.getElementById('create-tipo-doc-group');
  const tipoDoc = document.getElementById('create-tipo-doc')?.value || 'nit';
  const grp = document.getElementById('create-identificacion-group');
  const lbl = document.getElementById('create-identificacion-label');
  const inp = document.getElementById('create-identificacion');
  if (!grp || !lbl || !inp) return;

  if (rol === 'administrador') {
    if (tipoGrp) tipoGrp.style.display = 'none';
    grp.style.display = 'none';
    inp.required = false;
    inp.value = '';
  } else if (rol === 'desarrollador') {
    if (tipoGrp) tipoGrp.style.display = 'none';
    grp.style.display = '';
    lbl.textContent = 'Número de Identificación';
    inp.placeholder = 'Ej: 1001234567';
    inp.required = true;
  } else {
    if (tipoGrp) tipoGrp.style.display = '';
    grp.style.display = '';
    if (tipoDoc === 'nit') {
      lbl.textContent = 'NIT';
      inp.placeholder = 'Ej: 899.999.034-1';
    } else {
      lbl.textContent = 'Cédula';
      inp.placeholder = 'Ej: 1001234567';
    }
    inp.required = true;
  }
}

export async function openEditUserModal(id) {
  try {
    const response = await fetch(`/api/${id}/`);
    const user = await response.json();
    if (response.ok) {
      document.getElementById('edit-id').value = user.id;
      document.getElementById('edit-email').value = user.email;
      document.getElementById('edit-nombre').value = user.nombre || '';
      const identEl = document.getElementById('edit-identificacion');
      if (identEl) identEl.value = user.identificacion || '';
      document.getElementById('edit-rol').value = user.rol;
      document.getElementById('editUserModal').classList.add('open');
    } else {
      adminNotify(user.error || 'No se pudo cargar el usuario.');
    }
  } catch (e) {
    adminNotify('Error de conexión.');
  }
}

export async function deleteUser(id, username) {
  const ok = await adminConfirm({
    titulo: 'Eliminar usuario permanentemente',
    mensaje: `¿Estás SEGURO de que deseas eliminar permanentemente al usuario ${username}? Esta acción no se puede deshacer.`,
    textoConfirmar: 'Eliminar usuario',
    peligro: true,
  });
  if (ok) {
    try {
      const response = await fetch(`/api/${id}/eliminar/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': getCSRFToken() },
      });
      if (response.ok) {
        queueAdminToast('Usuario eliminado correctamente.', 'success');
        window.location.href = '?section=usersSection';
      } else {
        const result = await response.json();
        adminNotify(result.error || 'No se pudo eliminar.');
      }
    } catch (e) {
      adminNotify('Error de red.');
    }
  }
}

// --- Modal Doble Confirmación Toggle Usuario (SCRUM-407) ---

let _pendingToggleUserForm = null;

export function openToggleUserConfirmModal(btn, nombre, rol, isActive) {
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
    if (msgEl) {
      msgEl.textContent =
        '¿Estás seguro de que deseas suspender el acceso de esta cuenta a la plataforma?';
    }
    if (submitBtn) {
      submitBtn.textContent = 'Suspender usuario';
      submitBtn.className = 'btn btn-danger';
    }
  } else {
    if (titleEl) titleEl.textContent = 'Confirmar reactivación de usuario';
    if (msgEl) {
      msgEl.textContent =
        '¿Estás seguro de que deseas reactivar el acceso de esta cuenta a la plataforma?';
    }
    if (submitBtn) {
      submitBtn.textContent = 'Reactivar usuario';
      submitBtn.className = 'btn btn-success';
    }
  }

  modal.classList.add('open');
}

export function confirmToggleUserAction() {
  if (_pendingToggleUserForm) {
    const form = _pendingToggleUserForm;
    _pendingToggleUserForm = null;
    closeModal('toggleUserConfirmModal');
    form.submit();
  }
}

// --- Users CRUD Forms Initialization ---

export function initUsuariosCrudForms() {
  const createUserForm = document.getElementById('createUserForm');
  if (createUserForm) {
    createUserForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const rol = document.getElementById('create-rol').value;
      const data = {
        nombre: (document.getElementById('create-nombre')?.value || '').trim(),
        username: document.getElementById('create-username').value,
        email: document.getElementById('create-email').value,
        tipo_documento: rol === 'empresa' ? (document.getElementById('create-tipo-doc')?.value || 'nit') : 'cedula',
        identificacion: (document.getElementById('create-identificacion')?.value || '').trim(),
        password: document.getElementById('create-password').value,
        rol: rol,
      };
      try {
        const response = await fetch('/api/crear/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
          body: JSON.stringify(data),
        });
        const result = await response.json();
        if (response.ok) {
          queueAdminToast('Usuario creado correctamente.', 'success');
          window.location.href = '?section=usersSection';
        } else {
          adminNotify(result.error || 'Error al crear usuario.');
        }
      } catch (err) {
        adminNotify('Error de red.');
      }
    });
  }

  const editUserForm = document.getElementById('editUserForm');
  if (editUserForm) {
    editUserForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const id = document.getElementById('edit-id').value;
      const data = {
        email: document.getElementById('edit-email').value,
        nombre: document.getElementById('edit-nombre').value,
        identificacion: (document.getElementById('edit-identificacion')?.value || '').trim(),
        rol: document.getElementById('edit-rol').value,
      };
      try {
        const response = await fetch(`/api/${id}/actualizar/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
          body: JSON.stringify(data),
        });
        if (response.ok) {
          queueAdminToast('Usuario actualizado correctamente.', 'success');
          window.location.href = '?section=usersSection';
        } else {
          const result = await response.json();
          adminNotify(result.error || 'Error al actualizar.');
        }
      } catch (err) {
        adminNotify('Error de red.');
      }
    });
  }
}
