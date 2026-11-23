/**
 * JobDevs - Toggle reactivo de Favoritos con Fetch API (SCRUM-192)
 * Permite guardar y remover proyectos de favoritos al instante, sin recarga ni saltos.
 * Soporta actualización optimista (0ms), desmarcado reactivo y sincronización en tiempo real
 * entre el catálogo/explorar y la sección de Favoritos del Dashboard.
 */
(function() {
    'use strict';

    // Set en memoria para evitar llamadas simultáneas o dobles envíos sobre el mismo proyecto
    const proyectosEnProceso = new Set();

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

    function getCsrfToken(form) {
        if (form) {
            const tokenInput = form.querySelector('[name=csrfmiddlewaretoken]');
            if (tokenInput && tokenInput.value) return tokenInput.value;
        }
        const inputToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return inputToken ? inputToken.value : getCookie('csrftoken');
    }

    function obtenerEstadoFavorito(btn) {
        if (!btn) return false;
        if (btn.classList.contains('is-favorito')) return true;
        const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
        if (aria.includes('quitar')) return true;
        const icon = btn.querySelector('svg, i');
        if (icon) {
            const color = icon.style.color || '';
            const fill = icon.getAttribute('fill') || icon.style.fill || '';
            if (color.includes('ef4444') || fill.includes('ef4444') || fill === 'currentColor') {
                return true;
            }
        }
        return false;
    }

    function aplicarEstadoVisual(btn, icon, esFavorito, animar) {
        if (!btn) return;
        btn.classList.toggle('is-favorito', esFavorito);
        btn.setAttribute('title', esFavorito ? 'Quitar de favoritos' : 'Guardar en favoritos');
        btn.setAttribute('aria-label', esFavorito ? 'Quitar de favoritos' : 'Guardar en favoritos');

        const el = icon || btn.querySelector('svg, i');
        if (el) {
            el.style.color = esFavorito ? 'var(--danger, #ef4444)' : 'var(--text-muted, #8f8f8f)';
            el.style.fill = esFavorito ? 'var(--danger, #ef4444)' : 'none';
            if (el.tagName && el.tagName.toLowerCase() === 'svg') {
                el.setAttribute('fill', esFavorito ? 'currentColor' : 'none');
            }
        }

        if (animar) {
            btn.classList.remove('animating');
            void btn.offsetWidth; // Reflow para reiniciar animación CSS
            btn.classList.add('animating');
            setTimeout(() => {
                btn.classList.remove('animating');
            }, 360);
        }
    }

    function actualizarContadorSidebarFavoritos(delta) {
        const badge = document.getElementById('sidebarFavoritosCountBadge');
        if (!badge) return;
        const grid = document.getElementById('devFavoritosGrid');
        if (grid) {
            const count = grid.querySelectorAll('.project-card, .dev-explore-card').length;
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-flex' : 'none';
        } else if (typeof delta === 'number') {
            const current = parseInt(badge.textContent.trim(), 10) || 0;
            const nuevo = Math.max(0, current + delta);
            badge.textContent = nuevo;
            badge.style.display = nuevo > 0 ? 'inline-flex' : 'none';
        }
    }

    function verificarEmptyStateFavoritos() {
        const grid = document.querySelector('#devFavoritosGrid') || document.querySelector('.cards-grid');
        if (grid && grid.querySelectorAll('.project-card, .dev-explore-card').length === 0) {
            grid.innerHTML = `
                <div class="cockpit-empty-state empty-state" style="grid-column:1 / -1; padding:48px 20px;">
                    <i data-lucide="heart" style="width:42px; height:42px; opacity:0.35; margin-bottom:14px; color:var(--text-muted);"></i>
                    <h3 style="font-size:16px; font-weight:700; margin:0 0 6px; color:var(--fg);">No tienes proyectos guardados</h3>
                    <p style="color:var(--text-muted); font-size:13px; max-width:380px; margin:0 0 18px; line-height:1.5;">Explora el catálogo de proyectos y haz clic en el corazón para guardar oportunidades y revisarlas más tarde.</p>
                    <button type="button" class="btn-cockpit primary" onclick="verSeccion('explorar')">
                        <i data-lucide="compass"></i>
                        <span>Explorar Convocatorias</span>
                    </button>
                </div>
            `;
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        }
    }

    function animarYRemoverCard(card) {
        if (!card) return;
        card.style.transition = 'opacity 0.22s ease, transform 0.22s ease';
        card.style.opacity = '0';
        card.style.transform = 'scale(0.92)';
        setTimeout(() => {
            card.remove();
            verificarEmptyStateFavoritos();
            actualizarContadorSidebarFavoritos();
        }, 220);
    }

    function sincronizarFavoritosEnDOM(proyectoId, agregado, sourceCard) {
        if (!proyectoId) return;
        const pIdStr = String(proyectoId);

        // 1. Sincronizar todos los botones de corazón para este proyecto en la pantalla
        document.querySelectorAll('form[action*="/favoritos/toggle/' + pIdStr + '/"] .fav-toggle-btn').forEach(btn => {
            aplicarEstadoVisual(btn, btn.querySelector('svg, i'), agregado, false);
        });

        const favGrid = document.getElementById('devFavoritosGrid');

        // 2. Si se agregó a favoritos, insertarlo reactivamente en la grilla de Favoritos
        if (agregado && favGrid) {
            const yaExiste = document.getElementById('favCard_' + pIdStr);
            if (!yaExiste) {
                const empty = favGrid.querySelector('.cockpit-empty-state, .empty-state');
                if (empty) empty.remove();

                const origen = sourceCard || document.getElementById('exploreCard_' + pIdStr) || document.querySelector('.project-card[data-id="' + pIdStr + '"]');
                if (origen) {
                    const clon = origen.cloneNode(true);
                    clon.id = 'favCard_' + pIdStr;
                    clon.setAttribute('data-id', pIdStr);
                    clon.style.display = 'flex';
                    clon.style.opacity = '1';
                    clon.style.transform = 'none';
                    clon.style.animation = 'devFade 0.25s ease';

                    const clonBtn = clon.querySelector('.fav-toggle-btn');
                    if (clonBtn) {
                        aplicarEstadoVisual(clonBtn, clonBtn.querySelector('svg, i'), true, false);
                    }

                    favGrid.prepend(clon);
                    actualizarContadorSidebarFavoritos();

                    if (window.lucide && typeof window.lucide.createIcons === 'function') {
                        window.lucide.createIcons();
                    }
                }
            }
        } else if (!agregado) {
            // 3. Si se quitó de favoritos, remover la tarjeta en #devFavoritosGrid
            if (favGrid) {
                const cardEnFavoritos = document.getElementById('favCard_' + pIdStr);
                if (cardEnFavoritos) {
                    animarYRemoverCard(cardEnFavoritos);
                }
            }

            // 4. Si estamos en la página standalone /favoritos/
            if (window.location.pathname.includes('/favoritos/')) {
                const standaloneCard = document.getElementById('favCard_' + pIdStr) || (sourceCard && sourceCard.closest('.project-card'));
                if (standaloneCard) {
                    animarYRemoverCard(standaloneCard);
                }
            }
        }
    }

    async function ejecutarToggleFavorito(form) {
        if (!form) return;
        const btn = form.querySelector('.fav-toggle-btn') || form.querySelector('button');
        if (!btn) return;

        const url = form.getAttribute('action');
        if (!url) return;

        const proyIdMatch = url.match(/\/(\d+)\/?$/);
        const proyId = proyIdMatch ? String(proyIdMatch[1]) : null;
        if (!proyId) return;

        // Si ya hay una petición en curso para este mismo proyecto, evitar duplicados
        if (proyectosEnProceso.has(proyId)) return;
        proyectosEnProceso.add(proyId);

        const sourceCard = form.closest('.project-card, .dev-explore-card');
        const icon = btn.querySelector('svg, i');
        const estaFavorito = obtenerEstadoFavorito(btn);
        const nuevoEstado = !estaFavorito;

        // 1. Actualización optimista instantánea (0ms) en el botón
        aplicarEstadoVisual(btn, icon, nuevoEstado, true);

        // 2. Si se está desmarcando y el usuario está en la vista de Favoritos:
        const enSeccionFavoritos = !!form.closest('#favoritos') || window.location.pathname.includes('/favoritos/');
        if (!nuevoEstado && enSeccionFavoritos && sourceCard) {
            sourceCard.style.transition = 'opacity 0.22s ease, transform 0.22s ease';
            sourceCard.style.opacity = '0.35'; // Atenuar inmediatamente
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(form),
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'No se pudo actualizar el favorito');
            }

            const data = await response.json();
            if (data.status === 'ok') {
                const finalId = String(data.proyecto_id || proyId);
                sincronizarFavoritosEnDOM(finalId, data.agregado, sourceCard);
            }
        } catch (err) {
            console.error('Error en toggle de favoritos:', err);
            // Revertir estado visual en caso de fallo
            aplicarEstadoVisual(btn, icon, estaFavorito, false);
            if (sourceCard) {
                sourceCard.style.opacity = '1';
                sourceCard.style.transform = 'none';
            }

            if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
                window.JobDevsSSE.mostrarToast({
                    tipo: 'alerta',
                    mensaje: err.message || 'Error de conexión al actualizar favoritos.',
                });
            }
        } finally {
            proyectosEnProceso.delete(proyId);
        }
    }

    // Interceptar clics en botones de favoritos de manera global
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.fav-toggle-btn');
        if (!btn) return;

        const form = btn.closest('form[action*="/favoritos/toggle/"]');
        if (form) {
            e.preventDefault();
            e.stopPropagation();
            ejecutarToggleFavorito(form);
        }
    }, true);

    // Interceptar submits por si se envían por teclado o programación
    document.addEventListener('submit', function(e) {
        const form = e.target.closest('form[action*="/favoritos/toggle/"]');
        if (form) {
            e.preventDefault();
            e.stopPropagation();
            ejecutarToggleFavorito(form);
        }
    }, true);

    window.JobDevsFavoritos = {
        toggle: ejecutarToggleFavorito,
        sincronizar: sincronizarFavoritosEnDOM
    };
})();
