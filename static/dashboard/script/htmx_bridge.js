/**
 * JobDevs — Puente global HTMX v2 (CSRF, Lucide icons, HX-Trigger toasts).
 */
(function () {
  if (window.__jobdevsHtmxBridgeInit) return;
  window.__jobdevsHtmxBridgeInit = true;

  function getCsrfToken() {
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (match && match[1]) {
      return decodeURIComponent(match[1]);
    }
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input && input.value ? input.value : '';
  }

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
