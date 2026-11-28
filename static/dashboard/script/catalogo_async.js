/**
 * JobDevs - Integración HTMX del Catálogo de Proyectos (SCRUM-195 / Phase 2 S1)
 * Re-hidrata favoritos e iconos tras swaps parciales y mantiene el contrato
 * programático window.JobDevsCatalogo = { filtrar, inicializar }.
 */
(function () {
    'use strict';

    let listenersRegistrados = false;

    function rehidratarCatalogo(target) {
        if (window.JobDevsFavoritos && typeof window.JobDevsFavoritos.inicializar === 'function') {
            window.JobDevsFavoritos.inicializar();
        }
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            if (target && target.nodeType === 1) {
                try {
                    window.lucide.createIcons({ root: target });
                    return;
                } catch (e) {
                    // Fallback al escaneo global si la versión de Lucide no soporta root.
                }
            }
            window.lucide.createIcons();
        }
    }

    async function filtrarCatalogoAsync(urlParams) {
        const contenedor = document.getElementById('catalogoResultados');
        if (!contenedor) return;

        const query = urlParams ? urlParams.toString() : '';
        const fullUrl = query ? '/proyectos/?' + query : '/proyectos/';

        if (window.htmx && typeof window.htmx.ajax === 'function') {
            await window.htmx.ajax('GET', fullUrl, {
                target: '#catalogoResultados',
                swap: 'innerHTML',
            });
            if (window.history && typeof window.history.replaceState === 'function') {
                window.history.replaceState({}, '', fullUrl);
            }
            return;
        }

        contenedor.style.transition = 'opacity 0.2s';
        contenedor.style.opacity = '0.5';
        try {
            const response = await fetch(fullUrl, {
                headers: { 'HX-Request': 'true' },
            });
            if (!response.ok) throw new Error('Error al consultar proyectos');
            contenedor.innerHTML = await response.text();
            rehidratarCatalogo(contenedor);
            if (window.history && typeof window.history.replaceState === 'function') {
                window.history.replaceState({}, '', fullUrl);
            }
        } catch (err) {
            console.error('Error filtrando catálogo:', err);
        } finally {
            contenedor.style.opacity = '1';
        }
    }

    function inicializarCatalogoAsync() {
        if (listenersRegistrados) return;
        listenersRegistrados = true;

        document.addEventListener('htmx:afterSwap', function (event) {
            const target = event && event.detail ? event.detail.target : null;
            if (target && target.id === 'catalogoResultados') {
                rehidratarCatalogo(target);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializarCatalogoAsync);
    } else {
        inicializarCatalogoAsync();
    }

    window.JobDevsCatalogo = {
        filtrar: filtrarCatalogoAsync,
        inicializar: inicializarCatalogoAsync,
    };
})();
