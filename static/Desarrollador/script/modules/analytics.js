/**
 * Módulo Analytics — Dashboard Desarrollador
 * Gráfica de actividad Cockpit Dev (Vanilla SVG).
 */

import { animarContadorKpi } from './ui_core.js';

const devChartState = {
  metric: 'hitos',
  data: null,
  prevCoords: null,
  rafId: null,
};

const SVG_W = 680;
const PAD_L = 36;
const PAD_R = 20;
const PAD_T = 20;
const PAD_B = 30;
const PLOT_H = 200 - PAD_T - PAD_B;

function buildSmoothPath(pts) {
  if (!pts.length) return '';
  if (pts.length === 1) return 'M ' + pts[0].x.toFixed(2) + ' ' + pts[0].y.toFixed(2);
  let d = 'M ' + pts[0].x.toFixed(2) + ' ' + pts[0].y.toFixed(2);
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i === 0 ? i : i - 1];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2 < pts.length ? i + 2 : i + 1];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    let cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    let cp2y = p2.y - (p3.y - p1.y) / 6;
    const minY = Math.min(p1.y, p2.y);
    const maxY = Math.max(p1.y, p2.y);
    cp1y = Math.max(PAD_T, Math.min(PAD_T + PLOT_H, Math.max(minY - 8, Math.min(maxY + 8, cp1y))));
    cp2y = Math.max(PAD_T, Math.min(PAD_T + PLOT_H, Math.max(minY - 8, Math.min(maxY + 8, cp2y))));
    d += ' C ' + cp1x.toFixed(2) + ' ' + cp1y.toFixed(2) + ', ' + cp2x.toFixed(2) + ' ' + cp2y.toFixed(2) + ', ' + p2.x.toFixed(2) + ' ' + p2.y.toFixed(2);
  }
  return d;
}

function buildAreaPath(pts, lineD) {
  if (!pts.length || !lineD) return '';
  const baseY = (PAD_T + PLOT_H).toFixed(2);
  return lineD + ' L ' + pts[pts.length - 1].x.toFixed(2) + ' ' + baseY + ' L ' + pts[0].x.toFixed(2) + ' ' + baseY + ' Z';
}

function computeCoords(puntos, metric) {
  let maxVal = 1;
  for (let i = 0; i < puntos.length; i++) {
    const v = puntos[i][metric] || 0;
    if (v > maxVal) maxVal = v;
  }
  const niceMax = metric === 'calificacion' ? 5 : (maxVal <= 2 ? 3 : Math.ceil(maxVal * 1.25));
  const plotW = SVG_W - PAD_L - PAD_R;
  const n = puntos.length;
  const coords = [];
  for (let j = 0; j < n; j++) {
    const val = puntos[j][metric] || 0;
    const x = n === 1 ? PAD_L + plotW / 2 : PAD_L + (j / (n - 1)) * plotW;
    const y = PAD_T + PLOT_H - (val / niceMax) * PLOT_H;
    coords.push({ x: x, y: y, valor: val, etiqueta: puntos[j].etiqueta, fecha: puntos[j].fecha });
  }
  return { coords: coords, niceMax: niceMax };
}

function showTooltip(evt, pt, label) {
  const tip = document.getElementById('devChartTooltip');
  const wrap = tip ? tip.parentElement : null;
  if (!tip || !wrap) return;
  document.getElementById('tipPeriodo').textContent = pt.fecha || pt.etiqueta;

  const numEl = document.getElementById('tipMonto');
  const descEl = document.getElementById('tipDesc');
  if (devChartState.metric === 'calificacion') {
    if (pt.valor > 0) {
      numEl.textContent = Number(pt.valor).toFixed(1);
      descEl.textContent = '★ de calificación promedio';
    } else {
      numEl.textContent = '0.0';
      descEl.textContent = 'sin valoraciones en el mes';
    }
  } else {
    numEl.textContent = String(pt.valor);
    descEl.textContent = label;
  }

  tip.style.display = 'block';
  const rect = wrap.getBoundingClientRect();
  let left = (evt.clientX - rect.left);
  let top = (evt.clientY - rect.top) - 10;
  if (left + 140 > rect.width) left = Math.max(8, left - 150);
  if (top < 30) top = 30;
  tip.style.left = left + 'px';
  tip.style.top = top + 'px';
}

function hideTooltip() {
  const tip = document.getElementById('devChartTooltip');
  if (tip) tip.style.display = 'none';
}

