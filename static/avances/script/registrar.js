(function() {
  const form = document.getElementById('formRegistrarAvance');
  const urlInput = document.getElementById('archivoUrlInput');
  const fileInput = document.getElementById('archivoAdjuntoInput');
  const btnEnviar = document.getElementById('btnEnviarAvance');
  const previewBadge = document.getElementById('archivoPreviewBadge');
  const nombreLabel = document.getElementById('archivoNombreLabel');
  const tamanoLabel = document.getElementById('archivoTamanoLabel');
  const quitarBtn = document.getElementById('quitarArchivoBtn');

  function mostrarErrorEnVivo(mensaje) {
    if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
      window.JobDevsSSE.mostrarToast({ tipo: 'alerta', mensaje: mensaje });
    } else if (typeof window.jdToast === 'function') {
      window.jdToast(mensaje, true);
    } else {
      window.alert(mensaje);
    }
  }

  function ocultarError() {
    if (urlInput) urlInput.style.borderColor = 'var(--corp-border)';
    if (fileInput) fileInput.style.borderColor = 'var(--corp-border)';
  }

  if (fileInput) {
    fileInput.addEventListener('change', function() {
      ocultarError();
      const file = fileInput.files && fileInput.files[0];
      if (file) {
        if (nombreLabel) nombreLabel.textContent = file.name;
        if (tamanoLabel) tamanoLabel.textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
        if (previewBadge) {
          previewBadge.style.display = 'flex';
          if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
          }
        }
      } else {
        if (previewBadge) previewBadge.style.display = 'none';
      }
    });
  }

  if (quitarBtn) {
    quitarBtn.addEventListener('click', function() {
      if (fileInput) fileInput.value = '';
      if (previewBadge) previewBadge.style.display = 'none';
    });
  }

  if (urlInput) {
    urlInput.addEventListener('input', ocultarError);
  }

  if (form) {
    form.addEventListener('submit', async function(e) {
      ocultarError();

      const urlVal = (urlInput ? urlInput.value : '').trim();

      if (urlVal && !/^https?:\/\/.+/i.test(urlVal)) {
        e.preventDefault();
        if (urlInput) urlInput.style.borderColor = '#ef4444';
        mostrarErrorEnVivo('La URL de evidencia debe iniciar con http:// o https://');
        return;
      }

      // Envío asíncrono con Fetch + FormData para evitar recarga si el servidor detecta un problema
      e.preventDefault();
      const originalBtnHtml = btnEnviar.innerHTML;
      btnEnviar.disabled = true;
      btnEnviar.innerHTML = '<span>Enviando avance...</span>';

      try {
        const formData = new FormData(form);
        const response = await fetch(window.location.href, {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: formData,
        });

        const data = await response.json();
        if (response.ok && data.status === 'ok') {
          window.location.href = data.redirect_url || '/desarrollador/dashboard/?section=activos';
        } else {
          mostrarErrorEnVivo(data.error || 'Ocurrió un error al validar el avance.');
          btnEnviar.disabled = false;
          btnEnviar.innerHTML = originalBtnHtml;
        }
      } catch (err) {
        mostrarErrorEnVivo('Error de red al enviar el avance. Tus datos siguen intactos en el formulario.');
        btnEnviar.disabled = false;
        btnEnviar.innerHTML = originalBtnHtml;
      }
    });
  }
})();
