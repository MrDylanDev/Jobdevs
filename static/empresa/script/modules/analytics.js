/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Gráfica Lineal en Vivo (#inicio)
 * (Datos Reales + Morph SVG)
 * ============================================================
 */

const state = {
  data: null,
  metric: 'avances',
  period: '14d',
  prevCoords: null,
  lastSignature: '',
  rafId: null,
  pollTimer: null,
};

const SVG_W = 680;
const PAD_L = 34;
const PAD_R = 16;
const PAD_T = 18;
const PAD_B = 28;
const PLOT_H = 210 - PAD_T - PAD_B;

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
    cp1y = Math.max(PAD_T, Math.min(PAD_T + PLOT_H, Math.max(minY - 6, Math.min(maxY + 6, cp1y))));
    cp2y = Math.max(PAD_T, Math.min(PAD_T + PLOT_H, Math.max(minY - 6, Math.min(maxY + 6, cp2y))));
    d += ' C ' + cp1x.toFixed(2) + ' ' + cp1y.toFixed(2) + ', ' + cp2x.toFixed(2) + ' ' + cp2y.toFixed(2) + ', ' + p2.x.toFixed(2) + ' ' + p2.y.toFixed(2);
  }
  return d;
}

function buildAreaPath(pts, lineD) {
  if (!pts.length || !lineD) return '';
  const baseY = (PAD_T + PLOT_H).toFixed(2);
  return lineD + ' L ' + pts[pts.length - 1].x.toFixed(2) + ' ' + baseY + ' L ' + pts[0].x.toFixed(2) + ' ' + baseY + ' Z';
}

function computeCoords(puntos) {
  let maxVal = 1;
  for (let i = 0; i < puntos.length; i++) {
    if (puntos[i].valor > maxVal) maxVal = puntos[i].valor;
  }
  const niceMax = maxVal <= 2 ? 2 : Math.ceil(maxVal * 1.2);
  const plotW = SVG_W - PAD_L - PAD_R;
  const n = puntos.length;
  const coords = [];
  for (let j = 0; j < n; j++) {
    const x = n === 1 ? PAD_L + plotW / 2 : PAD_L + (j / (n - 1)) * plotW;
    const y = PAD_T + PLOT_H - (puntos[j].valor / niceMax) * PLOT_H;
    coords.push({ x: x, y: y, valor: puntos[j].valor, etiqueta: puntos[j].etiqueta, fecha: puntos[j].fecha });
  }
  return { coords: coords, niceMax: niceMax };
}

function showTooltip(evt, pt, label) {
  const tip = document.getElementById('inicioLineTooltip');
  const wrap = tip ? tip.parentElement : null;
  if (!tip || !wrap) return;
  tip.querySelector('.tooltip-mes').textContent = pt.etiqueta;
  tip.querySelector('.tooltip-monto').textContent = String(pt.valor);
  tip.querySelector('.tooltip-sub').textContent = label;
  tip.style.display = 'block';
  const rect = wrap.getBoundingClientRect();
  let left = (evt.clientX - rect.left) + 12;
  let top = (evt.clientY - rect.top) - 56;
  if (left + 150 > rect.width) left = Math.max(8, left - 165);
  if (top < 0) top = 8;
  tip.style.left = left + 'px';
  tip.style.top = top + 'px';
}

function hideTooltip() {
  const tip = document.getElementById('inicioLineTooltip');
  if (tip) tip.style.display = 'none';
}

