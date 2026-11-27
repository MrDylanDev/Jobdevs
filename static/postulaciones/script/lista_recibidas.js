function seleccionarCandidato(id, cardEl) {
  document.querySelectorAll('.candidate-row-corp').forEach(function(el) {
    el.classList.remove('is-selected');
  });
  if (cardEl) {
    cardEl.classList.add('is-selected');
  }
  document.querySelectorAll('.inspector-detail').forEach(function(el) {
    el.style.display = 'none';
  });
  var target = document.getElementById('inspector-' + id);
  if (target) {
    target.style.display = 'block';
  }
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

window.seleccionarCandidato = seleccionarCandidato;

document.addEventListener('DOMContentLoaded', function() {
  var checks = Array.from(document.querySelectorAll('[data-comparar-id]'));
  var boton = document.getElementById('btnCompararCandidatos');
  var ayuda = document.getElementById('comparadorAyuda');
  var comparador = document.querySelector('[data-testid="comparador-candidatos"]');
  function actualizarComparador() {
    var seleccionados = checks.filter(function(check) { return check.checked; });
    if (seleccionados.length > 4) {
      this.checked = false;
      seleccionados = checks.filter(function(check) { return check.checked; });
      ayuda.textContent = 'Puedes comparar como máximo 4 candidatos.';
    } else {
      ayuda.textContent = 'Selecciona entre 2 y 4 candidatos.';
    }
    boton.textContent = 'Comparar seleccionados (' + seleccionados.length + ')';
    boton.disabled = seleccionados.length < 2;
  }
  checks.forEach(function(check) { check.addEventListener('change', actualizarComparador); });
  if (boton) {
    boton.addEventListener('click', function() {
      var ids = checks.filter(function(check) { return check.checked; })
        .map(function(check) { return check.getAttribute('data-comparar-id'); });
      document.querySelectorAll('[data-comparacion-candidato]').forEach(function(card) {
        card.hidden = ids.indexOf(card.getAttribute('data-id')) === -1;
      });
      comparador.hidden = ids.length < 2;
      if (!comparador.hidden) comparador.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
