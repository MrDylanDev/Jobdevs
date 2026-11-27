/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Modales de Disputas,
 * Calificaciones, Valoraciones y Filtros en Tiempo Real
 * ============================================================
 */

import { t, csrfTokenActual, escaparHtml, mostrarToastCorp } from './ui_utils.js';

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
  bodyEl.innerHTML = '<div class="drawer-loading" style="padding:36px 16px;"><i data-lucide="loader-circle" class="corp-spin"></i><p>' + t('cargandoFormularioDisputa', 'Cargando formulario de mediación...') + '</p></div>';

  modal.classList.add('open');
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }

  fetch(actionUrl)
    .then(function (res) {
      if (!res.ok) throw new Error('Error al cargar el formulario de disputa.');
      return res.text();
    })
    .then(function (html) {
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const form = doc.getElementById('form-disputa');
      if (!form) throw new Error('Formulario no disponible.');

      form.setAttribute('action', actionUrl);
      form.style.background = 'transparent';
      form.style.border = '0';
      form.style.padding = '0';
      form.style.boxShadow = 'none';

      const cancelLink = form.querySelector('.disp-actions a');
      if (cancelLink) {
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn-corp-action secondary';
        cancelBtn.textContent = cancelLink.textContent || 'Cancelar';
        cancelBtn.addEventListener('click', cerrarModalDisputa);
        cancelLink.replaceWith(cancelBtn);
      }

      bodyEl.innerHTML = '';
      bodyEl.appendChild(form);

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

      form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        const errBox = form.querySelector('#disputa-error');
        const submitBtn = form.querySelector('button[type="submit"]');
        const oldBtnHtml = submitBtn ? submitBtn.innerHTML : '';

        if (errBox) {
          errBox.style.display = 'none';
          errBox.textContent = '';
        }
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Enviando...';
        }

        fetch(actionUrl, {
          method: 'POST',
          body: new FormData(form),
          headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfTokenActual(),
          },
        })
          .then(function (res) {
            return res.json().then(function (data) {
              return { ok: res.ok, data: data };
            }).catch(function () {
              return { ok: res.ok, data: { ok: res.ok, mensaje: res.ok ? 'Disputa abierta.' : 'No se pudo abrir la disputa.' } };
            });
          })
          .then(function (result) {
            if (!result.ok || result.data.ok === false) {
              if (errBox) {
                errBox.textContent = result.data.mensaje || 'Revisa los campos obligatorios.';
                errBox.style.display = 'block';
              }
              if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = oldBtnHtml;
              }
              return;
            }
            cerrarModalDisputa();
            mostrarToastCorp(result.data.mensaje || 'Disputa abierta exitosamente.');
            setTimeout(function () {
              window.location.hash = 'desarrollo';
              window.location.reload();
            }, 900);
          })
          .catch(function () {
            if (errBox) {
              errBox.textContent = 'Error de conexión al enviar la disputa.';
              errBox.style.display = 'block';
            }
            if (submitBtn) {
              submitBtn.disabled = false;
              submitBtn.innerHTML = oldBtnHtml;
            }
          });
      });

      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    })
    .catch(function () {
      bodyEl.innerHTML = '<div class="activity-empty" style="padding:36px 16px;"><i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i><p>No se pudo cargar el formulario de disputa.</p></div>';
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    });
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

  fetch(actionUrl)
    .then(function (res) {
      if (!res.ok) throw new Error('Error al cargar calificación.');
      return res.text();
    })
    .then(function (html) {
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const origForm = doc.querySelector('main form[method="post"]');
      if (!origForm) {
        bodyEl.innerHTML = '<div class="drawer-loading" style="padding:28px 16px;"><p>' + escaparHtml(t('todosCalificados', 'Todos los colaboradores de este proyecto ya fueron calificados.')) + '</p><button type="button" class="btn-corp-action secondary" onclick="cerrarModalCalificar()" style="margin-top:12px;">' + escaparHtml(t('cerrar', 'Cerrar')) + '</button></div>';
        return;
      }

      const csrfInput = origForm.querySelector('input[name="csrfmiddlewaretoken"]');
      const csrfVal = csrfInput ? csrfInput.value : '';
      const devNameEl = doc.querySelector('.card strong');
      const devName = devNameEl ? devNameEl.textContent.trim() : '';
      const restantesEl = doc.querySelector('.msg-error');
      const restantesTxt = restantesEl ? restantesEl.textContent.trim() : '';
      const hasStars = !!origForm.querySelector('.star-rating');

      if (!hasStars) {
        bodyEl.innerHTML = '<form id="formCalificarModal" method="post">' +
          '<input type="hidden" name="csrfmiddlewaretoken" value="' + escaparHtml(csrfVal) + '">' +
          '<p style="font-size:13.5px; color:var(--corp-slate-600); margin:0 0 18px;">' + escaparHtml(t('confirmarCierreProyecto', 'Todos los colaboradores han sido calificados. Confirma el cierre oficial del proyecto.')) + '</p>' +
          '<div class="modal-footer-corp"><button type="button" class="btn-corp-action secondary" onclick="cerrarModalCalificar()">' + escaparHtml(t('cancelar', 'Cancelar')) + '</button><button type="submit" class="btn-corp-primary">' + escaparHtml(t('confirmarFinalizar', 'Confirmar y Finalizar')) + '</button></div></form>';
      } else {
        bodyEl.innerHTML = '' +
          (devName ? '<div class="calificar-dev-summary"><div class="calificar-dev-label">' + escaparHtml(t('calificandoA', 'Calificando a')) + '</div><div class="calificar-dev-name">' + escaparHtml(devName) + '</div>' + (restantesTxt ? '<div class="calificar-dev-restantes">' + escaparHtml(restantesTxt) + '</div>' : '') + '</div>' : '') +
          '<form id="formCalificarModal" method="post">' +
            '<input type="hidden" name="csrfmiddlewaretoken" value="' + escaparHtml(csrfVal) + '">' +
            '<div class="form-group-corp" style="text-align:center;">' +
              '<div class="form-label-corp" style="margin-bottom:8px;">' + escaparHtml(t('puntuacionDev', 'Puntuación del Desarrollador')) + '</div>' +
              '<div class="corp-star-rating">' +
                '<input type="radio" name="puntuacion" value="5" id="modalStar5" required><label for="modalStar5" title="5">★</label>' +
                '<input type="radio" name="puntuacion" value="4" id="modalStar4"><label for="modalStar4" title="4">★</label>' +
                '<input type="radio" name="puntuacion" value="3" id="modalStar3"><label for="modalStar3" title="3">★</label>' +
                '<input type="radio" name="puntuacion" value="2" id="modalStar2"><label for="modalStar2" title="2">★</label>' +
                '<input type="radio" name="puntuacion" value="1" id="modalStar1"><label for="modalStar1" title="1">★</label>' +
              '</div>' +
            '</div>' +
            '<div class="form-group-corp">' +
              '<label class="form-label-corp" for="modalCalificarComentario">' + escaparHtml(t('comentariosAdicionales', 'Comentarios sobre el desempeño')) + '</label>' +
              '<textarea id="modalCalificarComentario" name="comentario" class="form-input-corp" rows="4" required minlength="20" maxlength="2000" placeholder="' + escaparHtml(t('placeholderCalificacion', 'Describe tu experiencia trabajando con este desarrollador (mínimo 20 caracteres)...')) + '"></textarea>' +
            '</div>' +
            '<div id="calificarModalError" style="display:none; color:var(--corp-danger); font-size:12.5px; font-weight:600; margin-bottom:10px;"></div>' +
            '<div class="modal-footer-corp">' +
              '<button type="button" class="btn-corp-action secondary" onclick="cerrarModalCalificar()">' + escaparHtml(t('cancelar', 'Cancelar')) + '</button>' +
              '<button type="submit" class="btn-corp-primary"><i data-lucide="star"></i><span>' + escaparHtml(t('guardarCalificacion', 'Enviar Calificación')) + '</span></button>' +
            '</div>' +
          '</form>';
      }

      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }

      const formEl = document.getElementById('formCalificarModal');
      if (formEl) {
        formEl.addEventListener('submit', function (ev) {
          ev.preventDefault();
          const submitBtn = formEl.querySelector('button[type="submit"]');
          const errBox = document.getElementById('calificarModalError');
          if (errBox) errBox.style.display = 'none';
          if (submitBtn) submitBtn.disabled = true;

          fetch(actionUrl, {
            method: 'POST',
            body: new FormData(formEl),
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
          })
            .then(function (r) {
              if (r.url && r.url.indexOf('/proyectos/finalizar/') !== -1 && r.ok) {
                // Aún quedan otros colaboradores por calificar o hubo validación
                abrirModalCalificar(null, actionUrl, titulo);
                return;
              }
              cerrarModalCalificar();
              mostrarToastCorp(t('calificacionGuardada', '¡Calificación enviada con éxito!'));
              setTimeout(function () {
                window.location.hash = 'historial';
                window.location.reload();
              }, 700);
            })
            .catch(function () {
              if (submitBtn) submitBtn.disabled = false;
              if (errBox) {
                errBox.textContent = t('errorCalificar', 'No se pudo enviar la calificación. Intenta de nuevo.');
                errBox.style.display = 'block';
              }
            });
        });
      }
    })
    .catch(function () {
      bodyEl.innerHTML = '<div class="drawer-loading" style="padding:28px 16px;"><p style="color:var(--corp-danger);">' + escaparHtml(t('errorCargarCalificacion', 'No se pudo cargar el formulario de calificación.')) + '</p></div>';
    });
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