function renderAxes(niceMax, coords) {
  const gridG = document.getElementById('inicioGridGroup');
  const yG = document.getElementById('inicioYAxisGroup');
  const xG = document.getElementById('inicioXAxisGroup');
  if (!gridG || !yG || !xG) return;

  const ns = 'http://www.w3.org/2000/svg';
  gridG.innerHTML = '';
  yG.innerHTML = '';
  xG.innerHTML = '';

  const ticks = [0, Math.round(niceMax / 2), niceMax];
  for (let idx = 0; idx < ticks.length; idx++) {
    const val = ticks[idx];
    const y = PAD_T + PLOT_H - (val / niceMax) * PLOT_H;
    const line = document.createElementNS(ns, 'line');
    line.setAttribute('x1', PAD_L);
    line.setAttribute('x2', SVG_W - PAD_R);
    line.setAttribute('y1', y.toFixed(1));
    line.setAttribute('y2', y.toFixed(1));
    line.setAttribute('class', 'inicio-grid-line');
    gridG.appendChild(line);

    const txt = document.createElementNS(ns, 'text');
    txt.setAttribute('x', PAD_L - 8);
    txt.setAttribute('y', (y + 4).toFixed(1));
    txt.setAttribute('text-anchor', 'end');
    txt.setAttribute('class', 'inicio-axis-label');
    txt.textContent = String(val);
    yG.appendChild(txt);
  }

  const step = coords.length > 16 ? 5 : 2;
  for (let i = 0; i < coords.length; i++) {
    if (i !== 0 && i !== coords.length - 1 && i % step !== 0) continue;
    const xTxt = document.createElementNS(ns, 'text');
    xTxt.setAttribute('x', coords[i].x.toFixed(1));
    xTxt.setAttribute('y', '203');
    xTxt.setAttribute('text-anchor', i === 0 ? 'start' : (i === coords.length - 1 ? 'end' : 'middle'));
    xTxt.setAttribute('class', 'inicio-axis-label');
    xTxt.textContent = coords[i].etiqueta;
    xG.appendChild(xTxt);
  }
}

function renderDots(coords, label) {
  const dotsG = document.getElementById('inicioDotsGroup');
  if (!dotsG) return;
  const ns = 'http://www.w3.org/2000/svg';
  dotsG.innerHTML = '';
  coords.forEach(function (pt) {
    const c = document.createElementNS(ns, 'circle');
    c.setAttribute('cx', pt.x.toFixed(2));
    c.setAttribute('cy', pt.y.toFixed(2));
    c.setAttribute('r', pt.valor > 0 ? '4' : '2.5');
    c.setAttribute('class', 'inicio-data-dot');
    c.setAttribute('tabindex', '0');
    c.setAttribute('aria-label', pt.etiqueta + ': ' + pt.valor);
    c.addEventListener('mouseenter', function (e) { showTooltip(e, pt, label); });
    c.addEventListener('mousemove', function (e) { showTooltip(e, pt, label); });
    c.addEventListener('mouseleave', hideTooltip);
    c.addEventListener('focus', function () {
      const r = c.getBoundingClientRect();
      showTooltip({ clientX: r.left, clientY: r.top }, pt, label);
    });
    c.addEventListener('blur', hideTooltip);
    dotsG.appendChild(c);
  });
}

