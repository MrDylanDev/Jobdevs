/**
 * JobDevs — Modales de Dashboard: Contratos Digitales y Calificación de Empresa
 */

import {
  escapeHtml,
  parseJsonResponse,
  getCsrfToken,
  mostrarToast,
  abrirModal,
  cerrarModal,
  setModalObligatorio,
  setHeader,
  setContent,
  setFooter,
} from './modal_core.js';

// ─────────────────────────────────────────────────────────────
// 1. CONTRATO DIGITAL
// ─────────────────────────────────────────────────────────────
export async function cargarContratoDigital(url, triggerBtn) {
  abrirModal('');
  setHeader('ACUERDO LEGAL DE CONTRATACIÓN', 'Cargando contrato…');

  try {
    const res = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      credentials: 'same-origin'
    });
    const data = await parseJsonResponse(res, 'No se pudo obtener el contrato (respuesta inesperada del servidor).');
    const c = data.contrato || (data.id ? data : null);
    if (!c) throw new Error(data.error || 'No se pudo obtener el contrato');

    setHeader('ACUERDO LEGAL DE CONTRATACIÓN', 'Contrato Digital #' + (c.codigo || ''), 'Proyecto: ' + (c.proyecto_titulo || ''));

    const estadoCls = c.estado === 'firmado' ? 'jdm-badge-success' : 'jdm-badge-gray';

    let html =
      '<div class="jdm-contract-meta-bar">' +
        '<div class="jdm-meta-item"><span class="jdm-meta-label">Monto</span> <span class="jdm-meta-val">' + escapeHtml(c.monto_formateado || ('$' + c.monto)) + '</span></div>' +
        '<span class="meta-dot">·</span>' +
        '<div class="jdm-meta-item"><span class="jdm-meta-label">Emisión</span> <span class="jdm-meta-val">' + escapeHtml(c.fecha_creacion) + '</span></div>' +
        '<span class="meta-dot">·</span>' +
        '<div class="jdm-meta-item"><span class="jdm-meta-label">Estado</span> <span class="jdm-badge ' + estadoCls + '">' + escapeHtml(c.estado_label) + '</span></div>' +
      '</div>' +

      '<div class="jdm-contract-parties">' +
        '<div class="jdm-party-item">' +
          '<span class="jdm-party-label"><i data-lucide="building"></i> Empresa Contratante</span>' +
          '<span class="jdm-party-name">' + escapeHtml(c.empresa_nombre) + '</span>' +
          '<span class="jdm-party-status">' +
            (c.firmado_empresa ? '<span class="jdm-sign-ok"><i data-lucide="check-check"></i> Firmado (' + escapeHtml(c.fecha_firma_empresa || '') + ')</span>' : '<span class="jdm-sign-wait"><i data-lucide="clock"></i> Pendiente de firma</span>') +
          '</span>' +
        '</div>' +
        '<div class="jdm-party-divider"></div>' +
        '<div class="jdm-party-item">' +
          '<span class="jdm-party-label"><i data-lucide="code-2"></i> Desarrollador / Contratista</span>' +
          '<span class="jdm-party-name">' + escapeHtml(c.desarrollador_nombre) + '</span>' +
          '<span class="jdm-party-status" id="jdmDevSignStatus">' +
            (c.firmado_desarrollador ? '<span class="jdm-sign-ok"><i data-lucide="check-check"></i> Firmado (' + escapeHtml(c.fecha_firma_desarrollador || '') + ')</span>' : '<span class="jdm-sign-urgent"><i data-lucide="file-signature"></i> Pendiente de tu firma</span>') +
          '</span>' +
        '</div>' +
      '</div>' +

      '<div class="jdm-clauses-doc">' +
        '<div class="jdm-doc-title"><i data-lucide="file-text"></i> Términos y Cláusulas del Acuerdo</div>';

    const clausulasArr = Array.isArray(c.clausulas) ? c.clausulas : (typeof c.clausulas === 'string' && c.clausulas.trim() ? [c.clausulas] : []);
    if (clausulasArr.length) {
      clausulasArr.forEach(function (clausula, i) {
        const limpia = String(clausula).replace(/^\d+[\.\)]\s*/, '').replace(/^CLÁUSULA\s*\d+[\.\:]\s*/i, '');
        html += '<div class="jdm-clause-item"><span class="jdm-clause-num">Cláusula ' + (i + 1) + '.</span> <span class="jdm-clause-text">' + escapeHtml(limpia) + '</span></div>';
      });
    } else {
      html += '<p style="color:#71717a; font-size:12.5px;">Sin cláusulas adicionales registradas.</p>';
    }
    html += '</div>';

    const perfil = c.perfil_profesional;
    if (perfil) {
      html +=
        '<details class="jdm-contract-profile-details">' +
          '<summary class="jdm-contract-profile-summary">' +
            '<span><i data-lucide="user-check"></i> Datos de postulación vinculados</span>' +
            '<i data-lucide="chevron-down" style="width:13px; height:13px;"></i>' +
          '</summary>' +
          '<div class="jdm-contract-profile-body">' +
            '<p style="margin:0 0 6px; font-size:11.5px; color:#71717a;">' + (c.hash_documento ? 'Evidencia técnica conservada en la formalización.' : 'Vista previa de la ficha que se conservará en la firma.') + '</p>' +
            '<div><strong>Nombre:</strong> ' + escapeHtml(perfil.nombre) + '</div>' +
            '<div><strong>Condición SENA:</strong> ' + escapeHtml(perfil.estado_verificacion) + ' · ' + escapeHtml(perfil.condicion_sena) + '</div>' +
            (perfil.programa_formacion ? '<div><strong>Programa:</strong> ' + escapeHtml(perfil.programa_formacion) + '</div>' : '') +
            (perfil.ficha ? '<div><strong>Ficha:</strong> ' + escapeHtml(perfil.ficha) + '</div>' : '') +
            (perfil.habilidades ? '<div><strong>Habilidades:</strong> ' + escapeHtml(perfil.habilidades) + '</div>' : '') +
            (perfil.portafolio_url ? '<div><strong>Portafolio:</strong> <a href="' + escapeHtml(perfil.portafolio_url) + '" target="_blank" rel="noopener" style="color:#ffffff; text-decoration:underline;">' + escapeHtml(perfil.portafolio_url) + '</a></div>' : '') +
            (perfil.mensaje_postulacion ? '<div style="margin-top:6px; padding-top:6px; border-top:1px dashed rgba(255,255,255,0.08); white-space:pre-wrap;"><strong>Mensaje:</strong>\n' + escapeHtml(perfil.mensaje_postulacion) + '</div>' : '') +
          '</div>' +
        '</details>';
    }

    if (c.puede_firmar) {
      html +=
        '<div class="jdm-contract-accept-box" style="margin-top:14px;padding:12px 14px;border-radius:8px;border:1px solid var(--border,rgba(255,255,255,0.12));background:rgba(255,255,255,0.02);">' +
          '<label for="jdmAceptaTerminos" style="display:flex;align-items:flex-start;gap:10px;font-size:12.5px;line-height:1.5;cursor:pointer;">' +
            '<input type="checkbox" id="jdmAceptaTerminos" name="acepta_terminos" required style="margin-top:3px;flex-shrink:0;">' +
            '<span>He leído y acepto íntegramente los términos y cláusulas de este contrato digital.</span>' +
          '</label>' +
        '</div>';
    }

    setContent(html);

    let footerHtml = '<div style="display:flex; align-items:center; justify-content:space-between; width:100%; gap:14px; flex-wrap:wrap;">';
    if (c.puede_firmar) {
      footerHtml +=
        '<div class="jdm-footer-note">' +
          '<i data-lucide="shield-check" style="width:15px; height:15px; color:var(--accent, #00713f); flex-shrink:0;"></i>' +
          '<span>Al firmar formalizas legalmente este acuerdo vinculante.</span>' +
        '</div>' +
        '<div style="display:inline-flex; gap:10px; margin-left:auto;">' +
          '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>' +
          '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmBtnFirmar" data-url-firmar="' + escapeHtml(c.firma_url || c.url_firmar || '') + '">' +
            '<i data-lucide="file-signature"></i> Firmar Contrato Digitalmente' +
          '</button>' +
        '</div>';
    } else {
      footerHtml +=
        '<div class="jdm-footer-note">' +
          '<i data-lucide="shield-check" style="width:14px; height:14px; color:var(--accent, #00713f); flex-shrink:0;"></i>' +
          '<span>Documento digital registrado y protegido por JobDevs.</span>' +
        '</div>' +
        '<div style="display:inline-flex; gap:10px; margin-left:auto;">' +
          '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>' +
        '</div>';
    }
    footerHtml += '</div>';
    setFooter(footerHtml);

    const btnFirmar = document.getElementById('jdmBtnFirmar');
    if (btnFirmar) {
      btnFirmar.addEventListener('click', async function () {
        const chkAcepta = document.getElementById('jdmAceptaTerminos');
        if (!chkAcepta || !chkAcepta.checked) {
          mostrarToast('Debes aceptar los términos y cláusulas del contrato antes de firmar.', true);
          if (chkAcepta) chkAcepta.focus();
          return;
        }
        btnFirmar.disabled = true;
        btnFirmar.innerHTML = '<i data-lucide="loader-2"></i> Firmando...';
        try {
          const signBody = new FormData();
          if (chkAcepta.checked) {
            signBody.append('acepta_terminos', 'on');
          }
          signBody.append('origen', 'dashboard');
          const signRes = await fetch(btnFirmar.getAttribute('data-url-firmar'), {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': getCsrfToken()
            },
            body: signBody,
            credentials: 'same-origin'
          });
          const signData = await parseJsonResponse(signRes, 'Error al procesar la firma del contrato (respuesta inesperada del servidor).');
          if (signData.ok) {
            mostrarToast(signData.mensaje || '¡Contrato firmado exitosamente!');
            const devStatus = document.getElementById('jdmDevSignStatus');
            if (devStatus) {
              devStatus.innerHTML = '<span class="jdm-sign-ok"><i data-lucide="check-check"></i> Firmado ahora</span>';
            }
            const f = document.getElementById('jdmFooter');
            if (f) {
              f.innerHTML =
                '<div style="display:flex; align-items:center; justify-content:space-between; width:100%; gap:14px; flex-wrap:wrap;">' +
                  '<span class="jdm-sign-ok" style="font-size:12px;">' +
                    '<i data-lucide="check-check" style="width:15px; height:15px;"></i> Has firmado este contrato con éxito.' +
                  '</span>' +
                  '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>' +
                '</div>';
              if (window.lucide && typeof window.lucide.createIcons === 'function') window.lucide.createIcons();
            }
            if (triggerBtn) {
              triggerBtn.innerHTML = '<i data-lucide="file-signature"></i> Ver Contrato';
            }
          } else {
            mostrarToast(signData.mensaje || signData.error || 'No se pudo firmar el contrato.', true);
            btnFirmar.disabled = false;
            btnFirmar.innerHTML = '<i data-lucide="file-signature"></i> Firmar Contrato Digitalmente';
          }
        } catch (err) {
          mostrarToast('Error de conexión al firmar.', true);
          btnFirmar.disabled = false;
          btnFirmar.innerHTML = '<i data-lucide="file-signature"></i> Firmar Contrato Digitalmente';
        }
      });
    }

  } catch (err) {
    setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
    setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
  }
}

