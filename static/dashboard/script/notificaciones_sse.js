/**
 * JobDevs - Notificaciones en tiempo real con Server-Sent Events (SSE) (SCRUM-188)
 * Conexión continua unidireccional HTTP con reconexión automática y toasts accesibles.
 */
(function() {
    'use strict';

    const STREAM_URL = '/notificaciones/stream/';
    let eventSource = null;
    let reconnectTimeout = null;

    const TOAST_DURACION_MS = 5000;
    const TOAST_MAX_VISIBLES = 4;
    const TOAST_SALIDA_MS = 320;

    const TOAST_TIPOS = {
        success: { etiqueta: 'Éxito', icono: 'check-circle-2' },
        info: { etiqueta: 'Información', icono: 'info' },
        warning: { etiqueta: 'Advertencia', icono: 'alert-triangle' },
        error: { etiqueta: 'Error', icono: 'alert-circle' },
    };

    const TOAST_ALIAS = {
        success: 'success', exito: 'success', 'éxito': 'success',
        aprobacion: 'success', 'aprobación': 'success', aprobado: 'success',
        info: 'info', informacion: 'info', 'información': 'info',
        postulacion: 'info', 'postulación': 'info', avance: 'info',
        mensaje: 'info', notificacion: 'info', 'notificación': 'info', otro: 'info',
        warning: 'warning', warn: 'warning', alerta: 'warning', advertencia: 'warning',
        error: 'error', danger: 'error', peligro: 'error', fallo: 'error',
    };

    const TOAST_ETIQUETAS = {
        postulacion: 'Postulación', avance: 'Avance', aprobacion: 'Aprobación',
        mensaje: 'Mensaje', alerta: 'Alerta', notificacion: 'Notificación', otro: 'Notificación',
    };

    const TOAST_ICONOS = {
        postulacion: 'file-text', avance: 'trending-up', aprobacion: 'check-circle-2',
        mensaje: 'message-circle', alerta: 'alert-triangle', error: 'alert-circle',
    };

    function getToastContainer() {
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

    function normalizarTipoToast(tipo) {
        const clave = String(tipo || '').trim().toLowerCase();
        return TOAST_ALIAS[clave] || 'info';
    }

    function actualizarBadges(count) {
        const parsedCount = parseInt(count, 10) || 0;
        const badges = document.querySelectorAll('.notif-badge, .nav-badge');

        if (parsedCount > 0) {
            badges.forEach(badge => {
                badge.textContent = parsedCount;
                badge.style.setProperty('display', 'inline-flex', 'important');
            });

            const notifBtn = document.querySelector('.notif-btn');
            if (notifBtn && !notifBtn.querySelector('.notif-badge')) {
                const badge = document.createElement('span');
                badge.className = 'notif-badge';
                badge.textContent = parsedCount;
                notifBtn.appendChild(badge);
            }
        } else {
            badges.forEach(badge => {
                badge.textContent = '0';
                badge.style.setProperty('display', 'none', 'important');
            });
        }
    }

    function crearToast(data) {
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

    function mostrarToast(data) {
        if (typeof data === 'string') {
            data = { mensaje: data };
        }
        data = data || {};

        const container = getToastContainer();
        const { toast, cerrarBtn, tipo, duracion } = crearToast(data);

        let timer = null;
        let restante = duracion;
        let inicio = 0;
        let cerrado = false;

        const cerrar = () => {
            if (cerrado) return;
            cerrado = true;
            if (timer) window.clearTimeout(timer);
            toast.classList.remove('is-visible');
            toast.classList.add('is-leaving');
            window.setTimeout(() => toast.remove(), TOAST_SALIDA_MS);
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
            if (cerrado || timer) return;
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

        toast.addEventListener('mouseenter', pausar);
        toast.addEventListener('mouseleave', reanudar);
        toast.addEventListener('focusin', pausar);
        toast.addEventListener('focusout', (event) => {
            if (!toast.contains(event.relatedTarget)) reanudar();
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
            container.firstElementChild.remove();
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

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function getCsrfToken() {
        const inputToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return inputToken ? inputToken.value : getCookie('csrftoken');
    }

    async function marcarTodasLeidasAsync(form) {
        const btn = form ? form.querySelector('button[type="submit"]') || form.querySelector('button') : null;
        if (btn) btn.disabled = true;

        const url = form ? form.getAttribute('action') : '/notificaciones/marcar-todas-leidas/';

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(),
                }
            });

            if (!response.ok) {
                throw new Error('No se pudieron marcar las notificaciones');
            }

            const data = await response.json();
            if (data.status === 'ok') {
                actualizarBadges(0);

                // Ocultar formulario o botón "Marcar todas como leídas"
                if (form) {
                    form.style.transition = 'opacity 0.2s';
                    form.style.opacity = '0';
                    setTimeout(() => form.remove(), 200);
                }

                // Desvanecer o actualizar elementos de notificación en la página
                const notifItems = document.querySelectorAll('.notification-item, tr[data-notif-id], .notif-row');
                notifItems.forEach(item => {
                    item.style.transition = 'opacity 0.3s';
                    item.classList.remove('no-leida', 'unread');
                    item.classList.add('leida', 'read');
                    const badge = item.querySelector('.badge-danger, .badge-warning');
                    if (badge && badge.textContent.toLowerCase().includes('nueva')) {
                        badge.remove();
                    }
                });

                // Toast confirmatorio
                mostrarToast({
                    tipo: 'success',
                    mensaje: data.mensaje || 'Todas las notificaciones han sido marcadas como leídas.',
                });
            }
        } catch (err) {
            console.error('Error marcando todas las notificaciones:', err);
            mostrarToast({
                tipo: 'error',
                mensaje: 'Error de conexión al marcar notificaciones.',
            });
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    async function marcarLeidaAsync(form, notificacionId) {
        const btn = form ? form.querySelector('button[type="submit"]') || form.querySelector('button') : null;
        if (btn) btn.disabled = true;

        const url = form ? form.getAttribute('action') : `/notificaciones/marcar-leida/${notificacionId}/`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(),
                }
            });

            if (!response.ok) {
                throw new Error('No se pudo marcar la notificación');
            }

            const data = await response.json();
            if (data.status === 'ok') {
                actualizarBadges(data.unread_count);

                // Desvanecer el item o botón
                const item = form ? form.closest('.notification-item, tr, .notif-row') : null;
                if (item) {
                    item.style.transition = 'opacity 0.3s';
                    item.classList.remove('no-leida', 'unread');
                    item.classList.add('leida', 'read');
                    if (form) form.remove();
                }
            }
        } catch (err) {
            console.error('Error marcando notificación leída:', err);
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    function inicializarFormulariosNotificaciones() {
        // Interceptar formularios de marcar todas leídas
        document.querySelectorAll('form[action*="/notificaciones/marcar-todas-leidas/"]').forEach(form => {
            if (form.dataset.asyncBound === 'true') return;
            form.dataset.asyncBound = 'true';
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                marcarTodasLeidasAsync(form);
            });
        });

        // Interceptar formularios de marcar individual como leída
        document.querySelectorAll('form[action*="/notificaciones/marcar-leida/"]').forEach(form => {
            if (form.dataset.asyncBound === 'true') return;
            form.dataset.asyncBound = 'true';
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                marcarLeidaAsync(form);
            });
        });
    }

    function conectarSSE() {
        if (!window.EventSource) {
            console.warn('JobDevs SSE: El navegador no soporta EventSource.');
            return;
        }
        if (eventSource) {
            eventSource.close();
        }

        try {
            eventSource = new EventSource(STREAM_URL);

            eventSource.addEventListener('init', (e) => {
                try {
                    const data = JSON.parse(e.data);
                    if (data.unread_count !== undefined) {
                        actualizarBadges(data.unread_count);
                    }
                } catch (err) {
                    console.error('Error procesando evento init SSE:', err);
                }
            });

            eventSource.addEventListener('sync', (e) => {
                try {
                    const data = JSON.parse(e.data);
                    if (data.unread_count !== undefined) {
                        actualizarBadges(data.unread_count);
                    }
                } catch (err) {
                    console.error('Error procesando evento sync SSE:', err);
                }
            });

            eventSource.addEventListener('notificacion', (e) => {
                try {
                    const data = JSON.parse(e.data);
                    if (data.unread_count !== undefined) {
                        actualizarBadges(data.unread_count);
                    }
                    mostrarToast(data);
                    document.dispatchEvent(new CustomEvent('jobdevs:notificacion', { detail: data }));
                } catch (err) {
                    console.error('Error procesando evento notificacion SSE:', err);
                }
            });

            eventSource.onerror = () => {
                if (eventSource.readyState === EventSource.CLOSED) {
                    if (reconnectTimeout) clearTimeout(reconnectTimeout);
                    reconnectTimeout = setTimeout(conectarSSE, 5000);
                }
            };

        } catch (err) {
            console.error('No se pudo establecer conexión EventSource:', err);
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
            reconnectTimeout = setTimeout(conectarSSE, 5000);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            conectarSSE();
            inicializarFormulariosNotificaciones();
        });
    } else {
        conectarSSE();
        inicializarFormulariosNotificaciones();
    }

    window.addEventListener('beforeunload', () => {
        if (eventSource) {
            eventSource.close();
        }
    });

    window.JobDevsToast = {
        mostrar: mostrarToast,
        success: (mensaje, opciones) => mostrarToast(Object.assign({}, opciones, { tipo: 'success', mensaje })),
        info: (mensaje, opciones) => mostrarToast(Object.assign({}, opciones, { tipo: 'info', mensaje })),
        warning: (mensaje, opciones) => mostrarToast(Object.assign({}, opciones, { tipo: 'warning', mensaje })),
        error: (mensaje, opciones) => mostrarToast(Object.assign({}, opciones, { tipo: 'error', mensaje })),
    };

    window.JobDevsSSE = {
        actualizarBadges: actualizarBadges,
        mostrarToast: mostrarToast,
        conectar: conectarSSE,
        marcarTodasLeidas: marcarTodasLeidasAsync,
        marcarLeida: marcarLeidaAsync,
        inicializarFormularios: inicializarFormulariosNotificaciones,
    };
})();
