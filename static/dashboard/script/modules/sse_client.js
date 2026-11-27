/**
 * JobDevs — Cliente Server-Sent Events (SSE), sincronización de badges,
 * deduplicación WS y formularios de notificaciones (SCRUM-188).
 */

import { mostrarToast } from './toast_manager.js';

const STREAM_URL = '/notificaciones/stream/';
const MENSAJE_WS_TTL_MS = 15000;
const mensajesRecientesWS = new Map();

let eventSource = null;
let reconnectTimeout = null;

export function registrarMensajeWS(mensaje) {
    const texto = String(mensaje || '').trim();
    if (!texto) return;
    const ahora = Date.now();
    mensajesRecientesWS.forEach((expira, key) => {
        if (expira <= ahora) mensajesRecientesWS.delete(key);
    });
    mensajesRecientesWS.set(texto, ahora + MENSAJE_WS_TTL_MS);
}

export function esMensajeRecienteWS(mensaje) {
    const texto = String(mensaje || '').trim();
    if (!texto || !mensajesRecientesWS.has(texto)) return false;
    const expira = mensajesRecientesWS.get(texto);
    if (expira <= Date.now()) {
        mensajesRecientesWS.delete(texto);
        return false;
    }
    mensajesRecientesWS.delete(texto);
    return true;
}

export function actualizarBadges(count) {
    const parsedCount = parseInt(count, 10) || 0;
    // Solo notificaciones: .nav-badge es genérico (mensajes, postulaciones...).
    const badges = document.querySelectorAll('.notif-badge, [data-notif-badge]');

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

export function getCookie(name) {
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

export function getCsrfToken() {
    const inputToken = document.querySelector('[name=csrfmiddlewaretoken]');
    return inputToken ? inputToken.value : getCookie('csrftoken');
}

export async function marcarTodasLeidasAsync(form) {
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

export async function marcarLeidaAsync(form, notificacionId) {
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

export function inicializarFormulariosNotificaciones() {
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

export function conectarSSE() {
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
                const esMensajeDuplicadoWS = (
                    String(data.tipo || '').trim().toLowerCase() === 'mensaje'
                    && esMensajeRecienteWS(data.mensaje)
                );
                if (!esMensajeDuplicadoWS) {
                    mostrarToast(data);
                }
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

export function desconectarSSE() {
    if (eventSource) {
        eventSource.close();
    }
}

export function initSSEClient() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            conectarSSE();
            inicializarFormulariosNotificaciones();
        });
    } else {
        conectarSSE();
        inicializarFormulariosNotificaciones();
    }

    window.addEventListener('beforeunload', desconectarSSE);
}

export function createSseApi() {
    return {
        actualizarBadges: actualizarBadges,
        mostrarToast: mostrarToast,
        conectar: conectarSSE,
        marcarTodasLeidas: marcarTodasLeidasAsync,
        marcarLeida: marcarLeidaAsync,
        inicializarFormularios: inicializarFormulariosNotificaciones,
    };
}
