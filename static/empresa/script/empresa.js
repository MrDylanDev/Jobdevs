/**
 * ============================================================
 * JobDevs - Dashboard Empresa (Vanilla JS Moderno)
 * ============================================================
 */

(function () {
  'use strict';

  const I18N = (function () {
    try {
      const el = document.getElementById('empresa-i18n');
      return el ? JSON.parse(el.textContent) : {};
    } catch (e) {
      return {};
    }
  })();
  function t(key, fallback) {
    return (I18N && I18N[key]) || fallback;
  }

  // --- Modo Claro / Oscuro ---
  const THEME_STORAGE_KEY = 'jobdevs-theme';

  function obtenerTemaActual() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function actualizarBotonTema(tema) {
    const btn = document.getElementById('empresaThemeToggle');
    if (!btn) return;
    btn.setAttribute('aria-pressed', tema === 'dark' ? 'true' : 'false');
    btn.setAttribute('aria-label', tema === 'dark' ? t('cambiarTemaClaro', 'Cambiar a tema claro') : t('cambiarTemaOscuro', 'Cambiar a tema oscuro'));
    const label = document.getElementById('empresaThemeLabel');
    if (label) {
      label.textContent = tema === 'dark' ? t('temaOscuroLabel', 'Tema oscuro') : t('temaClaroLabel', 'Tema claro');
    }
    const icon = document.getElementById('empresaThemeIcon');
    if (icon) {
      icon.setAttribute('data-lucide', tema === 'dark' ? 'sun' : 'moon');
    }
  }

  window.toggleEmpresaTheme = function () {
    const temaActual = obtenerTemaActual();
    const nuevoTema = temaActual === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', nuevoTema);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, nuevoTema);
    } catch (e) {}
    actualizarBotonTema(nuevoTema);
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  window.switchEmpresaIdioma = function (event, el) {
    if (!el || !el.href) return;
    if (event) event.preventDefault();
    el.classList.add('is-switching');
    const wrapper = document.querySelector('.main-wrapper');
    if (wrapper) wrapper.classList.add('is-lang-switching');
    const targetUrl = new URL(el.href, window.location.origin);
    const activeSec = document.querySelector('.seccion-v.activa, .section-v.activa');
    const currentHash = window.location.hash || (activeSec && activeSec.id ? '#' + activeSec.id : '');
    const params = new URLSearchParams(window.location.search);
    if (!params.get('section') && activeSec && activeSec.id) {
      params.set('section', activeSec.id);
    }
    const qs = params.toString();
    const finalHref = targetUrl.pathname + (qs ? '?' + qs : '') + currentHash;
    setTimeout(function () {
      if (typeof window.closeUserMenu === 'function') window.closeUserMenu();
      window.location.href = finalHref;
    }, 110);
  };

  window.cerrarSesionConSpinner = function (event, el) {
    if (!el || !el.href) return;
    if (event) event.preventDefault();
    if (typeof window.closeUserMenu === 'function') window.closeUserMenu();
    const overlay = document.getElementById('logoutSpinnerOverlay');
    if (overlay) {
      overlay.style.display = 'flex';
      overlay.setAttribute('aria-hidden', 'false');
    }
    setTimeout(function () {
      window.location.href = el.href;
    }, 350);
  };

  // --- 1. Tab Switching & URL Persistence ---
  let _initialTabReady = false;

  function ejecutarSwitchTabDOM(id, btn) {
    const sections = document.querySelectorAll('.seccion-v, .section-v');
    const navItems = document.querySelectorAll('.nav-item');

    sections.forEach(function (sec) {
      sec.classList.remove('activa', 'active');
    });

    navItems.forEach(function (item) {
      item.classList.remove('active');
    });

    const targetSection = document.getElementById(id);
    if (targetSection) {
      targetSection.classList.add('activa');
    }

    // Gestionar modo de pantalla completa para el chat (elimina paddings de carta)
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      if (id === 'centro-chat') {
        mainContent.classList.add('is-chat-active');
      } else {
        mainContent.classList.remove('is-chat-active');
      }
    }

    // Identificar botón activo
    if (!btn) {
      btn = Array.from(document.querySelectorAll('.nav-item')).find(function (el) {
        const onclickAttr = el.getAttribute('onclick') || '';
        const dataTarget = el.getAttribute('data-tab') || '';
        return onclickAttr.indexOf("'" + id + "'") !== -1 ||
               onclickAttr.indexOf('"' + id + '"') !== -1 ||
               dataTarget === id;
      });
    }

    if (btn) {
      btn.classList.add('active');
    }

    // Actualizar URL hash y section param de forma limpia sin saltos de scroll
    if (window.history && window.history.replaceState) {
      const url = new URL(window.location);
      url.hash = id;
      url.searchParams.set('section', id);
      window.history.replaceState(null, '', url);
    }

    // Cerrar sidebar en móviles tras seleccionar pestaña
    closeSidebar();

    if (targetSection && typeof window.animarSeccionCorp === 'function') {
      window.animarSeccionCorp(targetSection);
    }
  }

  window.switchTab = function (id, btn) {
    if (!id) return;
    if (id === 'reputacion') id = 'inicio';
    if (id === 'historial-disputas') id = 'disputas';

    const targetSection = document.getElementById(id);
    const yaActiva = targetSection && targetSection.classList.contains('activa');

    if (
      _initialTabReady &&
      !yaActiva &&
      typeof document.startViewTransition === 'function' &&
      !prefersReducedMotion()
    ) {
      try {
        document.startViewTransition(function () {
          ejecutarSwitchTabDOM(id, btn);
        });
      } catch (e) {
        ejecutarSwitchTabDOM(id, btn);
      }
    } else {
      ejecutarSwitchTabDOM(id, btn);
    }
    _initialTabReady = true;
  };

  // --- 1.5 Motor Nativo de Micro-Animaciones (WAAPI + rAF) ---
  const EASE_OUT_EXPO = 'cubic-bezier(0.16, 1, 0.3, 1)';

  function prefersReducedMotion() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  window.animarTextoNumericoCorp = function (el) {
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
  };

  window.animarSeccionCorp = function (sectionEl) {
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
        window.animarTextoNumericoCorp(numEl);
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
  };

  function animarExpedienteContrato(container, contrato) {
    if (!container || prefersReducedMotion()) return;
    const paper = container.querySelector('.contract-doc-paper');
    if (paper && typeof paper.animate === 'function') {
      paper.animate(
        [
          { opacity: 0, transform: 'translateY(10px) scale(0.99)' },
          { opacity: 1, transform: 'translateY(0) scale(1)' }
        ],
        { duration: 260, easing: EASE_OUT_EXPO, fill: 'backwards' }
      );
    }

    const esRecienFirmado = contrato && String(window._recienFirmadoContratoId) === String(contrato.id);
    if (esRecienFirmado) {
      window._recienFirmadoContratoId = null;
      const sellos = container.querySelectorAll('.contract-sign-done, .hash-pill, .contract-estado-badge');
      sellos.forEach(function (sello, idx) {
        if (typeof sello.animate === 'function') {
          sello.animate(
            [
              { opacity: 0.2, transform: 'scale(1.12)' },
              { opacity: 1, transform: 'scale(1)' }
            ],
            {
              duration: 380,
              delay: idx * 55,
              easing: EASE_OUT_EXPO,
              fill: 'backwards'
            }
          );
        }
      });

      const fila = document.querySelector('[data-contrato-row="' + contrato.id + '"]');
      if (fila && typeof fila.animate === 'function') {
        fila.animate(
          [
            { backgroundColor: 'var(--corp-brand-light)' },
            { backgroundColor: 'transparent' }
          ],
          { duration: 900, easing: EASE_OUT_EXPO }
        );
      }
    }
  }

  // --- 2. Modal de Nuevo Proyecto ---
  window.abrirModal = function () {
    const modal = document.getElementById('modalProyecto');
    if (modal) {
      modal.classList.add('open');
      modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
      if (typeof window.initCorpDatepicker === 'function') {
        window.initCorpDatepicker('datepicker-crear');
      }
      const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
      if (firstInput) firstInput.focus();
    }
  };

  window.cerrarModal = function () {
    const modal = document.getElementById('modalProyecto');
    if (modal) {
      modal.classList.remove('open');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  };

  document.addEventListener('DOMContentLoaded', function () {
    const formCrear = document.getElementById('formCrearProyecto');
    if (!formCrear) return;

    formCrear.addEventListener('submit', async function (e) {
      e.preventDefault();
      const submitBtn = formCrear.querySelector('button[type="submit"]');
      const textoOrig = submitBtn ? submitBtn.innerHTML : '';
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="corp-spinner-sm" style="display:inline-block;width:13px;height:13px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;animation:spin 0.6s linear infinite;vertical-align:middle;margin-right:6px;"></span> Publicando...';
      }

      try {
        const formData = new FormData(formCrear);
        const res = await fetch(formCrear.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json',
          },
          credentials: 'same-origin',
        });

        const data = await res.json().catch(() => null);

        if (res.ok && data && data.ok) {
          window.cerrarModal();
          formCrear.reset();
          if (typeof window.mostrarToastCorp === 'function') {
            window.mostrarToastCorp({
              tipo: 'aprobacion',
              mensaje: data.mensaje || '¡Convocatoria publicada exitosamente!',
            });
          }
          window.switchTab('ofertas');
          window.location.hash = '#ofertas';
          setTimeout(function () {
            window.location.reload();
          }, 350);
        } else {
          const errMsg = (data && data.mensaje) ? data.mensaje : 'Por favor verifica los datos de la convocatoria.';
          if (typeof window.mostrarToastCorp === 'function') {
            window.mostrarToastCorp({
              tipo: 'alerta',
              mensaje: errMsg,
            });
          } else if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
            window.JobDevsToast.mostrar({ tipo: 'error', mensaje: errMsg });
          } else if (typeof window.jdToast === 'function') {
            window.jdToast(errMsg, true);
          }
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = textoOrig;
          }
        }
      } catch (err) {
        console.error('Error al publicar convocatoria:', err);
        formCrear.submit();
      }
    });
  });

  // --- 2.1 Modal de Editar Perfil In-Situ ---
  window.abrirModalPerfil = function () {
    const modal = document.getElementById('modalEditarPerfil');
    if (modal) {
      modal.classList.add('open');
      modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
      const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
      if (firstInput) firstInput.focus();
    }
  };

  window.cerrarModalPerfil = function () {
    const modal = document.getElementById('modalEditarPerfil');
    if (modal) {
      modal.classList.remove('open');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  };

  // --- 2.1b Modal de Verificación de Identidad In-Situ ---
  window.abrirModalVerificacion = function (event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    const modal = document.getElementById('modalVerificacionEmpresa');
    if (modal) {
      modal.classList.add('open');
      modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
      const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
      if (firstInput) firstInput.focus();
    }
  };

  window.cerrarModalVerificacion = function () {
    const modal = document.getElementById('modalVerificacionEmpresa');
    if (modal) {
      modal.classList.remove('open');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  };

  // --- 2.2 Previsualización de Logo en Modal ---
  window.previewLogo = function (input) {
    if (input.files && input.files[0]) {
      const reader = new FileReader();
      reader.onload = function (e) {
        const previewBox = document.getElementById('logoPreviewBox');
        if (previewBox) {
          previewBox.innerHTML = '<img src="' + e.target.result + '" alt="' + t('vistaPrevia', 'Vista previa') + '" style="width:100%;height:100%;object-fit:cover;">';
        }
      };
      reader.readAsDataURL(input.files[0]);
    }
  };

  // --- 2.3 Sub-tabs de Perfil LinkedIn Style ---
  window.switchPerfilSubTab = function (paneId, btn) {
    const panes = document.querySelectorAll('.linkedin-tab-pane');
    const tabs = document.querySelectorAll('.linkedin-tab-btn');

    panes.forEach(function (p) {
      p.classList.remove('active');
    });

    tabs.forEach(function (t) {
      t.classList.remove('active');
    });

    const target = document.getElementById('pane-' + paneId);
    if (target) {
      target.classList.add('active');
    }

    if (btn) {
      btn.classList.add('active');
    }
  };

  // --- 2.3b Sub-tabs de Historial (Proyectos / Disputas) ---
  window.switchHistorialSubTab = function (subtabId, btn) {
    const panes = document.querySelectorAll('.history-tab-pane');
    const tabs = document.querySelectorAll('.history-tab-btn');

    panes.forEach(function (p) {
      p.classList.remove('active');
    });

    tabs.forEach(function (t) {
      t.classList.remove('active');
    });

    const target = document.getElementById('pane-historial-' + subtabId);
    if (target) {
      target.classList.add('active');
    }

    if (!btn) {
      btn = document.getElementById('btn-historial-' + subtabId);
    }
    if (btn) {
      btn.classList.add('active');
    }

    if (window.history && window.history.replaceState) {
      const url = new URL(window.location);
      url.searchParams.set('subtab', subtabId);
      window.history.replaceState(null, '', url);
    }

    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  // --- 2.5 Drawer de Candidatos In-Situ (Evita salir del panel) ---
  const drawerTabCache = new Map();
  let drawerFetchToken = 0;

  window._limpiarCacheDrawerCandidatos = function () {
    drawerTabCache.clear();
  };

  function parseDrawerResponse(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    const inspectorCards = Array.from(doc.querySelectorAll('.candidato-inspector-panel .inspector-detail'));
    const legacyCards = [];
    if (inspectorCards.length === 0) {
      doc.querySelectorAll('.main-content .card').forEach(function (c) {
        if (c.tagName.toLowerCase() === 'form') return;
        if (c.querySelector('form[method="get"]')) return;
        if (c.querySelector('h2') && c.querySelector('.card-subtitle')) return;
        legacyCards.push(c);
      });
    }

    const candidateCards = inspectorCards.length > 0 ? inspectorCards : legacyCards;
    const funnelTabs = doc.querySelector('.funnel-tabs-grid');
    const funnelHtml = funnelTabs ? funnelTabs.innerHTML : '';

    let listHtml = '';
    if (candidateCards.length > 0) {
      listHtml += '<div class="drawer-candidates-list">';
      candidateCards.forEach(function (c) {
        listHtml += '<div class="drawer-candidate-card">' + c.innerHTML + '</div>';
      });
      listHtml += '</div>';
    } else {
      listHtml += '<div class="activity-empty" style="padding:40px 20px;"><i data-lucide="user-x"></i><p>' + t('sinCandidatos', 'No se encontraron candidatos postulados para este proyecto.') + '</p></div>';
    }

    return { funnelHtml: funnelHtml, listHtml: listHtml };
  }

  function bindDrawerCandidateLinks(container) {
    if (!container) return;
    container.querySelectorAll('a').forEach(function (link) {
      const href = link.getAttribute('href') || '';
      const coincidenciaContrato = href.match(/contrato-digital\/(\d+)\/?/);
      if (coincidenciaContrato) {
        link.removeAttribute('target');
        link.setAttribute('rel', 'noopener');
        link.addEventListener('click', function (ev) {
          window.abrirModalContrato(ev, coincidenciaContrato[1]);
        });
        return;
      }
      link.setAttribute('target', '_blank');
      link.setAttribute('rel', 'noopener');
    });
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  function switchDrawerTab(event, tabLink, contentEl) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    const tabUrl = tabLink.getAttribute('href');
    if (!tabUrl || !contentEl) return;

    window._ultimoUrlCandidatos = tabUrl;
    contentEl.querySelectorAll('.drawer-funnel-tabs a').forEach(function (el) {
      el.classList.toggle('is-active', el === tabLink);
    });

    const bodyContainer = contentEl.querySelector('.drawer-candidates-body');
    if (!bodyContainer) return;

    if (drawerTabCache.has(tabUrl)) {
      bodyContainer.innerHTML = drawerTabCache.get(tabUrl);
      bodyContainer.style.opacity = '1';
      bindDrawerCandidateLinks(bodyContainer);
      return;
    }

    const token = ++drawerFetchToken;
    bodyContainer.style.opacity = '0.55';
    fetch(tabUrl)
      .then(function (res) {
        if (!res.ok) throw new Error(t('errorConsultarCandidatos', 'Error al consultar candidatos'));
        return res.text();
      })
      .then(function (html) {
        const parsed = parseDrawerResponse(html);
        drawerTabCache.set(tabUrl, parsed.listHtml);
        if (token !== drawerFetchToken) return;
        bodyContainer.innerHTML = parsed.listHtml;
        bodyContainer.style.opacity = '1';
        bindDrawerCandidateLinks(bodyContainer);
      })
      .catch(function () {
        if (token !== drawerFetchToken) return;
        bodyContainer.style.opacity = '1';
        bodyContainer.innerHTML = '<div class="activity-empty" style="padding:40px 20px;"><i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i><p>' + t('errorVistaPrevia', 'No se pudo cargar la vista previa in-situ.') + '</p></div>';
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      });
  }

  window.abrirDrawerCandidatos = function (event, url, titulo) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    window._ultimoUrlCandidatos = url;
    const token = ++drawerFetchToken;

    const drawer = document.getElementById('drawerCandidatos');
    const titleEl = document.getElementById('drawerProjectTitle');
    const contentEl = document.getElementById('drawerContent');

    if (titleEl) titleEl.textContent = titulo || t('candidatosPostulados', 'Candidatos Postulados');
    if (drawer) {
      drawer.classList.add('is-open');
      document.body.style.overflow = 'hidden';
    }

    if (contentEl) {
      contentEl.innerHTML = '<div class="drawer-loading"><i data-lucide="loader-circle" class="corp-spin"></i><p>' + t('cargandoPostulaciones', 'Cargando postulaciones y perfiles de candidatos...') + '</p></div>';
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }

      fetch(url)
        .then(function (res) {
          if (!res.ok) throw new Error(t('errorConsultarCandidatos', 'Error al consultar candidatos'));
          return res.text();
        })
        .then(function (html) {
          if (token !== drawerFetchToken) return;
          const parsed = parseDrawerResponse(html);
          drawerTabCache.set(url, parsed.listHtml);

          let outHtml = '';
          if (parsed.funnelHtml) {
            outHtml += '<div class="drawer-funnel-tabs">' + parsed.funnelHtml + '</div>';
          }
          outHtml += '<div class="drawer-candidates-body" style="transition:opacity 0.15s ease;">' + parsed.listHtml + '</div>';
          contentEl.innerHTML = outHtml;

          const bodyContainer = contentEl.querySelector('.drawer-candidates-body');
          bindDrawerCandidateLinks(bodyContainer);

          // Tabs del embudo cambian solo el listado sin recargar toda la vista
          contentEl.querySelectorAll('.drawer-funnel-tabs a').forEach(function (tabLink) {
            const tabUrl = tabLink.getAttribute('href');
            tabLink.addEventListener('click', function (ev) {
              switchDrawerTab(ev, tabLink, contentEl);
            });
            // Precarga silenciosa del resto de pestañas para cambio instantáneo
            if (tabUrl && tabUrl !== url && !drawerTabCache.has(tabUrl)) {
              fetch(tabUrl)
                .then(function (r) { return r.ok ? r.text() : ''; })
                .then(function (subHtml) {
                  if (!subHtml) return;
                  drawerTabCache.set(tabUrl, parseDrawerResponse(subHtml).listHtml);
                })
                .catch(function () {});
            }
          });
        })
        .catch(function () {
          if (token !== drawerFetchToken) return;
          contentEl.innerHTML = '<div class="activity-empty" style="padding:40px 20px;"><i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i><p>' + t('errorVistaPrevia', 'No se pudo cargar la vista previa in-situ.') + '</p></div>';
          if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
          }
        });
    }
  };

  window.cerrarDrawerCandidatos = function () {
    const drawer = document.getElementById('drawerCandidatos');
    if (drawer) {
      drawer.classList.remove('is-open');
      document.body.style.overflow = '';
    }
  };

  // --- 2.5b Modal In-Situ de Contrato Digital (firma electrónica sin recargar) ---
  function csrfTokenActual() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input && input.value) return input.value;
    const coincidencia = document.cookie.match(/csrftoken=([^;]+)/);
    return coincidencia ? coincidencia[1] : '';
  }

  function endpointContratoDigital(contratoId) {
    const seccion = document.getElementById('contratos');
    let base = seccion ? (seccion.getAttribute('data-contrato-endpoint') || '') : '';
    if (!base) base = '/contrataciones/contrato-digital/0/';
    return base.replace(/0\/$/, '') + contratoId + '/';
  }

  function escaparHtml(valor) {
    return String(valor === null || valor === undefined ? '' : valor)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatearFechaFirma(valor) {
    if (!valor) return t('pendiente', 'Pendiente');
    const fecha = new Date(valor);
    if (isNaN(fecha.getTime())) return String(valor);
    const locale = (document.documentElement.lang || '').trim() || 'es-CO';
    try {
      return fecha.toLocaleString(locale, { dateStyle: 'medium', timeStyle: 'short' });
    } catch (e) {
      return fecha.toLocaleString();
    }
  }

  function mostrarToastCorp(mensaje, esError) {
    const toast = document.getElementById('corpToast');
    if (!toast) return;
    const span = toast.querySelector('span');
    if (span) span.textContent = mensaje;
    toast.classList.toggle('is-error', !!esError);
    toast.classList.add('show');
    setTimeout(function () {
      toast.classList.remove('show');
      toast.classList.remove('is-error');
    }, 3500);
  }

  function bloqueFirmaParte(etiqueta, nombre, firmado, fecha) {
    const estado = firmado
      ? '<span class="signature-badge-corp is-signed"><i data-lucide="check-circle-2"></i><span>' + escaparHtml(t('firmado', 'Firmado')) + '</span></span>'
      : '<span class="signature-badge-corp is-pending"><i data-lucide="clock"></i><span>' + escaparHtml(t('pendienteFirma', 'Pendiente de firma')) + '</span></span>';
    return '' +
      '<div class="contract-signature-block">' +
        '<div class="contract-signature-block-label">' + escaparHtml(etiqueta) + '</div>' +
        '<div class="contract-signature-block-name">' + escaparHtml(nombre) + '</div>' +
        '<div class="contract-signature-block-stamp">' +
          '<span class="contract-signature-script">' + (firmado ? escaparHtml(t('firmadoDigitalmente', 'Firmado digitalmente')) : '—') + '</span>' +
        '</div>' +
        estado +
        '<div class="contract-signature-block-date">' + escaparHtml(formatearFechaFirma(fecha)) + '</div>' +
      '</div>';
  }

  function htmlFormularioFirma(contrato) {
    if (contrato.esta_firmado) {
      return '<div class="contract-sign-done"><i data-lucide="shield-check"></i>' +
        '<p>' + escaparHtml(t('contratoFirmadoAmbasPartes', 'Contrato firmado por ambas partes. La contratación quedó formalizada.')) + '</p></div>';
    }
    if (contrato.ya_firmo) {
      return '<div class="contract-sign-done"><i data-lucide="check-circle-2"></i>' +
        '<p>' + escaparHtml(t('contratoYaFirmo', 'Ya firmaste este contrato. Queda pendiente la firma de la otra parte.')) + '</p></div>';
    }
    if (!contrato.puede_firmar) {
      return '<div class="contract-sign-done is-muted"><i data-lucide="lock"></i>' +
        '<p>' + escaparHtml(t('contratoNoDisponible', 'Este contrato ya no está disponible para firma electrónica.')) + '</p></div>';
    }
    return '' +
      '<form id="formFirmarContrato" class="contract-sign-form" method="post" action="' +
        escaparHtml(contrato.url_firmar) + '" data-contrato-id="' + escaparHtml(contrato.id) + '">' +
        '<input type="hidden" name="csrfmiddlewaretoken" value="' + escaparHtml(csrfTokenActual()) + '">' +
        '<label class="contract-sign-check">' +
          '<input type="checkbox" name="acepta_terminos" value="1" required>' +
          '<span>' + escaparHtml(t('contratoAceptoTerminos', 'Acepto los términos, las condiciones y el perfil profesional mostrado, y firmo electrónicamente este contrato.')) + '</span>' +
        '</label>' +
        '<div id="contratoFirmaError" class="contract-sign-error" style="display:none;"></div>' +
        '<button type="submit" class="btn-corp-primary contract-sign-submit">' +
          '<i data-lucide="pen-tool"></i>' +
          '<span>' + escaparHtml(t('firmarElectronicamente', 'Firmar Electrónicamente')) + '</span>' +
        '</button>' +
      '</form>';
  }

  function esUrlHttpSegura(url) {
    return /^https?:\/\/\S+$/i.test(String(url || '').trim());
  }

  function htmlEnlaceSeguro(url) {
    const limpio = String(url || '').trim();
    if (!limpio) return '';
    if (esUrlHttpSegura(limpio)) {
      return '<a href="' + escaparHtml(limpio) + '" target="_blank" rel="noopener noreferrer" class="contract-profile-link">' + escaparHtml(limpio) + '</a>';
    }
    return escaparHtml(limpio);
  }

  function normalizarClausulasContrato(clausulas) {
    let lista = [];
    if (Array.isArray(clausulas)) {
      lista = clausulas.map(function (c) { return String(c || '').trim(); }).filter(Boolean);
    } else if (typeof clausulas === 'string' && clausulas.trim()) {
      lista = clausulas
        .split(/(?=\d+\.\s)/)
        .map(function (c) { return c.trim(); })
        .filter(Boolean);
    }
    return lista;
  }

  function htmlClausulasContrato(clausulas) {
    const lista = normalizarClausulasContrato(clausulas);
    if (!lista.length) {
      return '<p class="contract-clause-text">' + escaparHtml(t('sinClausulas', 'Sin cláusulas registradas.')) + '</p>';
    }
    return '<ul class="contract-clauses-list">' +
      lista.map(function (item) {
        const match = item.match(/^(\d+\.\s*[A-ZÁÉÍÓÚÑ0-9 _/-]+:)\s*(.*)$/s);
        if (match) {
          return '<li class="contract-clause-item">' +
            '<span class="contract-clause-title">' + escaparHtml(match[1]) + '</span> ' +
            '<span class="contract-clause-body">' + escaparHtml(match[2]) + '</span>' +
          '</li>';
        }
        return '<li class="contract-clause-item"><span class="contract-clause-body">' + escaparHtml(item) + '</span></li>';
      }).join('') +
    '</ul>';
  }

  function htmlMensajePostulacion(mensaje) {
    const texto = String(mensaje || '').trim();
    if (!texto) {
      return '<div class="contract-message-plain">' + escaparHtml(t('sinMensaje', 'Sin mensaje')) + '</div>';
    }
    const regex = /(CARTA DE PRESENTACIÓN|EXPERIENCIA|PORTAFOLIO\/ENLACE):/gi;
    if (!regex.test(texto)) {
      return '<div class="contract-message-plain">' + escaparHtml(texto) + '</div>';
    }
    const partes = texto.split(/(CARTA DE PRESENTACIÓN|EXPERIENCIA|PORTAFOLIO\/ENLACE):\s*/i);
    const bloques = [];
    for (let i = 1; i < partes.length; i += 2) {
      const titulo = (partes[i] || '').trim();
      const contenido = (partes[i + 1] || '').trim();
      if (!contenido) continue;
      const esEnlace = /PORTAFOLIO/i.test(titulo) && esUrlHttpSegura(contenido);
      bloques.push(
        '<div class="contract-message-block">' +
          '<span class="contract-message-label">' + escaparHtml(titulo) + '</span>' +
          '<div class="contract-message-body">' + (esEnlace ? htmlEnlaceSeguro(contenido) : escaparHtml(contenido)) + '</div>' +
        '</div>'
      );
    }
    if (!bloques.length) {
      return '<div class="contract-message-plain">' + escaparHtml(texto) + '</div>';
    }
    return '<div class="contract-message-blocks">' + bloques.join('') + '</div>';
  }

  function htmlPerfilProfesionalContrato(contrato) {
    const perfil = contrato.perfil_profesional;
    if (!perfil) {
      return '<div class="contract-clause-box">' + escaparHtml(t('contratoSinEvidenciaPerfil', 'Contrato anterior sin evidencia de perfil conservada.')) + '</div>';
    }
    const estadoNota = contrato.hash_documento
      ? t('datosConservadosFirma', 'Datos conservados en la primera firma.')
      : t('vistaPreviaFirma', 'Vista previa: se conservará en la primera firma.');
    const habilidadesRaw = String(perfil.habilidades || '').trim();
    const habilidadesHtml = habilidadesRaw
      ? '<div class="contract-skill-list">' +
          habilidadesRaw.split(',').map(function (s) { return s.trim(); }).filter(Boolean).map(function (skill) {
            return '<span class="contract-skill-chip">' + escaparHtml(skill) + '</span>';
          }).join('') +
        '</div>'
      : '<span class="contract-profile-empty">' + escaparHtml(t('noRegistradas', 'No registradas')) + '</span>';

    return '<div class="contract-clause-box contract-profile-box">' +
      '<div class="contract-section-heading">' + escaparHtml(t('perfilPostulacionPrefix', 'Perfil profesional de la postulación #')) + escaparHtml(perfil.postulacion_id) + '</div>' +
      '<p class="contract-profile-note">' + escaparHtml(estadoNota) + '</p>' +
      '<div class="contract-profile-grid">' +
        '<div class="contract-profile-field">' +
          '<span class="contract-profile-label">' + escaparHtml(t('etiquetaNombre', 'Nombre:').replace(/:$/, '')) + '</span>' +
          '<span class="contract-profile-value">' + escaparHtml(perfil.nombre) + '</span>' +
        '</div>' +
        '<div class="contract-profile-field">' +
          '<span class="contract-profile-label">' + escaparHtml(t('etiquetaSena', 'SENA:').replace(/:$/, '')) + '</span>' +
          '<span class="contract-profile-value">' + escaparHtml(perfil.estado_verificacion) + ' · ' + escaparHtml(perfil.condicion_sena) + '</span>' +
        '</div>' +
        '<div class="contract-profile-field">' +
          '<span class="contract-profile-label">' + escaparHtml(t('etiquetaPrograma', 'Programa:').replace(/:$/, '')) + '</span>' +
          '<span class="contract-profile-value">' + escaparHtml(perfil.programa_formacion || t('noRegistrado', 'No registrado')) + '</span>' +
        '</div>' +
        '<div class="contract-profile-field">' +
          '<span class="contract-profile-label">' + escaparHtml(t('etiquetaFicha', 'Ficha:').replace(/:$/, '')) + '</span>' +
          '<span class="contract-profile-value">' + escaparHtml(perfil.ficha || t('noRegistrada', 'No registrada')) + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="contract-profile-row">' +
        '<span class="contract-profile-label">' + escaparHtml(t('etiquetaHabilidades', 'Habilidades:').replace(/:$/, '')) + '</span>' +
        habilidadesHtml +
      '</div>' +
      (perfil.portafolio_url
        ? '<div class="contract-profile-row">' +
            '<span class="contract-profile-label">' + escaparHtml(t('etiquetaPortafolio', 'Portafolio:').replace(/:$/, '')) + '</span>' +
            '<div class="contract-profile-value">' + htmlEnlaceSeguro(perfil.portafolio_url) + '</div>' +
          '</div>'
        : '') +
      '<div class="contract-profile-row">' +
        '<span class="contract-profile-label">' + escaparHtml(t('etiquetaMensajePresentacion', 'Mensaje de presentación:').replace(/:$/, '')) + '</span>' +
        htmlMensajePostulacion(perfil.mensaje_postulacion) +
      '</div>' +
    '</div>';
  }

  function htmlDocumentoContrato(contrato) {
    const hashDocumento = contrato.hash_documento
      ? escaparHtml(contrato.hash_documento)
      : escaparHtml(t('hashPrimeraFirma', 'Se generará con la primera firma electrónica'));
    const hashContrato = contrato.hash_contrato ? escaparHtml(contrato.hash_contrato) : escaparHtml(t('sinSelloDefinitivo', 'Sin sello definitivo'));
    const comentarios = contrato.comentarios_adicionales
      ? '<div class="contract-clause-box"><div class="contract-section-heading">' + escaparHtml(t('comentariosAdicionales', 'Comentarios adicionales')) + '</div><p class="contract-clause-text">' +
        escaparHtml(contrato.comentarios_adicionales) + '</p></div>'
      : '';
    const evidenciaPerfil = htmlPerfilProfesionalContrato(contrato);

    let bloqueTerminos = '';
    if (contrato.puede_editar) {
      const opcionesMonedas = (contrato.monedas || []).map(function (m) {
        return '<option value="' + escaparHtml(m.valor) + '" ' + (m.valor === contrato.moneda ? 'selected' : '') + '>' + escaparHtml(m.label) + '</option>';
      }).join('');

      const opcionesFormas = (contrato.formas_pago || []).map(function (f) {
        return '<option value="' + escaparHtml(f.valor) + '" ' + (f.valor === contrato.forma_pago ? 'selected' : '') + '>' + escaparHtml(f.label) + '</option>';
      }).join('');

      const opcionesMedios = (contrato.medios_pago || []).map(function (p) {
        return '<option value="' + escaparHtml(p.valor) + '" ' + (p.valor === contrato.medio_pago ? 'selected' : '') + '>' + escaparHtml(p.label) + '</option>';
      }).join('');

      bloqueTerminos = '' +
        '<div class="contract-edit-terms-box" style="background:var(--corp-surface); border:1px solid var(--corp-brand); border-radius:var(--corp-radius); padding:20px; margin-bottom:18px;">' +
          '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">' +
            '<div style="display:flex; align-items:center; gap:8px; font-size:13px; font-weight:700; color:var(--corp-brand);">' +
              '<i data-lucide="sliders-horizontal"></i>' +
              '<span>' + t('definicionTerminos', 'Definición de Términos Contractuales (Editable por la Empresa)') + '</span>' +
            '</div>' +
            '<span class="badge" style="background:var(--corp-brand-light); color:var(--corp-brand); font-size:12px; padding:3px 8px; border-radius:10px;">' + t('faseNegociacion', 'Fase de Negociación') + '</span>' +
          '</div>' +
          '<form id="formEditarTerminosContrato" method="post" action="' + escaparHtml(contrato.url_editar) + '">' +
            '<div style="display:grid; grid-template-columns: 2fr 1fr; gap:12px; margin-bottom:12px;">' +
              '<div class="form-group-corp" style="margin-bottom:0;">' +
                '<label class="form-label-corp" for="contrato_monto">' + escaparHtml(t('montoContrato', 'Monto del Contrato')) + '</label>' +
                '<input type="number" id="contrato_monto" step="0.01" min="0" name="monto" class="form-input-corp" value="' + escaparHtml(contrato.monto) + '" required placeholder="' + escaparHtml(t('ejMontoContrato', 'Ej: 2500000')) + '">' +
              '</div>' +
              '<div class="form-group-corp" style="margin-bottom:0;">' +
                '<label class="form-label-corp" for="contrato_moneda">' + escaparHtml(t('monedaLabel', 'Moneda')) + '</label>' +
                '<select id="contrato_moneda" name="moneda" class="form-input-corp">' + opcionesMonedas + '</select>' +
              '</div>' +
            '</div>' +
            '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:12px;">' +
              '<div class="form-group-corp" style="margin-bottom:0;">' +
                '<label class="form-label-corp" for="contrato_forma_pago">' + escaparHtml(t('formaPagoCronograma', 'Forma de Pago (Cronograma)')) + '</label>' +
                '<select id="contrato_forma_pago" name="forma_pago" class="form-input-corp">' + opcionesFormas + '</select>' +
              '</div>' +
              '<div class="form-group-corp" style="margin-bottom:0;">' +
                '<label class="form-label-corp" for="contrato_medio_pago">' + escaparHtml(t('medioPagoLabel', 'Medio de Pago')) + '</label>' +
                '<select id="contrato_medio_pago" name="medio_pago" class="form-input-corp">' + opcionesMedios + '</select>' +
              '</div>' +
            '</div>' +
            '<div class="form-group-corp" style="margin-bottom:14px;">' +
              '<label class="form-label-corp" for="contrato_comentarios">' + escaparHtml(t('comentariosCondicionesLabel', 'Comentarios adicionales o condiciones de entrega (Opcional)')) + '</label>' +
              '<textarea id="contrato_comentarios" name="comentarios_adicionales" class="form-input-corp" rows="2" placeholder="' + escaparHtml(t('comentariosCondicionesPlaceholder', 'Notas sobre desembolsos, cuentas o entregas intermedias...')) + '">' + escaparHtml(contrato.comentarios_adicionales || '') + '</textarea>' +
            '</div>' +
            '<div style="display:flex; justify-content:flex-end;">' +
              '<button type="submit" class="btn-corp-primary btn-sm">' +
                '<i data-lucide="save"></i>' +
                '<span>' + escaparHtml(t('guardarTerminosContractuales', 'Guardar Términos Contractuales')) + '</span>' +
              '</button>' +
            '</div>' +
          '</form>' +
        '</div>';
    } else {
      bloqueTerminos = '' +
        '<div class="contract-sealed-notice">' +
          '<i data-lucide="lock" style="width:14px; height:14px; flex-shrink:0; color:var(--corp-slate-400);"></i>' +
          '<span>' + escaparHtml(t('terminosSellados', 'Términos sellados: Este contrato ya cuenta con firmas electrónicas o la negociación concluyó; los términos económicos no pueden alterarse.')) + '</span>' +
        '</div>' +
        '<div class="contract-terms-grid" style="grid-template-columns: repeat(3, 1fr);">' +
          '<div class="contract-term-box"><span class="contract-term-label">' + escaparHtml(t('montoAcordado', 'Monto acordado')) + '</span>' +
            '<div class="contract-term-value">' + escaparHtml(contrato.monto_formateado) + '</div>' +
            '<span class="contract-term-sub">' + escaparHtml(t('monedaPrefix', 'Moneda:')) + ' ' + escaparHtml(contrato.moneda) + '</span></div>' +
          '<div class="contract-term-box"><span class="contract-term-label">' + escaparHtml(t('formaPagoLabel', 'Forma de pago')) + '</span>' +
            '<div class="contract-term-value">' + escaparHtml(contrato.forma_pago_display) + '</div>' +
            '<span class="contract-term-sub">' + escaparHtml(t('cronogramaLiquidacion', 'Cronograma de liquidación')) + '</span></div>' +
          '<div class="contract-term-box"><span class="contract-term-label">' + escaparHtml(t('medioPagoLowerLabel', 'Medio de pago')) + '</span>' +
            '<div class="contract-term-value" style="font-size:14px; font-weight:700; color:var(--corp-slate-900);">' + escaparHtml(contrato.medio_pago_display) + '</div>' +
            '<span class="contract-term-sub">' + escaparHtml(t('canalAcordado', 'Canal acordado')) + '</span></div>' +
        '</div>';
    }

    const bloqueHashes = (contrato.hash_documento || contrato.hash_contrato)
      ? '<div class="contract-doc-hashes">' +
          (contrato.hash_documento ? '<span>Doc: ' + hashDocumento + '</span>' : '') +
          (contrato.hash_contrato ? '<span>Firma: ' + hashContrato + '</span>' : '') +
        '</div>'
      : '';

    return '' +
      '<article class="contract-doc-paper">' +
        '<header class="contract-doc-header">' +
          '<div>' +
            '<div class="contract-doc-eyebrow">' + escaparHtml(t('expedienteDigitalPrefix', 'Expediente digital CD-')) + escaparHtml(contrato.id) + '</div>' +
            '<h3 class="contract-doc-title">' + escaparHtml(t('acuerdoServiciosProfesionales', 'Acuerdo Digital de Servicios Profesionales')) + '</h3>' +
            '<div class="contract-doc-project">' + escaparHtml(contrato.proyecto_titulo) + '</div>' +
          '</div>' +
          '<span class="contract-estado-badge estado-' + escaparHtml(contrato.estado) + '">' +
            escaparHtml(contrato.estado_display) + '</span>' +
        '</header>' +
        bloqueHashes +
        '<div class="contract-doc-parties">' +
          '<div class="contract-party-card"><span class="contract-party-label">' + escaparHtml(t('empresaContratante', 'Empresa contratante')) + '</span>' +
            '<strong>' + escaparHtml(contrato.empresa_nombre) + '</strong></div>' +
          '<div class="contract-party-card"><span class="contract-party-label">' + escaparHtml(t('desarrolladorContratado', 'Desarrollador contratado')) + '</span>' +
            '<strong>' + escaparHtml(contrato.desarrollador_nombre) + '</strong></div>' +
          '<div class="contract-party-card"><span class="contract-party-label">' + escaparHtml(t('proyectoLabel', 'Proyecto')) + '</span>' +
            '<strong>' + escaparHtml(contrato.proyecto_titulo) + '</strong></div>' +
        '</div>' +
        bloqueTerminos +
        evidenciaPerfil +
        '<div class="contract-clause-box">' +
          '<div class="contract-section-heading">' + escaparHtml(t('clausulasContractuales', 'Cláusulas contractuales')) + '</div>' +
          htmlClausulasContrato(contrato.clausulas) +
        '</div>' +
        comentarios +
        '<div class="contract-signatures-row">' +
          bloqueFirmaParte(t('firmaEmpresa', 'Firma de la empresa'), contrato.empresa_nombre, contrato.firmado_empresa, contrato.fecha_firma_empresa) +
          bloqueFirmaParte(t('firmaDesarrollador', 'Firma del desarrollador'), contrato.desarrollador_nombre, contrato.firmado_desarrollador, contrato.fecha_firma_desarrollador) +
        '</div>' +
        '<div class="contract-doc-disclaimer"><i data-lucide="info"></i><span>' +
          escaparHtml(contrato.disclaimer) + '</span></div>' +
        htmlFormularioFirma(contrato) +
      '</article>';
  }

  function pintarEstadoFilaContrato(contrato) {
    const fila = document.querySelector('[data-contrato-row="' + contrato.id + '"]');
    if (!fila) return;
    const mapa = [
      { rol: 'firma-empresa', firmado: contrato.firmado_empresa, etiqueta: t('etiquetaEmpresa', 'Empresa') },
      { rol: 'firma-dev', firmado: contrato.firmado_desarrollador, etiqueta: t('etiquetaDev', 'Dev') },
    ];
    mapa.forEach(function (item) {
      const badge = fila.querySelector('[data-role="' + item.rol + '"]');
      if (!badge) return;
      badge.classList.toggle('is-signed', !!item.firmado);
      badge.classList.toggle('is-pending', !item.firmado);
      const span = badge.querySelector('span');
      if (span) span.textContent = item.etiqueta + ': ' + (item.firmado ? t('firmado', 'Firmado') : t('pendiente', 'Pendiente'));
      const icono = badge.querySelector('.lucide, svg, [data-lucide]');
      if (icono && icono.parentNode) {
        const nuevoIcono = document.createElement('i');
        nuevoIcono.setAttribute('data-lucide', item.firmado ? 'check-circle-2' : 'clock');
        icono.parentNode.replaceChild(nuevoIcono, icono);
      }
    });
    const estadoBadge = fila.querySelector('[data-role="estado-contrato"]');
    if (estadoBadge) {
      estadoBadge.className = 'contract-estado-badge estado-' + contrato.estado;
      estadoBadge.textContent = contrato.estado_display;
    }
    const montoEl = fila.querySelector('.contrato-monto');
    if (montoEl && contrato.monto_formateado) {
      montoEl.textContent = contrato.monto_formateado;
    }
    const hashPill = fila.querySelector('[data-role="hash-contrato"]');
    if (hashPill) {
      hashPill.textContent = contrato.hash_contrato ? contrato.hash_contrato.slice(0, 12) + '…' : t('sinSello', 'Sin sello');
    }
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  window.abrirChatEnCentro = function (event, receptorId, proyectoId) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    ejecutarSwitchTabDOM('centro-chat');
    try {
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, '', '#centro-chat');
      }
    } catch (e) {}

    const list = document.querySelector('#centro-chat [data-chat-list]');
    if (!list) return;
    const selectorExacto = '.jd-chat-item[data-receptor="' + String(receptorId) + '"][data-proyecto="' + String(proyectoId) + '"]';
    const item = list.querySelector(selectorExacto) || list.querySelector('.jd-chat-item[data-receptor="' + String(receptorId) + '"]');
    if (item) {
      item.click();
    }
  };

  window.abrirModalContrato = function (event, contratoId) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (!contratoId) return;

    const modal = document.getElementById('modalContratoDigital');
    const bodyEl = document.getElementById('contratoModalBody');
    if (!modal || !bodyEl) return;

    window._contratoAbiertoId = contratoId;
    bodyEl.innerHTML = '<div class="drawer-loading"><i data-lucide="loader-circle" class="corp-spin"></i><p>' + t('cargandoContrato', 'Cargando expediente contractual...') + '</p></div>';
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
    modal.classList.add('open');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    fetch(endpointContratoDigital(contratoId), {
      headers: { 'Accept': 'application/json' },
    })
      .then(function (res) {
        if (!res.ok) throw new Error('No se pudo cargar el contrato');
        return res.json();
      })
      .then(function (contrato) {
        bodyEl.innerHTML = htmlDocumentoContrato(contrato);
        pintarEstadoFilaContrato(contrato);
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
        animarExpedienteContrato(bodyEl, contrato);
      })
      .catch(function () {
        bodyEl.innerHTML = '<div class="activity-empty" style="padding:44px 20px;">' +
          '<i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i>' +
          '<p>' + t('errorContrato', 'No se pudo cargar el expediente contractual. Intenta de nuevo.') + '</p></div>';
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      });
  };

  window.cerrarModalContrato = function () {
    const modal = document.getElementById('modalContratoDigital');
    if (modal) {
      modal.classList.remove('open');
      modal.style.display = 'none';
    }
    document.body.style.overflow = '';
    const bodyEl = document.getElementById('contratoModalBody');
    if (bodyEl) {
      bodyEl.innerHTML = '<div class="drawer-loading"><i data-lucide="loader-circle" class="corp-spin"></i><p>' + t('cargandoContrato', 'Cargando expediente contractual...') + '</p></div>';
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    }
    window._contratoAbiertoId = null;
  };

  // --- 2.6 Buscador + filtro de modalidad en tiempo real de Ofertas ---
  let filtroModalidadOfertas = 'todas';
  let queryOfertas = '';

  function aplicarFiltrosOfertas() {
    const cards = document.querySelectorAll('.offers-grid-corp .offer-card-corp');
    let visibles = 0;

    cards.forEach(function (card) {
      const text = card.textContent.toLowerCase();
      const coincideTexto = !queryOfertas || text.indexOf(queryOfertas) !== -1;
      const modalidad = (card.dataset.modalidad || 'remoto').toLowerCase();
      const coincideModalidad = filtroModalidadOfertas === 'todas' || modalidad === filtroModalidadOfertas;
      const visible = coincideTexto && coincideModalidad;

      card.style.display = visible ? '' : 'none';
      if (visible) visibles += 1;
    });

    const sinResultados = document.getElementById('ofertasSinResultados');
    if (sinResultados) {
      sinResultados.style.display = (visibles === 0 && cards.length > 0) ? 'block' : 'none';
    }
  }

  window.filtrarOfertasEnTiempoReal = function (input) {
    queryOfertas = ((input && input.value) || '').toLowerCase().trim();
    aplicarFiltrosOfertas();
  };

  window.filtrarOfertasPorModalidad = function (valor, btn) {
    filtroModalidadOfertas = (valor || 'todas').toLowerCase();

    document.querySelectorAll('.offers-filter-bar .offers-filter-pill').forEach(function (pill) {
      pill.classList.toggle('is-active', pill === btn);
    });

    aplicarFiltrosOfertas();
  };
  // --- 2.7 Modal de Edición de Proyecto In-Situ (Mis Ofertas) ---
  window.abrirModalEditarProyecto = function (event, id, actionUrl, titulo, descripcion, tipo_solucion, prioridad, modalidad, ciudad, fecha_limite, vacantes, fecha_cumplimiento, soloBasicos) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    const modal = document.getElementById('modalEditarProyecto');
    const form = document.getElementById('formEditarProyecto');

    if (form) form.action = actionUrl;

    const tituloInput = document.getElementById('edit_titulo');
    if (tituloInput) tituloInput.value = titulo || '';

    const descInput = document.getElementById('edit_descripcion');
    if (descInput) descInput.value = descripcion || '';

    const tipoSelect = document.getElementById('edit_tipo_solucion');
    if (tipoSelect && tipo_solucion) tipoSelect.value = tipo_solucion;

    const prioSelect = document.getElementById('edit_prioridad');
    if (prioSelect && prioridad) prioSelect.value = prioridad;

    const modSelect = document.getElementById('edit_modalidad');
    if (modSelect && modalidad) {
      modSelect.value = modalidad;
      if (typeof window.toggleCiudadProyecto === 'function') {
        window.toggleCiudadProyecto(modSelect, 'edit_ciudad_group');
      }
    }

    const ciudadInput = document.getElementById('edit_ciudad');
    if (ciudadInput) ciudadInput.value = ciudad || '';

    const fechaInput = document.getElementById('edit_fecha_limite');
    if (fechaInput) fechaInput.value = fecha_limite || '';

    const cumplimientoInput = document.getElementById('edit_fecha_cumplimiento');
    if (cumplimientoInput) cumplimientoInput.value = fecha_cumplimiento || '';

    const vacantesInput = document.getElementById('edit_vacantes');
    if (vacantesInput) vacantesInput.value = vacantes || '1';

    const restringido = Boolean(soloBasicos);
    [descInput, tipoSelect, modSelect, ciudadInput, cumplimientoInput, vacantesInput, document.getElementById('edit_fecha_limite_display')].forEach(function (el) {
      if (el) el.disabled = restringido;
    });

    if (typeof window.setDatepickerValue === 'function') {
      window.setDatepickerValue('datepicker-editar', fecha_limite || '');
    }

    if (modal) {
      modal.classList.add('open');
      modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
      if (tituloInput) tituloInput.focus();
    }

    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  window.cerrarModalEditarProyecto = function () {
    const modal = document.getElementById('modalEditarProyecto');
    if (modal) {
      modal.classList.remove('open');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  };

  window.abrirModalDisputa = function (event, actionUrl, titulo) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    document.querySelectorAll('.dev-more-actions[open]').forEach(function (d) {
      d.removeAttribute('open');
    });

    // Si se invoca sin URL (botón "Iniciar Nueva Disputa"), abrir selector de proyecto
    if (!actionUrl) {
      const selectorModal = document.getElementById('modalNuevaDisputa');
      if (selectorModal) {
        selectorModal.classList.add('open');
        selectorModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
      }
      return;
    }

    const modal = document.getElementById('modalReportarDisputa');
    const subtituloEl = document.getElementById('modalDisputaSubtitulo');
    const bodyEl = document.getElementById('modalDisputaBody');
    if (!modal || !bodyEl) return;

    if (subtituloEl) subtituloEl.textContent = titulo || '';
    bodyEl.innerHTML = '<div class="drawer-loading" style="padding:36px 16px;"><i data-lucide="loader-circle" class="corp-spin"></i><p>' + t('cargandoFormularioDisputa', 'Cargando formulario de mediación...') + '</p></div>';

    modal.classList.add('open');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }

    fetch(actionUrl)
      .then(function (res) {
        if (!res.ok) throw new Error('Error al cargar el formulario de disputa.');
        return res.text();
      })
      .then(function (html) {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const form = doc.getElementById('form-disputa');
        if (!form) throw new Error('Formulario no disponible.');

        form.setAttribute('action', actionUrl);
        form.style.background = 'transparent';
        form.style.border = '0';
        form.style.padding = '0';
        form.style.boxShadow = 'none';

        const cancelLink = form.querySelector('.disp-actions a');
        if (cancelLink) {
          const cancelBtn = document.createElement('button');
          cancelBtn.type = 'button';
          cancelBtn.className = 'btn-corp-action secondary';
          cancelBtn.textContent = cancelLink.textContent || 'Cancelar';
          cancelBtn.addEventListener('click', window.cerrarModalDisputa);
          cancelLink.replaceWith(cancelBtn);
        }

        bodyEl.innerHTML = '';
        bodyEl.appendChild(form);

        const textarea = form.querySelector('#motivo');
        const charCount = form.querySelector('#char-count');
        if (textarea && charCount) {
          const syncCounter = function () {
            charCount.textContent = String((textarea.value || '').trim().length);
          };
          textarea.addEventListener('input', syncCounter);
          syncCounter();
        }

        const disputaChecks = form.querySelectorAll('#confirma_intento_previo, #confirma_gravedad, #acepta_sanciones');
        const disputaSubmitBtn = form.querySelector('#btn-submit-disputa');
        if (disputaChecks.length > 0 && disputaSubmitBtn) {
          const syncDisputaSubmit = function () {
            const allChecked = Array.prototype.every.call(disputaChecks, function (cb) { return cb.checked; });
            disputaSubmitBtn.disabled = !allChecked;
          };
          disputaChecks.forEach(function (cb) { cb.addEventListener('change', syncDisputaSubmit); });
          syncDisputaSubmit();
        }

        form.addEventListener('submit', function (ev) {
          ev.preventDefault();
          const errBox = form.querySelector('#disputa-error');
          const submitBtn = form.querySelector('button[type="submit"]');
          const oldBtnHtml = submitBtn ? submitBtn.innerHTML : '';

          if (errBox) {
            errBox.style.display = 'none';
            errBox.textContent = '';
          }
          if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Enviando...';
          }

          fetch(actionUrl, {
            method: 'POST',
            body: new FormData(form),
            headers: {
              'Accept': 'application/json',
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': csrfTokenActual(),
            },
          })
            .then(function (res) {
              return res.json().then(function (data) {
                return { ok: res.ok, data: data };
              }).catch(function () {
                return { ok: res.ok, data: { ok: res.ok, mensaje: res.ok ? 'Disputa abierta.' : 'No se pudo abrir la disputa.' } };
              });
            })
            .then(function (result) {
              if (!result.ok || result.data.ok === false) {
                if (errBox) {
                  errBox.textContent = result.data.mensaje || 'Revisa los campos obligatorios.';
                  errBox.style.display = 'block';
                }
                if (submitBtn) {
                  submitBtn.disabled = false;
                  submitBtn.innerHTML = oldBtnHtml;
                }
                return;
              }
              window.cerrarModalDisputa();
              mostrarToastCorp(result.data.mensaje || 'Disputa abierta exitosamente.');
              setTimeout(function () {
                window.location.hash = 'desarrollo';
                window.location.reload();
              }, 900);
            })
            .catch(function () {
              if (errBox) {
                errBox.textContent = 'Error de conexión al enviar la disputa.';
                errBox.style.display = 'block';
              }
              if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = oldBtnHtml;
              }
            });
        });

        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      })
      .catch(function () {
        bodyEl.innerHTML = '<div class="activity-empty" style="padding:36px 16px;"><i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i><p>No se pudo cargar el formulario de disputa.</p></div>';
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      });
  };

  window.cerrarModalDisputa = function () {
    ['modalReportarDisputa', 'modalNuevaDisputa'].forEach(function (id) {
      const m = document.getElementById(id);
      if (m) {
        m.classList.remove('open');
        m.style.display = 'none';
      }
    });
    document.body.style.overflow = '';
  };

  // --- 2.7b Modal Profesional de Calificar Equipo (100% in-situ) ---
  window.cerrarModalCalificar = function () {
    const modal = document.getElementById('modalCalificarEquipo');
    if (modal) {
      modal.classList.remove('open');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  };

  window.abrirModalCalificar = function (event, actionUrl, titulo) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    const modal = document.getElementById('modalCalificarEquipo');
    const subEl = document.getElementById('modalCalificarSubtitulo');
    const bodyEl = document.getElementById('modalCalificarBody');
    if (!modal || !bodyEl || !actionUrl) return;

    if (subEl) subEl.textContent = titulo || '';
    bodyEl.innerHTML = '<div class="drawer-loading" style="padding:36px 16px;"><div class="corp-spinner"></div><p>' + escaparHtml(t('cargandoCalificacion', 'Cargando formulario de calificación...')) + '</p></div>';

    modal.classList.add('open');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    fetch(actionUrl)
      .then(function (res) {
        if (!res.ok) throw new Error('Error al cargar calificación.');
        return res.text();
      })
      .then(function (html) {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const origForm = doc.querySelector('main form[method="post"]');
        if (!origForm) {
          bodyEl.innerHTML = '<div class="drawer-loading" style="padding:28px 16px;"><p>' + escaparHtml(t('todosCalificados', 'Todos los colaboradores de este proyecto ya fueron calificados.')) + '</p><button type="button" class="btn-corp-action secondary" onclick="cerrarModalCalificar()" style="margin-top:12px;">' + escaparHtml(t('cerrar', 'Cerrar')) + '</button></div>';
          return;
        }

        const csrfInput = origForm.querySelector('input[name="csrfmiddlewaretoken"]');
        const csrfVal = csrfInput ? csrfInput.value : '';
        const devNameEl = doc.querySelector('.card strong');
        const devName = devNameEl ? devNameEl.textContent.trim() : '';
        const restantesEl = doc.querySelector('.msg-error');
        const restantesTxt = restantesEl ? restantesEl.textContent.trim() : '';
        const hasStars = !!origForm.querySelector('.star-rating');

        if (!hasStars) {
          bodyEl.innerHTML = '<form id="formCalificarModal" method="post">' +
            '<input type="hidden" name="csrfmiddlewaretoken" value="' + escaparHtml(csrfVal) + '">' +
            '<p style="font-size:13.5px; color:var(--corp-slate-600); margin:0 0 18px;">' + escaparHtml(t('confirmarCierreProyecto', 'Todos los colaboradores han sido calificados. Confirma el cierre oficial del proyecto.')) + '</p>' +
            '<div class="modal-footer-corp"><button type="button" class="btn-corp-action secondary" onclick="cerrarModalCalificar()">' + escaparHtml(t('cancelar', 'Cancelar')) + '</button><button type="submit" class="btn-corp-primary">' + escaparHtml(t('confirmarFinalizar', 'Confirmar y Finalizar')) + '</button></div></form>';
        } else {
          bodyEl.innerHTML = '' +
            (devName ? '<div class="calificar-dev-summary"><div class="calificar-dev-label">' + escaparHtml(t('calificandoA', 'Calificando a')) + '</div><div class="calificar-dev-name">' + escaparHtml(devName) + '</div>' + (restantesTxt ? '<div class="calificar-dev-restantes">' + escaparHtml(restantesTxt) + '</div>' : '') + '</div>' : '') +
            '<form id="formCalificarModal" method="post">' +
              '<input type="hidden" name="csrfmiddlewaretoken" value="' + escaparHtml(csrfVal) + '">' +
              '<div class="form-group-corp" style="text-align:center;">' +
                '<div class="form-label-corp" style="margin-bottom:8px;">' + escaparHtml(t('puntuacionDev', 'Puntuación del Desarrollador')) + '</div>' +
                '<div class="corp-star-rating">' +
                  '<input type="radio" name="puntuacion" value="5" id="modalStar5" required><label for="modalStar5" title="5">★</label>' +
                  '<input type="radio" name="puntuacion" value="4" id="modalStar4"><label for="modalStar4" title="4">★</label>' +
                  '<input type="radio" name="puntuacion" value="3" id="modalStar3"><label for="modalStar3" title="3">★</label>' +
                  '<input type="radio" name="puntuacion" value="2" id="modalStar2"><label for="modalStar2" title="2">★</label>' +
                  '<input type="radio" name="puntuacion" value="1" id="modalStar1"><label for="modalStar1" title="1">★</label>' +
                '</div>' +
              '</div>' +
              '<div class="form-group-corp">' +
                '<label class="form-label-corp" for="modalCalificarComentario">' + escaparHtml(t('comentariosAdicionales', 'Comentarios sobre el desempeño')) + '</label>' +
                '<textarea id="modalCalificarComentario" name="comentario" class="form-input-corp" rows="4" required minlength="20" maxlength="2000" placeholder="' + escaparHtml(t('placeholderCalificacion', 'Describe tu experiencia trabajando con este desarrollador (mínimo 20 caracteres)...')) + '"></textarea>' +
              '</div>' +
              '<div id="calificarModalError" style="display:none; color:var(--corp-danger); font-size:12.5px; font-weight:600; margin-bottom:10px;"></div>' +
              '<div class="modal-footer-corp">' +
                '<button type="button" class="btn-corp-action secondary" onclick="cerrarModalCalificar()">' + escaparHtml(t('cancelar', 'Cancelar')) + '</button>' +
                '<button type="submit" class="btn-corp-primary"><i data-lucide="star"></i><span>' + escaparHtml(t('guardarCalificacion', 'Enviar Calificación')) + '</span></button>' +
              '</div>' +
            '</form>';
        }

        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }

        const formEl = document.getElementById('formCalificarModal');
        if (formEl) {
          formEl.addEventListener('submit', function (ev) {
            ev.preventDefault();
            const submitBtn = formEl.querySelector('button[type="submit"]');
            const errBox = document.getElementById('calificarModalError');
            if (errBox) errBox.style.display = 'none';
            if (submitBtn) submitBtn.disabled = true;

            fetch(actionUrl, {
              method: 'POST',
              body: new FormData(formEl),
              headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
              .then(function (r) {
                if (r.url && r.url.indexOf('/proyectos/finalizar/') !== -1 && r.ok) {
                  // Aún quedan otros colaboradores por calificar o hubo validación
                  window.abrirModalCalificar(null, actionUrl, titulo);
                  return;
                }
                window.cerrarModalCalificar();
                mostrarToastCorp(t('calificacionGuardada', '¡Calificación enviada con éxito!'));
                setTimeout(function () {
                  window.location.hash = 'historial';
                  window.location.reload();
                }, 700);
              })
              .catch(function () {
                if (submitBtn) submitBtn.disabled = false;
                if (errBox) {
                  errBox.textContent = t('errorCalificar', 'No se pudo enviar la calificación. Intenta de nuevo.');
                  errBox.style.display = 'block';
                }
              });
          });
        }
      })
      .catch(function () {
        bodyEl.innerHTML = '<div class="drawer-loading" style="padding:28px 16px;"><p style="color:var(--corp-danger);">' + escaparHtml(t('errorCargarCalificacion', 'No se pudo cargar el formulario de calificación.')) + '</p></div>';
      });
  };

  // --- 2.8 Modal de Confirmación Bonito para Retirar Oferta ---
  window._formRetiroPendiente = null;

  window.confirmarRetiroOferta = function (event, form, titulo) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    window._formRetiroPendiente = form;

    const modal = document.getElementById('modalConfirmarRetiro');
    const titleEl = document.getElementById('nombreOfertaRetirar');

    if (titleEl) titleEl.textContent = titulo || t('estaConvocatoria', 'esta convocatoria');
    if (modal) {
      modal.classList.add('open');
      modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
    }

    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  window.cerrarModalConfirmarRetiro = function () {
    const modal = document.getElementById('modalConfirmarRetiro');
    if (modal) {
      modal.classList.remove('open');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
    window._formRetiroPendiente = null;
  };

  window.ejecutarRetiroConfirmado = function () {
    if (window._formRetiroPendiente) {
      const form = window._formRetiroPendiente;
      window.cerrarModalConfirmarRetiro();
      form.submit();
    }
  };

  // --- 2.8.1 Modal de Todas las Valoraciones y Reseñas ---
  window._filtroEstrellasActual = 0;
  window._filtroTextoActual = '';

  window.abrirModalTodasValoraciones = function () {
    const modal = document.getElementById('modalTodasValoraciones');
    if (modal) {
      modal.classList.add('open');
      modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
      const searchInput = modal.querySelector('input');
      if (searchInput) {
        searchInput.value = '';
        window._filtroTextoActual = '';
        window._filtroEstrellasActual = 0;
        window._aplicarFiltrosResenas();
        searchInput.focus();
      }
    }
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  window.cerrarModalTodasValoraciones = function () {
    const modal = document.getElementById('modalTodasValoraciones');
    if (modal) {
      modal.classList.remove('open');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  };

  window.filtrarResenasModal = function (input) {
    window._filtroTextoActual = (input.value || '').toLowerCase().trim();
    window._aplicarFiltrosResenas();
  };

  window.filtrarPorEstrellasModal = function (stars, btn) {
    window._filtroEstrellasActual = parseInt(stars, 10) || 0;
    const parent = btn.parentElement;
    if (parent) {
      parent.querySelectorAll('.datepicker-preset-pill').forEach(function (b) {
        b.classList.remove('active');
      });
      btn.classList.add('active');
    }
    window._aplicarFiltrosResenas();
  };

  window._aplicarFiltrosResenas = function () {
    const items = document.querySelectorAll('#modalResenasFeed .modal-review-item');
    const emptyMsg = document.getElementById('noMatchResenas');
    let visibleCount = 0;

    items.forEach(function (item) {
      const itemStars = parseInt(item.getAttribute('data-stars'), 10) || 0;
      const itemText = item.textContent.toLowerCase();

      let matchStars = true;
      if (window._filtroEstrellasActual === 1) {
        matchStars = (itemStars === 1 || itemStars === 2);
      } else if (window._filtroEstrellasActual > 1) {
        matchStars = (itemStars === window._filtroEstrellasActual);
      }

      let matchText = true;
      if (window._filtroTextoActual) {
        matchText = (itemText.indexOf(window._filtroTextoActual) !== -1);
      }

      if (matchStars && matchText) {
        item.style.display = '';
        visibleCount++;
      } else {
        item.style.display = 'none';
      }
    });

    if (emptyMsg) {
      emptyMsg.style.display = (visibleCount === 0 && items.length > 0) ? 'block' : 'none';
    }
  };

  // --- 2.8.2 Filtrado de Historial en Tiempo Real (Sin recargar página) ---
  window.filtrarHistorialEnTiempoReal = function (event, estado, btn) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    // Actualizar píldora activa
    const parent = btn ? btn.closest('.segmented-filters-corp') : null;
    if (parent && btn) {
      parent.querySelectorAll('.segmented-pill').forEach(function (p) {
        p.classList.remove('is-active');
      });
      btn.classList.add('is-active');
    }

    // Filtrar tarjetas del historial
    const cards = document.querySelectorAll('[data-testid="historial-inactivos"] .history-card-corp');
    let visibleCount = 0;

    cards.forEach(function (card) {
      const cardEstado = card.getAttribute('data-historial-estado') || '';
      if (estado === 'todos' || !estado || cardEstado === estado) {
        card.style.display = '';
        visibleCount++;
      } else {
        card.style.display = 'none';
      }
    });

    // Control del empty state (evitar duplicar si el servidor ya mostró {% empty %})
    const emptyMsg = document.getElementById('historialSinResultados');
    if (emptyMsg) {
      emptyMsg.style.display = (cards.length > 0 && visibleCount === 0) ? 'block' : 'none';
    }

    // Actualizar URL de forma limpia sin recargar
    if (window.history && window.history.replaceState) {
      const url = new URL(window.location);
      url.searchParams.set('section', 'historial');
      url.searchParams.delete('historial_estado');
      url.hash = 'historial';
      window.history.replaceState(null, '', url);
    }
  };

  // --- 2.8.3 Filtrado de Disputas en Tiempo Real (Sin recargar página) ---
  window.filtrarDisputasEnTiempoReal = function (event, estado, btn) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    // Actualizar botón activo
    const parent = btn ? btn.closest('.disputas-filtros') : null;
    if (parent && btn) {
      parent.querySelectorAll('.btn').forEach(function (b) {
        b.classList.remove('btn-primary');
        b.classList.add('btn-secondary');
      });
      btn.classList.add('btn-primary');
      btn.classList.remove('btn-secondary');
    }

    // Ocultar card de disputas-filtradas del servidor si existía
    const serverFiltradas = document.querySelector('[data-testid="disputas-filtradas"]');
    if (serverFiltradas) {
      serverFiltradas.style.display = 'none';
    }

    const cardActivas = document.getElementById('cardDisputasActivas');
    const cardResueltas = document.getElementById('cardDisputasResueltas');
    const emptyMsg = document.getElementById('disputasClienteVacio');

    let totalVisibles = 0;
    let activasVisibles = 0;
    let resueltasVisibles = 0;

    const rows = document.querySelectorAll('.disputa-row-item');
    rows.forEach(function (r) {
      const rowEstado = r.getAttribute('data-disputa-row-estado') || '';
      const match = (estado === 'todos' || !estado || rowEstado === estado);
      r.style.display = match ? '' : 'none';
      if (match) {
        totalVisibles++;
        if (rowEstado === 'abierta' || rowEstado === 'en_mediacion') activasVisibles++;
        if (rowEstado === 'resuelta' || rowEstado === 'cancelada') resueltasVisibles++;
      }
    });

    if (cardActivas) {
      cardActivas.style.display = (estado === 'todos' || activasVisibles > 0) ? '' : 'none';
    }
    if (cardResueltas) {
      cardResueltas.style.display = (estado === 'todos' || resueltasVisibles > 0) ? '' : 'none';
    }
    if (emptyMsg) {
      emptyMsg.style.display = (estado !== 'todos' && totalVisibles === 0) ? 'block' : 'none';
    }

    // Actualizar URL sin recargar
    if (window.history && window.history.replaceState) {
      const url = new URL(window.location);
      url.searchParams.set('section', 'disputas');
      if (estado && estado !== 'todos') {
        url.searchParams.set('estado', estado);
      } else {
        url.searchParams.delete('estado');
      }
      url.hash = 'disputas';
      window.history.replaceState(null, '', url);
    }
  };

  // --- 2.9 Corporate DatePicker Suite (Calendario Moderno) ---
  function obtenerMeses() {
    const raw = t('mesesLista', 'Enero,Febrero,Marzo,Abril,Mayo,Junio,Julio,Agosto,Septiembre,Octubre,Noviembre,Diciembre');
    const arr = raw.split(',');
    return arr.length === 12 ? arr : ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
  }
  function formatearFechaDisplayDatepicker(d, m, y) {
    const locale = (document.documentElement.lang || '').trim() || 'es-CO';
    try {
      return new Date(y, m, d).toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
    } catch (e) {
      return d + ' ' + obtenerMeses()[m] + ', ' + y;
    }
  }
  window._corpDatepickers = {};

  function padZero(n) { return n < 10 ? '0' + n : '' + n; }

  window.initCorpDatepicker = function (pickerId, initialIso) {
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
      window.setDatepickerValue(pickerId, initialIso);
    }
    window.renderCorpDatepicker(pickerId);
  };

  window.toggleCorpDatepicker = function (pickerId) {
    const popover = document.getElementById(pickerId + '-popover');
    if (!popover) return;
    const isOpen = popover.classList.contains('is-open');
    document.querySelectorAll('.datepicker-popover').forEach(function (p) {
      p.classList.remove('is-open');
    });
    if (!isOpen) {
      if (!window._corpDatepickers[pickerId]) {
        window.initCorpDatepicker(pickerId);
      }
      window.renderCorpDatepicker(pickerId);
      popover.classList.add('is-open');
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    }
  };

  window.cerrarCorpDatepicker = function (pickerId) {
    const popover = document.getElementById(pickerId + '-popover');
    if (popover) popover.classList.remove('is-open');
  };

  window.navegarMesDatepicker = function (pickerId, delta) {
    const state = window._corpDatepickers[pickerId];
    if (!state) return;
    state.viewDate.setMonth(state.viewDate.getMonth() + delta);
    window.renderCorpDatepicker(pickerId);
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  window.aplicarPresetFecha = function (pickerId, dias) {
    const target = new Date();
    target.setDate(target.getDate() + dias);
    const iso = target.getFullYear() + '-' + padZero(target.getMonth() + 1) + '-' + padZero(target.getDate());
    window.setDatepickerValue(pickerId, iso);
    window.cerrarCorpDatepicker(pickerId);
  };

  window.seleccionarHoyDatepicker = function (pickerId) {
    const today = new Date();
    const iso = today.getFullYear() + '-' + padZero(today.getMonth() + 1) + '-' + padZero(today.getDate());
    window.setDatepickerValue(pickerId, iso);
    window.cerrarCorpDatepicker(pickerId);
  };

  window.seleccionarFechaDatepicker = function (pickerId, year, month, day) {
    const iso = year + '-' + padZero(month + 1) + '-' + padZero(day);
    window.setDatepickerValue(pickerId, iso);
    window.cerrarCorpDatepicker(pickerId);
  };

  window.setDatepickerValue = function (pickerId, isoString) {
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
  };

  window.renderCorpDatepicker = function (pickerId) {
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

      let classes = ['datepicker-day'];
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
  };

  // --- 3. Notificaciones Popover & Limpieza ---
  window.toggleNotifPopover = function (event) {
    if (event) event.stopPropagation();
    const popover = document.getElementById('notifPopover');
    const btn = document.querySelector('.notif-btn');
    if (popover) {
      const open = popover.classList.toggle('is-open');
      if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
  };

  window.closeNotifPopover = function () {
    const popover = document.getElementById('notifPopover');
    const btn = document.querySelector('.notif-btn');
    if (popover) {
      popover.classList.remove('is-open');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    }
  };

  // --- 3.1 Menú Desplegable de Usuario (Topbar) ---
  window.toggleUserMenu = function (e) {
    if (e) e.stopPropagation();
    const menu = document.getElementById('userDropdownMenu');
    const btn = document.getElementById('userMenuBtn');
    if (!menu) return;

    const isOpen = menu.style.display === 'block' || menu.classList.contains('is-open');
    if (isOpen) {
      window.closeUserMenu();
    } else {
      window.closeNotifPopover();
      menu.style.display = 'block';
      menu.classList.add('is-open');
      if (btn) btn.setAttribute('aria-expanded', 'true');
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    }
  };

  window.closeUserMenu = function () {
    const menu = document.getElementById('userDropdownMenu');
    const btn = document.getElementById('userMenuBtn');
    if (menu) {
      menu.style.display = 'none';
      menu.classList.remove('is-open');
    }
    if (btn) {
      btn.setAttribute('aria-expanded', 'false');
    }
  };

  window.limpiarNotificacionesAjax = function (event, form) {
    if (event) event.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    const oldHtml = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = t('limpiando', 'Limpiando...');
    }

    const formData = new FormData(form);
    fetch(form.action, {
      method: 'POST',
      body: formData,
      headers: {
        'Accept': 'application/json',
        'X-CSRFToken': csrfTokenActual(),
      },
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        // Vaciar la lista del popover
        const popoverBody = document.getElementById('notifPopoverBody');
        if (popoverBody) {
          popoverBody.innerHTML = '<div class="notif-popover-empty"><i data-lucide="bell-off"></i><span>' + t('sinNotificaciones', 'No hay notificaciones') + '</span></div>';
        }
        // Ocultar badge de la campana
        const notifBadge = document.querySelector('.notif-btn .notif-badge');
        if (notifBadge) {
          notifBadge.style.display = 'none';
        }
        // Ocultar botón de limpiar
        if (form) form.style.display = 'none';

        // Mostrar toast
        const toast = document.getElementById('corpToast');
        if (toast) {
          const toastSpan = toast.querySelector('span');
          if (toastSpan) toastSpan.textContent = data.message || t('notifEliminadas', 'Notificaciones eliminadas');
          toast.classList.add('show');
          setTimeout(function () { toast.classList.remove('show'); }, 3000);
        }

        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      })
      .catch(function () {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = oldHtml;
        }
        mostrarToastCorp(t('errorLimpiarNotif', 'Error al limpiar las notificaciones.'), true);
      });
  };

  // --- 4. Sidebar Móvil (Drawer) y Colapso ---
  window.toggleSidebar = function () {
    const sidebar = document.querySelector('.sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    if (sidebar) sidebar.classList.toggle('is-open');
    if (backdrop) backdrop.classList.toggle('is-open');
  };

  window.closeSidebar = function () {
    const sidebar = document.querySelector('.sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    if (sidebar) sidebar.classList.remove('is-open');
    if (backdrop) backdrop.classList.remove('is-open');
  };

  window.toggleSidebarCollapse = function () {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    const isCollapsed = sidebar.classList.toggle('is-collapsed');
    try {
      localStorage.setItem('sidebar_collapsed', isCollapsed ? '1' : '0');
    } catch (e) {}

    const btn = document.getElementById('sidebarCollapseBtn');
    if (btn) {
      btn.title = isCollapsed ? t('expandirSidebar', 'Expandir menú lateral') : t('colapsarSidebar', 'Colapsar menú (solo iconos)');
      btn.innerHTML = '<i data-lucide="' + (isCollapsed ? 'panel-left-open' : 'panel-left-close') + '"></i>';
    }

    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  window.toggleChatContextSidebar = function () {
    const chat = document.querySelector('#centro-chat .jd-chat');
    if (!chat) return;
    const isCollapsed = chat.classList.toggle('is-context-collapsed');
    try {
      localStorage.setItem('chat_context_collapsed', isCollapsed ? '1' : '0');
    } catch (e) {}

    const btn = document.getElementById('chatContextToggleBtn');
    if (btn) {
      btn.title = isCollapsed ? t('mostrarContextoProyecto', 'Mostrar contexto del proyecto') : t('ocultarContextoProyecto', 'Ocultar contexto del proyecto');
      btn.innerHTML = '<i data-lucide="' + (isCollapsed ? 'panel-right-open' : 'panel-right-close') + '"></i>';
    }

    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  // --- 5. Event Listeners y Teclado Global ---
  function initChatListResizer() {
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

  document.addEventListener('DOMContentLoaded', function () {
    initChatListResizer();
    // Backdrop del modal de proyectos
    const modal = document.getElementById('modalProyecto');
    if (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === modal) {
          window.cerrarModal();
        }
      });
    }

    // Backdrop del modal de editar perfil
    const modalPerfil = document.getElementById('modalEditarPerfil');
    if (modalPerfil) {
      modalPerfil.addEventListener('click', function (e) {
        if (e.target === modalPerfil) {
          window.cerrarModalPerfil();
        }
      });
    }

    // Backdrop del modal de editar proyecto
    const modalEditarProyecto = document.getElementById('modalEditarProyecto');
    if (modalEditarProyecto) {
      modalEditarProyecto.addEventListener('click', function (e) {
        if (e.target === modalEditarProyecto) {
          window.cerrarModalEditarProyecto();
        }
      });
    }

    // Backdrop del modal de confirmar retiro
    const modalConfirmarRetiro = document.getElementById('modalConfirmarRetiro');
    if (modalConfirmarRetiro) {
      modalConfirmarRetiro.addEventListener('click', function (e) {
        if (e.target === modalConfirmarRetiro) {
          window.cerrarModalConfirmarRetiro();
        }
      });
    }

    // Backdrop del modal de todas las valoraciones
    const modalTodasValoraciones = document.getElementById('modalTodasValoraciones');
    if (modalTodasValoraciones) {
      modalTodasValoraciones.addEventListener('click', function (e) {
        if (e.target === modalTodasValoraciones) {
          window.cerrarModalTodasValoraciones();
        }
      });
    }

    // Backdrop del modal de verificación de empresa
    const modalVerificacion = document.getElementById('modalVerificacionEmpresa');
    if (modalVerificacion) {
      modalVerificacion.addEventListener('click', function (e) {
        if (e.target === modalVerificacion) {
          window.cerrarModalVerificacion();
        if (typeof window.cerrarModalCalificar === 'function') window.cerrarModalCalificar();
        }
      });
    }

    // Backdrop del modal de contrato digital in-situ
    const modalContratoDigital = document.getElementById('modalContratoDigital');
    if (modalContratoDigital) {
      modalContratoDigital.addEventListener('click', function (e) {
        if (e.target === modalContratoDigital) {
          window.cerrarModalContrato();
        }
      });
    }

    // Edición de términos contractuales por AJAX desde el modal in-situ (sin recargar)
    document.addEventListener('submit', function (e) {
      const form = e.target;
      if (!form || form.id !== 'formEditarTerminosContrato') return;
      e.preventDefault();
      e.stopPropagation();

      const contratoId = window._contratoAbiertoId;
      const submitBtn = form.querySelector('button[type="submit"]');
      const oldBtnHtml = submitBtn ? submitBtn.innerHTML : '';
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i data-lucide="loader-circle" class="corp-spin"></i><span>' + t('guardandoTerminos', 'Guardando términos...') + '</span>';
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      }

      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': csrfTokenActual(),
        },
      })
        .then(function (res) {
          return res.json().catch(function () {
            return { status: res.ok ? 'ok' : 'error', message: t('errorGuardarTerminos', 'No se pudo guardar los términos.') };
          });
        })
        .then(function (data) {
          if (data.status !== 'ok') {
            mostrarToastCorp(data.message || t('errorActualizarTerminos', 'Error al actualizar los términos.'), true);
            if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = oldBtnHtml; }
            return;
          }

          const toast = document.getElementById('corpToast');
          if (toast) {
            const toastSpan = toast.querySelector('span');
            if (toastSpan) toastSpan.textContent = data.message || t('terminosActualizados', 'Términos del contrato actualizados exitosamente');
            toast.classList.add('show');
            setTimeout(function () { toast.classList.remove('show'); }, 3000);
          }

          // Recargar contrato in-situ y actualizar la fila de la tabla
          if (contratoId) {
            window.abrirModalContrato(null, contratoId);
          }
        })
        .catch(function () {
          if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = oldBtnHtml; }
          mostrarToastCorp(t('errorConexionTerminos', 'Error de conexión al guardar los términos del contrato.'), true);
        });
    });

    // Firma electrónica por AJAX desde el modal in-situ (sin recargar)
    document.addEventListener('submit', function (e) {
      const form = e.target;
      if (!form || form.id !== 'formFirmarContrato') return;
      e.preventDefault();
      e.stopPropagation();

      const contratoId = form.getAttribute('data-contrato-id') || window._contratoAbiertoId;
      const submitBtn = form.querySelector('button[type="submit"]');
      const oldBtnHtml = submitBtn ? submitBtn.innerHTML : '';
      const errorEl = form.querySelector('#contratoFirmaError');
      if (errorEl) {
        errorEl.style.display = 'none';
        errorEl.textContent = '';
      }
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i data-lucide="loader-circle" class="corp-spin"></i><span>' + t('firmando', 'Firmando...') + '</span>';
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      }

      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': csrfTokenActual(),
        },
      })
        .then(function (res) {
          return res.json().catch(function () {
            return { status: res.ok ? 'ok' : 'error', message: t('errorProcesarFirma', 'No se pudo procesar la firma.') };
          });
        })
        .then(function (data) {
          if (data.status !== 'ok') {
            if (errorEl) {
              errorEl.textContent = data.message || t('errorFirmarContrato', 'No se pudo firmar el contrato.');
              errorEl.style.display = 'block';
            }
            mostrarToastCorp(data.message || t('errorFirmarContrato', 'No se pudo firmar el contrato.'), true);
            if (submitBtn) {
              submitBtn.disabled = false;
              submitBtn.innerHTML = oldBtnHtml;
            }
            return;
          }
          mostrarToastCorp(data.message || t('contratoFirmado', 'Contrato firmado electrónicamente.'), false);
          if (contratoId) {
            window._recienFirmadoContratoId = String(contratoId);
            window.abrirModalContrato(null, contratoId);
          }
        })
        .catch(function () {
          if (errorEl) {
            errorEl.textContent = t('errorRedFirmar', 'Error de red al firmar el contrato. Intenta de nuevo.');
            errorEl.style.display = 'block';
          }
          mostrarToastCorp(t('errorRedFirmarCorto', 'Error de red al firmar el contrato.'), true);
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = oldBtnHtml;
          }
        });
    });

    // Backdrop de sidebar móvil
    const backdrop = document.getElementById('sidebarBackdrop');
    if (backdrop) {
      backdrop.addEventListener('click', window.closeSidebar);
    }
    document.querySelectorAll('.sidebar .nav-item').forEach(function (item) {
      item.addEventListener('click', function () {
        if (window.innerWidth <= 768) window.closeSidebar();
      });
    });

    // Backdrop del drawer de candidatos
    const drawerCandidatos = document.getElementById('drawerCandidatos');
    if (drawerCandidatos) {
      drawerCandidatos.addEventListener('click', function (e) {
        if (e.target === drawerCandidatos) {
          window.cerrarDrawerCandidatos();
        }
      });
    }

    // Interceptar envíos de formularios dentro del drawer de candidatos (evita recarga)
    const drawerContent = document.getElementById('drawerContent');
    if (drawerContent) {
      drawerContent.addEventListener('submit', function (e) {
        if (e.target && e.target.tagName.toLowerCase() === 'form') {
          e.preventDefault();
          const form = e.target;
          const submitBtn = form.querySelector('button[type="submit"]');
          const oldBtnHtml = submitBtn ? submitBtn.innerHTML : '';
          if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i data-lucide="loader-circle" class="corp-spin"></i> ' + t('procesando', 'Procesando...');
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
              window.lucide.createIcons();
            }
          }

          const formData = new FormData(form);
          fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
              'Accept': 'application/json',
              'X-CSRFToken': csrfTokenActual(),
            },
          })
            .then(function (res) {
              return res.json().catch(function () {
                return { status: res.ok ? 'ok' : 'error', message: res.ok ? t('accionProcesada', 'Acción procesada exitosamente') : t('errorProcesarSolicitud', 'Error al procesar la solicitud') };
              });
            })
            .then(function (data) {
              if (data.status === 'error') {
                mostrarToastCorp(data.message || t('errorProcesarAccion', 'Error al procesar la acción.'), true);
                if (submitBtn) {
                  submitBtn.disabled = false;
                  submitBtn.innerHTML = oldBtnHtml;
                }
                return;
              }
              const toast = document.getElementById('corpToast');
              if (toast) {
                const toastSpan = toast.querySelector('span');
                if (toastSpan) toastSpan.textContent = data.message || t('accionProcesada', 'Acción procesada exitosamente');
                toast.classList.add('show');
                setTimeout(function () { toast.classList.remove('show'); }, 3000);
              }

              // Re-cargar contenido del drawer usando el proyecto actual
              window._limpiarCacheDrawerCandidatos();
              const titleEl = document.getElementById('drawerProjectTitle');
              const currentTitle = titleEl ? titleEl.textContent : '';
              if (window._ultimoUrlCandidatos) {
                window.abrirDrawerCandidatos(null, window._ultimoUrlCandidatos, currentTitle);
              }
            })
            .catch(function () {
              if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = oldBtnHtml;
              }
              mostrarToastCorp(t('errorProcesarReintentar', 'Error al procesar la acción. Intenta de nuevo.'), true);
            });
        }
      });
    }

    // Cerrar popovers al hacer click fuera
    document.addEventListener('click', function (e) {
      const wrapper = document.querySelector('.notif-wrapper');
      if (wrapper && !wrapper.contains(e.target)) {
        window.closeNotifPopover();
      }

      const userWrapper = document.querySelector('.user-dropdown-wrapper');
      if (userWrapper && !userWrapper.contains(e.target)) {
        window.closeUserMenu();
      }

      // Cerrar datepickers si el clic fue afuera
      if (!e.target.closest('.corp-datepicker')) {
        document.querySelectorAll('.datepicker-popover').forEach(function (p) {
          p.classList.remove('is-open');
        });
      }
    });

    // Tecla Escape para modales y popovers
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        window.cerrarModal();
        window.cerrarModalPerfil();
        window.cerrarModalEditarProyecto();
        window.cerrarModalConfirmarRetiro();
        window.cerrarModalTodasValoraciones();
        window.cerrarModalContrato();
        window.cerrarModalVerificacion();
        if (typeof window.cerrarModalCalificar === 'function') window.cerrarModalCalificar();
        if (typeof window.cerrarModalBienvenida === 'function') window.cerrarModalBienvenida();
        window.cerrarDrawerCandidatos();
        window.closeNotifPopover();
        window.closeUserMenu();
        window.closeSidebar();
      }
    });

    // Restaurar pestaña activa desde URL: el hash o la sección actual mandan
    const params = new URLSearchParams(window.location.search);
    const calificarProyectoId = params.get('calificar_proyecto');
    if (calificarProyectoId && typeof window.abrirModalCalificar === 'function') {
      const btnCalificar = document.querySelector('a[href$="/finalizar/' + calificarProyectoId + '/"]');
      const urlCalificar = btnCalificar ? btnCalificar.href : ('/proyectos/finalizar/' + calificarProyectoId + '/');
      window.abrirModalCalificar(null, urlCalificar, '');
      params.delete('calificar_proyecto');
      if (window.history && window.history.replaceState) {
        const cleanQs = params.toString();
        window.history.replaceState(null, '', window.location.pathname + (cleanQs ? '?' + cleanQs : '') + (window.location.hash || ''));
      }
    }
    const hash = window.location.hash ? window.location.hash.substring(1) : null;
    const sectionParam = params.get('section');
    const chatReceptor = params.get('chat_receptor');
    const chatProyecto = params.get('chat_proyecto') || '0';
    const initialTab = chatReceptor ? 'centro-chat' : (hash || sectionParam || 'inicio');

    window.switchTab(initialTab);

    if (chatReceptor && typeof window.abrirChatEnCentro === 'function') {
      params.delete('chat_receptor');
      params.delete('chat_proyecto');
      if (window.history && window.history.replaceState) {
        const cleanQs = params.toString();
        window.history.replaceState(null, '', window.location.pathname + (cleanQs ? '?' + cleanQs : '') + '#centro-chat');
      }
      setTimeout(function () {
        window.abrirChatEnCentro(null, chatReceptor, chatProyecto);
      }, 0);
    }

    // Preservar la pestaña y subpestaña actual al cambiar de idioma
    document.addEventListener('click', function (e) {
      const langBtn = e.target.closest('.lang-switch');
      if (langBtn && langBtn.href) {
        e.preventDefault();
        const destUrl = new URL(langBtn.href, window.location.origin);
        
        // Identificar la sección activa actual
        const activeSection = document.querySelector('.seccion-v.activa, .section-v.activa');
        const activeTabId = window.location.hash ? window.location.hash.substring(1) : (activeSection ? activeSection.id : 'inicio');
        
        destUrl.searchParams.set('section', activeTabId);
        destUrl.hash = activeTabId;
        
        // Preservar subpestaña si estamos en disputas/historial
        const currentParams = new URLSearchParams(window.location.search);
        if (currentParams.has('subtab')) {
          destUrl.searchParams.set('subtab', currentParams.get('subtab'));
        }
        
        window.location.href = destUrl.toString();
      }
    });

    // Restaurar subpestaña de historial si aplica
    const subtabParam = params.get('subtab');
    if (subtabParam === 'disputas' || hash === 'historial-disputas') {
      window.switchHistorialSubTab('disputas');
    }

    // Restaurar estado de colapso del sidebar en desktop
    try {
      if (localStorage.getItem('sidebar_collapsed') === '1' && window.innerWidth > 768) {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
          sidebar.classList.add('is-collapsed');
          const btn = document.getElementById('sidebarCollapseBtn');
          if (btn) {
            btn.title = t('expandirSidebar', 'Expandir menú lateral');
            const icon = btn.querySelector('[data-lucide], .lucide');
            if (icon) icon.setAttribute('data-lucide', 'panel-left-open');
          }
        }
      }
    } catch (e) {}

    // Inicializar estado del botón de tema claro/oscuro
    actualizarBotonTema(obtenerTemaActual());

    // Escuchar cambios de preferencia del sistema
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleSystemThemeChange = function (e) {
        let guardado = null;
        try { guardado = localStorage.getItem(THEME_STORAGE_KEY); } catch (err) {}
        if (guardado === 'light' || guardado === 'dark') return;
        const tema = e.matches ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', tema);
        actualizarBotonTema(tema);
      };
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', handleSystemThemeChange);
      } else if (mediaQuery.addListener) {
        mediaQuery.addListener(handleSystemThemeChange);
      }
    }

    // Animación de segmentos de dona y leyenda al desplegar details en Inicio
    document.querySelectorAll('details.command-collapse-corp').forEach(function (det) {
      det.addEventListener('toggle', function () {
        if (!det.open || prefersReducedMotion()) return;
        det.querySelectorAll('.donut-segment-slice').forEach(function (slice, idx) {
          const targetDash = slice.getAttribute('stroke-dasharray');
          if (targetDash && typeof slice.animate === 'function') {
            slice.animate(
              [
                { strokeDasharray: '0 238.76', opacity: 0.3 },
                { strokeDasharray: targetDash, opacity: 1 }
              ],
              {
                duration: 460,
                delay: idx * 45,
                easing: EASE_OUT_EXPO,
                fill: 'backwards'
              }
            );
          }
        });
        det.querySelectorAll('.donut-legend-item').forEach(function (item, idx) {
          if (typeof item.animate === 'function') {
            item.animate(
              [
                { opacity: 0, transform: 'translateX(-6px)' },
                { opacity: 1, transform: 'translateX(0)' }
              ],
              {
                duration: 240,
                delay: Math.min(idx * 30, 150),
                easing: EASE_OUT_EXPO,
                fill: 'backwards'
              }
            );
          }
        });
      });
    });

    // Inicializar íconos Lucide
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  });
  window.mostrarToastCorp = mostrarToastCorp;
})();

