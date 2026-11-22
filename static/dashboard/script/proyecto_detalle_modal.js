/* ─────────────────────────────────────────────────────────────
   Modal compartido "Ver proyecto" — admin, empresa y desarrollador.
   Consulta la ficha JSON y la pinta con diseño Cockpit de alta fidelidad.
   ───────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var modal = null;
  var lastFocus = null;
  var controller = null;

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function estadoClass(estado) {
    var permitidos = ['publicado', 'en_desarrollo', 'en_revision', 'finalizado', 'rechazado', 'inactivo', 'en_disputa', 'pendiente', 'completado', 'cancelada'];
    return permitidos.indexOf(estado) !== -1 ? 'is-' + estado : '';
  }

  function refrescarIconos() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  function ensureModal() {
    if (modal) return modal;

    modal = document.createElement('div');
    modal.className = 'jdp-modal';
    modal.id = 'jdpModal';
    modal.hidden = true;
    modal.innerHTML =
      '<div class="jdp-backdrop" data-jdp-close></div>' +
      '<div class="jdp-card" role="dialog" aria-modal="true" aria-labelledby="jdpTitulo">' +
        '<header class="jdp-header">' +
          '<div style="min-width:0;">' +
            '<div class="jdp-kicker">Ficha Técnica de Convocatoria</div>' +
            '<h2 class="jdp-title" id="jdpTitulo">Cargando proyecto…</h2>' +
            '<div class="jdp-sub" data-jdp-sub></div>' +
          '</div>' +
          '<button type="button" class="jdp-close" data-jdp-close aria-label="Cerrar">&times;</button>' +
        '</header>' +
        '<div class="jdp-body" data-jdp-body aria-live="polite">' +
          '<div class="jdp-loading"><i data-lucide="loader-2"></i><span>Consultando la ficha del proyecto…</span></div>' +
        '</div>' +
        '<footer class="jdp-footer" data-jdp-footer hidden></footer>' +
      '</div>';

    document.body.appendChild(modal);
    modal.addEventListener('click', function (event) {
      if (event.target.closest('[data-jdp-close]')) {
        event.preventDefault();
        cerrar();
      }
    });
    document.addEventListener('keydown', onKeydown);
    return modal;
  }

  function onKeydown(event) {
    if (!modal || modal.hidden) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      cerrar();
      return;
    }
    if (event.key !== 'Tab') return;
    var focusables = Array.prototype.slice.call(
      modal.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')
    ).filter(function (el) { return el.offsetParent !== null; });
    if (!focusables.length) return;
    var first = focusables[0];
    var last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function abrir(enlace) {
    lastFocus = document.activeElement;
    ensureModal();
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    var body = modal.querySelector('[data-jdp-body]');
    var footer = modal.querySelector('[data-jdp-footer]');
    var titulo = modal.querySelector('#jdpTitulo');
    var sub = modal.querySelector('[data-jdp-sub]');
    body.scrollTop = 0;
    body.innerHTML = '<div class="jdp-loading"><i data-lucide="loader-2"></i><span>Consultando la ficha del proyecto…</span></div>';
    footer.hidden = true;
    footer.innerHTML = '';
    titulo.textContent = 'Cargando proyecto…';
    sub.textContent = '';
    refrescarIconos();

    setTimeout(function () {
      var close = modal.querySelector('.jdp-close');
      if (close) close.focus({ preventScroll: true });
    }, 30);

    if (controller) controller.abort();
    controller = new AbortController();

    fetch(enlace.getAttribute('data-url'), {
      method: 'GET',
      headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
      signal: controller.signal
    })
      .then(function (response) {
        return response.json().catch(function () { return null; }).then(function (data) {
          return { response: response, data: data };
        });
      })
      .then(function (result) {
        var data = result.data;
        if (!result.response.ok || !data || !data.ok) {
          var mensaje = (data && data.mensaje) || (result.response.status === 403
            ? 'No tienes permisos para ver este proyecto.'
            : 'No se pudo cargar la ficha del proyecto.');
          mostrarError(mensaje);
          return;
        }
        render(data);
      })
      .catch(function (error) {
        if (error && error.name === 'AbortError') return;
        mostrarError('Error de conexión al consultar el proyecto. Revisa tu red e inténtalo de nuevo.');
      });
  }

  function mostrarError(mensaje) {
    if (!modal) return;
    modal.querySelector('#jdpTitulo').textContent = 'No se pudo abrir el proyecto';
    modal.querySelector('[data-jdp-sub]').textContent = '';
    var body = modal.querySelector('[data-jdp-body]');
    body.innerHTML =
      '<div class="jdp-error"><i data-lucide="alert-triangle"></i>' +
      '<p>' + escapeHtml(mensaje) + '</p>' +
      '<button type="button" class="jdp-btn" data-jdp-close>Cerrar</button></div>';
    var footer = modal.querySelector('[data-jdp-footer]');
    footer.hidden = true;
    refrescarIconos();
  }

  function render(data) {
    var p = data.proyecto || {};
    var empresa = p.empresa || {};
    var sub = modal.querySelector('[data-jdp-sub]');
    modal.querySelector('#jdpTitulo').textContent = p.titulo || 'Proyecto';

    // 1. Subtítulo con Empresa, Verificación, Calificación y Modalidad
    var subHtml = '<div class="jdp-company-row">';
    subHtml += '<span class="jdp-company-name"><i data-lucide="building"></i> ' + escapeHtml(empresa.nombre || '') + '</span>';
    if (empresa.verificada) {
      subHtml += '<span class="jdp-verified"><i data-lucide="badge-check"></i> ' + escapeHtml(empresa.badge || 'Verificada') + '</span>';
    }
    if (Number(empresa.calificacion) > 0) {
      subHtml += '<span class="jdp-rating"><i data-lucide="star"></i> ' + Number(empresa.calificacion).toFixed(1) + '</span>';
    }
    if (p.modalidad) {
      var modIcon = p.modalidad === 'remoto' ? 'wifi' : (p.modalidad === 'hibrido' ? 'split' : 'map-pin');
      var ubicacionTexto = p.ubicacion_display || (escapeHtml(p.modalidad_label || p.modalidad) + (p.ciudad && p.modalidad !== 'remoto' ? ' · ' + escapeHtml(p.ciudad) : ''));
      subHtml += '<span class="jdp-modality"><i data-lucide="' + modIcon + '"></i> ' + ubicacionTexto + '</span>';
    }
    subHtml += '</div>';
    sub.innerHTML = subHtml;

    var html = '';

    // 2. Fila de Badges de Estado
    html += '<div class="jdp-status-row">';
    html += '<span class="jdp-badge ' + estadoClass(p.estado) + '"><i data-lucide="check-circle-2"></i> ' + escapeHtml(p.estado_label || '') + '</span>';
    if (p.tipo) {
      html += '<span class="jdp-badge"><i data-lucide="layers"></i> ' + escapeHtml(p.tipo) + '</span>';
    }
    if (p.prioridad) {
      var prioClass = p.prioridad === 'alta' ? 'is-alta' : (p.prioridad === 'media' ? 'is-media' : 'is-baja');
      html += '<span class="jdp-badge ' + prioClass + '"><i data-lucide="alert-circle"></i> Prioridad ' + escapeHtml(p.prioridad_label || p.prioridad) + '</span>';
    }
    if (p.acepta_postulaciones && (p.vacantes_disponibles > 0 || p.vacantes_disponibles == null)) {
      html += '<span class="jdp-badge is-open"><i data-lucide="door-open"></i> Convocatoria abierta</span>';
    }
    html += '</div>';

    // 3. Grid de Especificaciones Clave (Sin redundancias)
    html += '<div class="jdp-meta-grid">';
    html += '<div class="jdp-meta-card">' +
              '<span class="jdp-meta-label"><i data-lucide="users"></i> Vacantes</span>' +
              '<span class="jdp-meta-value">' + (p.vacantes_disponibles != null ? p.vacantes_disponibles : 0) + ' de ' + (p.vacantes || 0) + ' libres</span>' +
            '</div>';
    html += '<div class="jdp-meta-card">' +
              '<span class="jdp-meta-label"><i data-lucide="calendar"></i> Cierre</span>' +
              '<span class="jdp-meta-value">' + escapeHtml(p.fecha_limite || 'Sin límite') + '</span>' +
            '</div>';
    html += '<div class="jdp-meta-card">' +
              '<span class="jdp-meta-label"><i data-lucide="clock"></i> Publicado</span>' +
              '<span class="jdp-meta-value">' + escapeHtml(p.fecha_publicacion || '—') + '</span>' +
            '</div>';
    html += '<div class="jdp-meta-card">' +
              '<span class="jdp-meta-label"><i data-lucide="map-pin"></i> Modalidad</span>' +
              '<span class="jdp-meta-value">' + escapeHtml(p.ubicacion_display || p.modalidad_label || 'Remoto') + '</span>' +
            '</div>';
    html += '</div>';

    // 4. Descripción del Proyecto
    html += '<div class="jdp-desc-card">';
    html += '<h4 class="jdp-section-header"><i data-lucide="file-text"></i> Descripción de la Convocatoria</h4>';
    html += '<div class="jdp-desc-text">' + escapeHtml(p.descripcion || 'Sin descripción detallada registrada.') + '</div>';
    html += '</div>';

    // 5. Hitos del Proyecto (Solo si la empresa definió hitos)
    var totalHitos = p.hitos_totales || 0;
    var hechosHitos = p.hitos_completados || 0;
    if (totalHitos > 0 && p.hitos && p.hitos.length) {
      html += '<section class="jdp-section">';
      html += '<div class="jdp-section-title">' +
                '<span><i data-lucide="list-checks"></i> Plan de Hitos del Proyecto</span>' +
                '<span class="jdp-section-count">' + hechosHitos + '/' + totalHitos + ' completados (' + (Number(p.progreso) || 0) + '%)</span>' +
              '</div>';
      html += '<div class="jdp-progress-bar"><div class="jdp-progress-fill" style="width:' + Math.max(0, Math.min(100, Number(p.progreso) || 0)) + '%"></div></div>';
      html += '<ul class="jdp-list">';
      p.hitos.forEach(function (h, idx) {
        var isDone = h.estado === 'completado';
        var isRev = h.estado === 'en_revision';
        var iconName = isDone ? 'check-circle-2' : (isRev ? 'clock' : 'circle');
        html += '<li class="jdp-list-item ' + estadoClass(h.estado) + '">' +
                  '<i data-lucide="' + iconName + '" class="jdp-list-icon"></i>' +
                  '<div class="jdp-list-main">' +
                    '<span class="jdp-list-title">' + (idx + 1) + '. ' + escapeHtml(h.titulo) + '</span>' +
                    (h.descripcion ? '<span class="jdp-list-sub">' + escapeHtml(h.descripcion) + '</span>' : '') +
                  '</div>' +
                  '<span class="jdp-list-state">' + escapeHtml(h.estado_label || '') + '</span>' +
                '</li>';
      });
      html += '</ul>';
      html += '</section>';
    }

    // 6. Desarrolladores Contratados (Solo si hay contratados)
    if (p.contrataciones && p.contrataciones.length > 0) {
      html += '<section class="jdp-section">';
      html += '<div class="jdp-section-title">' +
                '<span><i data-lucide="users"></i> Desarrolladores Asignados</span>' +
                '<span class="jdp-section-count">' + p.contrataciones.length + '</span>' +
              '</div>';
      html += '<div class="jdp-team">';
      p.contrataciones.forEach(function (c) {
        html += '<span class="jdp-chip"><i data-lucide="code-2"></i> ' + escapeHtml(c.desarrollador || c.username || '') +
                ' <span class="jdp-list-state">' + escapeHtml(c.estado_label || '') + '</span></span>';
      });
      html += '</div>';
      html += '</section>';
    }

    modal.querySelector('[data-jdp-body]').innerHTML = html;

    // 7. Footer de Acciones
    var footer = modal.querySelector('[data-jdp-footer]');
    var acciones = data.acciones || [];
    var footerHtml = '';
    acciones.forEach(function (a) {
      var clase = a.estilo === 'primary' ? 'jdp-btn is-primary' : 'jdp-btn';
      var esPostularse = a.label === 'Postularme';
      var iconName = esPostularse ? 'rocket' : (a.icono || 'arrow-right');

      if (esPostularse && typeof window.abrirModalPostulacion === 'function') {
        footerHtml += '<button type="button" class="' + clase + '" data-jdp-postular-inline>' +
          '<i data-lucide="' + iconName + '"></i> ' + escapeHtml(a.label) + '</button>';
      } else {
        footerHtml += '<a class="' + clase + '" href="' + escapeHtml(a.url || '#') + '">' +
          '<i data-lucide="' + iconName + '"></i> ' + escapeHtml(a.label || 'Abrir') + '</a>';
      }
    });
    footerHtml += '<button type="button" class="jdp-btn" data-jdp-close><i data-lucide="x"></i> Cerrar</button>';
    footer.innerHTML = footerHtml;
    footer.hidden = false;

    // Conectar botón inline de postulación si existe
    var postularBtn = footer.querySelector('[data-jdp-postular-inline]');
    if (postularBtn) {
      postularBtn.addEventListener('click', function (e) {
        e.preventDefault();
        cerrar();
        if (typeof window.abrirModalPostulacion === 'function') {
          window.abrirModalPostulacion({
            url: aPostulacionUrl(p.id),
            titulo: p.titulo,
            empresa: empresa.nombre || '',
            tipo: p.tipo || '',
            prioridad: (p.prioridad || '').toUpperCase(),
            vacantes: p.vacantes_disponibles,
            cierre: p.fecha_limite || '',
            descripcion: p.descripcion || ''
          });
        }
      });
    }

    refrescarIconos();
  }

  function aPostulacionUrl(proyectoId) {
    return '/postulaciones/postularse/' + proyectoId + '/';
  }

  function cerrar() {
    if (!modal || modal.hidden) return;
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (controller) {
      controller.abort();
      controller = null;
    }
    if (lastFocus && typeof lastFocus.focus === 'function') {
      lastFocus.focus({ preventScroll: true });
    }
  }

  document.addEventListener('click', function (event) {
    var enlace = event.target.closest('[data-ver-proyecto]');
    if (!enlace) return;
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    abrir(enlace);
  });
})();
