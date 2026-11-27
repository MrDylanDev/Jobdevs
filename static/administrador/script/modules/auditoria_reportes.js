/**
 * ============================================================
 * JobDevs - Panel Administrador: Auditoría (Logs & Chats),
 * Gráficas Estadísticas (Donut & Líneas) y Reportes
 * ============================================================
 */

import { adminNotify, registerSectionHook } from './ui_core.js';

// --- Dashboard Bento Analytics Charts ---

function initAdminStatsCharts() {
  const grid = document.getElementById('adminChartsGrid');
  if (!grid) return;
  const n = (attr) => parseInt(grid.getAttribute(attr) || '0', 10) || 0;

  // 1. Donut de usuarios (paleta sobria monocromática)
  const userItems = [
    { label: 'Empresas', value: n('data-empresas'), color: '#ededed' },
    { label: 'Desarrolladores', value: n('data-devs'), color: '#94a3b8' },
    { label: 'Inactivos', value: n('data-inactivos'), color: '#52525b' },
    { label: 'Suspendidos', value: n('data-suspendidos'), color: '#27272a' },
  ];
  const segGroup = document.getElementById('adminUsersDonutSegments');
  const legend = document.getElementById('adminUsersLegend');
  const total = userItems.reduce((acc, item) => acc + item.value, 0);
  const r = 66;
  const circ = 2 * Math.PI * r;
  let offset = 0;

  if (segGroup && legend) {
    segGroup.innerHTML = '';
    legend.innerHTML = '';
    userItems.forEach((item) => {
      const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
      if (total > 0 && item.value > 0) {
        const dash = (item.value / total) * circ;
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', '90');
        circle.setAttribute('cy', '90');
        circle.setAttribute('r', String(r));
        circle.setAttribute('fill', 'none');
        circle.setAttribute('stroke', item.color);
        circle.setAttribute('stroke-width', '16');
        circle.setAttribute('stroke-dasharray', dash + ' ' + (circ - dash));
        circle.setAttribute('stroke-dashoffset', String(-offset));
        segGroup.appendChild(circle);
        offset += dash;
      }
      const li = document.createElement('li');
      li.className = 'admin-legend-item';
      li.innerHTML =
        '<span class="admin-legend-dot" style="background:' + item.color + ';"></span>' +
        '<span class="admin-legend-name">' + item.label + '</span>' +
        '<span class="admin-legend-val">' + item.value + ' <small>(' + pct + '%)</small></span>';
      legend.appendChild(li);
    });
  }

  // 2. Gráfica de líneas interactiva (Proyectos / Tendencia 6 meses)
  let tendenciaData = [];
  try {
    const tEl = document.getElementById('adminTendenciaData');
    if (tEl && tEl.textContent) tendenciaData = JSON.parse(tEl.textContent);
  } catch (e) {}

  const proyectoItems = [
    { label: 'Disponibles', value: n('data-p-pub'), color: '#ededed' },
    { label: 'En Desarrollo', value: n('data-p-des'), color: '#ededed' },
    { label: 'Finalizados', value: n('data-p-fin'), color: '#00e676' },
    { label: 'En Retraso', value: n('data-p-ret'), color: '#94a3b8' },
    { label: 'Postulaciones', value: n('data-post-pen'), color: '#ededed' },
  ];

  function drawAdminLineChart(cat) {
    const svg = document.getElementById('adminLineChartSvg');
    const titleEl = document.getElementById('adminLineChartTitle');
    const tooltip = document.getElementById('adminLineTooltip');
    if (!svg) return;
    if (tooltip) tooltip.hidden = true;

    const baseY = 165;
    const topY = 28;
    const spanY = baseY - topY;

    if (cat === 'tendencia' && tendenciaData.length > 0) {
      if (titleEl) titleEl.textContent = 'Tendencia Mensual (Últimos 6 meses)';
      const count = tendenciaData.length;
      const maxVal = Math.max(
        ...tendenciaData.reduce((acc, d) => {
          acc.push(d.proyectos || 0, d.usuarios || 0);
          return acc;
        }, [3])
      );
      const topVal = Math.ceil(maxVal / 3) * 3;
      const xs = tendenciaData.map((_, i) =>
        Math.round(58 + (i * (554 - 58)) / Math.max(count - 1, 1))
      );
      const ptsU = tendenciaData.map((d, i) => ({
        x: xs[i],
        y: Math.round((baseY - ((d.usuarios || 0) / topVal) * spanY) * 10) / 10,
        label: d.label,
        val: d.usuarios || 0,
        series: 'Usuarios',
        color: '#94a3b8',
      }));
      const ptsP = tendenciaData.map((d, i) => ({
        x: xs[i],
        y: Math.round((baseY - ((d.proyectos || 0) / topVal) * spanY) * 10) / 10,
        label: d.label,
        val: d.proyectos || 0,
        series: 'Proyectos',
        color: '#00e676',
      }));

      let html =
        '<defs><linearGradient id="adminAreaGrad_tP" x1="0" y1="0" x2="0" y2="1">' +
        '<stop offset="0%" stop-color="#00e676" stop-opacity="0.22"/><stop offset="100%" stop-color="#00e676" stop-opacity="0"/></linearGradient></defs>';

      [0, 1, 2, 3].forEach((k) => {
        const gy = baseY - (k / 3) * spanY;
        const val = Math.round((k / 3) * topVal);
        html +=
          '<line x1="38" y1="' + gy + '" x2="578" y2="' + gy +
          '" stroke="rgba(255,255,255,' + (k === 0 ? '0.14' : '0.07') + ')" ' +
          (k === 0 ? '' : 'stroke-dasharray="3 3"') + '/>';
        html +=
          '<text x="30" y="' + (gy + 4) +
          '" text-anchor="end" fill="#94a3b8" font-size="10" font-family="ui-monospace, monospace">' +
          val + '</text>';
      });

      const areaP =
        'M ' + ptsP[0].x + ' ' + ptsP[0].y + ' ' +
        ptsP.slice(1).map((p) => 'L ' + p.x + ' ' + p.y).join(' ') +
        ' L ' + ptsP[ptsP.length - 1].x + ' ' + baseY +
        ' L ' + ptsP[0].x + ' ' + baseY + ' Z';
      html += '<path d="' + areaP + '" fill="url(#adminAreaGrad_tP)"/>';
      html +=
        '<polyline class="admin-line-path" fill="none" stroke="#94a3b8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" points="' +
        ptsU.map((p) => p.x + ',' + p.y).join(' ') + '"/>';
      html +=
        '<polyline class="admin-line-path" fill="none" stroke="#00e676" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" points="' +
        ptsP.map((p) => p.x + ',' + p.y).join(' ') + '"/>';

      const allPts = ptsU.concat(ptsP);
      allPts.forEach((p, idx) => {
        html +=
          '<circle class="admin-line-dot" data-idx="' + idx + '" cx="' + p.x + '" cy="' + p.y +
          '" r="4.5" fill="#0a0a0a" stroke="' + p.color + '" stroke-width="2.4"/>';
      });
      tendenciaData.forEach((d, i) => {
        html +=
          '<text x="' + xs[i] + '" y="188" text-anchor="middle" fill="#94a3b8" font-size="11">' +
          d.label + '</text>';
      });
      html += '<circle cx="430" cy="12" r="4" fill="#00e676"/><text x="439" y="16" fill="#94a3b8" font-size="10.5">Proyectos</text>';
      html += '<circle cx="508" cy="12" r="4" fill="#94a3b8"/><text x="517" y="16" fill="#94a3b8" font-size="10.5">Usuarios</text>';

      svg.innerHTML = html;
      if (tooltip) {
        svg.querySelectorAll('.admin-line-dot').forEach((dot) => {
          dot.addEventListener('mouseenter', () => {
            const p = allPts[parseInt(dot.getAttribute('data-idx'), 10)];
            if (!p) return;
            tooltip.textContent = p.label + ' · ' + p.series + ': ' + p.val;
            tooltip.style.left = (p.x / 600) * 100 + '%';
            tooltip.style.top = (p.y / 205) * 100 + '%';
            tooltip.hidden = false;
          });
          dot.addEventListener('mouseleave', () => {
            tooltip.hidden = true;
          });
        });
      }
      return;
    }

    if (titleEl) titleEl.textContent = 'Pipeline de Proyectos';
    const items = proyectoItems;
    const maxVal = Math.max(...items.map((i) => i.value), 4);
    const topVal = Math.ceil(maxVal / 3) * 3;
    const xs = [64, 186, 308, 430, 552];
    const pts = items.map((it, idx) => {
      const y = baseY - (it.value / topVal) * spanY;
      return { x: xs[idx], y: Math.round(y * 10) / 10, item: it };
    });

    const poly = pts.map((p) => p.x + ',' + p.y).join(' ');
    const area =
      'M ' + pts[0].x + ' ' + pts[0].y + ' ' +
      pts.slice(1).map((p) => 'L ' + p.x + ' ' + p.y).join(' ') +
      ' L ' + pts[pts.length - 1].x + ' ' + baseY +
      ' L ' + pts[0].x + ' ' + baseY + ' Z';

    let html =
      '<defs><linearGradient id="adminAreaGrad_proyectos" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="#00e676" stop-opacity="0.28"/>' +
      '<stop offset="100%" stop-color="#00e676" stop-opacity="0"/>' +
      '</linearGradient></defs>';

    [0, 1, 2, 3].forEach((k) => {
      const gy = baseY - (k / 3) * spanY;
      const val = Math.round((k / 3) * topVal);
      html +=
        '<line x1="38" y1="' + gy + '" x2="578" y2="' + gy +
        '" stroke="rgba(255,255,255,' + (k === 0 ? '0.14' : '0.07') + ')" ' +
        (k === 0 ? '' : 'stroke-dasharray="3 3"') + '/>';
      html +=
        '<text x="30" y="' + (gy + 4) +
        '" text-anchor="end" fill="#94a3b8" font-size="10" font-family="ui-monospace, monospace">' +
        val + '</text>';
    });

    html += '<path d="' + area + '" fill="url(#adminAreaGrad_proyectos)"/>';
    html +=
      '<polyline class="admin-line-path" fill="none" stroke="#00e676" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" points="' +
      poly + '"/>';

    pts.forEach((p, idx) => {
      html +=
        '<circle class="admin-line-dot" data-idx="' + idx + '" cx="' + p.x + '" cy="' + p.y +
        '" r="4.8" fill="#0a0a0a" stroke="' + p.item.color + '" stroke-width="2.5"/>';
      html +=
        '<text x="' + p.x + '" y="' + (p.y - 11) +
        '" text-anchor="middle" fill="#ededed" font-size="11" font-weight="700" font-family="ui-monospace, monospace">' +
        p.item.value + '</text>';
      html +=
        '<text x="' + p.x + '" y="188" text-anchor="middle" fill="#94a3b8" font-size="11">' +
        p.item.label + '</text>';
    });

    svg.innerHTML = html;

    if (tooltip) {
      svg.querySelectorAll('.admin-line-dot').forEach((dot) => {
        dot.addEventListener('mouseenter', () => {
          const p = pts[parseInt(dot.getAttribute('data-idx'), 10)];
          if (!p) return;
          tooltip.textContent = p.item.label + ': ' + p.item.value;
          tooltip.style.left = (p.x / 600) * 100 + '%';
          tooltip.style.top = (p.y / 205) * 100 + '%';
          tooltip.hidden = false;
        });
        dot.addEventListener('mouseleave', () => {
          tooltip.hidden = true;
        });
      });
    }
  }

  window.switchAdminLineChart = function (cat, btn) {
    document.querySelectorAll('.chart-cat-btn').forEach((b) => {
      b.classList.remove('is-active');
      b.setAttribute('aria-selected', 'false');
    });
    if (btn) {
      btn.classList.add('is-active');
      btn.setAttribute('aria-selected', 'true');
    }
    drawAdminLineChart(cat);
  };

  drawAdminLineChart('proyectos');
}

