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
    const data = await res.json();
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
        btnFirmar.disabled = true;
        btnFirmar.innerHTML = '<i data-lucide="loader-2"></i> Firmando...';
        try {
          const signBody = new FormData();
          signBody.append('acepta_terminos', 'on');
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
          const signData = await signRes.json();
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
// 4. CALIFICAR EMPRESA
// ─────────────────────────────────────────────────────────────
export async function cargarCalificarEmpresa(url, triggerBtn, esObligatorio) {
  abrirModal('jdm-card-sm');
  setModalObligatorio(Boolean(esObligatorio));

  setHeader(
    esObligatorio ? 'EVALUACIÓN OBLIGATORIA' : 'PROYECTO // VALORACIÓN',
    'Cargando calificación…'
  );

  try {
    const res = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      credentials: 'same-origin'
    });
    const data = await parseJsonResponse(res, 'No se pudo cargar la valoración (respuesta inesperada del servidor).');
    if (!data.ok || !data.proyecto) throw new Error(data.error || data.mensaje || 'No se pudo cargar la valoración');

    const p = data.proyecto;
    setHeader(
      esObligatorio ? 'EVALUACIÓN OBLIGATORIA' : 'VALORAR EMPRESA',
      p.empresa,
      'Proyecto finalizado: ' + p.titulo
    );

    if (data.ya_califico) {
      setModalObligatorio(false);
      setContent(
        '<div style="text-align:center;padding:24px 10px;">' +
          '<i data-lucide="check-circle" style="font-size:36px;color:#00e676;margin-bottom:12px;display:block;"></i>' +
          '<h3 style="margin:0 0 8px;font-family:\'JetBrains Mono\',monospace;color:#ffffff;">¡Ya has calificado a esta empresa!</h3>' +
          '<p style="color:#a0a0a0;font-size:13px;">Tu reseña para este proyecto ya fue registrada en el perfil de la empresa.</p>' +
        '</div>'
      );
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
      return;
    }

    const avisoHtml = esObligatorio
      ? '<div style="display:flex;align-items:flex-start;gap:10px;padding:12px 14px;border-radius:6px;background:rgba(255,171,0,0.08);border:1px solid rgba(255,171,0,0.3);color:#ffab00;font-size:12.5px;margin-bottom:16px;line-height:1.45;">' +
          '<i data-lucide="shield-alert" style="width:18px;height:18px;flex-shrink:0;margin-top:1px;"></i>' +
          '<div><strong>Evaluación requerida:</strong> El proyecto ha finalizado. Para continuar navegando en tu panel, califica tu experiencia colaborando con la empresa.</div>' +
        '</div>'
      : '';

    const html =
      '<form id="jdmFormCalificar" novalidate>' +
        avisoHtml +
        '<div id="jdmCalificarError" class="jdm-error" style="display:none;"></div>' +
        '<div class="jdm-rating-container">' +
          '<div class="jdm-stars-row" id="jdmStars">' +
            '<button type="button" class="jdm-star-btn" data-val="1"><i data-lucide="star"></i></button>' +
            '<button type="button" class="jdm-star-btn" data-val="2"><i data-lucide="star"></i></button>' +
            '<button type="button" class="jdm-star-btn" data-val="3"><i data-lucide="star"></i></button>' +
            '<button type="button" class="jdm-star-btn" data-val="4"><i data-lucide="star"></i></button>' +
            '<button type="button" class="jdm-star-btn" data-val="5"><i data-lucide="star"></i></button>' +
          '</div>' +
          '<div class="jdm-rating-caption" id="jdmRatingCaption">Selecciona una puntuación (1 a 5)</div>' +
          '<input type="hidden" name="puntuacion" id="jdmInputPuntuacion" value="">' +
        '</div>' +

        '<div class="jdm-form-group">' +
          '<label class="jdm-form-label" for="jdmComentario">Comentario cualitativo <span class="req">* (mínimo 20 caracteres)</span></label>' +
          '<textarea id="jdmComentario" name="comentario" class="jdm-textarea" placeholder="Describe tu experiencia colaborando con la empresa, cumplimiento de pagos y comunicación…" required></textarea>' +
          '<div class="jdm-char-counter" id="jdmCharCount">0 / 20 caracteres mínimos</div>' +
        '</div>' +
      '</form>';

    setContent(html);

    if (esObligatorio) {
      setFooter(
        '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmBtnEnviarCalificacion" style="width:100%;justify-content:center;">' +
          '<i data-lucide="star"></i> Enviar Calificación Obligatoria' +
        '</button>'
      );
    } else {
      setFooter(
        '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cancelar</button>' +
        '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmBtnEnviarCalificacion"><i data-lucide="star"></i> Enviar Calificación</button>'
      );
    }

    let puntuacionVal = 0;
    const stars = document.querySelectorAll('#jdmStars .jdm-star-btn');
    const caption = document.getElementById('jdmRatingCaption');
    const inputPunt = document.getElementById('jdmInputPuntuacion');
    const txtComentario = document.getElementById('jdmComentario');
    const charCount = document.getElementById('jdmCharCount');
    const captions = ['', '1/5 - Muy insatisfactorio', '2/5 - Regular', '3/5 - Aceptable', '4/5 - Muy bueno', '5/5 - Excelente'];

    function pintarEstrellas(n) {
      stars.forEach(function (s, idx) {
        s.classList.toggle('is-active', (idx + 1) <= n);
      });
    }

    stars.forEach(function (star) {
      star.addEventListener('click', function () {
        puntuacionVal = parseInt(star.getAttribute('data-val'), 10);
        inputPunt.value = puntuacionVal;
        pintarEstrellas(puntuacionVal);
        caption.textContent = captions[puntuacionVal] || '';
        caption.style.color = '#00e676';
      });
      star.addEventListener('mouseenter', function () {
        pintarEstrellas(parseInt(star.getAttribute('data-val'), 10));
      });
    });

    document.getElementById('jdmStars').addEventListener('mouseleave', function () {
      pintarEstrellas(puntuacionVal);
    });

    txtComentario.addEventListener('input', function () {
      const len = txtComentario.value.trim().length;
      charCount.textContent = len + ' / 20 caracteres mínimos';
      charCount.style.color = len >= 20 ? '#00e676' : '#666666';
    });

    const btnEnviar = document.getElementById('jdmBtnEnviarCalificacion');
    btnEnviar.addEventListener('click', async function () {
      const errBox = document.getElementById('jdmCalificarError');
      const com = txtComentario.value.trim();

      if (!puntuacionVal) {
        errBox.style.display = 'flex';
        errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>Debes seleccionar una puntuación de 1 a 5 estrellas.</span>';
        return;
      }
      if (com.length < 20) {
        errBox.style.display = 'flex';
        errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>El comentario debe tener al menos 20 caracteres.</span>';
        return;
      }

      errBox.style.display = 'none';
      btnEnviar.disabled = true;
      btnEnviar.innerHTML = '<i data-lucide="loader-2"></i> Registrando...';

      try {
        const formData = new FormData();
        formData.append('puntuacion', puntuacionVal);
        formData.append('comentario', com);
        formData.append('origen', 'dashboard');

        const postRes = await fetch(data.url_calificar, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
          },
          body: formData,
          credentials: 'same-origin'
        });

        const resJson = await postRes.json();
        if (resJson.ok) {
          mostrarToast(resJson.mensaje || '¡Calificación enviada!');
          cerrarModal(true);
          if (triggerBtn) {
            triggerBtn.classList.remove('btn-primary', 'primary');
            triggerBtn.classList.add('btn-secondary');
            triggerBtn.innerHTML = '<i data-lucide="check-circle-2" style="color:#00e676;"></i> Empresa calificada (' + puntuacionVal + '/5)';
            triggerBtn.disabled = true;
          }
          document.querySelectorAll('.calificar-popup-overlay').forEach(function (popup) { popup.remove(); });
          if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
          }
        } else {
          errBox.style.display = 'flex';
          errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>' + escapeHtml(resJson.mensaje || 'No se pudo registrar la calificación.') + '</span>';
          btnEnviar.disabled = false;
          btnEnviar.innerHTML = '<i data-lucide="star"></i> Enviar Calificación';
        }
      } catch (e) {
        errBox.style.display = 'flex';
        errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>Error de conexión al enviar la calificación.</span>';
        btnEnviar.disabled = false;
        btnEnviar.innerHTML = '<i data-lucide="star"></i> Enviar Calificación';
      }
    });

  } catch (err) {
    setModalObligatorio(false);
    setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
    setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
  }
}
