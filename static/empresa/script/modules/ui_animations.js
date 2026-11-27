/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Micro-Animations, Chat Resizer
 * & Dialog Focus Trap
 * ============================================================
 */

import { EASE_OUT_EXPO, prefersReducedMotion, t } from './ui_utils.js';

// --- Motor Nativo de Micro-Animaciones (WAAPI + rAF) ---

export function animarTextoNumericoCorp(el) {
  if (!el || prefersReducedMotion()) return;
  const raw = (el.textContent || '').trim();
  if (!raw) return;

  // Extraer el primer bloque numérico con separadores de miles/decimales
  const match = raw.match(/^([^0-9\-]*)(-?[0-9][0-9.,]*)(.*)$/);
  if (!match) return;

  const prefix = match[1];
  const numStr = match[2];
  const suffix = match[3];

  // Ignorar fechas o rangos como "1-2" o "2026"
  if (suffix.indexOf('/') === 0 && numStr.length <= 2 && suffix.indexOf('5.0') === -1) return;

  let clean = numStr;
  let sepMiles = '';
  let sepDec = '.';
  let decimals = 0;

  if (numStr.indexOf('.') !== -1 && numStr.indexOf(',') !== -1) {
    if (numStr.lastIndexOf(',') > numStr.lastIndexOf('.')) {
      sepMiles = '.';
      sepDec = ',';
      decimals = numStr.length - numStr.lastIndexOf(',') - 1;
      clean = numStr.replace(/\./g, '').replace(',', '.');
    } else {
      sepMiles = ',';
      sepDec = '.';
      decimals = numStr.length - numStr.lastIndexOf('.') - 1;
      clean = numStr.replace(/,/g, '');
    }
  } else if ((numStr.match(/\./g) || []).length > 1) {
    sepMiles = '.';
    clean = numStr.replace(/\./g, '');
  } else if ((numStr.match(/,/g) || []).length > 1) {
    sepMiles = ',';
    clean = numStr.replace(/,/g, '');
  } else if (numStr.indexOf('.') !== -1) {
    const afterDot = numStr.split('.')[1] || '';
    if (afterDot.length === 3 && raw.indexOf('$') !== -1) {
      sepMiles = '.';
      clean = numStr.replace(/\./g, '');
    } else {
      sepDec = '.';
      decimals = afterDot.length;
    }
  } else if (numStr.indexOf(',') !== -1) {
    const afterComma = numStr.split(',')[1] || '';
    if (afterComma.length === 3 && raw.indexOf('$') !== -1) {
      sepMiles = ',';
      clean = numStr.replace(/,/g, '');
    } else {
      sepDec = ',';
      decimals = afterComma.length;
      clean = numStr.replace(',', '.');
    }
  }

  const targetVal = parseFloat(clean);
  if (!isFinite(targetVal) || targetVal === 0) return;

  if (el._corpTickerRaf) {
    cancelAnimationFrame(el._corpTickerRaf);
  }

  el.style.fontVariantNumeric = 'tabular-nums';
  const duration = 460;
  const startTime = performance.now();

  function formatNum(val) {
    const fixed = val.toFixed(decimals);
    const parts = fixed.split('.');
    let intPart = parts[0];
    if (sepMiles) {
      intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, sepMiles);
    }
    return decimals > 0 ? intPart + sepDec + parts[1] : intPart;
  }

  function tick(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = targetVal * eased;
    el.textContent = prefix + formatNum(current) + suffix;
    if (progress < 1) {
      el._corpTickerRaf = requestAnimationFrame(tick);
    } else {
      el.textContent = raw;
      el._corpTickerRaf = null;
    }
  }

  el._corpTickerRaf = requestAnimationFrame(tick);
}

