/**
 * JobDevs — Popover de notificaciones para los dashboards de administrador
 * y desarrollador. Abre/cierra la campana y permite marcar leídas o limpiar
 * sin recargar la página.
 */
(function () {
    'use strict';

    const popover = document.getElementById('notifPopover');
    const toggle = document.querySelector('[data-notif-toggle]');
    if (!popover || !toggle) return;

    const body = popover.querySelector('[data-notif-body]');

    function getCsrfToken() {
        const input = popover.querySelector('[name=csrfmiddlewaretoken]');
        if (input && input.value) return input.value;
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function estaAbierto() {
        return popover.classList.contains('is-open');
    }

    function setAbierto(abierto) {
        popover.classList.toggle('is-open', abierto);
        popover.setAttribute('aria-hidden', String(!abierto));
        toggle.setAttribute('aria-expanded', String(abierto));
    }

    function actualizarBadges(count) {
        if (window.JobDevsSSE && typeof window.JobDevsSSE.actualizarBadges === 'function') {
            window.JobDevsSSE.actualizarBadges(count);
            return;
        }
        const total = parseInt(count, 10) || 0;
        document.querySelectorAll('.notif-badge, .nav-badge').forEach(function (badge) {
            badge.textContent = String(total);
            badge.style.setProperty('display', total > 0 ? 'inline-flex' : 'none', 'important');
        });
    }

    function ocultarFormulariosMarcarLeidas() {
        document.querySelectorAll('form[action*="/notificaciones/marcar-todas-leidas/"]').forEach(function (form) {
            form.remove();
        });
    }

    function vaciarTarjetasNotificaciones() {
        document.querySelectorAll('.notif-list').forEach(function (list) {
            list.innerHTML = '';
            const empty = document.createElement('div');
            empty.className = 'empty-state';
            empty.style.padding = '20px';
            const icon = document.createElement('i');
            icon.className = 'fa fa-inbox';
            const text = document.createElement('p');
            text.textContent = 'Sin notificaciones';
            empty.appendChild(icon);
            empty.appendChild(text);
            list.appendChild(empty);
        });
    }

    function mostrarToast(mensaje, tipo) {
        if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
            window.JobDevsSSE.mostrarToast({ tipo: tipo || 'success', mensaje: mensaje });
        }
    }

    function estadoVacio() {
        const empty = document.createElement('div');
        empty.className = 'notif-popover-empty';
        empty.setAttribute('data-notif-empty', '');
        const icon = document.createElement('i');
        icon.className = 'fa fa-bell-slash';
        const text = document.createElement('span');
        text.textContent = 'No hay notificaciones';
        empty.appendChild(icon);
        empty.appendChild(text);
        return empty;
    }

    function crearItem(notificacion) {
        const item = document.createElement('div');
        item.className = 'notif-popover-item' + (notificacion.leida ? '' : ' is-unread');
        item.setAttribute('data-notif-id', notificacion.id || '');

        const icon = document.createElement('i');
        icon.className = 'fa fa-circle-dot';

        const wrapper = document.createElement('div');
        wrapper.className = 'notif-popover-text';
        const mensaje = document.createElement('span');
        mensaje.textContent = notificacion.mensaje || '';
        const fecha = document.createElement('small');
        fecha.textContent = notificacion.fecha || 'Ahora';
        wrapper.appendChild(mensaje);
        wrapper.appendChild(fecha);

        item.appendChild(icon);
        item.appendChild(wrapper);
        return item;
    }

    async function ejecutarAccion(btn, onSuccess) {
        const url = btn.getAttribute('data-url');
        if (!url) return;
        const textoOriginal = btn.textContent;
        btn.disabled = true;
        btn.textContent = '...';
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(),
                },
            });
            if (!response.ok) throw new Error('HTTP ' + response.status);
            const data = await response.json();
            onSuccess(data);
        } catch (error) {
            console.error('JobDevs notificaciones: error al actualizar', error);
            mostrarToast('No se pudieron actualizar las notificaciones.', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = textoOriginal;
        }
    }

    toggle.addEventListener('click', function (event) {
        event.stopPropagation();
        setAbierto(!estaAbierto());
    });

    document.addEventListener('click', function (event) {
        if (!estaAbierto()) return;
        if (popover.contains(event.target) || toggle.contains(event.target)) return;
        setAbierto(false);
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && estaAbierto()) setAbierto(false);
    });

    const btnMarcarTodas = popover.querySelector('[data-notif-mark-all]');
    if (btnMarcarTodas) {
        btnMarcarTodas.addEventListener('click', function () {
            ejecutarAccion(btnMarcarTodas, function (data) {
                popover.querySelectorAll('.notif-popover-item.is-unread').forEach(function (item) {
                    item.classList.remove('is-unread');
                });
                actualizarBadges(0);
                ocultarFormulariosMarcarLeidas();
                btnMarcarTodas.hidden = true;
                mostrarToast(data.mensaje || 'Notificaciones marcadas como leídas.');
            });
        });
    }

    const btnVerTodas = popover.querySelector('[data-notif-ver-todas]');
    let htmlInicial = null;
    let expandido = false;

    const btnLimpiar = popover.querySelector('[data-notif-clear]');
    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', function () {
            ejecutarAccion(btnLimpiar, function (data) {
                if (body) {
                    body.innerHTML = '';
                    body.appendChild(estadoVacio());
                }
                htmlInicial = '';
                expandido = false;
                if (btnVerTodas) btnVerTodas.hidden = true;
                actualizarBadges(0);
                ocultarFormulariosMarcarLeidas();
                vaciarTarjetasNotificaciones();
                btnLimpiar.hidden = true;
                if (btnMarcarTodas) btnMarcarTodas.hidden = true;
                mostrarToast(data.mensaje || 'Notificaciones eliminadas.');
            });
        });
    }

    // "Ver todas" carga el historial completo dentro del popover, sin navegar.
    if (btnVerTodas) {
        btnVerTodas.addEventListener('click', async function () {
            if (expandido) {
                if (body) body.innerHTML = htmlInicial || '';
                expandido = false;
                btnVerTodas.textContent = 'Ver todas';
                return;
            }

            if (htmlInicial === null && body) htmlInicial = body.innerHTML;

            const textoOriginal = btnVerTodas.textContent;
            btnVerTodas.disabled = true;
            btnVerTodas.textContent = 'Cargando...';
            try {
                const response = await fetch(btnVerTodas.getAttribute('data-url'), {
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                });
                if (!response.ok) throw new Error('HTTP ' + response.status);
                const data = await response.json();
                const notificaciones = data.notificaciones || [];

                if (body) {
                    body.innerHTML = '';
                    if (notificaciones.length) {
                        notificaciones.forEach(function (notificacion) {
                            body.appendChild(crearItem(notificacion));
                        });
                    } else {
                        body.appendChild(estadoVacio());
                    }
                }
                expandido = true;
                btnVerTodas.textContent = 'Ver menos';
            } catch (error) {
                console.error('JobDevs notificaciones: error al cargar el historial', error);
                mostrarToast('No se pudieron cargar las notificaciones.', 'error');
                btnVerTodas.textContent = textoOriginal;
            } finally {
                btnVerTodas.disabled = false;
            }
        });
    }

    // Las notificaciones que llegan por SSE se insertan en el popover abierto.
    document.addEventListener('jobdevs:notificacion', function (event) {
        const data = event.detail || {};
        if (!body || !data.mensaje) return;

        const empty = body.querySelector('[data-notif-empty]');
        if (empty) empty.remove();

        body.prepend(crearItem({ ...data, leida: false }));
    });

    window.JobDevsNotificaciones = {
        abrir: function () { setAbierto(true); },
        cerrar: function () { setAbierto(false); },
        alternar: function () { setAbierto(!estaAbierto()); },
    };
})();
