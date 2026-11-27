/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Corporate DatePicker Suite
 * ============================================================
 */

import { t } from './ui_core.js';

function obtenerMeses() {
  const raw = t('mesesLista', 'Enero,Febrero,Marzo,Abril,Mayo,Junio,Julio,Agosto,Septiembre,Octubre,Noviembre,Diciembre');
  const arr = raw.split(',');
  return arr.length === 12
    ? arr
    : ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
}

function formatearFechaDisplayDatepicker(d, m, y) {
  const locale = (document.documentElement.lang || '').trim() || 'es-CO';
  try {
    return new Date(y, m, d).toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
  } catch (e) {
    return d + ' ' + obtenerMeses()[m] + ', ' + y;
  }
}

function padZero(n) {
  return n < 10 ? '0' + n : '' + n;
}

window._corpDatepickers = {};

export function initCorpDatepicker(pickerId, initialIso) {
  const container = document.getElementById(pickerId);
  const hasVisualPicker = !!(container && container.querySelector('.datepicker-display') && document.getElementById(pickerId + '-popover'));
  if (!hasVisualPicker) return;

  const today = new Date();
  let initialDate = null;
  if (initialIso) {
    const parts = initialIso.split('-');
    if (parts.length === 3) {
      initialDate = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    }
  }

  window._corpDatepickers[pickerId] = {
    viewDate: initialDate ? new Date(initialDate) : new Date(today),
    selectedDate: initialDate ? new Date(initialDate) : null,
  };

  if (initialDate) {
    setDatepickerValue(pickerId, initialIso);
  }
  renderCorpDatepicker(pickerId);
}

export function toggleCorpDatepicker(pickerId) {
  const popover = document.getElementById(pickerId + '-popover');
  const container = document.getElementById(pickerId);
  const hasVisualPicker = !!(popover && container && container.querySelector('.datepicker-display'));
  if (!hasVisualPicker) return;
  const isOpen = popover.classList.contains('is-open');
  document.querySelectorAll('.datepicker-popover').forEach(function (p) {
    p.classList.remove('is-open');
  });
  if (!isOpen) {
    if (!window._corpDatepickers[pickerId]) {
      initCorpDatepicker(pickerId);
    }
    renderCorpDatepicker(pickerId);
    popover.classList.add('is-open');
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }
}

export function cerrarCorpDatepicker(pickerId) {
  const popover = document.getElementById(pickerId + '-popover');
  if (popover) popover.classList.remove('is-open');
}