window.validarRechazoAvance = function (form, event) {
  var submitter = event && event.submitter ? event.submitter : document.activeElement;
  if (submitter && submitter.name === 'accion' && submitter.value === 'rechazar') {
    var ta = form.querySelector('textarea[name="comentario"]');
    if (ta && !ta.value.trim()) {
      event.preventDefault();
      var toastEl = document.getElementById('corpToast');
      var msg = (toastEl && toastEl.dataset.msgRechazo) || 'Debes escribir un comentario explicando los ajustes solicitados.';
      var errEl = form.querySelector('.form-error-inline');
      if (!errEl) {
        errEl = document.createElement('div');
        errEl.className = 'form-error-inline';
        errEl.setAttribute('role', 'alert');
        ta.insertAdjacentElement('afterend', errEl);
        ta.addEventListener('input', function () {
          if (ta.value.trim() && errEl.parentNode) errEl.remove();
        });
      }
      errEl.textContent = msg;
      ta.focus();
      if (typeof window.mostrarToastCorp === 'function') {
        window.mostrarToastCorp(msg, true);
      }
      return false;
    }
  }
  return true;
};

document.addEventListener('click', function (e) {
  document.querySelectorAll('.dev-more-actions[open]').forEach(function (det) {
    if (!det.contains(e.target)) det.removeAttribute('open');
  });
});

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.dev-more-actions[open]').forEach(function (det) {
      det.removeAttribute('open');
    });
  }
});