// --- Audit Chats (HTMX Detail Modal & Privacy Notice) ---

function initAuditChats() {
  const form = document.getElementById('auditChatsForm');
  const body = document.getElementById('auditChatsBody');
  const pager = document.getElementById('auditChatsPager');
  if (!form || !body) return;

  body.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-audit-chat-detail]');
    if (!btn) return;
    const d = btn.dataset;
    document.getElementById('auditChatModalTitle').textContent =
      d.chatTitulo || 'Mensaje #' + (d.chatId || '');
    document.getElementById('auditChatModalMeta').textContent =
      (d.chatFecha || '') +
      ' · De ' + (d.chatRemitente || '') +
      ' → ' + (d.chatDestinatario || '') +
      (d.chatProyecto ? ' · Proyecto: ' + d.chatProyecto : '');
    document.getElementById('auditChatModalBody').textContent = d.chatContenido || '';
    document.getElementById('auditChatModal').classList.add('open');
  });

  [form, pager].filter(Boolean).forEach((el) => {
    el.addEventListener('htmx:responseError', () => {
      adminNotify('No se pudo completar la auditoría.');
    });
    el.addEventListener('htmx:sendError', () => {
      adminNotify('Error de red.');
    });
  });

  // Open privacy notice modal whenever admin navigates to auditChatsSection
  registerSectionHook((sectionId) => {
    if (sectionId === 'auditChatsSection') {
      const noticeModal = document.getElementById('auditChatsNoticeModal');
      if (noticeModal) noticeModal.classList.add('open');
    }
  });
}

