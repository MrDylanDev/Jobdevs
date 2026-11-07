/**
 * Lógica específica para el Dashboard de Desarrollador
 * (Manejado por Django y tabs.js)
 */

document.addEventListener("DOMContentLoaded", function () {
    // Inicialización específica si fuera necesaria
});

// Función para previsualizar foto de perfil antes de subir (opcional)
function previewFoto(event) {
    const reader = new FileReader();
    reader.onload = function() {
        const output = document.getElementById('fotoPerfil');
        output.src = reader.result;
    };
    reader.readAsDataURL(event.target.files[0]);
}

function verSeccion(id, btn) {
  document.querySelectorAll('.seccion-v').forEach(s => s.classList.remove('activa'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('activa');
  if (!btn) {
    btn = Array.from(document.querySelectorAll('.nav-item[onclick]')).find(b => (b.getAttribute('onclick') || '').indexOf("('" + id + "'") !== -1);
  }
  if (btn) btn.classList.add('active');
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// ═══════════════════════════════════════════════
// FILTRADO DINÁMICO: Explorar Proyectos (Dev)
// ═══════════════════════════════════════════════
function filterDevExplore() {
  const searchInput = document.getElementById('devExploreSearch');
  const catSelect = document.getElementById('devExploreCategory');
  const prioSelect = document.getElementById('devExplorePriority');
  if (!searchInput) return;

  const q = (searchInput.value || '').toLowerCase().trim();
  const cat = (catSelect ? catSelect.value : '').toLowerCase().trim();
  const prio = (prioSelect ? prioSelect.value : '').toLowerCase().trim();

  const cards = document.querySelectorAll('.dev-explore-card');
  let visibleCount = 0;

  cards.forEach(card => {
    const titulo = card.getAttribute('data-titulo') || '';
    const desc = card.getAttribute('data-desc') || '';
    const empresa = card.getAttribute('data-empresa') || '';
    const tipo = card.getAttribute('data-tipo') || '';
    const prioridad = card.getAttribute('data-prioridad') || '';

    const matchesQ = !q || titulo.includes(q) || desc.includes(q) || empresa.includes(q);
    const matchesCat = !cat || tipo === cat;
    const matchesPrio = !prio || prioridad === prio;

    if (matchesQ && matchesCat && matchesPrio) {
      card.style.display = 'flex';
      visibleCount++;
    } else {
      card.style.display = 'none';
    }
  });

  const noMatches = document.getElementById('devExploreNoMatches');
  if (noMatches) {
    noMatches.style.display = (visibleCount === 0 && cards.length > 0) ? 'block' : 'none';
  }
  const badge = document.getElementById('devExploreCountBadge');
  if (badge) {
    badge.textContent = visibleCount + ' DISPONIBLES';
  }
}

function resetDevExploreFilters() {
  const searchInput = document.getElementById('devExploreSearch');
  const catSelect = document.getElementById('devExploreCategory');
  const prioSelect = document.getElementById('devExplorePriority');
  if (searchInput) searchInput.value = '';
  if (catSelect) catSelect.value = '';
  if (prioSelect) prioSelect.value = '';
  filterDevExplore();
}

document.addEventListener("DOMContentLoaded", function () {
  const search = document.getElementById('devExploreSearch');
  const cat = document.getElementById('devExploreCategory');
  const prio = document.getElementById('devExplorePriority');
  if (search) search.addEventListener('input', filterDevExplore);
  if (cat) cat.addEventListener('change', filterDevExplore);
  if (prio) prio.addEventListener('change', filterDevExplore);

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});

window.addEventListener('load', function() {
  const s = new URLSearchParams(window.location.search).get('section');
  if (s) verSeccion(s);
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});

// ═══════════════════════════════════════════════
// SECCIÓN INICIAL DESDE QUERY (?seccion=)
// ═══════════════════════════════════════════════
// El token oculto puede quedar desfasado si la cookie csrftoken rotó
// (login en otra pestaña, reinicio con otra SECRET_KEY o botón atrás).
// Sincronizarlo evita el 403 "CSRF token from POST incorrect".
function leerCookie(nombre) {
  const par = document.cookie
    .split('; ')
    .find((item) => item.startsWith(nombre + '='));
  return par ? decodeURIComponent(par.slice(nombre.length + 1)) : '';
}

function sincronizarCsrf(scope) {
  const token = leerCookie('csrftoken');
  if (!token) return;
  (scope || document).querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach((input) => {
    input.value = token;
  });
}

document.addEventListener('DOMContentLoaded', () => {
  sincronizarCsrf();
  const params = new URLSearchParams(window.location.search);
  const inicial = document.body.getAttribute('data-seccion-inicial') || '';
  const seccion = params.get('seccion') || (inicial && inicial !== 'inicio' ? inicial : '');
  if (seccion && document.getElementById(seccion)) {
    verSeccion(seccion, null);
  }
  if (params.get('verificacion') === '1') {
    abrirVerificacion();
  }
});

// ═══════════════════════════════════════════════
// MODAL FLOTANTE: VERIFICACIÓN SENA
// ═══════════════════════════════════════════════
function abrirVerificacion() {
  const modal = document.getElementById('modalVerificacion');
  if (!modal) return;
  sincronizarCsrf(modal);
  modal.classList.add('is-open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  const focusTarget = modal.querySelector('.jd-tab.active, .jd-input, .jd-modal-close');
  if (focusTarget) focusTarget.focus({ preventScroll: true });
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

function cerrarVerificacion() {
  const modal = document.getElementById('modalVerificacion');
  if (!modal) return;
  modal.classList.remove('is-open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    cerrarVerificacion();
    cerrarPostulacion();
  }
});

document.addEventListener('click', (event) => {
  if (event.target.closest('[data-cerrar-verificacion]')) {
    cerrarVerificacion();
  }
});

// Pestañas del modal
document.addEventListener('click', (event) => {
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
function limpiarErroresVerificacion(form) {
  form.querySelectorAll('.jd-error').forEach((el) => { el.textContent = ''; });
  form.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
  const feedback = document.querySelector('[data-verificacion-feedback]');
  if (feedback) {
    feedback.hidden = true;
    feedback.classList.remove('is-error');
    feedback.textContent = '';
  }
}

function mostrarFeedbackVerificacion(mensaje, esError) {
  const feedback = document.querySelector('[data-verificacion-feedback]');
  if (!feedback) return;
  feedback.textContent = mensaje || '';
  feedback.hidden = !mensaje;
  feedback.classList.toggle('is-error', !!esError);
}

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
    submit.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Enviando...';
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

// ═══════════════════════════════════════════════
// MODAL FLOTANTE: POSTULACIÓN A PROYECTO
// ═══════════════════════════════════════════════
let postulacionUrl = '';
let postulacionCard = null;

function setTextoPostulacion(modal, selector, valor) {
  const el = modal.querySelector(selector);
  if (el) el.textContent = valor;
}

function abrirPostulacion(btn) {
  const modal = document.getElementById('modalPostulacion');
  if (!modal || !btn) return;

  postulacionUrl = btn.getAttribute('data-url') || '';
  postulacionCard = btn.closest('.project-card');

  setTextoPostulacion(modal, '[data-postulacion-tipo]', btn.dataset.tipo || 'Proyecto');
  setTextoPostulacion(modal, '[data-postulacion-prioridad]', btn.dataset.prioridad || '—');
  setTextoPostulacion(modal, '[data-postulacion-titulo]', btn.dataset.titulo || 'Proyecto');
  setTextoPostulacion(modal, '[data-postulacion-empresa]', btn.dataset.empresa || '');
  setTextoPostulacion(modal, '[data-postulacion-vacantes]', btn.dataset.vacantes || '0');
  setTextoPostulacion(modal, '[data-postulacion-cierre]', btn.dataset.cierre || 'Sin límite');
  setTextoPostulacion(modal, '[data-postulacion-descripcion]', btn.dataset.descripcion || '');

  const form = modal.querySelector('[data-postulacion-form]');
  if (form) form.reset();
  mostrarFeedbackPostulacion('', false);
  const btnVerificar = modal.querySelector('[data-ir-verificacion]');
  if (btnVerificar) btnVerificar.hidden = true;

  sincronizarCsrf(modal);
  modal.classList.add('is-open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';

  const first = modal.querySelector('#id_post_carta');
  if (first) first.focus({ preventScroll: true });
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

function cerrarPostulacion() {
  const modal = document.getElementById('modalPostulacion');
  if (!modal) return;
  modal.classList.remove('is-open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

function mostrarFeedbackPostulacion(mensaje, esError) {
  const feedback = document.querySelector('[data-postulacion-feedback]');
  if (!feedback) return;
  feedback.textContent = mensaje || '';
  feedback.hidden = !mensaje;
  feedback.classList.toggle('is-error', !!esError);
}

function mostrarToast(mensaje) {
  let toast = document.getElementById('jdToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'jdToast';
    toast.className = 'jd-toast';
    toast.setAttribute('role', 'status');
    document.body.appendChild(toast);
  }
  toast.textContent = mensaje;
  toast.classList.add('is-visible');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('is-visible'), 4200);
}

function actualizarContadorExplorar() {
  const badge = document.getElementById('devExploreCountBadge');
  if (!badge) return;
  const actual = parseInt((badge.textContent || '').replace(/[^\d]/g, ''), 10);
  if (Number.isNaN(actual)) return;
  badge.textContent = `${Math.max(0, actual - 1)} DISPONIBLES`;
}

document.addEventListener('click', (event) => {
  const abrir = event.target.closest('[data-abrir-postulacion]');
  if (abrir) {
    event.preventDefault();
    abrirPostulacion(abrir);
    return;
  }

  if (event.target.closest('[data-cerrar-postulacion]')) {
    cerrarPostulacion();
    return;
  }

  if (event.target.closest('[data-ir-verificacion]')) {
    cerrarPostulacion();
    abrirVerificacion();
  }
});

document.addEventListener('submit', async (event) => {
  const form = event.target.closest('[data-postulacion-form]');
  if (!form) return;
  event.preventDefault();

  const modal = form.closest('#modalPostulacion');
  const carta = form.querySelector('[name="carta"]');
  if (carta && !carta.value.trim()) {
    mostrarFeedbackPostulacion('La carta de presentación es obligatoria.', true);
    carta.focus({ preventScroll: true });
    return;
  }
  if (!postulacionUrl) return;

  sincronizarCsrf(form);
  const submit = form.querySelector('[data-postulacion-submit]');
  const textoOriginal = submit ? submit.innerHTML : '';
  if (submit) {
    submit.disabled = true;
    submit.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Enviando...';
  }
  mostrarFeedbackPostulacion('', false);

  try {
    const csrf = leerCookie('csrftoken');
    const response = await fetch(postulacionUrl, {
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
        mostrarFeedbackPostulacion(
          'Tu token de seguridad expiró. Recargando la página para continuar…',
          true
        );
        setTimeout(() => window.location.reload(), 1200);
        return;
      }
      throw new Error('Respuesta inesperada del servidor');
    }

    if (data.ok) {
      cerrarPostulacion();
      if (postulacionCard) {
        postulacionCard.remove();
        postulacionCard = null;
        actualizarContadorExplorar();
      }
      mostrarToast(data.mensaje || '¡Postulación enviada!');
      return;
    }

    const btnVerificar = modal ? modal.querySelector('[data-ir-verificacion]') : null;
    if (btnVerificar) btnVerificar.hidden = !data.requiere_verificacion;
    mostrarFeedbackPostulacion(data.mensaje || 'No se pudo enviar la postulación.', true);
  } catch (error) {
    mostrarFeedbackPostulacion(
      'No pudimos enviar tu postulación. Revisa tu conexión e inténtalo de nuevo.',
      true
    );
  } finally {
    if (submit) {
      submit.disabled = false;
      submit.innerHTML = textoOriginal;
    }
  }
});
