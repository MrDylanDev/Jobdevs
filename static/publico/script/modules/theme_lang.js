/* =========================================
   Jobdevs // SYSTEM.ROOT — Theme & Language Controls
   ========================================= */

export function initThemeLang() {
  /* ============================
     CAMBIO DE IDIOMA (MICRO-INTERACCIÓN)
     ============================ */
  const langSwitchBtn = document.querySelector('.lang-switch');
  if (langSwitchBtn && langSwitchBtn.href) {
    langSwitchBtn.addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      langSwitchBtn.classList.add('is-switching');
      const targetHref = langSwitchBtn.href + (window.location.hash || '');
      setTimeout(function () {
        window.location.href = targetHref;
      }, 120);
    });
  }

  /* ============================
     TEMA CLARO / OSCURO
     El tema inicial ya lo fijó el script de <head> antes del primer paint.
     Acá solo se sincroniza la UI, se alterna y se recuerda la elección.
     ============================ */
  const CLAVE_TEMA = 'jobdevs-theme';
  const botonTema = document.getElementById('themeToggle');

  function temaActual() {
    return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  }

  // El switch muestra las dos posiciones: el estado lo comunica aria-pressed y
  // el CSS enciende el icono que corresponde, así que acá sólo se expone el estado.
  function pintarBotonTema(tema) {
    if (!botonTema) return;
    botonTema.setAttribute('aria-pressed', tema === 'light' ? 'true' : 'false');
  }

  function aplicarTema(tema, recordar) {
    document.documentElement.setAttribute('data-theme', tema);
    pintarBotonTema(tema);
    if (recordar) {
      try { localStorage.setItem(CLAVE_TEMA, tema); } catch (e) { /* modo privado */ }
    }
  }

  pintarBotonTema(temaActual());

  if (botonTema) {
    botonTema.addEventListener('click', function () {
      aplicarTema(temaActual() === 'light' ? 'dark' : 'light', true);
    });
  }

  // Sin elección guardada, el tema sigue al sistema mientras la página está abierta.
  if (window.matchMedia) {
    const consultaSistema = window.matchMedia('(prefers-color-scheme: light)');
    const seguimientoSistema = function (evento) {
      let guardado = null;
      try { guardado = localStorage.getItem(CLAVE_TEMA); } catch (e) { /* modo privado */ }
      if (guardado === 'light' || guardado === 'dark') return;
      aplicarTema(evento.matches ? 'light' : 'dark', false);
    };
    if (consultaSistema.addEventListener) {
      consultaSistema.addEventListener('change', seguimientoSistema);
    } else if (consultaSistema.addListener) {
      consultaSistema.addListener(seguimientoSistema);
    }
  }
}