// --- Audit Logs (HTMX Detail Modal & Reset) ---

function initAuditLogs() {
  const form = document.getElementById('auditLogsForm');
  const body = document.getElementById('auditLogsBody');
  const pager = document.getElementById('auditLogsPager');
  const resetBtn = document.getElementById('auditResetBtn');
  if (!form || !body) return;

  body.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-audit-log-detail]');
    if (!btn) return;
    const d = btn.dataset;
    document.getElementById('auditLogModalTitle').textContent =
      'Registro de Auditoría #' + (d.logId || '');
    document.getElementById('auditLogModalMeta').textContent =
      (d.logFecha || '—') +
      ' · Usuario: ' + (d.logUsuario || 'Sistema') +
      ' · Tabla: ' + (d.logTabla || '—') +
      (d.logRegistro ? ' · Registro ID: #' + d.logRegistro : '');
    document.getElementById('auditLogModalAction').textContent = d.logAccion || '—';
    document.getElementById('auditLogModalPrev').textContent = d.logPrev || '—';
    document.getElementById('auditLogModalNext').textContent = d.logNext || '—';
    document.getElementById('auditLogDetailModal').classList.add('open');
  });

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      form.reset();
      if (window.htmx && typeof window.htmx.trigger === 'function') {
        window.htmx.trigger(form, 'submit');
      }
    });
  }

  [form, pager].filter(Boolean).forEach((el) => {
    el.addEventListener('htmx:responseError', () => {
      adminNotify('No se pudo cargar el registro de auditoría.');
    });
    el.addEventListener('htmx:sendError', () => {
      adminNotify('Error de red al cargar auditoría.');
    });
  });
}

// --- Module Initializer ---

export function initAuditoriaReportes() {
  initAdminStatsCharts();
  initAuditChats();
  initAuditLogs();
}