function renderChart(mode) {
  if (!devChartState.data || !devChartState.data.length) return;
  const metric = devChartState.metric;
  const computed = computeCoords(devChartState.data, metric);
  const niceMax = computed.niceMax;
  const coords = computed.coords;

  const gridG = document.getElementById('devChartGrid');
  const yG = document.getElementById('devChartYAxis');
  const xG = document.getElementById('devChartXAxis');
  const dotsG = document.getElementById('devChartDots');
  const linePath = document.getElementById('devChartLinePath');
  const areaPath = document.getElementById('devChartAreaPath');

  if (!linePath || !areaPath || !gridG) return;

  const ns = 'http://www.w3.org/2000/svg';
  gridG.innerHTML = '';
  yG.innerHTML = '';
  xG.innerHTML = '';
  dotsG.innerHTML = '';

  // Eje Y y líneas horizontales
  const ticks = [0, Math.round(niceMax / 2), niceMax];
  for (let t = 0; t < ticks.length; t++) {
    const val = ticks[t];
    const y = PAD_T + PLOT_H - (val / niceMax) * PLOT_H;
    const line = document.createElementNS(ns, 'line');
    line.setAttribute('x1', PAD_L);
    line.setAttribute('x2', SVG_W - PAD_R);
    line.setAttribute('y1', y.toFixed(1));
    line.setAttribute('y2', y.toFixed(1));
    line.setAttribute('class', 'chart-grid-line');
    gridG.appendChild(line);

    const txt = document.createElementNS(ns, 'text');
    txt.setAttribute('x', PAD_L - 8);
    txt.setAttribute('y', (y + 4).toFixed(1));
    txt.setAttribute('text-anchor', 'end');
    txt.setAttribute('class', 'chart-axis-label');
    txt.textContent = String(val);
    yG.appendChild(txt);
  }

  // Eje X
  for (let i = 0; i < coords.length; i++) {
    const xTxt = document.createElementNS(ns, 'text');
    xTxt.setAttribute('x', coords[i].x.toFixed(1));
    xTxt.setAttribute('y', '195');
    xTxt.setAttribute('text-anchor', i === 0 ? 'start' : (i === coords.length - 1 ? 'end' : 'middle'));
    xTxt.setAttribute('class', 'chart-axis-label');
    xTxt.textContent = coords[i].etiqueta;
    xG.appendChild(xTxt);
  }

  // Trazos de curva y área
  const d = buildSmoothPath(coords);
  const isGold = metric === 'calificacion';
  linePath.setAttribute('stroke', isGold ? '#f59e0b' : '#00e676');
  linePath.setAttribute('filter', isGold ? 'url(#goldGlow)' : 'url(#neonGlow)');
  areaPath.setAttribute('fill', isGold ? 'url(#goldAreaGradient)' : 'url(#neonAreaGradient)');
  linePath.setAttribute('d', d);
  areaPath.setAttribute('d', buildAreaPath(coords, d));

  if (mode === 'draw' && typeof linePath.getTotalLength === 'function') {
    const len = linePath.getTotalLength();
    linePath.style.transition = 'none';
    linePath.style.strokeDasharray = len;
    linePath.style.strokeDashoffset = len;
    linePath.getBoundingClientRect();
    linePath.style.transition = 'stroke-dashoffset 550ms cubic-bezier(0.16, 1, 0.3, 1)';
    linePath.style.strokeDashoffset = '0';
  }

  // Puntos interactivos
  const labelText = metric === 'calificacion' ? '★ de calificación promedio' : (metric === 'hitos' ? 'hitos entregados' : 'postulaciones');
  coords.forEach(function (pt) {
    const c = document.createElementNS(ns, 'circle');
    c.setAttribute('cx', pt.x.toFixed(2));
    c.setAttribute('cy', pt.y.toFixed(2));
    c.setAttribute('r', pt.valor > 0 ? '4.5' : '3');
    c.setAttribute('class', 'chart-data-dot');
    c.setAttribute('stroke', isGold ? '#f59e0b' : '#00e676');
    c.setAttribute('tabindex', '0');
    c.addEventListener('mouseenter', function (e) { showTooltip(e, pt, labelText); });
    c.addEventListener('mousemove', function (e) { showTooltip(e, pt, labelText); });
    c.addEventListener('mouseleave', hideTooltip);
    dotsG.appendChild(c);
  });

  devChartState.prevCoords = coords;
}

export function cambiarMetricaGrafica(metric, btn) {
  devChartState.metric = metric;
  document.querySelectorAll('.cockpit-chart-tab').forEach(function (b) { b.classList.remove('active'); });
  if (btn) btn.classList.add('active');

  const title = document.getElementById('devChartTitle');
  const kpiVal = document.getElementById('devChartKpiVal');
  const kpiLabel = document.getElementById('devChartKpiLabel');
  const rawData = devChartState.data || [];

  if (metric === 'hitos') {
    if (title) title.textContent = 'Evolución de Entregas y Cumplimiento';
    const sumH = rawData.reduce(function (acc, p) { return acc + (p.hitos || 0); }, 0);
    if (kpiVal) {
      kpiVal.removeAttribute('data-target-val');
      kpiVal.textContent = String(sumH);
      animarContadorKpi(kpiVal);
    }
    if (kpiLabel) kpiLabel.textContent = 'Hitos Completados (6m)';
  } else if (metric === 'postulaciones') {
    if (title) title.textContent = 'Ritmo de Postulaciones Enviadas';
    const sumP = rawData.reduce(function (acc, p) { return acc + (p.postulaciones || 0); }, 0);
    if (kpiVal) {
      kpiVal.removeAttribute('data-target-val');
      kpiVal.textContent = String(sumP);
      animarContadorKpi(kpiVal);
    }
    if (kpiLabel) kpiLabel.textContent = 'Postulaciones Totales (6m)';
  } else if (metric === 'calificacion') {
    if (title) title.textContent = 'Evolución de Calificación y Reputación';
    const vals = rawData.map(function (p) { return p.calificacion || 0; }).filter(function (v) { return v > 0; });
    const avg = vals.length ? (vals.reduce(function (a, b) { return a + b; }, 0) / vals.length).toFixed(1) : '5.0';
    if (kpiVal) {
      kpiVal.removeAttribute('data-target-val');
      kpiVal.textContent = avg;
      animarContadorKpi(kpiVal);
    }
    if (kpiLabel) kpiLabel.textContent = 'Promedio Empresas';
  }

  renderChart('draw');
}

export function initDevActivityChart() {
  const dataEl = document.getElementById('devChartDataScript');
  if (!dataEl) return;
  try {
    devChartState.data = JSON.parse(dataEl.textContent);
  } catch (e) {
    devChartState.data = [];
  }
  renderChart('draw');
}

// Exponer en window para manejadores inline HTML y scripts hermanos
window.cambiarMetricaGrafica = cambiarMetricaGrafica;
window.initDevActivityChart = initDevActivityChart;

export function initAnalytics() {
  initDevActivityChart();
}
