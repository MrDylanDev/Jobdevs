/**
 * JobDevs — Modales de Dashboard: Perfiles Públicos (Empresa y Desarrollador)
 */

import {
  escapeHtml,
  parseJsonResponse,
  abrirModal,
  setHeader,
  setContent,
  setFooter,
} from './modal_core.js';

// ─────────────────────────────────────────────────────────────
// 5. DETALLE EMPRESA
// ─────────────────────────────────────────────────────────────
export async function cargarDetalleEmpresa(url) {
  abrirModal('');
  setHeader('PERFIL // INSTITUCIONAL', 'Cargando perfil de empresa…');

  try {
    const res = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      credentials: 'same-origin'
    });
    const data = await parseJsonResponse(res, 'No se pudo obtener el perfil de la empresa.');
    if (!data.ok || !data.empresa) throw new Error(data.error || 'No se pudo obtener el perfil de la empresa');

    const e = data.empresa;
    setHeader('EMPRESA // FICHA INSTITUCIONAL', e.nombre, e.sector + ' · ' + e.ciudad);

    const badgeHtml = e.es_verificada
      ? '<span class="jdm-badge jdm-badge-success"><i data-lucide="check-circle"></i> ' + escapeHtml(e.badge_label || 'Verificada') + '</span>'
      : '<span class="jdm-badge jdm-badge-gray"><i data-lucide="shield"></i> ' + escapeHtml(e.badge_label || 'Sin verificar') + '</span>';

    const initial = (e.nombre || 'E').slice(0, 1).toUpperCase();
    const avatarInner = e.logo_url
      ? '<img src="' + escapeHtml(e.logo_url) + '" alt="' + escapeHtml(e.nombre) + '" class="jdm-empresa-logo-img">'
      : escapeHtml(initial);

    let html =
      '<div class="jdm-empresa-header">' +
        '<div class="jdm-empresa-avatar">' + avatarInner + '</div>' +
        '<div>' +
          '<div class="jdm-empresa-name">' +
            escapeHtml(e.nombre) + ' ' + badgeHtml +
          '</div>' +
          '<div class="jdm-empresa-meta">@' + escapeHtml(e.username) + ' · ' + escapeHtml(e.sector) + ' (' + escapeHtml(e.ciudad) + ')</div>' +
        '</div>' +
      '</div>' +

      '<div class="jdm-empresa-stats-flat">' +
        '<div class="jdm-stat-flat">' +
          '<span class="jdm-stat-val">⭐ ' + e.reputacion + '</span>' +
          '<span class="jdm-stat-lbl">Reputación</span>' +
        '</div>' +
        '<div class="jdm-stat-flat-divider"></div>' +
        '<div class="jdm-stat-flat">' +
          '<span class="jdm-stat-val">' + e.total_resenas + '</span>' +
          '<span class="jdm-stat-lbl">Reseñas</span>' +
        '</div>' +
        '<div class="jdm-stat-flat-divider"></div>' +
        '<div class="jdm-stat-flat">' +
          '<span class="jdm-stat-val">' + e.proyectos_activos + '</span>' +
          '<span class="jdm-stat-lbl">Activos</span>' +
        '</div>' +
        '<div class="jdm-stat-flat-divider"></div>' +
        '<div class="jdm-stat-flat">' +
          '<span class="jdm-stat-val">' + e.proyectos_finalizados + '</span>' +
          '<span class="jdm-stat-lbl">Finalizados</span>' +
        '</div>' +
      '</div>' +

      '<div class="jdm-section-clean">' +
        '<div class="jdm-clean-label"><i data-lucide="building"></i> Acerca de la empresa</div>' +
        '<p class="jdm-clean-desc">' +
          escapeHtml(e.descripcion || 'Sin descripción corporativa registrada.') +
        '</p>' +
      '</div>' +

      '<div class="jdm-section-clean">' +
        '<div class="jdm-clean-label"><i data-lucide="message-circle"></i> Reseñas de desarrolladores (' + (e.total_resenas ?? (e.resenas ? e.resenas.length : 0)) + ')</div>';

    if (e.resenas && e.resenas.length) {
      html += '<div class="jdm-resenas-flat-list">';
      e.resenas.forEach(function (r) {
        html +=
          '<div class="jdm-resena-flat-item">' +
            '<div class="jdm-resena-header">' +
              '<strong class="jdm-resena-author">' + escapeHtml(r.desarrollador) + ' <span class="jdm-resena-project">en ' + escapeHtml(r.proyecto_titulo) + '</span></strong>' +
              '<span class="jdm-resena-rating">⭐ ' + r.puntuacion + '/5</span>' +
            '</div>' +
            '<p class="jdm-resena-comment">"' + escapeHtml(r.comentario) + '"</p>' +
            '<div class="jdm-resena-date">' + escapeHtml(r.fecha) + '</div>' +
          '</div>';
      });
      html += '</div>';
    } else {
      html += '<div class="jdm-empty" style="padding:16px 0;"><i data-lucide="message-square-off"></i>Aún no registra reseñas de proyectos finalizados.</div>';
    }

    html += '</div>';

    setContent(html);
    setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');

  } catch (err) {
    setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
    setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
  }
}

