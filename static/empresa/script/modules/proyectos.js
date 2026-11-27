/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Proyectos & Ofertas
 * (Crear, Editar, Filtrar y Confirmar Retiro)
 * ============================================================
 */

import { t, mostrarToastCorp, switchTab } from './ui_core.js';
import { initCorpDatepicker, setDatepickerValue } from './datepicker.js';

// --- Modal de Nuevo Proyecto ---

export function abrirModal() {
  const modal = document.getElementById('modalProyecto');
  if (modal) {
    modal.classList.add('open');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    initCorpDatepicker('datepicker-crear');
    const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
    if (firstInput) firstInput.focus();
  }
}

export function cerrarModal() {
  const modal = document.getElementById('modalProyecto');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

// --- Buscador + Filtro de Modalidad en Tiempo Real de Ofertas ---

let filtroModalidadOfertas = 'todas';
let queryOfertas = '';

function aplicarFiltrosOfertas() {
  const cards = document.querySelectorAll('.offers-grid-corp .offer-card-corp');
  let visibles = 0;

  cards.forEach(function (card) {
    const text = card.textContent.toLowerCase();
    const coincideTexto = !queryOfertas || text.indexOf(queryOfertas) !== -1;
    const modalidad = (card.dataset.modalidad || 'remoto').toLowerCase();
    const coincideModalidad = filtroModalidadOfertas === 'todas' || modalidad === filtroModalidadOfertas;
    const visible = coincideTexto && coincideModalidad;

    card.style.display = visible ? '' : 'none';
    if (visible) visibles += 1;
  });

  const sinResultados = document.getElementById('ofertasSinResultados');
  if (sinResultados) {
    sinResultados.style.display = (visibles === 0 && cards.length > 0) ? 'block' : 'none';
  }
}

export function filtrarOfertasEnTiempoReal(input) {
  queryOfertas = ((input && input.value) || '').toLowerCase().trim();
  aplicarFiltrosOfertas();
}

export function filtrarOfertasPorModalidad(valor, btn) {
  filtroModalidadOfertas = (valor || 'todas').toLowerCase();

  document.querySelectorAll('.offers-filter-bar .offers-filter-pill').forEach(function (pill) {
    pill.classList.toggle('is-active', pill === btn);
  });

  aplicarFiltrosOfertas();
}

// --- Modal de Edición de Proyecto In-Situ (Mis Ofertas) ---

export function abrirModalEditarProyecto(event, id, actionUrl, titulo, descripcion, tipo_solucion, prioridad, modalidad, ciudad, fecha_limite, vacantes, fecha_cumplimiento, soloBasicos) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  const modal = document.getElementById('modalEditarProyecto');
  const form = document.getElementById('formEditarProyecto');

  if (form) form.action = actionUrl;

  const tituloInput = document.getElementById('edit_titulo');
  if (tituloInput) tituloInput.value = titulo || '';

  const descInput = document.getElementById('edit_descripcion');
  if (descInput) descInput.value = descripcion || '';

  const tipoSelect = document.getElementById('edit_tipo_solucion');
  if (tipoSelect && tipo_solucion) tipoSelect.value = tipo_solucion;

  const prioSelect = document.getElementById('edit_prioridad');
  if (prioSelect && prioridad) prioSelect.value = prioridad;

  const modSelect = document.getElementById('edit_modalidad');
  if (modSelect && modalidad) {
    modSelect.value = modalidad;
    if (typeof window.toggleCiudadProyecto === 'function') {
      window.toggleCiudadProyecto(modSelect, 'edit_ciudad_group');
    }
  }

  const ciudadInput = document.getElementById('edit_ciudad');
  if (ciudadInput) ciudadInput.value = ciudad || '';

  const fechaInput = document.getElementById('edit_fecha_limite');
  if (fechaInput) fechaInput.value = fecha_limite || '';

  const cumplimientoInput = document.getElementById('edit_fecha_cumplimiento');
  if (cumplimientoInput) cumplimientoInput.value = fecha_cumplimiento || '';

  const vacantesInput = document.getElementById('edit_vacantes');
  if (vacantesInput) vacantesInput.value = vacantes || '1';

  const restringido = Boolean(soloBasicos);
  [descInput, tipoSelect, modSelect, ciudadInput, cumplimientoInput, vacantesInput, document.getElementById('edit_fecha_limite_display')].forEach(function (el) {
    if (el) el.disabled = restringido;
  });

  setDatepickerValue('datepicker-editar', fecha_limite || '');

  if (modal) {
    modal.classList.add('open');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    if (tituloInput) tituloInput.focus();
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function cerrarModalEditarProyecto() {
  const modal = document.getElementById('modalEditarProyecto');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

// --- Modal de Confirmación para Retirar Oferta ---

window._formRetiroPendiente = null;

export function confirmarRetiroOferta(event, form, titulo) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  window._formRetiroPendiente = form;

  const modal = document.getElementById('modalConfirmarRetiro');
  const titleEl = document.getElementById('nombreOfertaRetirar');

  if (titleEl) titleEl.textContent = titulo || t('estaConvocatoria', 'esta convocatoria');
  if (modal) {
    modal.classList.add('open');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function cerrarModalConfirmarRetiro() {
  const modal = document.getElementById('modalConfirmarRetiro');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
  window._formRetiroPendiente = null;
}

export function ejecutarRetiroConfirmado() {
  if (window._formRetiroPendiente) {
    const form = window._formRetiroPendiente;
    cerrarModalConfirmarRetiro();
    form.submit();
  }
}

// --- Global Window Contracts ---

window.abrirModal = abrirModal;
window.cerrarModal = cerrarModal;
window.abrirModalEditarProyecto = abrirModalEditarProyecto;
window.cerrarModalEditarProyecto = cerrarModalEditarProyecto;
window.filtrarOfertasEnTiempoReal = filtrarOfertasEnTiempoReal;
window.filtrarOfertasPorModalidad = filtrarOfertasPorModalidad;
window.confirmarRetiroOferta = confirmarRetiroOferta;
window.cerrarModalConfirmarRetiro = cerrarModalConfirmarRetiro;
window.ejecutarRetiroConfirmado = ejecutarRetiroConfirmado;

// --- DOM Initialization ---

export function initProyectos() {
  const formCrear = document.getElementById('formCrearProyecto');
  if (formCrear) {
    formCrear.addEventListener('submit', async function (e) {
      e.preventDefault();
      const submitBtn = formCrear.querySelector('button[type="submit"]');
      const textoOrig = submitBtn ? submitBtn.innerHTML : '';
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="corp-spinner-sm" style="display:inline-block;width:13px;height:13px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;animation:spin 0.6s linear infinite;vertical-align:middle;margin-right:6px;"></span> Publicando...';
      }

      try {
        const formData = new FormData(formCrear);
        const res = await fetch(formCrear.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json',
          },
          credentials: 'same-origin',
        });

        const data = await res.json().catch(() => null);

        if (res.ok && data && data.ok) {
          cerrarModal();
          formCrear.reset();
          mostrarToastCorp(data.mensaje || '¡Convocatoria publicada exitosamente!');
          switchTab('ofertas');
          window.location.hash = '#ofertas';
          setTimeout(function () {
            window.location.reload();
          }, 350);
        } else {
          const errMsg = (data && data.mensaje) ? data.mensaje : 'Por favor verifica los datos de la convocatoria.';
          if (typeof mostrarToastCorp === 'function') {
            mostrarToastCorp(errMsg, true);
          } else if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
            window.JobDevsToast.mostrar({ tipo: 'error', mensaje: errMsg });
          } else if (typeof window.jdToast === 'function') {
            window.jdToast(errMsg, true);
          }
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = textoOrig;
          }
        }
      } catch (err) {
        console.error('Error al publicar convocatoria:', err);
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = textoOrig;
        }
        mostrarToastCorp('Error de conexión al publicar la convocatoria. Intenta de nuevo.', true);
      }
    });
  }

  // Backdrop del modal de proyectos
  const modal = document.getElementById('modalProyecto');
  if (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === modal) {
        cerrarModal();
      }
    });
  }

  // Backdrop del modal de editar proyecto
  const modalEditarProyecto = document.getElementById('modalEditarProyecto');
  if (modalEditarProyecto) {
    modalEditarProyecto.addEventListener('click', function (e) {
      if (e.target === modalEditarProyecto) {
        cerrarModalEditarProyecto();
      }
    });
  }

  // Backdrop del modal de confirmar retiro
  const modalConfirmarRetiro = document.getElementById('modalConfirmarRetiro');
  if (modalConfirmarRetiro) {
    modalConfirmarRetiro.addEventListener('click', function (e) {
      if (e.target === modalConfirmarRetiro) {
        cerrarModalConfirmarRetiro();
      }
    });
  }
}
