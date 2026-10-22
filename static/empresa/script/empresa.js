/**
 * Lógica específica para el Dashboard de Empresa
 * (Manejado principalmente por Django y tabs.js)
 */

document.addEventListener("DOMContentLoaded", function () {
    // Funciones específicas para la empresa que no sean navegación general
});

function abrirModal() {
  document.getElementById("modalProyecto").style.display = "flex";
}

function cerrarModal() {
  document.getElementById("modalProyecto").style.display = "none";
}

function switchTab(id, btn) {
  document.querySelectorAll('.seccion-v').forEach(s => s.classList.remove('activa'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('activa');
  if (!btn) {
    btn = Array.from(document.querySelectorAll('.nav-item[onclick]')).find(b => (b.getAttribute('onclick') || '').indexOf("('" + id + "'") !== -1);
  }
  if (btn) btn.classList.add('active');
}

function cerrarModal() {
  document.getElementById('modalProyecto').classList.remove('open');
}

window.addEventListener('load', function() {
  const s = new URLSearchParams(window.location.search).get('section');
  if (s) switchTab(s);
});
