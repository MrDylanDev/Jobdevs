/* =========================================
   Jobdevs // SYSTEM.ROOT — Login Modal, Recovery & Auth Spinner
   ========================================= */

export function initLoginModal() {
  /* ============================
     TOGGLE PASSWORD
     ============================ */
  const togglePassBtn = document.getElementById('togglePassTech');
  if (togglePassBtn) {
    togglePassBtn.addEventListener('click', function () {
      const input = document.getElementById('password');
      const mostrando = this.getAttribute('aria-pressed') === 'true';
      input.type = mostrando ? 'password' : 'text';
      // El estado lo pinta el CSS con aria-pressed; los dos ojos ya estan en el DOM.
      this.setAttribute('aria-pressed', mostrando ? 'false' : 'true');
    });
  }

  /* ============================
     I18N & RECOVERY FORM STATE
     ============================ */
  // Textos traducidos por el template: el JS no guarda copias en español.
  const TEXTOS_I18N = (function () {
    const nodo = document.getElementById('textos-i18n');
    if (!nodo) return {};
    try { return JSON.parse(nodo.textContent) || {}; } catch (e) { return {}; }
  })();

  function texto(clave, porDefecto) {
    const valor = TEXTOS_I18N[clave];
    return (typeof valor === 'string' && valor) ? valor : porDefecto;
  }

  const loginFormDiv = document.getElementById('loginForm');
  const recoveryFormDiv = document.getElementById('recoveryForm');
  const modalTitle = document.querySelector('#loginModal .modal-title');
  const recoveryOriginalHTML = recoveryFormDiv ? recoveryFormDiv.innerHTML : '';

  function showLogin() {
    if (loginFormDiv) loginFormDiv.style.display = 'block';
    if (recoveryFormDiv) recoveryFormDiv.style.display = 'none';
    if (modalTitle) modalTitle.textContent = texto('authTitle', 'AUTENTICACIÓN SEGURA');
  }

  function showRecovery() {
    if (loginFormDiv) loginFormDiv.style.display = 'none';
    if (recoveryFormDiv) {
      recoveryFormDiv.style.display = 'block';
      recoveryFormDiv.innerHTML = recoveryOriginalHTML;
      if (window.htmx && typeof window.htmx.process === 'function') {
        window.htmx.process(recoveryFormDiv);
      }
    }
    if (modalTitle) modalTitle.textContent = texto('recoveryTitle', 'RECUPERAR CONTRASEÑA');
  }

  if (recoveryFormDiv) {
    recoveryFormDiv.addEventListener('click', function (e) {
      if (e.target.closest('[data-back-to-login], #backToLoginLink, #backToLoginLink2')) {
        e.preventDefault();
        showLogin();
      } else if (e.target.closest('[data-retry-recovery]')) {
        e.preventDefault();
        showRecovery();
      }
    });
    recoveryFormDiv.addEventListener('htmx:sendError', function () {
      alert(texto('connectionError', 'Error de conexión. Intenta de nuevo.'));
    });
  }

  /* ============================
     MODAL DE LOGIN — controlador propio
     ============================ */
  // Bootstrap se cargaba entero (80 KB desde un segundo CDN) solo para abrir este
  // modal. Este controlador cubre lo que aportaba: ESC, clic en el fondo, bloqueo
  // del scroll del body, aria correcto, foco inicial, retorno del foco y trampa
  // de tabulacion. Un unico estado, sin instancias paralelas sobre el elemento.
  const loginModalEl = document.getElementById('loginModal');
  let focoPrevio = null;

  const SELECTOR_FOCALIZABLES = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',');

  function focalizablesDelModal() {
    if (!loginModalEl) return [];
    return Array.prototype.filter.call(
      loginModalEl.querySelectorAll(SELECTOR_FOCALIZABLES),
      function (el) { return el.offsetWidth > 0 || el.offsetHeight > 0; }
    );
  }

  function modalAbierto() {
    return !!(loginModalEl && loginModalEl.classList.contains('show'));
  }

  function abrirLoginModal() {
    if (!loginModalEl || modalAbierto()) return;
    focoPrevio = document.activeElement;
    loginModalEl.classList.add('show');
    loginModalEl.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
    const primero = loginModalEl.querySelector('#username') || focalizablesDelModal()[0];
    if (primero) primero.focus();
  }

  function cerrarLoginModal() {
    if (!modalAbierto()) return;
    loginModalEl.classList.remove('show');
    document.body.classList.remove('modal-open');
    // El foco vuelve al control que abrio el modal y recien despues se oculta
    // para lectores de pantalla: al reves, quedaria dentro de un nodo aria-hidden.
    if (focoPrevio && typeof focoPrevio.focus === 'function') focoPrevio.focus();
    focoPrevio = null;
    loginModalEl.setAttribute('aria-hidden', 'true');
    showLogin();
  }

  document.querySelectorAll('[data-abrir-login], [data-abrir-recuperar]').forEach(function (abridor) {
    abridor.addEventListener('click', function (e) {
      e.preventDefault();
      abrirLoginModal();
      if (abridor.hasAttribute('data-abrir-recuperar')) {
        showRecovery();
      }
    });
  });

  if (loginModalEl) {
    // Clic en el fondo: el velo lo pinta el propio .modal, asi que el blanco es
    // el elemento y no un backdrop aparte.
    loginModalEl.addEventListener('click', function (e) {
      if (e.target === loginModalEl) cerrarLoginModal();
    });
    const botonCerrar = loginModalEl.querySelector('[data-cerrar-login]');
    if (botonCerrar) {
      botonCerrar.addEventListener('click', function () { cerrarLoginModal(); });
    }
  }

  document.addEventListener('keydown', function (e) {
    if (!modalAbierto()) return;
    if (e.key === 'Escape') { e.preventDefault(); cerrarLoginModal(); return; }
    if (e.key !== 'Tab') return;
    const focos = focalizablesDelModal();
    if (!focos.length) return;
    const primero = focos[0];
    const ultimo = focos[focos.length - 1];
    if (e.shiftKey && document.activeElement === primero) {
      e.preventDefault(); ultimo.focus();
    } else if (!e.shiftKey && document.activeElement === ultimo) {
      e.preventDefault(); primero.focus();
    }
  });

  /* ============================
     DJANGO MESSAGES MODAL
     ============================ */
  const djangoMsgs = document.getElementById('django-messages');
  if (djangoMsgs) {
    const spans = djangoMsgs.querySelectorAll('span');
    const form = document.querySelector('#loginModal form');
    if (spans.length && form) {
      const msgContainer = document.createElement('div');
      msgContainer.style.marginBottom = '14px';
      spans.forEach(function (s) {
        const msgDiv = document.createElement('div');
        msgDiv.style.cssText = 'background:rgba(220,38,38,0.06);border:1px solid rgba(220,38,38,0.15);padding:10px 14px;margin-bottom:8px;font-size:13px;color:#fca5a5;display:flex;align-items:center;gap:8px;';
        const icon = document.createElement('span');
        icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-alert icono-linea" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>';
        icon.style.display = 'flex';
        msgDiv.appendChild(icon);
        const textNode = document.createTextNode(' ' + s.textContent.trim());
        msgDiv.appendChild(textNode);
        msgContainer.appendChild(msgDiv);
      });
      form.insertBefore(msgContainer, form.firstChild);
      abrirLoginModal();
    }
  }

  /* ============================
     URL PARAM MODAL
     ============================ */
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('login') === '1' || urlParams.has('recuperar')) {
    abrirLoginModal();
    if (urlParams.has('recuperar')) {
      showRecovery();
    }
    urlParams.delete('login');
    urlParams.delete('recuperar');
    if (window.history && window.history.replaceState) {
      const cleanQs = urlParams.toString();
      window.history.replaceState(null, '', window.location.pathname + (cleanQs ? '?' + cleanQs : '') + (window.location.hash || ''));
    }
  }

  const recoveryLink = document.getElementById('recoveryLink');
  if (recoveryLink) {
    recoveryLink.addEventListener('click', function (e) { e.preventDefault(); showRecovery(); });
  }

  /* ============================
     LOGIN SPINNER OVERLAY
     ============================ */
  const loginFormEl = document.getElementById('loginFormElement');
  const loginSpinnerOverlay = document.getElementById('loginSpinnerOverlay');
  if (loginFormEl) {
    loginFormEl.addEventListener('submit', function (e) {
      if (loginFormEl.dataset.submitting === '1') return;
      e.preventDefault();
      loginFormEl.dataset.submitting = '1';
      if (loginModalEl) {
        loginModalEl.classList.remove('show');
        loginModalEl.setAttribute('aria-hidden', 'true');
      }
      if (loginSpinnerOverlay) {
        loginSpinnerOverlay.style.display = 'flex';
        loginSpinnerOverlay.setAttribute('aria-hidden', 'false');
      }
      setTimeout(function () {
        loginFormEl.submit();
      }, 260);
    });
    window.addEventListener('pageshow', function () {
      loginFormEl.dataset.submitting = '0';
      if (loginSpinnerOverlay) {
        loginSpinnerOverlay.style.display = 'none';
        loginSpinnerOverlay.setAttribute('aria-hidden', 'true');
      }
    });
  }
}
