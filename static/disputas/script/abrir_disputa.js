document.addEventListener('DOMContentLoaded', function () {
  const motivo = document.getElementById('motivo');
  const count = document.getElementById('char-count');
  const counter = document.getElementById('char-counter');
  const form = document.getElementById('form-disputa');
  const error = document.getElementById('disputa-error');
  const categoria = document.getElementById('categoria');
  const gravedad = document.getElementById('confirma_gravedad');
  const submitBtn = document.getElementById('btn-submit-disputa');
  const checks = document.querySelectorAll('#confirma_intento_previo, #confirma_gravedad, #acepta_sanciones');
  function syncSubmit() {
    if (!submitBtn || checks.length === 0) return;
    const ready = Array.prototype.every.call(checks, function (cb) { return cb.disabled || cb.checked; });
    submitBtn.disabled = !ready;
    submitBtn.style.opacity = ready ? '1' : '0.42';
    submitBtn.style.cursor = ready ? 'pointer' : 'not-allowed';
  }
  checks.forEach(function (cb) { cb.addEventListener('change', syncSubmit); });
  syncSubmit();

  function actualizarCausal() {
    const esFuerzaMayor = categoria.value === 'fuerza_mayor';
    gravedad.required = !esFuerzaMayor;
    gravedad.disabled = esFuerzaMayor;
    gravedad.closest('label').style.display = esFuerzaMayor ? 'none' : '';
    syncSubmit();
  }
  categoria.addEventListener('change', actualizarCausal);
  actualizarCausal();

  function actualizar() {
    if (!motivo) return;
    const len = motivo.value.trim().length;
    if (count) count.textContent = len;
    if (counter) counter.classList.toggle('ok', len >= 80);
  }
  function mostrarError(texto) {
    if (!error) return;
    error.textContent = texto;
    error.style.display = 'block';
    error.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  if (motivo) {
    motivo.addEventListener('input', actualizar);
    actualizar();
  }

  if (form) {
    form.addEventListener('submit', function (e) {
      if (error) error.style.display = 'none';
      if (motivo && motivo.value.trim().length < 80) {
        e.preventDefault();
        mostrarError('El motivo debe tener al menos 80 caracteres explicando los hechos y antecedentes.');
        motivo.focus();
        return;
      }
      const marcadas = ['confirma_intento_previo', 'confirma_gravedad', 'acepta_sanciones']
        .every(id => {
          const el = document.getElementById(id);
          return el && (el.disabled || el.checked);
        });
      if (!marcadas) {
        e.preventDefault();
        mostrarError('Debes confirmar el intento previo y aceptar las reglas; en otras causales, también declarar la gravedad.');
      }
    });
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