export function animarSeccionCorp(sectionEl) {
  if (!sectionEl || prefersReducedMotion()) return;

  // 1. Entrada escalonada rápida (stagger <= 150ms) en tarjetas visibles
  const cardSelector = [
    '.kpi-card-corp',
    '.command-section-card',
    '.command-financial-card',
    '.command-trust-card',
    '.offer-card-corp',
    '.dev-card-corp',
    '.contract-card-corp',
    '.ledger-metric-card',
    '.ledger-chart-card',
    '.distribution-card-corp',
    '.disputas-kpi-card',
    '.disputas-case-card',
    '.linkedin-profile-card',
    '.linkedin-content-card'
  ].join(', ');

  const cards = Array.prototype.filter.call(sectionEl.querySelectorAll(cardSelector), function (el) {
    return el.offsetParent !== null;
  });

  cards.forEach(function (card, idx) {
    if (typeof card.animate === 'function') {
      card.animate(
        [
          { opacity: 0, transform: 'translateY(8px)' },
          { opacity: 1, transform: 'translateY(0)' }
        ],
        {
          duration: 240,
          delay: Math.min(idx * 24, 150),
          easing: EASE_OUT_EXPO,
          fill: 'backwards'
        }
      );
    }
  });

  // 2. Contadores numéricos (tabular-nums)
  const numSelector = '.kpi-card-value, .ledger-metric-val, .financial-card-escrow-amount, .disputas-kpi-val, .stat-number';
  sectionEl.querySelectorAll(numSelector).forEach(function (numEl) {
    if (numEl.offsetParent !== null) {
      animarTextoNumericoCorp(numEl);
    }
  });

  // 3. Barras de progreso horizontales
  sectionEl.querySelectorAll('[role="progressbar"] > div, .distribution-bar-track > div, .rep-histo-fill').forEach(function (bar, idx) {
    if (bar.offsetParent !== null && typeof bar.animate === 'function') {
      bar.style.transformOrigin = 'left center';
      bar.animate(
        [
          { transform: 'scaleX(0)' },
          { transform: 'scaleX(1)' }
        ],
        {
          duration: 420,
          delay: Math.min(idx * 30, 120),
          easing: EASE_OUT_EXPO,
          fill: 'backwards'
        }
      );
    }
  });

  // 4. Trazado de curvas SVG en la sección activa (ej. Curva de Hitos o Ledger)
  sectionEl.querySelectorAll('svg path[stroke]:not([stroke="none"])').forEach(function (pathEl) {
    if (typeof pathEl.getTotalLength === 'function' && typeof pathEl.animate === 'function') {
      try {
        const len = pathEl.getTotalLength();
        if (len > 10) {
          pathEl.style.strokeDasharray = len + ' ' + len;
          pathEl.animate(
            [
              { strokeDashoffset: len },
              { strokeDashoffset: 0 }
            ],
            { duration: 500, easing: EASE_OUT_EXPO, fill: 'forwards' }
          );
        }
      } catch (err) {}
    }
  });
}

// --- Chat List Resizer ---

