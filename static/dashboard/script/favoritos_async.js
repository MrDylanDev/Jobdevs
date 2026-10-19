/**
 * JobDevs - Toggle reactivo de Favoritos con Promesas (Fetch API) (SCRUM-192)
 * Permite guardar o remover proyectos de favoritos sin recarga de página ni salto de scroll.
 */
(function() {
    'use strict';

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

    async function ejecutarToggleFavorito(form) {
        const btn = form.querySelector('button[type="submit"]') || form.querySelector('button');
        if (!btn || btn.disabled) return;

        const icon = btn.querySelector('i');
        const url = form.getAttribute('action');
        if (!url) return;

        btn.disabled = true;

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
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'No se pudo actualizar el favorito');
            }

            const data = await response.json();
            if (data.status === 'ok') {
                // Micro-animación de pulso
                if (icon) {
                    icon.style.transition = 'transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                    icon.style.transform = 'scale(1.35)';

                    if (data.agregado) {
                        icon.className = 'fa-solid fa-heart';
                        icon.style.color = 'var(--danger, #ef4444)';
                        btn.setAttribute('title', 'Quitar de favoritos');
                        btn.setAttribute('aria-label', 'Quitar de favoritos');
                    } else {
                        icon.className = 'fa-regular fa-heart';
                        icon.style.color = 'var(--text-muted, #94a3b8)';
                        btn.setAttribute('title', 'Guardar en favoritos');
                        btn.setAttribute('aria-label', 'Guardar en favoritos');
                    }

                    setTimeout(() => {
                        icon.style.transform = 'scale(1)';
                    }, 200);
                }

                // Si estamos en la página dedicada de favoritos (/favoritos/), animar eliminación de tarjeta
                const card = form.closest('.project-card');
                if (card && window.location.pathname.includes('/favoritos/') && !data.agregado) {
                    card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.95)';
                    setTimeout(() => {
                        card.remove();
                        // Si no quedan tarjetas, mostrar empty state
                        const grid = document.querySelector('.cards-grid');
                        if (grid && grid.querySelectorAll('.project-card').length === 0) {
                            grid.innerHTML = `
                                <div class="empty-state" style="grid-column:1/-1;">
                                    <i class="fa fa-heart-crack"></i>
                                    <p style="font-size:16px; font-weight:600; margin-bottom:8px;">Aún no tienes favoritos</p>
                                    <p style="margin-bottom:20px;">Guarda proyectos que te interesen para postularte después.</p>
                                    <a href="/proyectos/" class="btn btn-primary"><i class="fa fa-magnifying-glass"></i> Explorar Proyectos</a>
                                </div>
                            `;
                        }
                    }, 300);
                }

                // Disparar toast informativo si existe el módulo SSE/Toast
                if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
                    window.JobDevsSSE.mostrarToast({
                        tipo: data.agregado ? 'aprobacion' : 'alerta',
                        mensaje: data.mensaje,
                    });
                }
            }
        } catch (err) {
            console.error('Error en toggle de favoritos:', err);
            if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
                window.JobDevsSSE.mostrarToast({
                    tipo: 'alerta',
                    mensaje: err.message || 'Error de conexión al actualizar favoritos.',
                });
            }
        } finally {
            btn.disabled = false;
        }
    }

    function inicializarFavoritosAsync() {
        document.querySelectorAll('form[action*="/favoritos/toggle/"]').forEach(form => {
            if (form.dataset.asyncBound === 'true') return;
            form.dataset.asyncBound = 'true';

            form.addEventListener('submit', function(e) {
                e.preventDefault();
                ejecutarToggleFavorito(form);
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializarFavoritosAsync);
    } else {
        inicializarFavoritosAsync();
    }

    window.JobDevsFavoritos = {
        inicializar: inicializarFavoritosAsync,
        toggle: ejecutarToggleFavorito,
    };
})();