// ─────────────────────────────────────────────────────────────
// 5B. DETALLE PÚBLICO DE DESARROLLADOR (IN-SITU)
// ─────────────────────────────────────────────────────────────
export async function cargarDetalleDesarrollador(url) {
  abrirModal('');
  setHeader('TALENTO SENA // PERFIL PÚBLICO', 'Cargando perfil profesional…');

  try {
    const res = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      credentials: 'same-origin'
    });
    const data = await parseJsonResponse(res, 'No se pudo obtener el perfil del desarrollador.');
    if (!data.ok || !data.desarrollador) throw new Error(data.error || 'No se pudo obtener el perfil del desarrollador');

    const d = data.desarrollador;
    setHeader('TALENTO SENA // PERFIL PÚBLICO', d.nombre, d.programa_formacion + ' · Ficha ' + d.ficha);

    const badgeHtml = d.es_verificado_sena
      ? '<span class="jdm-badge jdm-badge-success"><i data-lucide="check-circle"></i> ' + escapeHtml(d.badge_label || 'Verificado SENA') + '</span>'
      : '<span class="jdm-badge jdm-badge-gray"><i data-lucide="id-card"></i> ' + escapeHtml(d.badge_label || 'Sin verificar') + '</span>';

    const initial = (d.nombre || 'D').slice(0, 1).toUpperCase();
    const avatarInner = d.foto_url
      ? '<img src="' + escapeHtml(d.foto_url) + '" alt="' + escapeHtml(d.nombre) + '" class="jdm-empresa-logo-img">'
      : escapeHtml(initial);

    let html =
      '<div class="jdm-empresa-header">' +
        '<div class="jdm-empresa-avatar">' + avatarInner + '</div>' +
        '<div>' +
          '<div class="jdm-empresa-name">' +
            escapeHtml(d.nombre) + ' ' + badgeHtml +
          '</div>' +
          '<div class="jdm-empresa-meta">@' + escapeHtml(d.username) + ' · ' + escapeHtml(d.condicion_sena) + ' SENA (' + escapeHtml(d.programa_formacion) + ')</div>' +
        '</div>' +
      '</div>' +

      '<div class="jdm-empresa-stats-flat">' +
        '<div class="jdm-stat-flat">' +
          '<span class="jdm-stat-val">⭐ ' + d.reputacion + '</span>' +
          '<span class="jdm-stat-lbl">Reputación</span>' +
        '</div>' +
        '<div class="jdm-stat-flat-divider"></div>' +
        '<div class="jdm-stat-flat">' +
          '<span class="jdm-stat-val">' + d.total_resenas + '</span>' +
          '<span class="jdm-stat-lbl">Reseñas</span>' +
        '</div>' +
        '<div class="jdm-stat-flat-divider"></div>' +
        '<div class="jdm-stat-flat">' +
          '<span class="jdm-stat-val">' + d.proyectos_activos + '</span>' +
          '<span class="jdm-stat-lbl">Activos</span>' +
        '</div>' +
        '<div class="jdm-stat-flat-divider"></div>' +
        '<div class="jdm-stat-flat">' +
          '<span class="jdm-stat-val">' + d.proyectos_finalizados + '</span>' +
          '<span class="jdm-stat-lbl">Finalizados</span>' +
        '</div>' +
      '</div>' +

      '<div class="jdm-section-clean">' +
        '<div class="jdm-clean-label"><i data-lucide="award"></i> Habilidades Técnicas</div>' +
        '<div style="display:flex;flex-wrap:wrap;gap:6px;">';
    if (d.habilidades && d.habilidades.length) {
      d.habilidades.forEach(function (hab) {
        html += '<span class="jdm-badge jdm-badge-gray" style="text-transform:none;font-size:11.5px;">' + escapeHtml(hab) + '</span>';
      });
    } else {
      html += '<span style="font-size:12.5px;color:var(--text-muted,#94a3b8);">Sin habilidades técnicas registradas.</span>';
    }
    html += '</div></div>';

    if (d.portafolio_url) {
      html += '<div class="jdm-section-clean">' +
        '<div class="jdm-clean-label"><i data-lucide="globe"></i> Portafolio / Repositorio</div>' +
        '<a href="' + escapeHtml(d.portafolio_url) + '" target="_blank" rel="noopener" class="jdm-advance-attachment">' +
          '<i data-lucide="external-link"></i> ' + escapeHtml(d.portafolio_url) +
        '</a>' +
      '</div>';
    }

    html += '<div class="jdm-section-clean">' +
      '<div class="jdm-clean-label"><i data-lucide="message-circle"></i> Valoraciones de Empresas (' + (d.total_resenas ?? (d.resenas ? d.resenas.length : 0)) + ')</div>';

    if (d.resenas && d.resenas.length) {
      html += '<div class="jdm-resenas-flat-list">';
      d.resenas.forEach(function (r) {
        html +=
          '<div class="jdm-resena-flat-item">' +
            '<div class="jdm-resena-header">' +
              '<strong class="jdm-resena-author">' + escapeHtml(r.empresa) + ' <span class="jdm-resena-project">en ' + escapeHtml(r.proyecto_titulo) + '</span></strong>' +
              '<span class="jdm-resena-rating">⭐ ' + r.puntuacion + '/5</span>' +
            '</div>' +
            '<p class="jdm-resena-comment">"' + escapeHtml(r.comentario) + '"</p>' +
            '<div class="jdm-resena-date">' + escapeHtml(r.fecha) + '</div>' +
          '</div>';
      });
      html += '</div>';
    } else {
      html += '<div class="jdm-empty" style="padding:16px 0;"><i data-lucide="message-square-off"></i>Aún no registra valoraciones de empresas contratantes.</div>';
    }

    html += '</div>';

    setContent(html);
    setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');

  } catch (err) {
    setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
    setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
  }
}
