/**
 * JobDevs - Notificaciones en tiempo real con Server-Sent Events (SSE) (SCRUM-188)
 * Conexión continua unidireccional HTTP con reconexión automática y toasts accesibles.
 */
(function() {
    'use strict';

    if (!window.EventSource) {
        console.warn('JobDevs SSE: El navegador no soporta EventSource.');
        return;
    }

    const STREAM_URL = '/notificaciones/stream/';
    let eventSource = null;
    let reconnectTimeout = null;

    function getToastContainer() {
        let container = document.getElementById('jobdevs-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'jobdevs-toast-container';
            container.setAttribute('aria-live', 'polite');
            container.setAttribute('aria-atomic', 'true');
            Object.assign(container.style, {
                position: 'fixed',
                top: '20px',
                right: '20px',
                zIndex: '99999',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                pointerEvents: 'none',
                maxWidth: '380px',
                width: 'calc(100vw - 40px)',
            });
            document.body.appendChild(container);
        }
        return container;
    }

    function actualizarBadges(count) {
        const parsedCount = parseInt(count, 10) || 0;
        const badges = document.querySelectorAll('.notif-badge, .nav-badge');

        if (parsedCount > 0) {
            badges.forEach(badge => {
                badge.textContent = parsedCount;
                badge.style.display = 'inline-flex';
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
                badge.style.display = 'none';
            });
        }
    }

    function obtenerIconoTipo(tipo) {
        switch (tipo) {
            case 'postulacion': return 'fa-file-lines';
            case 'avance': return 'fa-bars-progress';
            case 'aprobacion': return 'fa-circle-check';
            case 'mensaje': return 'fa-comments';
            case 'alerta': return 'fa-triangle-exclamation';
            default: return 'fa-bell';
        }
    }

    function mostrarToast(data) {
        const container = getToastContainer();
        const toast = document.createElement('div');
        toast.className = 'jobdevs-sse-toast';
        toast.setAttribute('role', 'alert');

        Object.assign(toast.style, {
            backgroundColor: '#1e293b',
            color: '#f8fafc',
            borderRadius: '10px',
            padding: '14px 16px',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
            pointerEvents: 'auto',
            transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
            transform: 'translateX(120%)',
            opacity: '0',
            borderLeft: '4px solid #3b82f6',
            fontSize: '13px',
            lineHeight: '1.4',
            cursor: 'pointer',
        });

        const iconClass = obtenerIconoTipo(data.tipo);

        toast.innerHTML = `
            <div style="color: #60a5fa; font-size: 16px; margin-top: 2px;">
                <i class="fa ${iconClass}"></i>
            </div>
            <div style="flex: 1; min-width: 0;">
                <div style="font-weight: 600; color: #ffffff; margin-bottom: 2px; text-transform: capitalize;">
                    ${data.tipo || 'Notificación'}
                </div>
                <div style="color: #cbd5e1; word-break: break-word;">
                    ${data.mensaje || ''}
                </div>
                ${data.fecha ? `<div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">${data.fecha}</div>` : ''}
            </div>
            <button type="button" aria-label="Cerrar notificación" style="background: none; border: none; color: #94a3b8; cursor: pointer; padding: 0 4px; font-size: 14px;">
                <i class="fa fa-xmark"></i>
            </button>
        `;

        const closeBtn = toast.querySelector('button');
        const cerrar = (e) => {
            if (e) e.stopPropagation();
            toast.style.transform = 'translateX(120%)';
            toast.style.opacity = '0';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        };

        closeBtn.addEventListener('click', cerrar);

        toast.addEventListener('click', (e) => {
            if (e.target !== closeBtn && !closeBtn.contains(e.target)) {
                window.location.href = '/notificaciones/';
            }
        });

        container.appendChild(toast);

        requestAnimationFrame(() => {
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        });

        setTimeout(cerrar, 6000);
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
                    tipo: 'aprobacion',
                    mensaje: data.mensaje || 'Todas las notificaciones han sido marcadas como leídas.',
                });
            }
        } catch (err) {
            console.error('Error marcando todas las notificaciones:', err);
            mostrarToast({
                tipo: 'alerta',
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

    window.JobDevsSSE = {
        actualizarBadges: actualizarBadges,
        mostrarToast: mostrarToast,
        conectar: conectarSSE,
        marcarTodasLeidas: marcarTodasLeidasAsync,
        marcarLeida: marcarLeidaAsync,
        inicializarFormularios: inicializarFormulariosNotificaciones,
    };
})();
