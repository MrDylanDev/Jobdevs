/**
 * JobDevs - Prevalidación asíncrona de archivos y FileReader con Promesas (SCRUM-194)
 * Valida tamaño, extensiones y magic bytes en el cliente antes de subir archivos.
 */
(function() {
    'use strict';

    /**
     * Promesifica la lectura de un archivo usando FileReader.
     * @param {File} file
     * @param {'dataUrl' | 'arrayBuffer' | 'text'} mode
     * @returns {Promise<string | ArrayBuffer>}
     */
    function leerArchivoAsync(file, mode = 'dataUrl') {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(new Error('Error al leer el archivo en el navegador.'));

            if (mode === 'arrayBuffer') {
                reader.readAsArrayBuffer(file);
            } else if (mode === 'text') {
                reader.readAsText(file);
            } else {
                reader.readAsDataURL(file);
            }
        });
    }

    /**
     * Valida magic bytes de archivos para evitar extensiones falsas.
     * @param {ArrayBuffer} buffer
     * @param {string} extension
     * @returns {boolean}
     */
    function validarMagicBytes(buffer, extension) {
        if (!buffer || buffer.byteLength < 4) return false;
        const bytes = new Uint8Array(buffer.slice(0, 4));

        switch (extension.toLowerCase()) {
            case 'pdf':
                // %PDF -> 0x25 0x50 0x44 0x46
                return bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46;
            case 'png':
                // .PNG -> 0x89 0x50 0x4E 0x47
                return bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4E && bytes[3] === 0x47;
            case 'jpg':
            case 'jpeg':
                // JPEG -> 0xFF 0xD8 0xFF
                return bytes[0] === 0xFF && bytes[1] === 0xD8 && bytes[2] === 0xFF;
            default:
                return true; // Si no hay regla estricta para el tipo, permitir
        }
    }

    /**
     * Valida y lee un archivo de forma asíncrona retornando una Promesa.
     * @param {File} file
     * @param {Object} options
     * @returns {Promise<Object>}
     */
    async function validarYLeerArchivo(file, options = {}) {
        if (!file) {
            throw new Error('No se seleccionó ningún archivo.');
        }

        const maxMb = options.maxMb || 5;
        const maxBytes = maxMb * 1024 * 1024;

        if (file.size > maxBytes) {
            const tamanoActual = (file.size / (1024 * 1024)).toFixed(1);
            throw new Error(`El archivo pesa ${tamanoActual} MB y supera el límite máximo permitido de ${maxMb} MB.`);
        }

        const nombre = file.name || '';
        const extension = nombre.includes('.') ? nombre.split('.').pop().toLowerCase() : '';
        const allowedExts = options.allowedExts || [];

        if (allowedExts.length > 0 && !allowedExts.includes(extension)) {
            throw new Error(`Formato .${extension} no permitido. Formatos válidos: ${allowedExts.join(', ')}.`);
        }

        // Lectura de buffer para validación de magic bytes (primeros 64 bytes)
        const headerSlice = file.slice(0, 64);
        const headerBuffer = await leerArchivoAsync(headerSlice, 'arrayBuffer');

        if (!validarMagicBytes(headerBuffer, extension)) {
            throw new Error(`El contenido del archivo no coincide con su extensión .${extension} (archivo corrupto o alterado).`);
        }

        let dataUrl = null;
        if (options.readDataUrl !== false && (file.type.startsWith('image/') || ['jpg', 'jpeg', 'png', 'webp'].includes(extension))) {
            dataUrl = await leerArchivoAsync(file, 'dataUrl');
        }

        return {
            file,
            nombre: file.name,
            sizeBytes: file.size,
            sizeFormatted: (file.size / (1024 * 1024)).toFixed(2) + ' MB',
            extension,
            dataUrl,
            valido: true,
        };
    }

    function inicializarValidacionArchivos() {
        document.querySelectorAll('input[type="file"]').forEach(input => {
            if (input.dataset.validatorBound === 'true') return;
            input.dataset.validatorBound = 'true';

            const maxMb = parseFloat(input.dataset.maxMb || '5') || 5;
            const acceptAttr = input.getAttribute('accept') || '';
            let allowedExts = [];

            if (acceptAttr) {
                allowedExts = acceptAttr.split(',')
                    .map(a => a.trim().replace(/^\./, '').toLowerCase())
                    .filter(a => a && !a.includes('/'));
            }

            input.addEventListener('change', async function() {
                const file = input.files && input.files[0];
                if (!file) return;

                try {
                    const resultado = await validarYLeerArchivo(file, {
                        maxMb,
                        allowedExts,
                        readDataUrl: true,
                    });

                    // Previsualización si existe un elemento de destino
                    const previewSelector = input.dataset.previewTarget || '#fotoPerfil';
                    const previewImg = document.querySelector(previewSelector);
                    if (previewImg && resultado.dataUrl) {
                        previewImg.src = resultado.dataUrl;
                    }

                    // Notificación accesible de éxito
                    if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
                        window.JobDevsSSE.mostrarToast({
                            tipo: 'aprobacion',
                            mensaje: `Archivo '${resultado.nombre}' (${resultado.sizeFormatted}) validado correctamente.`,
                        });
                    }
                } catch (err) {
                    input.value = ''; // Limpiar input para forzar corrección
                    console.warn('JobDevs FileValidator:', err.message);

                    if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
                        window.JobDevsSSE.mostrarToast({
                            tipo: 'alerta',
                            mensaje: err.message,
                        });
                    } else {
                        alert(err.message);
                    }
                }
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializarValidacionArchivos);
    } else {
        inicializarValidacionArchivos();
    }

    window.JobDevsFileValidator = {
        validarYLeerArchivo,
        leerArchivoAsync,
        inicializar: inicializarValidacionArchivos,
    };
})();
