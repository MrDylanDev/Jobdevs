/**
 * ============================================================
 * JobDevs - Panel Administrador: CRUD de Categorías de Solución
 * ============================================================
 */

import {
  getCSRFToken,
  adminNotify,
  queueAdminToast,
} from './ui_core.js';

export function _categoryApiUrl(tpl, id) {
  return tpl.replace('/0/', '/' + id + '/');
}

async function _sendCategory(url, method, payload) {
  try {
    const response = await fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
      body: JSON.stringify(payload || {}),
    });
    const result = await response.json().catch(() => ({}));
    if (response.ok) {
      queueAdminToast('Categoría guardada correctamente.', 'success');
      window.location.href = '?section=categoriesSection';
    } else {
      adminNotify(result.error || 'No se pudo completar la operación.');
    }
  } catch (err) {
    adminNotify('Error de red.');
  }
}

export function openCategoryModal(id) {
  const form = document.getElementById('categoryForm');
  if (!form) return;
  form.reset();
  document.getElementById('category-id').value = id || '';
  if (id) {
    const row = document.querySelector('#categoriesTable tr[data-id="' + id + '"]');
    if (row) {
      document.getElementById('categoryModalTitle').textContent = 'Editar Categoría';
      document.getElementById('category-nombre').value = row.dataset.nombre;
      document.getElementById('category-slug').value = row.dataset.slug;
      document.getElementById('category-slug').disabled = true;
      document.getElementById('category-descripcion').value = row.dataset.descripcion;
      document.getElementById('category-activo').checked = row.dataset.activo === 'true';
    }
  } else {
    document.getElementById('categoryModalTitle').textContent = 'Nueva Categoría';
    document.getElementById('category-slug').disabled = false;
    document.getElementById('category-activo').checked = true;
  }
  const modal = document.getElementById('categoryModal');
  if (modal) modal.classList.add('open');
}

export function toggleCategory(id) {
  const form = document.getElementById('categoryForm');
  const toggleTpl = form?.dataset.urlToggle || '';
  if (!toggleTpl) return;
  _sendCategory(_categoryApiUrl(toggleTpl, id), 'POST');
}

export function initCategoriasCrudForm() {
  const categoryForm = document.getElementById('categoryForm');
  if (categoryForm) {
    categoryForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const id = document.getElementById('category-id').value;
      const payload = {
        nombre: document.getElementById('category-nombre').value,
        descripcion: document.getElementById('category-descripcion').value,
        activo: document.getElementById('category-activo').checked,
      };
      if (id) {
        const updateTpl = categoryForm.dataset.urlActualizar || '';
        if (updateTpl) _sendCategory(_categoryApiUrl(updateTpl, id), 'PUT', payload);
      } else {
        const slug = document.getElementById('category-slug').value.trim();
        if (slug) payload.slug = slug;
        const createUrl = categoryForm.dataset.urlCrear || '';
        if (createUrl) _sendCategory(createUrl, 'POST', payload);
      }
    });
  }
}
