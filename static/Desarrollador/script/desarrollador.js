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
}

window.addEventListener('load', function() {
  const s = new URLSearchParams(window.location.search).get('section');
  if (s) verSeccion(s);
});
