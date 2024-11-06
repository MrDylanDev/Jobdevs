/* ─────────────────────────────────────────────────────────────
   Modal compartido "Ver proyecto" — admin, empresa y desarrollador.
   Intercepta enlaces [data-ver-proyecto], consulta la ficha JSON y la
   pinta sin abandonar el dashboard. Sin dependencias externas.
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

  function safeIcon(name) {
    return /^fa-[a-z0-9- ]+$/i.test(name || '') ? name : 'fa-solid fa-circle-info';
  }

  function estadoClass(estado) {
    var permitidos = ['publicado', 'en_desarrollo', 'en_revision', 'finalizado', 'rechazado', 'inactivo', 'en_disputa', 'pendiente', 'completado', 'cancelada'];
    return permitidos.indexOf(estado) !== -1 ? 'is-' + estado : '';
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
            '<div class="jdp-kicker">// Ficha del proyecto</div>' +
            '<h2 class="jdp-title" id="jdpTitulo">Cargando proyecto…</h2>' +
            '<div class="jdp-sub" data-jdp-sub></div>' +
          '</div>' +
          '<button type="button" class="jdp-close" data-jdp-close aria-label="Cerrar">&times;</button>' +
        '</header>' +
        '<div class="jdp-body" data-jdp-body aria-live="polite">' +
          '<div class="jdp-loading"><i class="fa-solid fa-circle-notch fa-spin"></i><span>Consultando la ficha del proyecto…</span></div>' +
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
    body.innerHTML = '<div class="jdp-loading"><i class="fa-solid fa-circle-notch fa-spin"></i><span>Consultando la ficha del proyecto…</span></div>';
    footer.hidden = true;
    footer.innerHTML = '';
    titulo.textContent = 'Cargando proyecto…';
    sub.textContent = '';
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
      '<div class="jdp-error"><i class="fa-solid fa-triangle-exclamation"></i>' +
      '<p>' + escapeHtml(mensaje) + '</p>' +
      '<button type="button" class="jdp-btn" data-jdp-close>Cerrar</button></div>';
    var footer = modal.querySelector('[data-jdp-footer]');
    footer.hidden = true;
  }

  function render(data) {
    var p = data.proyecto || {};
    var empresa = p.empresa || {};
    var sub = modal.querySelector('[data-jdp-sub]');
    modal.querySelector('#jdpTitulo').textContent = p.titulo || 'Proyecto';

    sub.innerHTML =
      '<span><i class="fa-solid fa-building" style="color:#00e676;margin-right:5px;"></i>' + escapeHtml(empresa.nombre || '') + '</span>' +
      (empresa.verificada
        ? '<span class="jdp-verified"><i class="fa-solid fa-circle-check"></i>' + escapeHtml(empresa.badge || 'Verificada') + '</span>'
        : '') +
      (Number(empresa.calificacion) > 0
        ? '<span><i class="fa-solid fa-star" style="color:#ffc107;margin-right:4px;"></i>' + Number(empresa.calificacion).toFixed(1) + '</span>'
        : '');

    var html = '';
    html += '<div class="jdp-status-row">';
    html += '<span class="jdp-badge ' + estadoClass(p.estado) + '">' + escapeHtml(p.estado_label || '') + '</span>';
    html += '<span class="jdp-badge">' + escapeHtml(p.tipo || 'Proyecto') + '</span>';
    html += '<span class="jdp-badge ' + (p.prioridad === 'alta' ? 'is-en_disputa' : (p.prioridad === 'media' ? 'is-pendiente' : '')) + '">Prioridad ' + escapeHtml(p.prioridad_label || p.prioridad || '') + '</span>';
    if (p.acepta_postulaciones) {
      html += '<span class="jdp-badge is-publicado"><i class="fa-solid fa-door-open"></i> Recibe postulaciones</span>';
    }
    html += '</div>';

    html += '<p class="jdp-desc">' + escapeHtml(p.descripcion || 'Sin descripción registrada.') + '</p>';
