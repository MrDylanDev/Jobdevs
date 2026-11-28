/**
 * JobDevs — Puente global HTMX v2 (CSRF, Lucide icons, HX-Trigger toasts,
 * refresco parcial de secciones y recuperación centralizada 403 CSRF).
 */
(function () {
  if (window.__jobdevsHtmxBridgeInit) return;
  window.__jobdevsHtmxBridgeInit = true;

  var csrfReloadScheduled = false;

  function getCsrfToken() {
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (match && match[1]) {
      return decodeURIComponent(match[1]);
    }
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input && input.value ? input.value : '';
  }

  function refreshSections(selectors) {
    if (!window.htmx || typeof window.htmx.ajax !== 'function') {
      return Promise.resolve([]);
    }

    var list = Array.isArray(selectors) ? selectors : (selectors ? [selectors] : []);
    var seen = Object.create(null);
    var uniqueSelectors = [];
    for (var i = 0; i < list.length; i++) {
      var sel = typeof list[i] === 'string' ? list[i].trim() : '';
      if (!sel || seen[sel]) continue;
      seen[sel] = true;
      if (document.querySelector(sel)) {
        uniqueSelectors.push(sel);
      }
    }

    if (!uniqueSelectors.length) {
      return Promise.resolve([]);
    }

    var url = window.location.pathname + window.location.search;
    var tasks = uniqueSelectors.map(function (selector) {
      var currentEl = document.querySelector(selector);
      var preserveTabState = Boolean(
        currentEl &&
        (currentEl.classList.contains('seccion-v') || currentEl.classList.contains('section-v'))
      );
      var hadActiva = Boolean(currentEl && currentEl.classList.contains('activa'));
      var hadActive = Boolean(currentEl && currentEl.classList.contains('active'));

      var onAfterSwap = function (ev) {
        var swapped = document.querySelector(selector);
        if (!swapped || !preserveTabState) return;
        swapped.classList.toggle('activa', hadActiva);
        swapped.classList.toggle('active', hadActive);
        if (ev && ev.detail && ev.detail.target && ev.detail.target.id === swapped.id) {
          document.removeEventListener('htmx:afterSwap', onAfterSwap);
        }
      };
      if (preserveTabState) {
        document.addEventListener('htmx:afterSwap', onAfterSwap);
      }

      return Promise.resolve(
        window.htmx.ajax('GET', url, {
          select: selector,
          target: selector,
          swap: 'outerHTML',
          headers: { 'Cache-Control': 'no-cache' },
        })
      ).then(
        function () {
          document.removeEventListener('htmx:afterSwap', onAfterSwap);
          var updatedEl = document.querySelector(selector);
          if (updatedEl && preserveTabState) {
            updatedEl.classList.toggle('activa', hadActiva);
            updatedEl.classList.toggle('active', hadActive);
          }
          return { selector: selector, ok: true };
        },
        function () {
          document.removeEventListener('htmx:afterSwap', onAfterSwap);
          return { selector: selector, ok: false };
        }
      );
    });

    return Promise.all(tasks);
  }

  window.JobDevsHTMX = Object.assign({}, window.JobDevsHTMX, {
    refreshSections: refreshSections,
  });

  document.addEventListener('htmx:configRequest', function (event) {
    var detail = event && event.detail;
    if (!detail) return;
    var verb = String(detail.verb || 'get').toUpperCase();
    if (verb === 'GET' || verb === 'HEAD') return;

    detail.headers = detail.headers || {};
    var hasHeader = Object.keys(detail.headers).some(function (key) {
      return key.toLowerCase() === 'x-csrftoken';
    });
    if (hasHeader) return;

    var token = getCsrfToken();
    if (token) {
      detail.headers['X-CSRFToken'] = token;
    }
  });

  document.addEventListener('htmx:responseError', function (event) {
    var detail = event && event.detail;
    var xhr = detail && detail.xhr;
    if (!xhr || xhr.status !== 403) return;

    var responseText = typeof xhr.responseText === 'string' ? xhr.responseText : '';
    if (!/csrf/i.test(responseText)) return;

    if (csrfReloadScheduled) return;
    csrfReloadScheduled = true;

    document.dispatchEvent(
      new CustomEvent('jobdevs:toast', {
        detail: {
          mensaje: 'Tu sesión de seguridad (CSRF) expiró. Actualizando la página…',
          tipo: 'warning',
        },
      })
    );

    setTimeout(function () {
      window.location.reload();
    }, 1200);
  });

  document.addEventListener('htmx:afterSwap', function (event) {
    if (!window.lucide || typeof window.lucide.createIcons !== 'function') return;
    var target = event && event.detail && event.detail.target;
    if (target && target.nodeType === 1) {
      try {
        window.lucide.createIcons({ root: target });
        return;
      } catch (e) {
        // Fallback to full document icon scan if root option is unsupported.
      }
    }
    window.lucide.createIcons();
  });

  document.addEventListener('jobdevs:toast', function (event) {
    var detail = event && event.detail ? event.detail : {};
    var payload = typeof detail === 'string'
      ? { mensaje: detail, tipo: 'info' }
      : {
          mensaje: detail.mensaje || detail.message || '',
          tipo: detail.tipo || detail.type || 'info',
          titulo: detail.titulo || detail.title,
          duracion: detail.duracion,
        };
    if (!payload.mensaje) return;

    if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
      window.JobDevsToast.mostrar(payload);
    } else if (window.JobDevsToast && typeof window.JobDevsToast.show === 'function') {
      window.JobDevsToast.show(payload);
    } else if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
      window.JobDevsSSE.mostrarToast(payload);
    }
  });
})();