// ─────────────────────────────────────────────────────────────
// 4. CALIFICAR EMPRESA (HTMX partial)
// ─────────────────────────────────────────────────────────────
const RATING_CAPTIONS = [
  '',
  '1/5 - Muy insatisfactorio',
  '2/5 - Regular',
  '3/5 - Aceptable',
  '4/5 - Muy bueno',
  '5/5 - Excelente',
];

let activeCalificarTrigger = null;
let calificarHooksInit = false;

function hidratarCalificarModal(container) {
  if (!container) return;
  const metaEl = container.querySelector('.jdm-calificar-partial');
  if (metaEl) {
    setHeader(
      metaEl.dataset.modalKicker || 'VALORAR EMPRESA',
      metaEl.dataset.modalTitle || '',
      metaEl.dataset.modalSubtitle || ''
    );
    setModalObligatorio(metaEl.dataset.obligatorio === 'true');
  }

  const form = container.querySelector('#jdmFormCalificar');
  if (!form) return;

  const starsWrap = form.querySelector('#jdmStars');
  const stars = form.querySelectorAll('#jdmStars .jdm-star-btn');
  const caption = form.querySelector('#jdmRatingCaption');
  const inputPunt = form.querySelector('#jdmInputPuntuacion');
  const txtComentario = form.querySelector('#jdmComentario');
  const charCount = form.querySelector('#jdmCharCount');
  let puntuacionVal = parseInt(inputPunt && inputPunt.value, 10) || 0;

  function pintarEstrellas(n) {
    stars.forEach(function (s, idx) {
      s.classList.toggle('is-active', (idx + 1) <= n);
    });
  }

  if (puntuacionVal && caption) {
    pintarEstrellas(puntuacionVal);
    caption.textContent = RATING_CAPTIONS[puntuacionVal] || '';
    caption.style.color = '#00e676';
  }

  stars.forEach(function (star) {
    star.addEventListener('click', function () {
      puntuacionVal = parseInt(star.getAttribute('data-val'), 10);
      if (inputPunt) inputPunt.value = puntuacionVal;
      pintarEstrellas(puntuacionVal);
      if (caption) {
        caption.textContent = RATING_CAPTIONS[puntuacionVal] || '';
        caption.style.color = '#00e676';
      }
    });
    star.addEventListener('mouseenter', function () {
      pintarEstrellas(parseInt(star.getAttribute('data-val'), 10));
    });
  });

  if (starsWrap) {
    starsWrap.addEventListener('mouseleave', function () {
      pintarEstrellas(puntuacionVal);
    });
  }

  if (txtComentario && charCount) {
    const actualizarContador = function () {
      const len = txtComentario.value.trim().length;
      charCount.textContent = len + ' / 20 caracteres mínimos';
      charCount.style.color = len >= 20 ? '#00e676' : '#666666';
    };
    txtComentario.addEventListener('input', actualizarContador);
    actualizarContador();
  }
}

