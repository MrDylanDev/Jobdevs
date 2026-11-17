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
    const btnMarcarTodas = popover.querySelector('[data-notif-mark-all]');
    const btnLimpiar = popover.querySelector('[data-notif-clear]');
    const btnVerTodas = popover.querySelector('[data-notif-ver-todas]');

    // Estado canónico de la lista. El DOM se renderiza a partir de aquí, así
    // que "Ver menos" no restaura HTML viejo ni pierde eventos SSE.
    let recientes = leerNotificacionesIniciales();
    let historial = null;
    let expandido = false;
    let peticionHistorial = null;
    // Se incrementa con cada mutación (marcar/limpiar) para descartar
    // respuestas de historial que lleguen tarde.
    let versionEstado = 0;

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

    function refrescarIconos() {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    }

    function crearIcono(nombre) {
        const icon = document.createElement('i');
        icon.setAttribute('data-lucide', nombre);
        return icon;
    }

    function leerNotificacionesIniciales() {
        if (!body) return [];
        return Array.from(body.querySelectorAll('.notif-popover-item')).map(function (item) {
            const mensajeEl = item.querySelector('.notif-popover-text > span');
            const fechaEl = item.querySelector('.notif-popover-text > small');
            return {
                id: item.getAttribute('data-notif-id') || '',
                mensaje: mensajeEl ? mensajeEl.textContent : '',
                fecha: fechaEl ? fechaEl.textContent : '',
                leida: !item.classList.contains('is-unread'),
                tipo: '',
            };
        });
    }

    function mismoId(a, b) {
        return String(a) === String(b);
    }

    function hayNoLeidas() {
        return recientes.some(function (n) { return !n.leida; })
            || (historial || []).some(function (n) { return !n.leida; });
    }

    function hayNotificaciones() {
        return recientes.length > 0 || (historial || []).length > 0;
    }

    function mostrarControles() {
        if (btnMarcarTodas) btnMarcarTodas.hidden = !hayNoLeidas();
        if (btnLimpiar) btnLimpiar.hidden = !hayNotificaciones();
    }

    function actualizarBadges(count) {
        if (window.JobDevsSSE && typeof window.JobDevsSSE.actualizarBadges === 'function') {
            window.JobDevsSSE.actualizarBadges(count);
            return;
        }
        const total = parseInt(count, 10) || 0;
        // Solo el badge de notificaciones: .nav-badge es genérico y lo usan
        // mensajes, postulaciones, contratos, etc.
        document.querySelectorAll('.notif-badge, [data-notif-badge]').forEach(function (badge) {
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
            const icon = crearIcono('inbox');
            const text = document.createElement('p');
            text.textContent = 'Sin notificaciones';
            empty.appendChild(icon);
            empty.appendChild(text);
            list.appendChild(empty);
        });
        refrescarIconos();
    }

    function mostrarToast(mensaje) {
        if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
            window.JobDevsSSE.mostrarToast({ tipo: 'aprobacion', mensaje: mensaje });
        }
    }

    function estadoVacio() {
        const empty = document.createElement('div');
        empty.className = 'notif-popover-empty';
        empty.setAttribute('data-notif-empty', '');
        const icon = crearIcono('bell-off');
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

        const icon = crearIcono('circle');

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

    function renderLista(lista) {
        if (!body) return;
        body.innerHTML = '';
        if (!lista.length) {
            body.appendChild(estadoVacio());
        } else {
            lista.forEach(function (notificacion) {
                body.appendChild(crearItem(notificacion));
            });
        }
        refrescarIconos();
    }

    function cancelarPeticionHistorial() {
        if (peticionHistorial) {
            peticionHistorial.abort();
            peticionHistorial = null;
        }
    }

    function fusionarHistorial(items) {
        const porId = new Map();
        const idsServidor = [];

        (items || []).forEach(function (notificacion) {
            const id = String(notificacion.id);
            idsServidor.push(id);
            porId.set(id, Object.assign({}, notificacion));
        });

        // El estado local es más reciente para los ids ya conocidos (por
        // ejemplo, si se marcaron leídas mientras la petición estaba en vuelo).
        recientes.forEach(function (notificacion) {
            const id = String(notificacion.id);
            if (porId.has(id)) {
                const base = porId.get(id);
                base.leida = notificacion.leida;
                if (!base.mensaje) base.mensaje = notificacion.mensaje;
                if (!base.fecha) base.fecha = notificacion.fecha;
            } else {
                porId.set(id, Object.assign({}, notificacion));
            }
        });

        const extras = recientes.filter(function (notificacion) {
            return !idsServidor.includes(String(notificacion.id));
        });

        return extras.concat(Array.from(porId.values()));
    }

    async function cargarHistorial(opciones) {
        if (!btnVerTodas) return;
        const silencioso = Boolean(opciones && opciones.silencioso);
        const url = btnVerTodas.getAttribute('data-url');
        if (!url) return;

        cancelarPeticionHistorial();
        const controlador = new AbortController();
        peticionHistorial = controlador;
        const version = versionEstado;
        const textoOriginal = btnVerTodas.textContent;

        btnVerTodas.disabled = true;
        if (!silencioso) btnVerTodas.textContent = 'Cargando...';

        try {
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                signal: controlador.signal,
            });
            if (!response.ok) throw new Error('HTTP ' + response.status);

            const data = await response.json();
            // Si hubo "Limpiar"/"Marcar leídas" mientras cargaba, esta
            // respuesta ya no representa el estado actual.
            if (controlador.signal.aborted || version !== versionEstado) return;

            historial = fusionarHistorial(data.notificaciones || []);
            expandido = true;
            renderLista(historial);
            btnVerTodas.hidden = false;
            btnVerTodas.textContent = 'Ver menos';
            mostrarControles();

            if (typeof data.unread_count === 'number') {
                actualizarBadges(data.unread_count);
            }
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('JobDevs notificaciones: error al cargar el historial', error);
            mostrarToast('No se pudieron cargar las notificaciones.');
            btnVerTodas.textContent = expandido ? 'Ver menos' : textoOriginal;
        } finally {
            if (peticionHistorial === controlador) {
                peticionHistorial = null;
                btnVerTodas.disabled = false;
            } else if (!peticionHistorial) {
                // La petición fue cancelada y no hay otra en curso.
                btnVerTodas.disabled = false;
            }
        }
    }

    function colapsarHistorial() {
        expandido = false;
        historial = null;
        cancelarPeticionHistorial();
        renderLista(recientes);
        if (btnVerTodas) {
            btnVerTodas.textContent = 'Ver todas';
            btnVerTodas.hidden = recientes.length === 0;
        }
        mostrarControles();
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
            mostrarToast('No se pudieron actualizar las notificaciones.');
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

    if (btnMarcarTodas) {
        btnMarcarTodas.addEventListener('click', function () {
            ejecutarAccion(btnMarcarTodas, function (data) {
                // Invalida cualquier historial en vuelo antes de mutar estado.
                versionEstado += 1;
                cancelarPeticionHistorial();
                ocultarFormulariosMarcarLeidas();

                recientes.forEach(function (notificacion) { notificacion.leida = true; });
                if (historial) {
                    historial.forEach(function (notificacion) { notificacion.leida = true; });
                }
                renderLista(expandido && historial ? historial : recientes);
                actualizarBadges(0);
                mostrarControles();

                // Si el historial estaba abierto, recargarlo para reflejar
                // también las notificaciones que no estaban en pantalla.
                if (expandido) cargarHistorial({ silencioso: true });

                mostrarToast(data.mensaje || 'Notificaciones marcadas como leídas.');
            });
        });
    }

    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', function () {
            ejecutarAccion(btnLimpiar, function (data) {
                versionEstado += 1;
                cancelarPeticionHistorial();

                recientes = [];
                historial = null;
                expandido = false;
                renderLista([]);
                if (btnVerTodas) btnVerTodas.hidden = true;
                actualizarBadges(0);
                ocultarFormulariosMarcarLeidas();
                vaciarTarjetasNotificaciones();
                mostrarControles();
                mostrarToast(data.mensaje || 'Notificaciones eliminadas.');
            });
        });
    }

    // "Ver todas" carga el historial completo dentro del popover, sin navegar.
    if (btnVerTodas) {
        btnVerTodas.addEventListener('click', function () {
            if (expandido) {
                colapsarHistorial();
                return;
            }
            cargarHistorial();
        });
    }

    // Las notificaciones que llegan por SSE se insertan en el estado y en la
    // vista activa; también reactivan los controles si estaban ocultos.
    document.addEventListener('jobdevs:notificacion', function (event) {
        const data = event.detail || {};
        if (!body || !data.mensaje) return;

        const notificacion = {
            id: data.id != null ? String(data.id) : '',
            mensaje: data.mensaje,
            fecha: data.fecha || 'Ahora',
            leida: false,
            tipo: data.tipo || '',
        };

        if (notificacion.id && recientes.some(function (n) { return mismoId(n.id, notificacion.id); })) {
            return;
        }

        recientes.unshift(notificacion);
        if (historial && (!notificacion.id || !historial.some(function (n) {
            return mismoId(n.id, notificacion.id);
        }))) {
            historial.unshift(notificacion);
        }

        renderLista(expandido && historial ? historial : recientes);
        if (btnVerTodas) btnVerTodas.hidden = false;
        mostrarControles();
    });

    mostrarControles();

    window.JobDevsNotificaciones = {
        abrir: function () { setAbierto(true); },
        cerrar: function () { setAbierto(false); },
        alternar: function () { setAbierto(!estaAbierto()); },
    };
})();
