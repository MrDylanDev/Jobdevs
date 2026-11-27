/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Gráfica Ledger (#historial)
 * y Tooltips Interactivos SVG (Línea, Hito, Dona)
 * ============================================================
 */

import { t, prefersReducedMotion } from './ui_utils.js';
import { animarTextoNumericoCorp } from './ui_animations.js';

let ledgerChartDatasets = {};
const ledgerEstadoActual = { metrica: 'contratado', periodo: '6m' };

function cargarDatasetsLedger() {
  const el = document.getElementById('empresa-ledger-datasets');
  if (!el) return {};
  try {
    return JSON.parse(el.textContent || '{}');
  } catch (e) {
    return {};
  }
}

export function formatearValorLedger(metrica, valor) {
  const num = Number(valor) || 0;
  if (metrica === 'hitos_qty') {
    const ent = Math.round(num);
    return ent + (ent === 1 ? t('hitoSingular', ' hito') : t('hitosPlural', ' hitos'));
  }
  const locale = (document.documentElement.lang || '').trim() || 'es-CO';
  return '$' + Math.round(num).toLocaleString(locale) + ' COP';
}

export function seleccionarMetricaLedger(metrica, btnEl) {
  ledgerEstadoActual.metrica = metrica;
  document.querySelectorAll('.ledger-filter-pill').forEach(function (btn) {
    btn.classList.remove('active');
  });
  if (btnEl) btnEl.classList.add('active');
  actualizarGraficaLedger(ledgerEstadoActual.metrica, ledgerEstadoActual.periodo);
}

export function seleccionarPeriodoLedger(periodo, btnEl) {
  ledgerEstadoActual.periodo = periodo;
  document.querySelectorAll('.ledger-chart-controls .time-tab-corp').forEach(function (btn) {
    btn.classList.remove('active');
  });
  if (btnEl) btnEl.classList.add('active');
  actualizarGraficaLedger(ledgerEstadoActual.metrica, ledgerEstadoActual.periodo);
}

export function actualizarGraficaLedger(metrica, periodo) {
  const dataset = ledgerChartDatasets && ledgerChartDatasets[metrica];
  if (!dataset) return;

  const keyPuntos = periodo === '12m' ? 'puntos_12m' : 'puntos_6m';
  const keyTotal = periodo === '12m' ? 'total_12m' : 'total_6m';
  const puntos = dataset[keyPuntos] || [];
  const totalPeriodo = dataset[keyTotal] || 0;

  const titleEl = document.getElementById('ledgerChartTitle');
  const subEl = document.getElementById('ledgerChartSub');
  const totalEl = document.getElementById('ledgerChartTotal');
  if (titleEl) titleEl.textContent = dataset.label || '';

  const subMap = {
    contratado: periodo === '12m'
      ? t('subContratado12m', 'Contratos digitales creados en los últimos 12 meses')
      : t('subContratado6m', 'Contratos digitales creados en los últimos 6 meses'),
    liquidado: periodo === '12m'
      ? t('subLiquidado12m', 'Liquidaciones devengadas por hitos en los últimos 12 meses')
      : t('subLiquidado6m', 'Liquidaciones devengadas por hitos en los últimos 6 meses'),
    hitos_qty: periodo === '12m'
      ? t('subHitos12m', 'Entregables técnicos aprobados en los últimos 12 meses')
      : t('subHitos6m', 'Entregables técnicos aprobados en los últimos 6 meses'),
  };
  if (subEl) subEl.textContent = subMap[metrica] || '';
  if (totalEl) {
    totalEl.textContent = t('totalPrefijo', 'Total: ') + formatearValorLedger(metrica, totalPeriodo);
    animarTextoNumericoCorp(totalEl);
  }

  const svgPoints = document.getElementById('ledgerChartPoints');
  const svgLabels = document.getElementById('ledgerChartLabels');
  const linePathEl = document.getElementById('ledgerLinePath');
  const areaPathEl = document.getElementById('ledgerAreaPath');
  if (!svgPoints || !svgLabels || !linePathEl || !areaPathEl || puntos.length === 0) return;

  const xStart = 50;
  const xEnd = 720;
  const yTop = 28;
  const yBottom = 150;
  const n = puntos.length;
  const maxVal = Math.max.apply(null, puntos.map(function (p) { return Number(p.valor) || 0; }).concat([0]));

  const coords = puntos.map(function (p, idx) {
    const x = n === 1 ? (xStart + xEnd) / 2 : xStart + (idx / (n - 1)) * (xEnd - xStart);
    const val = Number(p.valor) || 0;
    const y = maxVal > 0 ? yBottom - (val / maxVal) * (yBottom - yTop) : yBottom;
    return { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10, mes: p.mes, valor: val };
  });

  let dLine = 'M ' + coords[0].x + ',' + coords[0].y;
  for (let i = 1; i < coords.length; i++) {
    const prev = coords[i - 1];
    const curr = coords[i];
    const cx = Math.round(((prev.x + curr.x) / 2) * 10) / 10;
    dLine += ' C ' + cx + ',' + prev.y + ' ' + cx + ',' + curr.y + ' ' + curr.x + ',' + curr.y;
  }
  const last = coords[coords.length - 1];
  const first = coords[0];
  const dArea = dLine + ' L ' + last.x + ',' + yBottom + ' L ' + first.x + ',' + yBottom + ' Z';

  linePathEl.setAttribute('d', dLine);
  areaPathEl.setAttribute('d', dArea);

  const reduceMotion = prefersReducedMotion();
  if (!reduceMotion && typeof linePathEl.getTotalLength === 'function' && typeof linePathEl.animate === 'function') {
    try {
      const totalLen = linePathEl.getTotalLength();
      if (totalLen > 0) {
        linePathEl.style.strokeDasharray = totalLen + ' ' + totalLen;
        linePathEl.animate(
          [
            { strokeDashoffset: totalLen },
            { strokeDashoffset: 0 },
          ],
          { duration: 520, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'forwards' }
        );
      }
      areaPathEl.animate(
        [
          { opacity: 0, transform: 'translateY(6px)' },
          { opacity: 1, transform: 'translateY(0)' },
        ],
        { duration: 420, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'forwards' }
      );
    } catch (err) {}
  }

  const tooltipSubMap = {
    contratado: t('tooltipContratado', 'Presupuesto contratado'),
    liquidado: t('tooltipLiquidado', 'Liquidado por hitos aprobados'),
    hitos_qty: t('tooltipHitos', 'Hitos técnicos aprobados'),
  };
  const subTooltip = tooltipSubMap[metrica] || '';
  const hitWidth = n > 1 ? Math.max(28, Math.floor((xEnd - xStart) / n)) : 60;

  svgPoints.innerHTML = '';
  svgLabels.innerHTML = '';

  const ns = 'http://www.w3.org/2000/svg';
  coords.forEach(function (pt, idx) {
    const isLast = idx === coords.length - 1;
    const g = document.createElementNS(ns, 'g');
    g.setAttribute('class', 'chart-point-target');
    g.setAttribute('tabindex', '0');
    g.setAttribute('role', 'button');
    g.setAttribute('aria-label', pt.mes + ': ' + formatearValorLedger(metrica, pt.valor));
    g.setAttribute('data-mes', pt.mes);
    g.setAttribute('data-monto', formatearValorLedger(metrica, pt.valor));
    g.setAttribute('data-sub', subTooltip);
    g.addEventListener('mouseenter', function (evt) { mostrarTooltipLinea(evt, g); });
    g.addEventListener('mousemove', function (evt) { moverTooltipLinea(evt); });
    g.addEventListener('mouseleave', ocultarTooltipLinea);
    g.addEventListener('focus', function () {
      const box = g.getBoundingClientRect();
      mostrarTooltipLinea({ clientX: box.left + box.width / 2, clientY: box.top + 24 }, g);
    });
    g.addEventListener('blur', ocultarTooltipLinea);

    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('x', Math.round((pt.x - hitWidth / 2) * 10) / 10);
    rect.setAttribute('y', '0');
    rect.setAttribute('width', hitWidth);
    rect.setAttribute('height', '170');
    rect.setAttribute('fill', 'transparent');
    rect.style.cursor = 'pointer';

    const circle = document.createElementNS(ns, 'circle');
    circle.setAttribute('cx', pt.x);
    circle.setAttribute('cy', pt.y);
    circle.setAttribute('r', isLast ? '5.5' : '4');
    circle.setAttribute('class', 'chart-node-circle');
    circle.setAttribute('fill', 'var(--corp-brand)');
    if (isLast) {
      circle.setAttribute('stroke', 'var(--corp-surface)');
      circle.setAttribute('stroke-width', '2');
    }

    g.appendChild(rect);
    g.appendChild(circle);
    svgPoints.appendChild(g);

    if (!reduceMotion && typeof circle.animate === 'function') {
      circle.style.transformOrigin = pt.x + 'px ' + pt.y + 'px';
      circle.animate(
        [
          { opacity: 0, transform: 'scale(0.3)' },
          { opacity: 1, transform: 'scale(1)' },
        ],
        {
          duration: 300,
          delay: Math.min(idx * 35, 220),
          easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
          fill: 'backwards',
        }
      );
    }

    const txt = document.createElementNS(ns, 'text');
    txt.setAttribute('x', pt.x);
    txt.setAttribute('y', '170');
    txt.setAttribute('fill', 'var(--corp-slate-500)');
    txt.setAttribute('font-size', '12');
    txt.setAttribute('font-weight', '600');
    txt.setAttribute('text-anchor', 'middle');
    txt.textContent = pt.mes;
    svgLabels.appendChild(txt);
  });
}

// --- Tooltips SVG (Línea, Hito, Dona) ---

export function mostrarTooltipLinea(evt, el) {
  const tip = document.getElementById('ledgerLineTooltip');
  if (!tip) return;
  const mes = el.getAttribute('data-mes') || '';
  const monto = el.getAttribute('data-monto') || '';
  const sub = el.getAttribute('data-sub') || '';
  tip.querySelector('.tooltip-mes').textContent = mes;
  tip.querySelector('.tooltip-monto').textContent = monto;
  const subEl = tip.querySelector('.tooltip-sub');
  if (subEl && sub) subEl.textContent = sub;
  const wrap = el.closest('.ledger-svg-wrap');
  if (wrap) {
    const wrapRect = wrap.getBoundingClientRect();
    tip.style.left = (evt.clientX - wrapRect.left) + 'px';
    tip.style.top = (evt.clientY - wrapRect.top) + 'px';
    tip.style.display = 'block';
  }
}

export function moverTooltipLinea(evt) {
  const tip = document.getElementById('ledgerLineTooltip');
  if (!tip || tip.style.display === 'none') return;
  const wrap = tip.closest('.ledger-svg-wrap');
  if (wrap) {
    const wrapRect = wrap.getBoundingClientRect();
    tip.style.left = (evt.clientX - wrapRect.left) + 'px';
    tip.style.top = (evt.clientY - wrapRect.top) + 'px';
  }
}

export function ocultarTooltipLinea() {
  const tip = document.getElementById('ledgerLineTooltip');
  if (tip) tip.style.display = 'none';
}

export function mostrarTooltipHito(evt, el) {
  const tip = document.getElementById('roadmapHomeTooltip');
  if (!tip) return;
  const hito = el.getAttribute('data-hito') || '';
  const estado = el.getAttribute('data-estado') || '';
  const color = el.getAttribute('data-color') || 'var(--corp-brand)';
  tip.querySelector('.tooltip-hito').textContent = hito;
  const estEl = tip.querySelector('.tooltip-estado');
  if (estEl) {
    estEl.textContent = estado;
    estEl.style.color = color;
  }
  const wrap = el.closest('.roadmap-svg-box-corp');
  if (wrap) {
    const wrapRect = wrap.getBoundingClientRect();
    tip.style.left = (evt.clientX - wrapRect.left) + 'px';
    tip.style.top = (evt.clientY - wrapRect.top) + 'px';
    tip.style.display = 'block';
  }
}

export function moverTooltipHito(evt) {
  const tip = document.getElementById('roadmapHomeTooltip');
  if (!tip || tip.style.display === 'none') return;
  const wrap = tip.closest('.roadmap-svg-box-corp');
  if (wrap) {
    const wrapRect = wrap.getBoundingClientRect();
    tip.style.left = (evt.clientX - wrapRect.left) + 'px';
    tip.style.top = (evt.clientY - wrapRect.top) + 'px';
  }
}

export function ocultarTooltipHito() {
  const tip = document.getElementById('roadmapHomeTooltip');
  if (tip) tip.style.display = 'none';
}

export function mostrarTooltipDona(evt, el) {
  const tip = document.getElementById('donutHomeTooltip');
  if (!tip) return;
  const label = el.getAttribute('data-label') || '';
  const val = el.getAttribute('data-val') || '';
  const pct = el.getAttribute('data-pct') || '';
  const color = el.getAttribute('data-color') || 'var(--corp-brand)';
  const lblEl = tip.querySelector('.tooltip-label');
  if (lblEl) lblEl.textContent = label;
  const valEl = tip.querySelector('.tooltip-val');
  if (valEl) valEl.textContent = val;
  const pctEl = tip.querySelector('.tooltip-pct');
  if (pctEl) {
    pctEl.textContent = pct;
    pctEl.style.color = color;
  }
  const wrap = el.closest('.donut-chart-wrapper');
  if (wrap) {
    const wrapRect = wrap.getBoundingClientRect();
    tip.style.left = (evt.clientX - wrapRect.left) + 'px';
    tip.style.top = (evt.clientY - wrapRect.top) + 'px';
    tip.style.display = 'block';
  }
}

export function moverTooltipDona(evt) {
  const tip = document.getElementById('donutHomeTooltip');
  if (!tip || tip.style.display === 'none') return;
  const wrap = tip.closest('.donut-chart-wrapper');
  if (wrap) {
    const wrapRect = wrap.getBoundingClientRect();
    tip.style.left = (evt.clientX - wrapRect.left) + 'px';
    tip.style.top = (evt.clientY - wrapRect.top) + 'px';
  }
}

export function ocultarTooltipDona() {
  const tip = document.getElementById('donutHomeTooltip');
  if (tip) tip.style.display = 'none';
}

// --- Global Window Contracts ---

window.formatearValorLedger = formatearValorLedger;
window.seleccionarMetricaLedger = seleccionarMetricaLedger;
window.seleccionarPeriodoLedger = seleccionarPeriodoLedger;
window.actualizarGraficaLedger = actualizarGraficaLedger;
window.mostrarTooltipLinea = mostrarTooltipLinea;
window.moverTooltipLinea = moverTooltipLinea;
window.ocultarTooltipLinea = ocultarTooltipLinea;
window.mostrarTooltipHito = mostrarTooltipHito;
window.moverTooltipHito = moverTooltipHito;
window.ocultarTooltipHito = ocultarTooltipHito;
window.mostrarTooltipDona = mostrarTooltipDona;
window.moverTooltipDona = moverTooltipDona;
window.ocultarTooltipDona = ocultarTooltipDona;

// --- DOM Initialization ---

export function initLedgerChart() {
  ledgerChartDatasets = cargarDatasetsLedger();
  actualizarGraficaLedger(ledgerEstadoActual.metrica, ledgerEstadoActual.periodo);
}