/* Dialog / Drawer focus trap & focus restoration */
(function () {
  var focusRestoreMap = new WeakMap();
  var lastUserTrigger = null;
  var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  document.addEventListener('pointerdown', function (e) {
    if (e.target && !e.target.closest('[role="dialog"].open, [role="dialog"].is-open')) {
      var cand = e.target.closest('button, a, [role="button"], [tabindex]:not([tabindex="-1"])');
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

  var observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      var target = m.target;
      if (!target || !target.matches || !target.matches('[role="dialog"]')) return;
      if (isDialogOpen(target)) {
        if (!focusRestoreMap.has(target)) {
          var trigger = lastUserTrigger || (document.activeElement && !target.contains(document.activeElement) ? document.activeElement : null);
          lastUserTrigger = null;
          if (trigger) focusRestoreMap.set(target, trigger);
        }
        var items = getFocusable(target);
        if (items.length && !target.contains(document.activeElement)) {
          items[0].focus();
        }
      } else if (focusRestoreMap.has(target)) {
        var prev = focusRestoreMap.get(target);
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
    var allOpen = document.querySelectorAll('[role="dialog"].open, [role="dialog"].is-open');
    var activeDialog = allOpen.length ? allOpen[allOpen.length - 1] : null;
    if (!activeDialog) return;
    var items = getFocusable(activeDialog);
    if (!items.length) return;
    var first = items[0];
    var last = items[items.length - 1];
    if (e.shiftKey && (document.activeElement === first || !activeDialog.contains(document.activeElement))) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });
})();

/* ============================================================
   GRÁFICA LINEAL EN VIVO DE #inicio (Datos Reales + Morph)
   ============================================================ */
(function () {
  var state = {
    data: null,
    metric: 'avances',
    period: '14d',
    prevCoords: null,
    lastSignature: '',
    rafId: null,
    pollTimer: null
  };

  var SVG_W = 680;
  var PAD_L = 34;
  var PAD_R = 16;
  var PAD_T = 18;
  var PAD_B = 28;
  var PLOT_H = 210 - PAD_T - PAD_B;

  function buildSmoothPath(pts) {
    if (!pts.length) return '';
    if (pts.length === 1) return 'M ' + pts[0].x.toFixed(2) + ' ' + pts[0].y.toFixed(2);
    var d = 'M ' + pts[0].x.toFixed(2) + ' ' + pts[0].y.toFixed(2);
    for (var i = 0; i < pts.length - 1; i++) {
      var p0 = pts[i === 0 ? i : i - 1];
      var p1 = pts[i];
      var p2 = pts[i + 1];
      var p3 = pts[i + 2 < pts.length ? i + 2 : i + 1];
      var cp1x = p1.x + (p2.x - p0.x) / 6;
      var cp1y = p1.y + (p2.y - p0.y) / 6;
      var cp2x = p2.x - (p3.x - p1.x) / 6;
      var cp2y = p2.y - (p3.y - p1.y) / 6;
      var minY = Math.min(p1.y, p2.y);
      var maxY = Math.max(p1.y, p2.y);
      cp1y = Math.max(PAD_T, Math.min(PAD_T + PLOT_H, Math.max(minY - 6, Math.min(maxY + 6, cp1y))));
      cp2y = Math.max(PAD_T, Math.min(PAD_T + PLOT_H, Math.max(minY - 6, Math.min(maxY + 6, cp2y))));
      d += ' C ' + cp1x.toFixed(2) + ' ' + cp1y.toFixed(2) + ', ' + cp2x.toFixed(2) + ' ' + cp2y.toFixed(2) + ', ' + p2.x.toFixed(2) + ' ' + p2.y.toFixed(2);
    }
    return d;
  }

  function buildAreaPath(pts, lineD) {
    if (!pts.length || !lineD) return '';
    var baseY = (PAD_T + PLOT_H).toFixed(2);
    return lineD + ' L ' + pts[pts.length - 1].x.toFixed(2) + ' ' + baseY + ' L ' + pts[0].x.toFixed(2) + ' ' + baseY + ' Z';
  }

  function computeCoords(puntos) {
    var maxVal = 1;
    for (var i = 0; i < puntos.length; i++) {
      if (puntos[i].valor > maxVal) maxVal = puntos[i].valor;
    }
    var niceMax = maxVal <= 2 ? 2 : Math.ceil(maxVal * 1.2);
    var plotW = SVG_W - PAD_L - PAD_R;
    var n = puntos.length;
    var coords = [];
    for (var j = 0; j < n; j++) {
      var x = n === 1 ? PAD_L + plotW / 2 : PAD_L + (j / (n - 1)) * plotW;
      var y = PAD_T + PLOT_H - (puntos[j].valor / niceMax) * PLOT_H;
      coords.push({ x: x, y: y, valor: puntos[j].valor, etiqueta: puntos[j].etiqueta, fecha: puntos[j].fecha });
    }
    return { coords: coords, niceMax: niceMax };
  }

  function showTooltip(evt, pt, label) {
    var tip = document.getElementById('inicioLineTooltip');
    var wrap = tip ? tip.parentElement : null;
    if (!tip || !wrap) return;
    tip.querySelector('.tooltip-mes').textContent = pt.etiqueta;
    tip.querySelector('.tooltip-monto').textContent = String(pt.valor);
    tip.querySelector('.tooltip-sub').textContent = label;
    tip.style.display = 'block';
    var rect = wrap.getBoundingClientRect();
    var left = (evt.clientX - rect.left) + 12;
    var top = (evt.clientY - rect.top) - 56;
    if (left + 150 > rect.width) left = Math.max(8, left - 165);
    if (top < 0) top = 8;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }

  function hideTooltip() {
    var tip = document.getElementById('inicioLineTooltip');
    if (tip) tip.style.display = 'none';
  }

  function renderAxes(niceMax, coords) {
    var gridG = document.getElementById('inicioGridGroup');
    var yG = document.getElementById('inicioYAxisGroup');
    var xG = document.getElementById('inicioXAxisGroup');
    if (!gridG || !yG || !xG) return;

    var ns = 'http://www.w3.org/2000/svg';
    gridG.innerHTML = '';
    yG.innerHTML = '';
    xG.innerHTML = '';

    var ticks = [0, Math.round(niceMax / 2), niceMax];
    for (var t = 0; t < ticks.length; t++) {
      var val = ticks[t];
      var y = PAD_T + PLOT_H - (val / niceMax) * PLOT_H;
      var line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', PAD_L);
      line.setAttribute('x2', SVG_W - PAD_R);
      line.setAttribute('y1', y.toFixed(1));
      line.setAttribute('y2', y.toFixed(1));
      line.setAttribute('class', 'inicio-grid-line');
      gridG.appendChild(line);

      var txt = document.createElementNS(ns, 'text');
      txt.setAttribute('x', PAD_L - 8);
      txt.setAttribute('y', (y + 4).toFixed(1));
      txt.setAttribute('text-anchor', 'end');
      txt.setAttribute('class', 'inicio-axis-label');
      txt.textContent = String(val);
      yG.appendChild(txt);
    }

    var step = coords.length > 16 ? 5 : 2;
    for (var i = 0; i < coords.length; i++) {
      if (i !== 0 && i !== coords.length - 1 && i % step !== 0) continue;
      var xTxt = document.createElementNS(ns, 'text');
      xTxt.setAttribute('x', coords[i].x.toFixed(1));
      xTxt.setAttribute('y', '203');
      xTxt.setAttribute('text-anchor', i === 0 ? 'start' : (i === coords.length - 1 ? 'end' : 'middle'));
      xTxt.setAttribute('class', 'inicio-axis-label');
      xTxt.textContent = coords[i].etiqueta;
      xG.appendChild(xTxt);
    }
  }

  function renderDots(coords, label) {
    var dotsG = document.getElementById('inicioDotsGroup');
    if (!dotsG) return;
    var ns = 'http://www.w3.org/2000/svg';
    dotsG.innerHTML = '';
    coords.forEach(function (pt) {
      var c = document.createElementNS(ns, 'circle');
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
        var r = c.getBoundingClientRect();
        showTooltip({ clientX: r.left, clientY: r.top }, pt, label);
      });
      c.addEventListener('blur', hideTooltip);
      dotsG.appendChild(c);
    });
  }

  function renderChart(mode) {
    if (!state.data) return;
    var serie = state.data[state.metric];
    if (!serie) return;
    var puntos = state.period === '30d' ? serie.puntos_30d : serie.puntos_14d;
    var total = state.period === '30d' ? serie.total_30d : serie.total_14d;

    var titleEl = document.getElementById('inicioChartTitle');
    var totalEl = document.getElementById('inicioChartTotal');
    if (titleEl) titleEl.textContent = serie.label;
    if (totalEl) totalEl.textContent = String(total) + ' ' + (state.period === '30d' ? '(30d)' : '(14d)');

    var linePath = document.getElementById('inicioLinePath');
    var areaPath = document.getElementById('inicioAreaPath');
    if (!linePath || !areaPath) return;

    var computed = computeCoords(puntos);
    renderAxes(computed.niceMax, computed.coords);

    if (mode === 'morph' && state.prevCoords && state.prevCoords.length === computed.coords.length) {
      if (state.rafId) cancelAnimationFrame(state.rafId);
      var fromCoords = state.prevCoords;
      var toCoords = computed.coords;
      var start = performance.now();
      var duration = 420;
      var stepFrame = function (now) {
        var t = Math.min(1, (now - start) / duration);
        var ease = 1 - Math.pow(1 - t, 3);
        var interp = toCoords.map(function (pt, idx) {
          return {
            x: pt.x,
            y: fromCoords[idx].y + (pt.y - fromCoords[idx].y) * ease,
            valor: pt.valor,
            etiqueta: pt.etiqueta,
            fecha: pt.fecha
          };
        });
        var d = buildSmoothPath(interp);
        linePath.setAttribute('d', d);
        areaPath.setAttribute('d', buildAreaPath(interp, d));
        if (t < 1) {
          state.rafId = requestAnimationFrame(stepFrame);
        } else {
          state.prevCoords = toCoords;
          renderDots(toCoords, serie.label);
        }
      };
      state.rafId = requestAnimationFrame(stepFrame);
    } else {
      var d = buildSmoothPath(computed.coords);
      linePath.setAttribute('d', d);
      areaPath.setAttribute('d', buildAreaPath(computed.coords, d));
      renderDots(computed.coords, serie.label);
      state.prevCoords = computed.coords;

      if (mode === 'draw' && typeof linePath.getTotalLength === 'function') {
        var len = linePath.getTotalLength();
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
    var pill = document.getElementById('inicioLivePill');
    if (!pill) return;
    pill.classList.add('is-updating');
    setTimeout(function () { pill.classList.remove('is-updating'); }, 700);
  }

  function fetchLiveSeries() {
    var svg = document.getElementById('inicioLineSvg');
    var url = svg ? svg.getAttribute('data-feed-url') : '';
    if (!url || document.visibilityState !== 'visible') return;
    var sec = document.getElementById('inicio');
    if (sec && !sec.classList.contains('activa')) return;

    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (json) {
        if (!json) return;
        var sig = signatureOf(json);
        if (sig && sig !== state.lastSignature) {
          state.lastSignature = sig;
          state.data = json;
          renderChart('morph');
          pulseLivePill();
        }
      })
      .catch(function () {});
  }

  window.seleccionarMetricaInicio = function (metric, btn) {
    state.metric = metric;
    if (btn && btn.parentElement) {
      btn.parentElement.querySelectorAll('.ledger-filter-pill').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
    }
    renderChart('morph');
  };

  window.seleccionarPeriodoInicio = function (period, btn) {
    state.period = period;
    if (btn && btn.parentElement) {
      btn.parentElement.querySelectorAll('.time-tab-corp').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
    }
    state.prevCoords = null;
    renderChart('draw');
  };

  window.refreshInicioLineChart = fetchLiveSeries;

  function initInicioActivityChart() {
    var el = document.getElementById('inicioActivityData');
    if (!el) return;
    try {
      state.data = JSON.parse(el.textContent || '{}');
      state.lastSignature = signatureOf(state.data);
      renderChart('draw');
      if (!state.pollTimer) {
        state.pollTimer = setInterval(fetchLiveSeries, 15000);
      }
      document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible') fetchLiveSeries();
      });
    } catch (e) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initInicioActivityChart);
  } else {
    initInicioActivityChart();
  }
})();
