/**
 * JobDevs — Gestor de toasts accesibles y contrato window.JobDevsToast.
 */

export const TOAST_DURACION_MS = 5000;
export const TOAST_MAX_VISIBLES = 4;
export const TOAST_SALIDA_MS = 320;

export const TOAST_TIPOS = {
    success: { etiqueta: 'Éxito', icono: 'check-circle-2' },
    info: { etiqueta: 'Información', icono: 'info' },
    warning: { etiqueta: 'Advertencia', icono: 'alert-triangle' },
    error: { etiqueta: 'Error', icono: 'alert-circle' },
};

export const TOAST_ALIAS = {
    success: 'success', exito: 'success', 'éxito': 'success',
    aprobacion: 'success', 'aprobación': 'success', aprobado: 'success',
    info: 'info', informacion: 'info', 'información': 'info',
    postulacion: 'info', 'postulación': 'info', avance: 'info',
    mensaje: 'info', notificacion: 'info', 'notificación': 'info', otro: 'info',
    warning: 'warning', warn: 'warning', alerta: 'warning', advertencia: 'warning',
    error: 'error', danger: 'error', peligro: 'error', fallo: 'error',
};

export const TOAST_ETIQUETAS = {
    postulacion: 'Postulación', avance: 'Avance', aprobacion: 'Aprobación',
    mensaje: 'Mensaje', alerta: 'Alerta', notificacion: 'Notificación', otro: 'Notificación',
};

export const TOAST_ICONOS = {
    postulacion: 'file-text', avance: 'trending-up', aprobacion: 'check-circle-2',
    mensaje: 'message-circle', alerta: 'alert-triangle', error: 'alert-circle',
};

let onWsMessageToast = null;

export function setOnWsMessageToast(handler) {
    onWsMessageToast = typeof handler === 'function' ? handler : null;
}

export function getToastContainer() {
    let container = document.getElementById('jobdevs-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'jobdevs-toast-container';
        document.body.appendChild(container);
    }
    container.classList.add('jobdevs-toast-container');
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'false');
    container.setAttribute('aria-relevant', 'additions');
    return container;
}

export function normalizarTipoToast(tipo) {
    const clave = String(tipo || '').trim().toLowerCase();
    return Object.prototype.hasOwnProperty.call(TOAST_ALIAS, clave) ? TOAST_ALIAS[clave] : 'info';
}

export function crearToast(data) {
    const tipoOriginal = String(data.tipo || 'otro').trim().toLowerCase();
    const tipo = normalizarTipoToast(tipoOriginal);
    const config = TOAST_TIPOS[tipo];
    const titulo = data.titulo || data.tipo_display || TOAST_ETIQUETAS[tipoOriginal] || config.etiqueta;
    const mensaje = data.mensaje || '';
    const duracionSolicitada = Number(data.duracion);
    const duracion = Number.isFinite(duracionSolicitada) && duracionSolicitada > 0
        ? duracionSolicitada
        : TOAST_DURACION_MS;

    const toast = document.createElement('article');
    toast.className = `jobdevs-toast jobdevs-toast--${tipo}`;
    toast.tabIndex = 0;
    toast.setAttribute('role', tipo === 'error' || tipo === 'warning' ? 'alert' : 'status');
    toast.dataset.toastType = tipo;
    toast.style.setProperty('--jd-toast-duration', `${duracion}ms`);

    const icono = document.createElement('span');
    icono.className = 'jobdevs-toast__icon';
    icono.setAttribute('aria-hidden', 'true');
    const iconEl = document.createElement('i');
    iconEl.setAttribute('data-lucide', TOAST_ICONOS[tipoOriginal] || config.icono);
    icono.appendChild(iconEl);

    const cuerpo = document.createElement('div');
    cuerpo.className = 'jobdevs-toast__body';

    const tituloEl = document.createElement('p');
    tituloEl.className = 'jobdevs-toast__title';
    tituloEl.textContent = titulo;
    cuerpo.appendChild(tituloEl);

    if (mensaje) {
        const mensajeEl = document.createElement('p');
        mensajeEl.className = 'jobdevs-toast__message';
        mensajeEl.textContent = mensaje;
        cuerpo.appendChild(mensajeEl);
    }

    if (data.fecha) {
        const metaEl = document.createElement('p');
        metaEl.className = 'jobdevs-toast__meta';
        metaEl.textContent = data.fecha;
        cuerpo.appendChild(metaEl);
    }

    const cerrarBtn = document.createElement('button');
    cerrarBtn.type = 'button';
    cerrarBtn.className = 'jobdevs-toast__close';
    cerrarBtn.setAttribute('aria-label', 'Cerrar notificación');
    cerrarBtn.textContent = '×';

    const progreso = document.createElement('span');
    progreso.className = 'jobdevs-toast__progress';
    progreso.setAttribute('aria-hidden', 'true');

    toast.appendChild(icono);
    toast.appendChild(cuerpo);
    toast.appendChild(cerrarBtn);
    toast.appendChild(progreso);

    return { toast, cerrarBtn, tipo, duracion };
}

