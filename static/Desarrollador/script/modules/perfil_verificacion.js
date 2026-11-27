/**
 * Módulo Perfil & Verificación SENA — Dashboard Desarrollador
 * Modal de edición de perfil, guardado AJAX, vista previa de avatar,
 * modal de verificación SENA, pestañas y envío AJAX.
 */

import {
  leerCookie,
  sincronizarCsrf,
  _setupModalFocusTrap,
  _cleanupModalFocusTrap,
} from './ui_core.js';

// ═══════════════════════════════════════════════
// MODAL DE EDICIÓN DE PERFIL
// ═══════════════════════════════════════════════
let _perfilModalLastFocus = null;

export function abrirModalPerfilDev() {
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
  _setupModalFocusTrap(modal, cerrarModalPerfilDev);
}

export function cerrarModalPerfilDev() {
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
}

// ═══════════════════════════════════════════════
// MODAL FLOTANTE: VERIFICACIÓN SENA
// ═══════════════════════════════════════════════
let _verifModalLastFocus = null;

export function abrirVerificacion() {
  const modal = document.getElementById('modalVerificacion');
  if (!modal) return;
  _verifModalLastFocus = document.activeElement;
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

export function cerrarVerificacion() {
  const modal = document.getElementById('modalVerificacion');
  if (!modal || !modal.classList.contains('is-open')) return;
  _cleanupModalFocusTrap();
  modal.classList.remove('is-open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  if (_verifModalLastFocus && typeof _verifModalLastFocus.focus === 'function') {
    _verifModalLastFocus.focus();
  }
  _verifModalLastFocus = null;
}

export function limpiarErroresVerificacion(form) {
  form.querySelectorAll('.jd-error').forEach((el) => { el.textContent = ''; });
  form.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
  const feedback = document.querySelector('[data-verificacion-feedback]');
  if (feedback) {
    feedback.hidden = true;
    feedback.classList.remove('is-error');
    feedback.textContent = '';
  }
}

export function mostrarFeedbackVerificacion(mensaje, esError) {
  const feedback = document.querySelector('[data-verificacion-feedback]');
  if (!feedback) return;
  feedback.textContent = mensaje || '';
  feedback.hidden = !mensaje;
  feedback.classList.toggle('is-error', !!esError);
}

// Exponer en window para manejadores inline HTML y scripts hermanos
window.abrirModalPerfilDev = abrirModalPerfilDev;
window.cerrarModalPerfilDev = cerrarModalPerfilDev;
window.abrirVerificacion = abrirVerificacion;
window.cerrarVerificacion = cerrarVerificacion;

// ═══════════════════════════════════════════════
// INICIALIZACIÓN PERFIL Y VERIFICACIÓN
// ═══════════════════════════════════════════════
export function initPerfilVerificacion() {
  // Manejo AJAX del guardado de perfil para evitar recarga de pantalla
  const formPerfil = document.getElementById('formPerfilDev');
  if (formPerfil) {
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
        sincronizarCsrf(formPerfil);
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
  }

  // Vista previa en tiempo real de la foto de perfil
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

  // Cierre y pestañas del modal de verificación SENA
  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-cerrar-verificacion]')) {
      cerrarVerificacion();
      return;
    }

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
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
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
}
