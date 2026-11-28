const montoInput = document.getElementById('monto');
const monedaSelect = document.getElementById('moneda');
const previewEl = document.getElementById('monto_formateado_preview');

if (montoInput && monedaSelect && previewEl) {
  const actualizarMontoPreview = () => {
    const raw = parseFloat(montoInput.value) || 0;
    const moneda = monedaSelect.value;
    if (moneda === 'COP') {
      if (raw % 1 === 0) {
        previewEl.textContent = `$ ${Math.round(raw).toLocaleString('es-CO')} COP`;
      } else {
        previewEl.textContent = `$ ${raw.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} COP`;
      }
    } else if (moneda === 'USD') {
      previewEl.textContent = `$ ${raw.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`;
    } else {
      previewEl.textContent = `$ ${raw.toFixed(2)} ${moneda}`;
    }
  };

  montoInput.addEventListener('input', actualizarMontoPreview);
  monedaSelect.addEventListener('change', actualizarMontoPreview);
}

const initIcons = () => {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initIcons);
} else {
  initIcons();
}
