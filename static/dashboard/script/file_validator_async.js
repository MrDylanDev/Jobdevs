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
            case 'zip':
                // ZIP -> PK\x03\x04 o PK\x05\x06 (0x50 0x4B)
                return bytes[0] === 0x50 && bytes[1] === 0x4B && (bytes[2] === 0x03 || bytes[2] === 0x05);
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

        const maxMb = options.maxMb || 10;
        const maxBytes = maxMb * 1024 * 1024;

        if (file.size > maxBytes) {
            const tamanoActual = (file.size / (1024 * 1024)).toFixed(1);
            throw new Error(`El archivo pesa ${tamanoActual} MB y supera el límite máximo permitido de ${maxMb} MB.`);
        }

        const nombre = file.name || '';
        const extension = nombre.includes('.') ? nombre.split('.').pop().toLowerCase() : '';
        const allowedExts = options.allowedExts || ['pdf', 'zip', 'png', 'jpg', 'jpeg'];

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

    /**
     * Sube un archivo directamente a Cloudflare R2 usando una presigned URL.
     * @param {Object} params
     * @param {File} params.file
     * @param {string} [params.presignedEndpoint]
     * @param {string} [params.csrfToken]
     * @param {string} [params.prefijo]
     * @param {Function} [params.onProgress] - callback(porcentaje, loaded, total)
     * @param {AbortSignal} [params.signal]
     * @returns {Promise<Object>}
     */
    function subirArchivoR2Async(params) {
        const {
            file,
            presignedEndpoint = '/usuarios/api/storage/presigned-upload/',
            csrfToken = '',
            prefijo = 'avances/evidencias',
            onProgress = null,
            signal = null,
        } = params;

        return new Promise(async (resolve, reject) => {
            if (!file) {
                return reject(new Error('No se proporcionó ningún archivo para subir a R2.'));
            }

            try {
                // 1. Solicitar URL prefirmada al backend Django
                const token = csrfToken || (document.querySelector('[name=csrfmiddlewaretoken]')?.value || '');
                const respPrefirmada = await fetch(presignedEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': token,
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        nombre_archivo: file.name,
                        content_type: file.type || 'application/octet-stream',
                        prefijo: prefijo,
                    }),
                    signal,
                });

                if (respPrefirmada.status === 503) {
                    // R2 no está configurado en este entorno -> degradación transparente a multipart
                    const data = await respPrefirmada.json().catch(() => ({}));
                    return resolve({
                        r2_disponible: false,
                        fallback: true,
                        mensaje: data.mensaje || 'Cloudflare R2 no configurado, usando almacenamiento local.',
                    });
                }

                if (!respPrefirmada.ok) {
                    const errData = await respPrefirmada.json().catch(() => ({}));
                    throw new Error(errData.error || `Error ${respPrefirmada.status} al solicitar URL prefirmada de R2.`);
                }

                const dataPresigned = await respPrefirmada.json();
                if (!dataPresigned.r2_disponible || !dataPresigned.upload?.url) {
                    return resolve({
                        r2_disponible: false,
                        fallback: true,
                    });
                }

                const uploadInfo = dataPresigned.upload;

                // 2. Realizar PUT directo a Cloudflare R2 con seguimiento mediante XMLHttpRequest
                const xhr = new XMLHttpRequest();
                xhr.open('PUT', uploadInfo.url, true);

                if (uploadInfo.content_type) {
                    xhr.setRequestHeader('Content-Type', uploadInfo.content_type);
                }

                if (signal) {
                    signal.addEventListener('abort', () => xhr.abort());
                }

                xhr.upload.onprogress = (evt) => {
                    if (evt.lengthComputable && typeof onProgress === 'function') {
                        const percent = Math.min(100, Math.round((evt.loaded / evt.total) * 100));
                        onProgress(percent, evt.loaded, evt.total);
                    }
                };

                xhr.onload = () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        if (typeof onProgress === 'function') {
                            onProgress(100, file.size, file.size);
                        }
                        const cleanUrl = uploadInfo.url.split('?')[0];
                        resolve({
                            r2_disponible: true,
                            success: true,
                            url: cleanUrl,
                            file_key: uploadInfo.file_key,
                            content_type: uploadInfo.content_type,
                        });
                    } else {
                        reject(new Error(`Error al subir a Cloudflare R2 (HTTP ${xhr.status}): ${xhr.statusText || 'Fallo de subida'}`));
                    }
                };

                xhr.onerror = () => {
                    reject(new Error('Error de red al conectar con Cloudflare R2.'));
                };

                xhr.onabort = () => {
                    reject(new Error('Subida cancelada por el usuario.'));
                };

                xhr.send(file);
            } catch (err) {
                reject(err);
            }
        });
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
        subirArchivoR2Async,
        inicializar: inicializarValidacionArchivos,
    };
})();
