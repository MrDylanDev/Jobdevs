/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Candidatos Drawer & Chat Integration
 * ============================================================
 */

import { t, csrfTokenActual, mostrarToastCorp, ejecutarSwitchTabDOM } from './ui_core.js';
import { abrirModalContrato } from './contratos_hitos.js';

const drawerTabCache = new Map();
let drawerFetchToken = 0;

export function _limpiarCacheDrawerCandidatos() {
  drawerTabCache.clear();
}

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
        abrirModalContrato(ev, coincidenciaContrato[1]);
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

export function abrirDrawerCandidatos(event, url, titulo) {
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
}

export function cerrarDrawerCandidatos() {
  const drawer = document.getElementById('drawerCandidatos');
  if (drawer) {
    drawer.classList.remove('is-open');
    document.body.style.overflow = '';
  }
}

export function abrirChatEnCentro(event, receptorId, proyectoId) {
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
}

// --- Global Window Contracts ---

window._limpiarCacheDrawerCandidatos = _limpiarCacheDrawerCandidatos;
window.abrirDrawerCandidatos = abrirDrawerCandidatos;
window.cerrarDrawerCandidatos = cerrarDrawerCandidatos;
window.abrirChatEnCentro = abrirChatEnCentro;

// --- DOM Initialization ---

export function initCandidatos() {
  // Backdrop del drawer de candidatos
  const drawerCandidatos = document.getElementById('drawerCandidatos');
  if (drawerCandidatos) {
    drawerCandidatos.addEventListener('click', function (e) {
      if (e.target === drawerCandidatos) {
        cerrarDrawerCandidatos();
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
            _limpiarCacheDrawerCandidatos();
            const titleEl = document.getElementById('drawerProjectTitle');
            const currentTitle = titleEl ? titleEl.textContent : '';
            if (window._ultimoUrlCandidatos) {
              abrirDrawerCandidatos(null, window._ultimoUrlCandidatos, currentTitle);
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
}