export function mostrarToast(data) {
    if (typeof data === 'string') {
        data = { mensaje: data };
    }
    data = data || {};
    if (
        data.origen === 'ws'
        && String(data.tipo || '').trim().toLowerCase() === 'mensaje'
        && onWsMessageToast
    ) {
        onWsMessageToast(data.mensaje);
    }

    const container = getToastContainer();
    const { toast, cerrarBtn, duracion } = crearToast(data);

    let timer = null;
    let exitTimer = null;
    let restante = duracion;
    let inicio = 0;
    let cerrado = false;
    let enHover = false;
    let enFoco = false;

    const limpiarTimers = () => {
        cerrado = true;
        if (timer) {
            window.clearTimeout(timer);
            timer = null;
        }
        if (exitTimer) {
            window.clearTimeout(exitTimer);
            exitTimer = null;
        }
    };

    toast._jdLimpiar = limpiarTimers;

    const cerrar = () => {
        if (cerrado) return;
        limpiarTimers();
        toast.classList.remove('is-visible');
        toast.classList.add('is-leaving');
        exitTimer = window.setTimeout(() => {
            exitTimer = null;
            toast.remove();
        }, TOAST_SALIDA_MS);
    };

    const programar = () => {
        inicio = Date.now();
        timer = window.setTimeout(cerrar, restante);
    };

    const pausar = () => {
        if (!timer || cerrado) return;
        window.clearTimeout(timer);
        timer = null;
        restante -= Date.now() - inicio;
        toast.classList.add('is-paused');
    };

    const reanudar = () => {
        if (cerrado || timer || enHover || enFoco) return;
        if (restante <= 0) {
            cerrar();
            return;
        }
        toast.classList.remove('is-paused');
        programar();
    };

    cerrarBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        cerrar();
    });

    toast.addEventListener('click', (event) => {
        if (event.target.closest && event.target.closest('.jobdevs-toast__close')) return;
        event.stopPropagation();

        if (typeof data.onClick === 'function') {
            try {
                data.onClick();
            } catch (err) {
                console.error('Error en la acción del toast:', err);
            }
            cerrar();
            return;
        }

        // En dashboards con campana, abrir el popover en la misma página
        // en lugar de navegar al listado de notificaciones.
        const popover = document.getElementById('notifPopover');
        if (popover) {
            if (!popover.classList.contains('is-open')) {
                if (window.JobDevsNotificaciones && typeof window.JobDevsNotificaciones.abrir === 'function') {
                    window.JobDevsNotificaciones.abrir();
                } else if (typeof window.toggleNotifPopover === 'function') {
                    window.toggleNotifPopover();
                } else {
                    popover.classList.add('is-open');
                }
            }
            cerrar();
            return;
        }

        window.location.href = '/notificaciones/';
    });

    toast.addEventListener('mouseenter', () => {
        enHover = true;
        pausar();
    });
    toast.addEventListener('mouseleave', () => {
        enHover = false;
        reanudar();
    });
    toast.addEventListener('focusin', () => {
        enFoco = true;
        pausar();
    });
    toast.addEventListener('focusout', (event) => {
        if (!toast.contains(event.relatedTarget)) {
            enFoco = false;
            reanudar();
        }
    });
    toast.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            cerrar();
            return;
        }
        if ((event.key === 'Enter' || event.key === ' ') && event.target === toast) {
            event.preventDefault();
            toast.click();
        }
    });

    container.appendChild(toast);

    while (container.children.length > TOAST_MAX_VISIBLES) {
        const expulsado = container.firstElementChild;
        if (typeof expulsado._jdLimpiar === 'function') {
            expulsado._jdLimpiar();
        }
        expulsado.remove();
    }

    if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
    }

    requestAnimationFrame(() => {
        toast.classList.add('is-visible');
    });

    programar();

    return toast;
}

export function createToastApi() {
    return {
        mostrar: mostrarToast,
        success: (mensaje, opciones) => mostrarToast(Object.assign({}, opciones, { tipo: 'success', mensaje })),
        info: (mensaje, opciones) => mostrarToast(Object.assign({}, opciones, { tipo: 'info', mensaje })),
        warning: (mensaje, opciones) => mostrarToast(Object.assign({}, opciones, { tipo: 'warning', mensaje })),
        error: (mensaje, opciones) => mostrarToast(Object.assign({}, opciones, { tipo: 'error', mensaje })),
    };
}
