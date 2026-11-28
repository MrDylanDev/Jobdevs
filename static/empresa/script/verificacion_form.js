if (window.lucide && typeof window.lucide.createIcons === 'function') {
  window.lucide.createIcons();
}

const persona = document.getElementById('tipo_persona');
const documento = document.getElementById('tipo_documento');

if (persona && documento) {
  const sync = () => {
    const juridica = persona.value === 'juridica';
    if (juridica) documento.value = 'NIT';
    Array.from(documento.options).forEach((opt) => {
      opt.disabled = juridica && opt.value !== 'NIT';
    });
  };

  persona.addEventListener('change', sync);
  sync();
}