function initCalificarHooks() {
  if (calificarHooksInit) return;
  calificarHooksInit = true;

  document.addEventListener('htmx:afterSwap', function (event) {
    const target = event && event.detail && event.detail.target;
    if (target && target.id === 'jdmBody' && target.querySelector('.jdm-calificar-partial')) {
      hidratarCalificarModal(target);
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    }
  });

  document.addEventListener('jobdevs:calificacion-empresa-guardada', function (event) {
    const detail = (event && event.detail) || {};
    cerrarModal(true);
    if (activeCalificarTrigger) {
      activeCalificarTrigger.classList.remove('btn-primary', 'primary');
      activeCalificarTrigger.classList.add('btn-secondary');
      activeCalificarTrigger.innerHTML =
        '<i data-lucide="check-circle-2" style="color:#00e676;"></i> Empresa calificada' +
        (detail.puntuacion ? ' (' + escapeHtml(detail.puntuacion) + '/5)' : '');
      activeCalificarTrigger.disabled = true;
      activeCalificarTrigger = null;
    }
    document.querySelectorAll('.calificar-popup-overlay').forEach(function (popup) {
      popup.remove();
    });
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  });
}

export async function cargarCalificarEmpresa(url, triggerBtn, esObligatorio) {
  initCalificarHooks();
  activeCalificarTrigger = triggerBtn || null;
  abrirModal('jdm-card-sm');
  setModalObligatorio(Boolean(esObligatorio));
  setHeader(
    esObligatorio ? 'EVALUACIÓN OBLIGATORIA' : 'PROYECTO // VALORACIÓN',
    'Cargando calificación…'
  );

  try {
    const fetchUrl = esObligatorio
      ? url + (url.indexOf('?') === -1 ? '?' : '&') + 'obligatorio=1'
      : url;
    const res = await fetch(fetchUrl, {
      headers: { 'HX-Request': 'true' },
      credentials: 'same-origin',
    });
    const html = await res.text();
    if (!html || !html.includes('jdm-calificar-partial')) {
      throw new Error('No se pudo cargar la valoración (respuesta inesperada del servidor).');
    }

    setContent(html);
    setFooter('');
    const bodyEl = document.getElementById('jdmBody');
    hidratarCalificarModal(bodyEl);
    if (window.htmx && typeof window.htmx.process === 'function' && bodyEl) {
      window.htmx.process(bodyEl);
    }
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  } catch (err) {
    setModalObligatorio(false);
    setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
    setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
  }
}