export function initChatListResizer() {
  const chat = document.querySelector('#centro-chat .jd-chat');
  const resizer = document.getElementById('chatListResizer');
  const list = chat ? chat.querySelector('.jd-chat-list') : null;
  if (!chat || !resizer || !list) return;

  // Por defecto el panel de contexto arranca cerrado; solo se abre si el usuario lo dejó abierto
  try {
    const savedCollapsed = localStorage.getItem('chat_context_collapsed');
    const shouldCollapse = savedCollapsed !== '0';
    chat.classList.toggle('is-context-collapsed', shouldCollapse);
    const btn = document.getElementById('chatContextToggleBtn');
    if (btn) {
      btn.title = shouldCollapse ? t('mostrarContextoProyecto', 'Mostrar contexto del proyecto') : t('ocultarContextoProyecto', 'Ocultar contexto del proyecto');
      btn.innerHTML = '<i data-lucide="' + (shouldCollapse ? 'panel-right-open' : 'panel-right-close') + '"></i>';
    }
  } catch (e) {}

  const MIN_WIDTH = 220;
  const MAX_WIDTH = 520;
  const STORAGE_KEY = 'empresa_chat_list_width';

  function clampWidth(px) {
    const chatWidth = chat.getBoundingClientRect().width;
    const hasOpenContext = chat.classList.contains('has-context') && !chat.classList.contains('is-context-collapsed');
    const reservedRight = hasOpenContext ? 620 : 360;
    const dynamicMax = chatWidth > (MIN_WIDTH + reservedRight)
      ? Math.min(MAX_WIDTH, chatWidth - reservedRight)
      : MIN_WIDTH;
    return Math.round(Math.min(Math.max(px, MIN_WIDTH), Math.max(MIN_WIDTH, dynamicMax)));
  }

  try {
    const saved = parseInt(localStorage.getItem(STORAGE_KEY) || '', 10);
    if (Number.isFinite(saved) && saved >= MIN_WIDTH) {
      chat.style.setProperty('--jd-chat-list-width', clampWidth(saved) + 'px');
    }
  } catch (e) {}

  resizer.addEventListener('pointerdown', function (e) {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    e.preventDefault();

    const startX = e.clientX;
    const startWidth = list.getBoundingClientRect().width;
    resizer.classList.add('is-resizing');
    document.body.classList.add('is-chat-resizing');

    function onMove(ev) {
      const nextWidth = clampWidth(startWidth + (ev.clientX - startX));
      chat.style.setProperty('--jd-chat-list-width', nextWidth + 'px');
    }

    function onUp() {
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerup', onUp);
      document.removeEventListener('pointercancel', onUp);
      resizer.classList.remove('is-resizing');
      document.body.classList.remove('is-chat-resizing');
      try {
        const finalWidth = Math.round(list.getBoundingClientRect().width);
        if (finalWidth >= MIN_WIDTH) {
          localStorage.setItem(STORAGE_KEY, String(finalWidth));
        }
      } catch (err) {}
    }

    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp);
    document.addEventListener('pointercancel', onUp);
  });
}

// --- Dialog / Drawer Focus Trap & Focus Restoration ---

export function initDialogFocusTrap() {
  const focusRestoreMap = new WeakMap();
  let lastUserTrigger = null;
  const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  document.addEventListener('pointerdown', function (e) {
    if (e.target && !e.target.closest('[role="dialog"].open, [role="dialog"].is-open')) {
      const cand = e.target.closest('button, a, [role="button"], [tabindex]:not([tabindex="-1"])');
      lastUserTrigger = cand || null;
    }
  }, true);

  document.addEventListener('keydown', function (e) {
    if ((e.key === 'Enter' || e.key === ' ') && document.activeElement && !document.activeElement.closest('[role="dialog"].open, [role="dialog"].is-open')) {
      lastUserTrigger = document.activeElement;
    }
  }, true);

  function isDialogOpen(el) {
    return el.classList.contains('open') || el.classList.contains('is-open');
  }

  function getFocusable(container) {
    return Array.prototype.filter.call(container.querySelectorAll(FOCUSABLE), function (el) {
      return el.offsetParent !== null;
    });
  }

  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      const target = m.target;
      if (!target || !target.matches || !target.matches('[role="dialog"]')) return;
      if (isDialogOpen(target)) {
        if (!focusRestoreMap.has(target)) {
          const trigger = lastUserTrigger || (document.activeElement && !target.contains(document.activeElement) ? document.activeElement : null);
          lastUserTrigger = null;
          if (trigger) focusRestoreMap.set(target, trigger);
        }
        const items = getFocusable(target);
        if (items.length && !target.contains(document.activeElement)) {
          items[0].focus();
        }
      } else if (focusRestoreMap.has(target)) {
        const prev = focusRestoreMap.get(target);
        focusRestoreMap.delete(target);
        if (prev && typeof prev.focus === 'function' && prev.isConnected) {
          prev.focus();
        }
      }
    });
  });

  document.querySelectorAll('[role="dialog"].modal-overlay, [role="dialog"].drawer-overlay').forEach(function (dlg) {
    observer.observe(dlg, { attributes: true, attributeFilter: ['class'] });
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab') return;
    const allOpen = document.querySelectorAll('[role="dialog"].open, [role="dialog"].is-open');
    const activeDialog = allOpen.length ? allOpen[allOpen.length - 1] : null;
    if (!activeDialog) return;
    const items = getFocusable(activeDialog);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && (document.activeElement === first || !activeDialog.contains(document.activeElement))) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });
}
