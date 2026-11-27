/* ─────────────────────────────────────────────────────────────
   Modal compartido "Ver proyecto" — admin, empresa y desarrollador.
   Carga el partial HTML vía HTMX (`HX-Request: true`) en `#jdpModal`.
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
      headers: { 'HX-Request': 'true', 'Accept': 'text/html' },
      credentials: 'same-origin',
      signal: controller.signal
    })
      .then(function (response) {
        return response.text().then(function (html) {
          return { response: response, html: html };
        });
      })
      .then(function (result) {
        var wrapper = document.createElement('div');
        wrapper.innerHTML = result.html || '';
        var partial = wrapper.querySelector('[data-jdp-partial]');

        if (!result.response.ok || !partial || partial.getAttribute('data-jdp-partial') !== 'ok') {
          if (partial && partial.getAttribute('data-jdp-partial') === 'error') {
            modal.querySelector('#jdpTitulo').textContent = 'No se pudo abrir el proyecto';
            modal.querySelector('[data-jdp-sub]').textContent = '';
            body.innerHTML = '';
            body.appendChild(partial);
            footer.hidden = true;
            refrescarIconos();
            return;
          }
          var fallback = result.response.status === 403
            ? 'No tienes permisos para ver este proyecto.'
            : 'No se pudo cargar la ficha del proyecto.';
          mostrarError(fallback);
          return;
        }

        hidratarPartial(partial);
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

  function hidratarPartial(partial) {
    var titulo = modal.querySelector('#jdpTitulo');
    var sub = modal.querySelector('[data-jdp-sub]');
    var body = modal.querySelector('[data-jdp-body]');
    var footer = modal.querySelector('[data-jdp-footer]');

    titulo.textContent = partial.getAttribute('data-jdp-titulo') || 'Proyecto';

    var subTpl = partial.querySelector('template[data-jdp-slot="sub"]');
    sub.innerHTML = subTpl ? subTpl.innerHTML : '';

    var bodySlot = partial.querySelector('[data-jdp-slot="body"]');
    body.innerHTML = bodySlot ? bodySlot.innerHTML : '';

    var footerTpl = partial.querySelector('template[data-jdp-slot="footer"]');
    footer.innerHTML = footerTpl ? footerTpl.innerHTML : '';
    footer.hidden = !footer.innerHTML.trim();

    var postularBtn = footer.querySelector('[data-jdp-postular-inline]');
    if (postularBtn && typeof window.abrirModalPostulacion === 'function') {
      postularBtn.addEventListener('click', function (e) {
        e.preventDefault();
        cerrar();
        window.abrirModalPostulacion({
          url: postularBtn.getAttribute('data-postulacion-url'),
          titulo: postularBtn.getAttribute('data-titulo') || '',
          empresa: postularBtn.getAttribute('data-empresa') || '',
          tipo: postularBtn.getAttribute('data-tipo') || '',
          prioridad: postularBtn.getAttribute('data-prioridad') || '',
          vacantes: Number(postularBtn.getAttribute('data-vacantes') || 0),
          cierre: postularBtn.getAttribute('data-cierre') || '',
          descripcion: postularBtn.getAttribute('data-descripcion') || ''
        });
      });
    }

    refrescarIconos();
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