function renderChart(mode) {
  if (!state.data) return;
  const serie = state.data[state.metric];
  if (!serie) return;
  const puntos = state.period === '30d' ? serie.puntos_30d : serie.puntos_14d;
  const total = state.period === '30d' ? serie.total_30d : serie.total_14d;

  const titleEl = document.getElementById('inicioChartTitle');
  const totalEl = document.getElementById('inicioChartTotal');
  if (titleEl) titleEl.textContent = serie.label;
  if (totalEl) totalEl.textContent = String(total) + ' ' + (state.period === '30d' ? '(30d)' : '(14d)');

  const linePath = document.getElementById('inicioLinePath');
  const areaPath = document.getElementById('inicioAreaPath');
  if (!linePath || !areaPath) return;

  const computed = computeCoords(puntos);
  renderAxes(computed.niceMax, computed.coords);

  if (mode === 'morph' && state.prevCoords && state.prevCoords.length === computed.coords.length) {
    if (state.rafId) cancelAnimationFrame(state.rafId);
    const fromCoords = state.prevCoords;
    const toCoords = computed.coords;
    const start = performance.now();
    const duration = 420;
    const stepFrame = function (now) {
      const progress = Math.min(1, (now - start) / duration);
      const ease = 1 - Math.pow(1 - progress, 3);
      const interp = toCoords.map(function (pt, idx) {
        return {
          x: pt.x,
          y: fromCoords[idx].y + (pt.y - fromCoords[idx].y) * ease,
          valor: pt.valor,
          etiqueta: pt.etiqueta,
          fecha: pt.fecha,
        };
      });
      const d = buildSmoothPath(interp);
      linePath.setAttribute('d', d);
      areaPath.setAttribute('d', buildAreaPath(interp, d));
      if (progress < 1) {
        state.rafId = requestAnimationFrame(stepFrame);
      } else {
        state.prevCoords = toCoords;
        renderDots(toCoords, serie.label);
      }
    };
    state.rafId = requestAnimationFrame(stepFrame);
  } else {
    const d = buildSmoothPath(computed.coords);
    linePath.setAttribute('d', d);
    areaPath.setAttribute('d', buildAreaPath(computed.coords, d));
    renderDots(computed.coords, serie.label);
    state.prevCoords = computed.coords;

    if (mode === 'draw' && typeof linePath.getTotalLength === 'function') {
      const len = linePath.getTotalLength();
      linePath.style.transition = 'none';
      linePath.style.strokeDasharray = len;
      linePath.style.strokeDashoffset = len;
      linePath.getBoundingClientRect();
      linePath.style.transition = 'stroke-dashoffset 520ms cubic-bezier(0.16, 1, 0.3, 1)';
      linePath.style.strokeDashoffset = '0';
    }
  }
}

function signatureOf(data) {
  if (!data) return '';
  return JSON.stringify([data.avances && data.avances.puntos_30d, data.postulaciones && data.postulaciones.puntos_30d, data.hitos && data.hitos.puntos_30d]);
}

function pulseLivePill() {
  const pill = document.getElementById('inicioLivePill');
  if (!pill) return;
  pill.classList.add('is-updating');
  setTimeout(function () { pill.classList.remove('is-updating'); }, 700);
}

export function refreshInicioLineChart() {
  const svg = document.getElementById('inicioLineSvg');
  const url = svg ? svg.getAttribute('data-feed-url') : '';
  if (!url || document.visibilityState !== 'visible') return;
  const sec = document.getElementById('inicio');
  if (sec && !sec.classList.contains('activa')) return;

  fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (json) {
      if (!json) return;
      const sig = signatureOf(json);
      if (sig && sig !== state.lastSignature) {
        state.lastSignature = sig;
        state.data = json;
        renderChart('morph');
        pulseLivePill();
      }
    })
    .catch(function () {});
}

export function seleccionarMetricaInicio(metric, btn) {
  state.metric = metric;
  if (btn && btn.parentElement) {
    btn.parentElement.querySelectorAll('.ledger-filter-pill').forEach(function (b) { b.classList.remove('active'); });
    btn.classList.add('active');
  }
  renderChart('morph');
}

export function seleccionarPeriodoInicio(period, btn) {
  state.period = period;
  if (btn && btn.parentElement) {
    btn.parentElement.querySelectorAll('.time-tab-corp').forEach(function (b) { b.classList.remove('active'); });
    btn.classList.add('active');
  }
  state.prevCoords = null;
  renderChart('draw');
}

// --- Global Window Contracts ---

window.seleccionarMetricaInicio = seleccionarMetricaInicio;
window.seleccionarPeriodoInicio = seleccionarPeriodoInicio;
window.refreshInicioLineChart = refreshInicioLineChart;

// --- DOM Initialization ---

export function initAnalytics() {
  const el = document.getElementById('inicioActivityData');
  if (!el) return;
  try {
    state.data = JSON.parse(el.textContent || '{}');
    state.lastSignature = signatureOf(state.data);
    renderChart('draw');
    if (!state.pollTimer) {
      state.pollTimer = setInterval(refreshInicioLineChart, 15000);
    }
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'visible') refreshInicioLineChart();
    });
  } catch (e) {}
}
