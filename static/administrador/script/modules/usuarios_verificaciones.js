/**
 * ============================================================
 * JobDevs - Panel Administrador: Usuarios, Proyectos,
 * Categorías, Explorar Catálogo y Quick Search Barrel
 * ============================================================
 */

import {
  openCreateUserModal,
  syncCreateUserDocField,
  openEditUserModal,
  deleteUser,
  openToggleUserConfirmModal,
  confirmToggleUserAction,
  initUsuariosCrudForms,
} from './usuarios_crud.js';

import {
  filterUsersClientSide,
  _renderUsersTableRows,
  filterUsers,
  filterProjects,
  debouncedFilterUsers,
  debouncedFilterProjects,
  setAdminProjectEstadoPill,
  setAdminUserRolePill,
  switchUsersTab,
  filterAdminExplore,
  resetAdminExploreFilters,
  filterAdminQuickSearch,
  initUsuariosFiltros,
} from './usuarios_filtros.js';

import {
  _categoryApiUrl,
  openCategoryModal,
  toggleCategory,
  initCategoriasCrudForm,
} from './categorias_crud.js';

export {
  openCreateUserModal,
  syncCreateUserDocField,
  openEditUserModal,
  deleteUser,
  openToggleUserConfirmModal,
  confirmToggleUserAction,
  filterUsersClientSide,
  _renderUsersTableRows,
  filterUsers,
  filterProjects,
  debouncedFilterUsers,
  debouncedFilterProjects,
  setAdminProjectEstadoPill,
  setAdminUserRolePill,
  switchUsersTab,
  filterAdminExplore,
  resetAdminExploreFilters,
  filterAdminQuickSearch,
  _categoryApiUrl,
  openCategoryModal,
  toggleCategory,
};

// --- Module Initializer ---

export function initUsuariosVerificaciones() {
  // Expose inline HTML handlers on window
  window.openCreateUserModal = openCreateUserModal;
  window.syncCreateUserDocField = syncCreateUserDocField;
  window.openEditUserModal = openEditUserModal;
  window.deleteUser = deleteUser;
  window.openToggleUserConfirmModal = openToggleUserConfirmModal;
  window.confirmToggleUserAction = confirmToggleUserAction;
  window.filterUsersClientSide = filterUsersClientSide;
  window.filterUsers = filterUsers;
  window.debouncedFilterUsers = debouncedFilterUsers;
  window.filterProjects = filterProjects;
  window.debouncedFilterProjects = debouncedFilterProjects;
  window.setAdminProjectEstadoPill = setAdminProjectEstadoPill;
  window.setAdminUserRolePill = setAdminUserRolePill;
  window.switchUsersTab = switchUsersTab;
  window.filterAdminExplore = filterAdminExplore;
  window.resetAdminExploreFilters = resetAdminExploreFilters;
  window.openCategoryModal = openCategoryModal;
  window.toggleCategory = toggleCategory;
  window.filterAdminQuickSearch = filterAdminQuickSearch;

  initUsuariosCrudForms();
  initCategoriasCrudForm();
  initUsuariosFiltros();
  syncCreateUserDocField();
}