export function navegarMesDatepicker(pickerId, delta) {
  const state = window._corpDatepickers[pickerId];
  if (!state) return;
  state.viewDate.setMonth(state.viewDate.getMonth() + delta);
  renderCorpDatepicker(pickerId);
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

export function aplicarPresetFecha(pickerId, dias) {
  const target = new Date();
  target.setDate(target.getDate() + dias);
  const iso = target.getFullYear() + '-' + padZero(target.getMonth() + 1) + '-' + padZero(target.getDate());
  setDatepickerValue(pickerId, iso);
  cerrarCorpDatepicker(pickerId);
}

export function seleccionarHoyDatepicker(pickerId) {
  const today = new Date();
  const iso = today.getFullYear() + '-' + padZero(today.getMonth() + 1) + '-' + padZero(today.getDate());
  setDatepickerValue(pickerId, iso);
  cerrarCorpDatepicker(pickerId);
}

export function seleccionarFechaDatepicker(pickerId, year, month, day) {
  const iso = year + '-' + padZero(month + 1) + '-' + padZero(day);
  setDatepickerValue(pickerId, iso);
  cerrarCorpDatepicker(pickerId);
}

export function setDatepickerValue(pickerId, isoString) {
  if (!pickerId) return;
  const container = document.getElementById(pickerId);
  if (!container) return;

  const hiddenInput = container.querySelector('input[type="hidden"]');
  const displayInput = container.querySelector('.datepicker-display');

  if (isoString) {
    const parts = isoString.split('-');
    if (parts.length === 3) {
      const y = parseInt(parts[0], 10);
      const m = parseInt(parts[1], 10) - 1;
      const d = parseInt(parts[2], 10);
      const selDate = new Date(y, m, d);

      if (!window._corpDatepickers[pickerId]) {
        window._corpDatepickers[pickerId] = { viewDate: new Date(selDate), selectedDate: selDate };
      } else {
        window._corpDatepickers[pickerId].selectedDate = selDate;
        window._corpDatepickers[pickerId].viewDate = new Date(selDate);
      }

      if (hiddenInput) hiddenInput.value = isoString;
      if (displayInput) displayInput.value = formatearFechaDisplayDatepicker(d, m, y);
      return;
    }
  }

  if (hiddenInput) hiddenInput.value = '';
  if (displayInput) displayInput.value = '';
  if (window._corpDatepickers[pickerId]) {
    window._corpDatepickers[pickerId].selectedDate = null;
  }
}

export function renderCorpDatepicker(pickerId) {
  const state = window._corpDatepickers[pickerId];
  if (!state) return;

  const monthYearEl = document.getElementById(pickerId + '-monthyear');
  const daysContainer = document.getElementById(pickerId + '-days');
  if (!monthYearEl || !daysContainer) return;

  const year = state.viewDate.getFullYear();
  const month = state.viewDate.getMonth();
  monthYearEl.textContent = obtenerMeses()[month] + ' ' + year;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const firstDay = new Date(year, month, 1).getDay();
  const startOffset = (firstDay + 6) % 7; // Lunes = 0

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();

  let html = '';

  for (let i = startOffset - 1; i >= 0; i--) {
    const prevD = daysInPrevMonth - i;
    html += '<div class="datepicker-day other-month disabled">' + prevD + '</div>';
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const thisDate = new Date(year, month, d);
    thisDate.setHours(0, 0, 0, 0);

    const isPast = thisDate < today;
    const isToday = thisDate.getTime() === today.getTime();
    const isSelected = state.selectedDate && (
      state.selectedDate.getFullYear() === year &&
      state.selectedDate.getMonth() === month &&
      state.selectedDate.getDate() === d
    );

    const classes = ['datepicker-day'];
    if (isPast) classes.push('disabled');
    if (isToday) classes.push('today');
    if (isSelected) classes.push('selected');

    const clickHandler = isPast ? '' : 'role="button" tabindex="0" onclick="seleccionarFechaDatepicker(\'' + pickerId + '\', ' + year + ', ' + month + ', ' + d + ')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();seleccionarFechaDatepicker(\'' + pickerId + '\', ' + year + ', ' + month + ', ' + d + ');}"';
    html += '<div class="' + classes.join(' ') + '" ' + clickHandler + '>' + d + '</div>';
  }

  const totalRendered = startOffset + daysInMonth;
  const remaining = (7 - (totalRendered % 7)) % 7;
  for (let j = 1; j <= remaining; j++) {
    html += '<div class="datepicker-day other-month disabled">' + j + '</div>';
  }

  daysContainer.innerHTML = html;
}

// --- Global Window Contracts ---

window.initCorpDatepicker = initCorpDatepicker;
window.toggleCorpDatepicker = toggleCorpDatepicker;
window.cerrarCorpDatepicker = cerrarCorpDatepicker;
window.navegarMesDatepicker = navegarMesDatepicker;
window.aplicarPresetFecha = aplicarPresetFecha;
window.seleccionarHoyDatepicker = seleccionarHoyDatepicker;
window.seleccionarFechaDatepicker = seleccionarFechaDatepicker;
window.setDatepickerValue = setDatepickerValue;
window.renderCorpDatepicker = renderCorpDatepicker;

// --- DOM Initialization ---

export function initDatepicker() {
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.corp-datepicker')) {
      document.querySelectorAll('.datepicker-popover').forEach(function (p) {
        p.classList.remove('is-open');
      });
    }
  });
}
