/**
 * JobDevs - Búsqueda y filtrado dinámico del Catálogo de Proyectos con Promesas (SCRUM-195)
 * Actualiza la grilla de proyectos en vivo ante cambios en búsqueda o filtros sin recargar.
 */
(function() {
    'use strict';

    let debounceTimer = null;

    function escapeHtml(text) {
        if (!text) return '';
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return text.toString().replace(/[&<>"']/g, m => map[m]);
    }

    function renderizarCard(p, favoritosIds, csrfToken, esDesarrollador) {
        const esFav = favoritosIds.includes(p.id);
        const prioridadBadgeClass = p.prioridad === 'alta' ? 'danger' : (p.prioridad === 'media' ? 'warning' : 'info');

        let favButtonHtml = '';
        if (esDesarrollador) {
            favButtonHtml = `
                <form method="post" action="/favoritos/toggle/${p.id}/" style="display:inline; margin:0; padding:0;">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                    <button type="submit" aria-label="${esFav ? 'Quitar de favoritos' : 'Guardar en favoritos'}" title="${esFav ? 'Quitar de favoritos' : 'Guardar en favoritos'}" style="background:none; border:none; padding:0; cursor:pointer; font-size:18px; line-height:1; transition:transform 0.2s;">
                        <i class="${esFav ? 'fa-solid fa-heart' : 'fa-regular fa-heart'}" style="color:${esFav ? 'var(--danger)' : 'var(--text-muted)'}"></i>
                    </button>
                </form>
            `;
        }

        let badgeEmpresaHtml = '';
        if (p.empresa_badge) {
            const badgeLabel = escapeHtml(p.empresa_badge.label);
            if (p.empresa_verificada) {
                const bClass = p.empresa_badge.label === 'Negocio Verificado' ? 'badge-info' : 'badge-success';
                badgeEmpresaHtml = `
                    <div style="margin-top:4px;">
                        <span class="badge ${bClass}" data-testid="badge-verificacion" title="${badgeLabel}">
                            <i class="fa fa-circle-check" style="margin-right:4px;"></i>${badgeLabel}
                        </span>
                    </div>
                `;
            } else {
                const bClass = p.empresa_estado_verificacion === 'rechazada' ? 'badge-danger' : 'badge-warning';
                badgeEmpresaHtml = `
                    <div style="margin-top:4px;">
                        <span class="badge ${bClass}" data-testid="badge-verificacion" title="${badgeLabel}">
                            <i class="fa fa-triangle-exclamation" style="margin-right:4px;"></i>${badgeLabel}
                        </span>
                    </div>
                `;
            }
        }

        const reputacionHtml = p.empresa_reputacion > 0
            ? `<i class="fa fa-star" style="color:#f59e0b; margin-right:3px;"></i>${parseFloat(p.empresa_reputacion).toFixed(1)} reputación`
            : `Empresa nueva`;

        const logoHtml = p.empresa_logo
            ? `<img src="${escapeHtml(p.empresa_logo)}" alt="Logo">`
            : `<i class="fa fa-building" style="color: var(--text-muted);"></i>`;

        const empresaNombreHtml = p.empresa_id
            ? `<a href="/usuarios/empresa/${p.empresa_id}/" style="text-decoration:none; color:inherit;" title="Ver perfil institucional y reseñas">
                 <div style="font-size:13px; font-weight:600; color:var(--text-primary); display:inline-flex; align-items:center; gap:4px;">
                   ${escapeHtml(p.empresa_nombre)} <i class="fa fa-arrow-up-right-from-square" style="font-size:10px; opacity:0.6;"></i>
                 </div>
               </a>`
            : `<div style="font-size:13px; font-weight:600; color:var(--text-primary);">${escapeHtml(p.empresa_nombre)}</div>`;

        return `
            <div class="project-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <span class="tag-solucion">${escapeHtml(p.tipo_solucion)}</span>
                    ${favButtonHtml}
                </div>
                <h3 class="project-card-title">${escapeHtml(p.titulo)}</h3>
                <div style="margin: 8px 0; display:flex; flex-wrap:wrap; align-items:center; gap:8px;">
                    <span class="badge badge-${prioridadBadgeClass}">${escapeHtml(p.prioridad)}</span>
                    <span class="badge badge-${p.modalidad === 'remoto' ? 'success' : (p.modalidad === 'presencial' ? 'info' : 'warning')}" style="display:inline-flex; align-items:center; gap:4px;">
                        <i class="fa ${p.modalidad === 'remoto' ? 'fa-globe' : (p.modalidad === 'presencial' ? 'fa-location-dot' : 'fa-laptop-house')}"></i>
                        ${escapeHtml(p.ubicacion_display || (p.modalidad === 'remoto' ? 'Remoto (Nivel Nacional)' : p.ciudad))}
                    </span>
                    <span style="font-size: 12px; color: var(--text-muted); margin-left: 4px;">
                        <i class="fa fa-users" style="margin-right:4px;"></i>${p.num_postulaciones || 0} postulantes
                    </span>
                    <span style="font-size: 12px; color: var(--text-muted); margin-left: 4px;">
                        <i class="fa fa-door-open" style="margin-right:4px;"></i>${p.vacantes_disponibles !== undefined ? p.vacantes_disponibles : p.vacantes} de ${p.vacantes} cupos libres
                    </span>
                </div>
                <p class="project-desc">${escapeHtml(p.descripcion)}</p>
                <div class="card-footer">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div class="user-avatar" style="width: 32px; height: 32px; font-size: 11px; background: var(--page-bg); border: 1px solid var(--border);">
                            ${logoHtml}
                        </div>
                        <div>
                            ${empresaNombreHtml}
                            ${badgeEmpresaHtml}
                            <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">
                                ${reputacionHtml}
                            </div>
                        </div>
                    </div>
                    <a href="/postulaciones/postular/${p.id}/" class="btn btn-primary btn-sm">
                      <i class="fa fa-paper-plane"></i> Postularme
                    </a>
                </div>
            </div>
        `;
    }

    async function filtrarCatalogoAsync(urlParams) {
        const grid = document.querySelector('.cards-grid');
        if (!grid) return;

        grid.style.transition = 'opacity 0.2s';
        grid.style.opacity = '0.5';

        const fullUrl = '/proyectos/?' + urlParams.toString();

        try {
            const response = await fetch(fullUrl, {
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });

            if (!response.ok) throw new Error('Error al consultar proyectos');

            const data = await response.json();
            if (data.status === 'ok') {
                const csrfTokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
                const csrfToken = csrfTokenInput ? csrfTokenInput.value : '';
                const esDesarrollador = document.body.dataset.userRol === 'desarrollador' || Boolean(document.querySelector('form[action*="/favoritos/toggle/"]'));

                if (data.proyectos && data.proyectos.length > 0) {
                    grid.innerHTML = data.proyectos.map(p => renderizarCard(p, data.favoritos_ids || [], csrfToken, esDesarrollador)).join('');
                } else {
                    grid.innerHTML = `
                        <div class="empty-state" style="grid-column: 1 / -1; padding: 60px; background: var(--card-bg); border-radius: var(--radius); border: 1px solid var(--border);">
                            <i class="fa fa-magnifying-glass" style="font-size: 32px; color: var(--text-muted); margin-bottom: 15px;"></i>
                            <p style="color: var(--text-secondary); font-size: 15px;">No se encontraron proyectos con los filtros seleccionados.</p>
                            <a href="/proyectos/" class="btn btn-primary" style="margin-top: 15px;">Limpiar filtros</a>
                        </div>
                    `;
                }

                // Re-vincular eventos reactivos de favoritos en las tarjetas recién renderizadas
                if (window.JobDevsFavoritos && typeof window.JobDevsFavoritos.inicializar === 'function') {
                    window.JobDevsFavoritos.inicializar();
                }

                // Actualizar URL del navegador sin recarga
                window.history.replaceState({}, '', fullUrl);
            }
        } catch (err) {
            console.error('Error filtrando catálogo:', err);
        } finally {
            grid.style.opacity = '1';
        }
    }

    function inicializarCatalogoAsync() {
        const form = document.querySelector('form.filters-bar');
        if (!form) return;

        function recolectarParametros() {
            const formData = new FormData(form);
            const params = new URLSearchParams();
            for (const [key, value] of formData.entries()) {
                const trimmed = (value || '').trim();
                if (trimmed) {
                    params.append(key, trimmed);
                }
            }
            return params;
        }

        const inputBusqueda = form.querySelector('input[name="q"]');
        if (inputBusqueda) {
            inputBusqueda.addEventListener('input', function() {
                if (debounceTimer) clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    filtrarCatalogoAsync(recolectarParametros());
                }, 300);
            });
        }

        form.querySelectorAll('select').forEach(sel => {
            sel.addEventListener('change', function() {
                filtrarCatalogoAsync(recolectarParametros());
            });
        });

        form.addEventListener('submit', function(e) {
            e.preventDefault();
            filtrarCatalogoAsync(recolectarParametros());
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
