/**
 * JobDevs — Sistema de Modales Integrados en Dashboards
 * Controla Contratos, Avances, Calificaciones, Empresas y Disputas sin redirecciones.
 */
(function () {
  'use strict';

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function leerCookie(nombre) {
    var match = document.cookie
      .split('; ')
      .find(function (item) { return item.indexOf(nombre + '=') === 0; });
    return match ? decodeURIComponent(match.slice(nombre.length + 1)) : '';
  }

  async function parseJsonResponse(res, fallbackMsg) {
    var ct = res.headers.get('content-type') || '';
    if (!ct.includes('application/json')) {
      throw new Error(fallbackMsg || 'Respuesta inesperada del servidor.');
    }
    return await res.json();
  }

  function getCsrfToken() {
    var cookie = leerCookie('csrftoken');
    if (cookie) return cookie;
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : '';
  }

  function mostrarToast(mensaje, esError) {
    if (window.JobDevsToast && typeof window.JobDevsToast.mostrar === 'function') {
      window.JobDevsToast.mostrar({
        tipo: esError ? 'error' : 'success',
        mensaje: mensaje,
        duracion: 4500,
      });
      return;
    }
    if (window.JobDevsSSE && typeof window.JobDevsSSE.mostrarToast === 'function') {
      window.JobDevsSSE.mostrarToast({
        tipo: esError ? 'alerta' : 'info',
        mensaje: mensaje,
      });
      return;
    }
    if (typeof window.mostrarToast === 'function' && window.mostrarToast !== mostrarToast) {
      window.mostrarToast(mensaje, esError);
      return;
    }
    // Fallback Toast Flotante Personalizado
    var t = document.createElement('div');
    t.className = 'jobdevs-toast-fallback ' + (esError ? 'is-error' : 'is-success');
    t.textContent = mensaje;
    document.body.appendChild(t);
    setTimeout(function () {
      t.style.opacity = '0';
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
    }, 4000);
  }

  // ─────────────────────────────────────────────────────────────
  // Modal Personalizado de Confirmación In-Situ (Reemplaza window.confirm)
  // ─────────────────────────────────────────────────────────────
  var confirmEl = null;

  function ensureConfirmModal() {
    if (confirmEl) return confirmEl;
    confirmEl = document.createElement('div');
    confirmEl.id = 'jdmConfirmModal';
    confirmEl.className = 'jdm-modal jdm-confirm-overlay';
    confirmEl.hidden = true;
    confirmEl.style.zIndex = '2350';
    confirmEl.innerHTML =
      '<div class="jdm-backdrop" data-jdm-confirm-cancel></div>' +
      '<div class="jdm-card jdm-confirm-card" role="alertdialog" aria-modal="true" aria-labelledby="jdmConfirmTitle" aria-describedby="jdmConfirmMsg" style="max-width:460px;">' +
        '<header class="jdm-header" style="padding:18px 22px 14px;">' +
          '<div style="min-width:0;flex:1;">' +
            '<div class="jdm-kicker" id="jdmConfirmKicker">CONFIRMACIÓN REQUERIDA</div>' +
            '<h2 class="jdm-title" id="jdmConfirmTitle" style="font-size:17px;">¿Deseas continuar?</h2>' +
          '</div>' +
          '<button type="button" class="jdm-close" data-jdm-confirm-cancel aria-label="Cerrar">&times;</button>' +
        '</header>' +
        '<div class="jdm-body" style="padding:18px 22px;">' +
          '<p id="jdmConfirmMsg" style="margin:0;font-size:13.5px;line-height:1.6;"></p>' +
        '</div>' +
        '<footer class="jdm-footer" style="padding:14px 22px;display:flex;justify-content:flex-end;gap:10px;">' +
          '<button type="button" class="jdm-btn jdm-btn-secondary" id="jdmConfirmBtnCancel" data-jdm-confirm-cancel>Cancelar</button>' +
          '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmConfirmBtnOk">Confirmar</button>' +
        '</footer>' +
      '</div>';
    document.body.appendChild(confirmEl);
    return confirmEl;
  }

  function confirmarAccion(opciones) {
    var opts = typeof opciones === 'string' ? { mensaje: opciones } : (opciones || {});
    var modal = ensureConfirmModal();
    var titleEl = document.getElementById('jdmConfirmTitle');
    var kickerEl = document.getElementById('jdmConfirmKicker');
    var msgEl = document.getElementById('jdmConfirmMsg');
    var btnOk = document.getElementById('jdmConfirmBtnOk');
    var btnCancel = document.getElementById('jdmConfirmBtnCancel');

    if (kickerEl) kickerEl.textContent = opts.kicker || (opts.peligro ? 'ACCIÓN CRÍTICA' : 'CONFIRMACIÓN REQUERIDA');
    if (titleEl) titleEl.textContent = opts.titulo || '¿Confirmar esta acción?';
    if (msgEl) msgEl.textContent = opts.mensaje || '¿Estás seguro de que deseas continuar?';
    if (btnOk) {
      btnOk.textContent = opts.textoConfirmar || 'Confirmar';
      btnOk.className = 'jdm-btn ' + (opts.peligro ? 'jdm-btn-danger' : 'jdm-btn-primary');
    }
    if (btnCancel) {
      btnCancel.textContent = opts.textoCancelar || 'Cancelar';
    }

    modal.hidden = false;

    return new Promise(function (resolve) {
      function limpiar(resultado) {
        modal.hidden = true;
        modal.removeEventListener('click', onClick);
        document.removeEventListener('keydown', onKey);
        resolve(resultado);
      }

      function onClick(e) {
        if (e.target.closest('#jdmConfirmBtnOk')) {
          e.preventDefault();
          limpiar(true);
        } else if (e.target.closest('[data-jdm-confirm-cancel]')) {
          e.preventDefault();
          limpiar(false);
        }
      }

      function onKey(e) {
        if (e.key === 'Escape' && !modal.hidden) {
          e.preventDefault();
          e.stopPropagation();
          limpiar(false);
        }
      }

      modal.addEventListener('click', onClick);
      document.addEventListener('keydown', onKey, true);
      if (btnOk) btnOk.focus();
    });
  }

  window.JdConfirm = confirmarAccion;
  window.jdToast = mostrarToast;

  // ─────────────────────────────────────────────────────────────
  // Modal Base Manager
  // ─────────────────────────────────────────────────────────────
  var modalEl = null;
  var lastFocusEl = null;

  function ensureModal() {
    if (modalEl) return modalEl;

    modalEl = document.createElement('div');
    modalEl.id = 'jdmModal';
    modalEl.className = 'jdm-modal';
    modalEl.hidden = true;
    modalEl.innerHTML =
      '<div class="jdm-backdrop" data-jdm-close></div>' +
      '<div class="jdm-card" id="jdmCard" role="dialog" aria-modal="true" aria-labelledby="jdmTitulo">' +
        '<header class="jdm-header">' +
          '<div style="min-width:0;flex:1;">' +
            '<div class="jdm-kicker" id="jdmKicker">// ACCIÓN</div>' +
            '<h2 class="jdm-title" id="jdmTitulo">Cargando…</h2>' +
            '<div class="jdm-sub" id="jdmSub"></div>' +
          '</div>' +
          '<button type="button" class="jdm-close" data-jdm-close aria-label="Cerrar">&times;</button>' +
        '</header>' +
        '<div class="jdm-body" id="jdmBody" aria-live="polite">' +
          '<div class="jdm-loading"><i data-lucide="loader-2"></i><span>Cargando información…</span></div>' +
        '</div>' +
        '<footer class="jdm-footer" id="jdmFooter" hidden></footer>' +
      '</div>';

    document.body.appendChild(modalEl);

    modalEl.addEventListener('click', function (e) {
      if (modalEl.dataset.obligatorio === 'true') return;
      if (e.target.closest('[data-jdm-close]')) {
        e.preventDefault();
        cerrarModal();
      }
    });

    document.addEventListener('keydown', function (e) {
      if (!modalEl || modalEl.hidden) return;
      if (e.key === 'Escape') {
        if (modalEl.dataset.obligatorio === 'true') {
          e.preventDefault();
          return;
        }
        e.preventDefault();
        cerrarModal();
      }
    });

    return modalEl;
  }

  function abrirModal(cardClass) {
    lastFocusEl = document.activeElement;
    ensureModal();
    var card = document.getElementById('jdmCard');
    card.className = 'jdm-card' + (cardClass ? ' ' + cardClass : '');
    modalEl.hidden = false;
    document.body.style.overflow = 'hidden';

    var body = document.getElementById('jdmBody');
    var footer = document.getElementById('jdmFooter');
    body.scrollTop = 0;
    body.innerHTML = '<div class="jdm-loading"><i data-lucide="loader-2"></i><span>Cargando información…</span></div>';
    footer.hidden = true;
    footer.innerHTML = '';
  }

  function cerrarModal(forzar) {
    if (!modalEl) return;
    if (!forzar && modalEl.dataset.obligatorio === 'true') return;
    modalEl.dataset.obligatorio = 'false';
    modalEl.hidden = true;
    document.body.style.overflow = '';
    var closeBtn = modalEl.querySelector('.jdm-close');
    if (closeBtn) closeBtn.style.display = 'flex';
    if (lastFocusEl && typeof lastFocusEl.focus === 'function') {
      try { lastFocusEl.focus(); } catch (err) {}
    }
  }

  function setHeader(kicker, titulo, sub) {
    var k = document.getElementById('jdmKicker');
    var t = document.getElementById('jdmTitulo');
    var s = document.getElementById('jdmSub');
    if (k) k.textContent = kicker || '';
    if (t) t.textContent = titulo || '';
    if (s) {
      s.textContent = sub || '';
      s.style.display = sub ? 'block' : 'none';
    }
  }

  function setContent(html) {
    var b = document.getElementById('jdmBody');
    if (b) b.innerHTML = html;
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  function setFooter(html) {
    var f = document.getElementById('jdmFooter');
    if (!f) return;
    if (html) {
      f.innerHTML = html;
      f.hidden = false;
    } else {
      f.innerHTML = '';
      f.hidden = true;
    }
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 1. CONTRATO DIGITAL
  // ─────────────────────────────────────────────────────────────
  async function cargarContratoDigital(url, triggerBtn) {
    abrirModal('');
    setHeader('ACUERDO LEGAL DE CONTRATACIÓN', 'Cargando contrato…');

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      var data = await res.json();
      var c = data.contrato || (data.id ? data : null);
      if (!c) throw new Error(data.error || 'No se pudo obtener el contrato');

      setHeader('ACUERDO LEGAL DE CONTRATACIÓN', 'Contrato Digital #' + (c.codigo || ''), 'Proyecto: ' + (c.proyecto_titulo || ''));

      var estadoCls = c.estado === 'firmado' ? 'jdm-badge-success' : 'jdm-badge-gray';

      var html =
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

      var clausulasArr = Array.isArray(c.clausulas) ? c.clausulas : (typeof c.clausulas === 'string' && c.clausulas.trim() ? [c.clausulas] : []);
      if (clausulasArr.length) {
        clausulasArr.forEach(function (clausula, i) {
          var limpia = String(clausula).replace(/^\d+[\.\)]\s*/, '').replace(/^CLÁUSULA\s*\d+[\.\:]\s*/i, '');
          html += '<div class="jdm-clause-item"><span class="jdm-clause-num">Cláusula ' + (i + 1) + '.</span> <span class="jdm-clause-text">' + escapeHtml(limpia) + '</span></div>';
        });
      } else {
        html += '<p style="color:#71717a; font-size:12.5px;">Sin cláusulas adicionales registradas.</p>';
      }
      html += '</div>';

      var perfil = c.perfil_profesional;
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

      var footerHtml = '<div style="display:flex; align-items:center; justify-content:space-between; width:100%; gap:14px; flex-wrap:wrap;">';
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

      var btnFirmar = document.getElementById('jdmBtnFirmar');
      if (btnFirmar) {
        btnFirmar.addEventListener('click', async function () {
          btnFirmar.disabled = true;
          btnFirmar.innerHTML = '<i data-lucide="loader-2"></i> Firmando...';
          try {
            var signBody = new FormData();
            signBody.append('acepta_terminos', 'on');
            signBody.append('origen', 'dashboard');
            var signRes = await fetch(btnFirmar.getAttribute('data-url-firmar'), {
              method: 'POST',
              headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
              },
              body: signBody,
              credentials: 'same-origin'
            });
            var signData = await signRes.json();
            if (signData.ok) {
              mostrarToast(signData.mensaje || '¡Contrato firmado exitosamente!');
              var devStatus = document.getElementById('jdmDevSignStatus');
              if (devStatus) {
                devStatus.innerHTML = '<span class="jdm-sign-ok"><i data-lucide="check-check"></i> Firmado ahora</span>';
              }
              var f = document.getElementById('jdmFooter');
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
  // 2. VER AVANCES & HISTORIAL
  // ─────────────────────────────────────────────────────────────
  async function cargarAvances(url) {
    abrirModal('jdm-card-lg');
    setHeader('HISTORIAL DE ENTREGAS', 'Cargando avances…');

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      var data = await parseJsonResponse(res, 'No se pudieron obtener los avances (respuesta inesperada del servidor).');
      if (!data.ok || !data.proyecto) throw new Error(data.error || data.mensaje || 'No se pudieron obtener los avances');

      var p = data.proyecto;
      setHeader('HISTORIAL DE ENTREGAS', p.titulo, 'Empresa: ' + p.empresa + ' · Estado: ' + p.estado_label);

      var html =
        '<div class="jdm-progress-header">' +
          '<div class="jdm-progress-top-row">' +
            '<span class="jdm-progress-lbl">PROGRESO GENERAL</span>' +
            '<span class="jdm-progress-pct">' + p.progreso + '% (' + p.hitos_completados + ' / ' + p.hitos_totales + ' hitos completados)</span>' +
          '</div>' +
          '<div class="jdm-progress-bar-bg">' +
            '<div class="jdm-progress-bar-fill" style="width:' + p.progreso + '%;"></div>' +
          '</div>' +
        '</div>';

      if (data.hitos && data.hitos.length) {
        html += '<div class="jdm-clean-label"><i data-lucide="list-check"></i> Hitos del Proyecto</div><div class="jdm-hitos-scroll">';
        data.hitos.forEach(function (h) {
          var iconCls = h.estado === 'completado' ? 'is-done' : (h.estado === 'en_revision' ? 'is-rev' : 'is-wait');
          var iconName = h.estado === 'completado' ? 'check-circle-2' : (h.estado === 'en_revision' ? 'clock' : 'circle');
          html +=
            '<div class="jdm-hito-pill ' + iconCls + '">' +
              '<i data-lucide="' + iconName + '"></i>' +
              '<div>' +
                '<strong class="jdm-hito-pill-title">' + escapeHtml(h.titulo) + '</strong>' +
                '<div class="jdm-hito-pill-state">' + escapeHtml(h.estado_label) + '</div>' +
              '</div>' +
            '</div>';
        });
        html += '</div>';
      }

      html += '<div class="jdm-clean-label"><i data-lucide="git-branch"></i> Registro de Entregas y Evidencias (' + (data.avances ? data.avances.length : 0) + ')</div>';

      if (data.avances && data.avances.length) {
        html += '<div class="jdm-advances-feed">';
        data.avances.forEach(function (a) {
          var badgeCls = a.estado === 'aprobado' ? 'jdm-badge-success' : (a.estado === 'rechazado' ? 'jdm-badge-danger' : 'jdm-badge-warning');
          html +=
            '<div class="jdm-advance-card">' +
              '<div class="jdm-advance-head">' +
                '<div>' +
                  '<div class="jdm-advance-title">' + escapeHtml(a.entregable_titulo) + '</div>' +
                  '<div class="jdm-advance-meta">Por ' + escapeHtml(a.desarrollador) + ' · ' + escapeHtml(a.fecha) + '</div>' +
                '</div>' +
                '<span class="jdm-badge ' + badgeCls + '">' + escapeHtml(a.estado_label) + '</span>' +
              '</div>' +
              '<div class="jdm-advance-desc">' + escapeHtml(a.descripcion) + '</div>';

          if (a.archivo_adjunto_url || a.archivo_url) {
            html += '<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;">';
            if (a.archivo_adjunto_url) {
              html += '<a href="' + escapeHtml(a.archivo_adjunto_url) + '" target="_blank" rel="noopener" class="jdm-advance-attachment"><i data-lucide="paperclip"></i> ' + escapeHtml(a.archivo_adjunto_nombre || 'Descargar archivo') + '</a>';
            }
            if (a.archivo_url) {
              html += '<a href="' + escapeHtml(a.archivo_url) + '" target="_blank" rel="noopener" class="jdm-advance-attachment"><i data-lucide="arrow-up-right"></i> Ver enlace externo</a>';
            }
            html += '</div>';
          }

          if (a.observaciones) {
            html += '<div class="jdm-advance-feedback"><i data-lucide="message-circle"></i> Observaciones: ' + escapeHtml(a.observaciones) + '</div>';
          }

          html += '</div>';
        });
        html += '</div>';
      } else {
        html += '<div class="jdm-empty"><i data-lucide="package-open"></i>No se han registrado entregas para este proyecto aún.</div>';
      }

      var footerBtns = '';
      if (data.puede_registrar && data.registrar_url) {
        footerBtns += '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmBtnIrRegistrar" data-url-registrar="' + escapeHtml(data.registrar_url) + '"><i data-lucide="pen"></i> Registrar Nuevo Avance</button>';
      }
      footerBtns += '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>';

      setContent(html);
      setFooter(footerBtns);

      var btnIrReg = document.getElementById('jdmBtnIrRegistrar');
      if (btnIrReg) {
        btnIrReg.addEventListener('click', function () {
          cargarFormularioAvance(btnIrReg.getAttribute('data-url-registrar'));
        });
      }

    } catch (err) {
      setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 3. REGISTRAR AVANCE FORMULARIO
  // ─────────────────────────────────────────────────────────────
  async function cargarFormularioAvance(url) {
    abrirModal('');
    setHeader('GESTIÓN DE ENTREGABLES', 'Registrar Avance Técnico', 'Cargando hitos pendientes…');

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      var data = await parseJsonResponse(res, 'No se pudieron consultar los hitos (respuesta inesperada del servidor).');
      if (!data.ok || !data.proyecto) throw new Error(data.error || data.mensaje || 'No se pudieron consultar los hitos');

      setHeader('GESTIÓN DE ENTREGABLES', 'Registrar Avance Técnico', 'Proyecto: ' + data.proyecto.titulo);

      var options = '<option value="">-- Selecciona el hito a reportar --</option>';
      if (data.hitos_pendientes && data.hitos_pendientes.length) {
        data.hitos_pendientes.forEach(function (h) {
          options += '<option value="' + h.id + '">' + escapeHtml(h.titulo) + '</option>';
        });
      }

      var html =
        '<form id="jdmFormAvance" enctype="multipart/form-data" novalidate>' +
          '<div id="jdmAvanceError" class="jdm-error" style="display:none;"></div>' +

          '<div class="jdm-form-group">' +
            '<label class="jdm-form-label" for="jdmHitoSelect">Hito correspondiente <span class="req">*</span></label>' +
            '<select id="jdmHitoSelect" name="entregable_id" class="jdm-select" required>' + options + '</select>' +
          '</div>' +

          '<div class="jdm-form-group">' +
            '<label class="jdm-form-label" for="jdmDescAvance">Descripción detallada del avance realizado <span class="req">*</span></label>' +
            '<textarea id="jdmDescAvance" name="descripcion" class="jdm-textarea" placeholder="Explica qué implementaste, pruebas realizadas y consideraciones técnicas…" required></textarea>' +
          '</div>' +

          '<div class="jdm-form-group">' +
            '<label class="jdm-form-label" for="jdmUrlAvance">URL de evidencia o repositorio (opcional si adjuntas archivo)</label>' +
            '<input type="url" id="jdmUrlAvance" name="archivo_url" class="jdm-input" placeholder="https://github.com/... o enlace a demo">' +
          '</div>' +

          '<div class="jdm-form-group">' +
            '<label class="jdm-form-label" for="jdmArchivoAvance">Archivo adjunto (ZIP, PDF, imagen, max 10MB)</label>' +
            '<input type="file" id="jdmArchivoAvance" name="archivo_adjunto" class="jdm-input" style="padding:6px;">' +
          '</div>' +
        '</form>';

      setContent(html);
      setFooter(
        '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cancelar</button>' +
        '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmBtnEnviarAvance"><i data-lucide="upload-cloud"></i> Registrar Avance</button>'
      );

      var btnEnviar = document.getElementById('jdmBtnEnviarAvance');
      var form = document.getElementById('jdmFormAvance');

      if (btnEnviar && form) {
        btnEnviar.addEventListener('click', async function () {
          var hito = form.querySelector('[name="entregable_id"]').value;
          var desc = form.querySelector('[name="descripcion"]').value.trim();
          var urlEv = form.querySelector('[name="archivo_url"]').value.trim();
          var file = form.querySelector('[name="archivo_adjunto"]').files[0];
          var errBox = document.getElementById('jdmAvanceError');

          if (!hito) {
            errBox.style.display = 'flex';
            errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>Debes seleccionar un hito.</span>';
            return;
          }
          if (!desc) {
            errBox.style.display = 'flex';
            errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>Debes ingresar una descripción del avance.</span>';
            return;
          }
          if (!urlEv && !file) {
            errBox.style.display = 'flex';
            errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>Debes ingresar una URL de evidencia o adjuntar un archivo.</span>';
            return;
          }

          errBox.style.display = 'none';
          btnEnviar.disabled = true;
          btnEnviar.innerHTML = '<i data-lucide="loader-2"></i> Registrando...';

          try {
            var formData = new FormData(form);
            var postRes = await fetch(data.url_registrar, {
              method: 'POST',
              headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
              },
              body: formData,
              credentials: 'same-origin'
            });

            var resJson = await postRes.json();
            if (resJson.status === 'ok' || resJson.ok) {
              mostrarToast(resJson.mensaje || '¡Avance registrado exitosamente!');
              cerrarModal();
              setTimeout(function () { window.location.reload(); }, 1200);
            } else {
              errBox.style.display = 'flex';
              errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>' + escapeHtml(resJson.error || resJson.mensaje || 'Error al guardar avance') + '</span>';
              btnEnviar.disabled = false;
              btnEnviar.innerHTML = '<i data-lucide="upload-cloud"></i> Registrar Avance';
            }
          } catch (e) {
            errBox.style.display = 'flex';
            errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>Error de conexión al enviar el avance.</span>';
            btnEnviar.disabled = false;
            btnEnviar.innerHTML = '<i data-lucide="upload-cloud"></i> Registrar Avance';
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
  async function cargarCalificarEmpresa(url, triggerBtn, esObligatorio) {
    abrirModal('jdm-card-sm');
    if (modalEl) modalEl.dataset.obligatorio = esObligatorio ? 'true' : 'false';
    var closeBtn = modalEl ? modalEl.querySelector('.jdm-close') : null;
    if (closeBtn) closeBtn.style.display = esObligatorio ? 'none' : 'flex';

    setHeader(
      esObligatorio ? 'EVALUACIÓN OBLIGATORIA' : 'PROYECTO // VALORACIÓN',
      'Cargando calificación…'
    );

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      var data = await parseJsonResponse(res, 'No se pudo cargar la valoración (respuesta inesperada del servidor).');
      if (!data.ok || !data.proyecto) throw new Error(data.error || data.mensaje || 'No se pudo cargar la valoración');

      var p = data.proyecto;
      setHeader(
        esObligatorio ? 'EVALUACIÓN OBLIGATORIA' : 'VALORAR EMPRESA',
        p.empresa,
        'Proyecto finalizado: ' + p.titulo
      );

      if (data.ya_califico) {
        if (modalEl) modalEl.dataset.obligatorio = 'false';
        if (closeBtn) closeBtn.style.display = 'flex';
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

      var avisoHtml = esObligatorio
        ? '<div style="display:flex;align-items:flex-start;gap:10px;padding:12px 14px;border-radius:6px;background:rgba(255,171,0,0.08);border:1px solid rgba(255,171,0,0.3);color:#ffab00;font-size:12.5px;margin-bottom:16px;line-height:1.45;">' +
            '<i data-lucide="shield-alert" style="width:18px;height:18px;flex-shrink:0;margin-top:1px;"></i>' +
            '<div><strong>Evaluación requerida:</strong> El proyecto ha finalizado. Para continuar navegando en tu panel, califica tu experiencia colaborando con la empresa.</div>' +
          '</div>'
        : '';

      var html =
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

      var puntuacionVal = 0;
      var stars = document.querySelectorAll('#jdmStars .jdm-star-btn');
      var caption = document.getElementById('jdmRatingCaption');
      var inputPunt = document.getElementById('jdmInputPuntuacion');
      var txtComentario = document.getElementById('jdmComentario');
      var charCount = document.getElementById('jdmCharCount');
      var captions = ['', '1/5 - Muy insatisfactorio', '2/5 - Regular', '3/5 - Aceptable', '4/5 - Muy bueno', '5/5 - Excelente'];

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
        var len = txtComentario.value.trim().length;
        charCount.textContent = len + ' / 20 caracteres mínimos';
        charCount.style.color = len >= 20 ? '#00e676' : '#666666';
      });

      var btnEnviar = document.getElementById('jdmBtnEnviarCalificacion');
      btnEnviar.addEventListener('click', async function () {
        var errBox = document.getElementById('jdmCalificarError');
        var com = txtComentario.value.trim();

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
          var formData = new FormData();
          formData.append('puntuacion', puntuacionVal);
          formData.append('comentario', com);
          formData.append('origen', 'dashboard');

          var postRes = await fetch(data.url_calificar, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': getCsrfToken()
            },
            body: formData,
            credentials: 'same-origin'
          });

          var resJson = await postRes.json();
          if (resJson.ok) {
            mostrarToast(resJson.mensaje || '¡Calificación enviada!');
            cerrarModal(true);
            if (triggerBtn) {
              triggerBtn.classList.remove('btn-primary', 'primary');
              triggerBtn.classList.add('btn-secondary');
              triggerBtn.innerHTML = '<i data-lucide="check-circle-2" style="color:#00e676;"></i> Empresa calificada (' + puntuacionVal + '/5)';
              triggerBtn.disabled = true;
            }
            document.querySelectorAll('.calificar-popup-overlay').forEach(function(p) { p.remove(); });
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
      setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 5. DETALLE EMPRESA
  // ─────────────────────────────────────────────────────────────
  async function cargarDetalleEmpresa(url) {
    abrirModal('');
    setHeader('PERFIL // INSTITUCIONAL', 'Cargando perfil de empresa…');

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      var data = await res.json();
      if (!data.ok || !data.empresa) throw new Error(data.error || 'No se pudo obtener el perfil de la empresa');

      var e = data.empresa;
      setHeader('EMPRESA // FICHA INSTITUCIONAL', e.nombre, e.sector + ' · ' + e.ciudad);

      var badgeHtml = e.es_verificada
        ? '<span class="jdm-badge jdm-badge-success"><i data-lucide="check-circle"></i> ' + escapeHtml(e.badge_label || 'Verificada') + '</span>'
        : '<span class="jdm-badge jdm-badge-gray"><i data-lucide="shield"></i> ' + escapeHtml(e.badge_label || 'Sin verificar') + '</span>';

      var initial = (e.nombre || 'E').slice(0, 1).toUpperCase();
      var avatarInner = e.logo_url
        ? '<img src="' + escapeHtml(e.logo_url) + '" alt="' + escapeHtml(e.nombre) + '" class="jdm-empresa-logo-img">'
        : escapeHtml(initial);

      var html =
        '<div class="jdm-empresa-header">' +
          '<div class="jdm-empresa-avatar">' + avatarInner + '</div>' +
          '<div>' +
            '<div class="jdm-empresa-name">' +
              escapeHtml(e.nombre) + ' ' + badgeHtml +
            '</div>' +
            '<div class="jdm-empresa-meta">@' + escapeHtml(e.username) + ' · ' + escapeHtml(e.sector) + ' (' + escapeHtml(e.ciudad) + ')</div>' +
          '</div>' +
        '</div>' +

        '<div class="jdm-empresa-stats-flat">' +
          '<div class="jdm-stat-flat">' +
            '<span class="jdm-stat-val">⭐ ' + e.reputacion + '</span>' +
            '<span class="jdm-stat-lbl">Reputación</span>' +
          '</div>' +
          '<div class="jdm-stat-flat-divider"></div>' +
          '<div class="jdm-stat-flat">' +
            '<span class="jdm-stat-val">' + e.total_resenas + '</span>' +
            '<span class="jdm-stat-lbl">Reseñas</span>' +
          '</div>' +
          '<div class="jdm-stat-flat-divider"></div>' +
          '<div class="jdm-stat-flat">' +
            '<span class="jdm-stat-val">' + e.proyectos_activos + '</span>' +
            '<span class="jdm-stat-lbl">Activos</span>' +
          '</div>' +
          '<div class="jdm-stat-flat-divider"></div>' +
          '<div class="jdm-stat-flat">' +
            '<span class="jdm-stat-val">' + e.proyectos_finalizados + '</span>' +
            '<span class="jdm-stat-lbl">Finalizados</span>' +
          '</div>' +
        '</div>' +

        '<div class="jdm-section-clean">' +
          '<div class="jdm-clean-label"><i data-lucide="building"></i> Acerca de la empresa</div>' +
          '<p class="jdm-clean-desc">' +
            escapeHtml(e.descripcion || 'Sin descripción corporativa registrada.') +
          '</p>' +
        '</div>' +

        '<div class="jdm-section-clean">' +
          '<div class="jdm-clean-label"><i data-lucide="message-circle"></i> Reseñas de desarrolladores (' + (e.resenas ? e.resenas.length : 0) + ')</div>';

      if (e.resenas && e.resenas.length) {
        html += '<div class="jdm-resenas-flat-list">';
        e.resenas.forEach(function (r) {
          html +=
            '<div class="jdm-resena-flat-item">' +
              '<div class="jdm-resena-header">' +
                '<strong class="jdm-resena-author">' + escapeHtml(r.desarrollador) + ' <span class="jdm-resena-project">en ' + escapeHtml(r.proyecto_titulo) + '</span></strong>' +
                '<span class="jdm-resena-rating">⭐ ' + r.puntuacion + '/5</span>' +
              '</div>' +
              '<p class="jdm-resena-comment">"' + escapeHtml(r.comentario) + '"</p>' +
              '<div class="jdm-resena-date">' + escapeHtml(r.fecha) + '</div>' +
            '</div>';
        });
        html += '</div>';
      } else {
        html += '<div class="jdm-empty" style="padding:16px 0;"><i data-lucide="message-square-off"></i>Aún no registra reseñas de proyectos finalizados.</div>';
      }

      html += '</div>';

      setContent(html);
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');

    } catch (err) {
      setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 5B. DETALLE PÚBLICO DE DESARROLLADOR (IN-SITU)
  // ─────────────────────────────────────────────────────────────
  async function cargarDetalleDesarrollador(url) {
    abrirModal('');
    setHeader('TALENTO SENA // PERFIL PÚBLICO', 'Cargando perfil profesional…');

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      var data = await parseJsonResponse(res, 'No se pudo obtener el perfil del desarrollador.');
      if (!data.ok || !data.desarrollador) throw new Error(data.error || 'No se pudo obtener el perfil del desarrollador');

      var d = data.desarrollador;
      setHeader('TALENTO SENA // PERFIL PÚBLICO', d.nombre, d.programa_formacion + ' · Ficha ' + d.ficha);

      var badgeHtml = d.es_verificado_sena
        ? '<span class="jdm-badge jdm-badge-success"><i data-lucide="check-circle"></i> ' + escapeHtml(d.badge_label || 'Verificado SENA') + '</span>'
        : '<span class="jdm-badge jdm-badge-gray"><i data-lucide="id-card"></i> ' + escapeHtml(d.badge_label || 'Sin verificar') + '</span>';

      var initial = (d.nombre || 'D').slice(0, 1).toUpperCase();
      var avatarInner = d.foto_url
        ? '<img src="' + escapeHtml(d.foto_url) + '" alt="' + escapeHtml(d.nombre) + '" class="jdm-empresa-logo-img">'
        : escapeHtml(initial);

      var html =
        '<div class="jdm-empresa-header">' +
          '<div class="jdm-empresa-avatar">' + avatarInner + '</div>' +
          '<div>' +
            '<div class="jdm-empresa-name">' +
              escapeHtml(d.nombre) + ' ' + badgeHtml +
            '</div>' +
            '<div class="jdm-empresa-meta">@' + escapeHtml(d.username) + ' · ' + escapeHtml(d.condicion_sena) + ' SENA (' + escapeHtml(d.programa_formacion) + ')</div>' +
          '</div>' +
        '</div>' +

        '<div class="jdm-empresa-stats-flat">' +
          '<div class="jdm-stat-flat">' +
            '<span class="jdm-stat-val">⭐ ' + d.reputacion + '</span>' +
            '<span class="jdm-stat-lbl">Reputación</span>' +
          '</div>' +
          '<div class="jdm-stat-flat-divider"></div>' +
          '<div class="jdm-stat-flat">' +
            '<span class="jdm-stat-val">' + d.total_resenas + '</span>' +
            '<span class="jdm-stat-lbl">Reseñas</span>' +
          '</div>' +
          '<div class="jdm-stat-flat-divider"></div>' +
          '<div class="jdm-stat-flat">' +
            '<span class="jdm-stat-val">' + d.proyectos_activos + '</span>' +
            '<span class="jdm-stat-lbl">Activos</span>' +
          '</div>' +
          '<div class="jdm-stat-flat-divider"></div>' +
          '<div class="jdm-stat-flat">' +
            '<span class="jdm-stat-val">' + d.proyectos_finalizados + '</span>' +
            '<span class="jdm-stat-lbl">Finalizados</span>' +
          '</div>' +
        '</div>' +

        '<div class="jdm-section-clean">' +
          '<div class="jdm-clean-label"><i data-lucide="award"></i> Habilidades Técnicas</div>' +
          '<div style="display:flex;flex-wrap:wrap;gap:6px;">';
      if (d.habilidades && d.habilidades.length) {
        d.habilidades.forEach(function (hab) {
          html += '<span class="jdm-badge jdm-badge-gray" style="text-transform:none;font-size:11.5px;">' + escapeHtml(hab) + '</span>';
        });
      } else {
        html += '<span style="font-size:12.5px;color:var(--text-muted,#94a3b8);">Sin habilidades técnicas registradas.</span>';
      }
      html += '</div></div>';

      if (d.portafolio_url) {
        html += '<div class="jdm-section-clean">' +
          '<div class="jdm-clean-label"><i data-lucide="globe"></i> Portafolio / Repositorio</div>' +
          '<a href="' + escapeHtml(d.portafolio_url) + '" target="_blank" rel="noopener" class="jdm-advance-attachment">' +
            '<i data-lucide="external-link"></i> ' + escapeHtml(d.portafolio_url) +
          '</a>' +
        '</div>';
      }

      html += '<div class="jdm-section-clean">' +
        '<div class="jdm-clean-label"><i data-lucide="message-circle"></i> Valoraciones de Empresas (' + (d.resenas ? d.resenas.length : 0) + ')</div>';

      if (d.resenas && d.resenas.length) {
        html += '<div class="jdm-resenas-flat-list">';
        d.resenas.forEach(function (r) {
          html +=
            '<div class="jdm-resena-flat-item">' +
              '<div class="jdm-resena-header">' +
                '<strong class="jdm-resena-author">' + escapeHtml(r.empresa) + ' <span class="jdm-resena-project">en ' + escapeHtml(r.proyecto_titulo) + '</span></strong>' +
                '<span class="jdm-resena-rating">⭐ ' + r.puntuacion + '/5</span>' +
              '</div>' +
              '<p class="jdm-resena-comment">"' + escapeHtml(r.comentario) + '"</p>' +
              '<div class="jdm-resena-date">' + escapeHtml(r.fecha) + '</div>' +
            '</div>';
        });
        html += '</div>';
      } else {
        html += '<div class="jdm-empty" style="padding:16px 0;"><i data-lucide="message-square-off"></i>Aún no registra valoraciones de empresas contratantes.</div>';
      }

      html += '</div>';

      setContent(html);
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');

    } catch (err) {
      setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 6. SALA DE DISPUTA & EXPEDIENTE
  // ─────────────────────────────────────────────────────────────
  async function cargarSalaDisputa(url) {
    abrirModal('jdm-card-lg');
    setHeader('DISPUTAS // SALA DE MEDIACIÓN', 'Cargando expediente arbitral…');

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      var data = await res.json();
      if (!data.ok || !data.disputa) throw new Error(data.error || 'No se pudo obtener el expediente de disputa');

      var d = data.disputa;
      setHeader('SALA DE MEDIACIÓN #' + d.id, d.proyecto_titulo, 'Causal: ' + d.categoria + ' · Estado: ' + d.estado_label);

      var estadoCls = d.estado === 'resuelta' ? 'jdm-badge-success' : (d.estado === 'cancelada' ? 'jdm-badge-gray' : 'jdm-badge-danger');

      var html =
        '<div class="jdm-disputa-summary">' +
          '<div class="jdm-disputa-summary-top">' +
            '<div>' +
              '<span class="jdm-badge ' + estadoCls + '">' + escapeHtml(d.estado_label) + '</span> ' +
              '<span class="jdm-badge jdm-badge-gray">' + escapeHtml(d.categoria) + '</span>' +
            '</div>' +
            '<div class="jdm-disputa-iniciado">Iniciada por: <strong>' + escapeHtml(d.iniciado_por) + '</strong></div>' +
          '</div>' +
          '<div class="jdm-disputa-parties-grid">' +
            '<div>Empresa: <strong>' + escapeHtml(d.empresa) + '</strong></div>' +
            '<div>Desarrollador: <strong>' + escapeHtml(d.desarrollador) + '</strong></div>' +
            '<div>Mediador JobDevs: <strong>' + escapeHtml(d.mediador) + '</strong></div>' +
          '</div>' +
          '<div class="jdm-disputa-motivo-box">' +
            '<strong>Motivo de apertura:</strong> ' + escapeHtml(d.motivo) +
            (d.evidencia_url ? '<div style="margin-top:4px;"><a href="' + escapeHtml(d.evidencia_url) + '" target="_blank" rel="noopener" class="jdm-disputa-evidencia-link"><i data-lucide="link"></i> Ver enlace de evidencia</a></div>' : '') +
          '</div>';

      if (d.resolucion) {
        html +=
          '<div class="jdm-disputa-resolucion-box">' +
            '<div class="jdm-resolucion-header"><i data-lucide="gavel"></i> RESOLUCIÓN ARBITRAL EMITIDA: ' + escapeHtml(d.resolucion) + '</div>' +
            (d.dictamen ? '<div class="jdm-resolucion-dictamen">Dictamen: ' + escapeHtml(d.dictamen) + '</div>' : '') +
          '</div>';
      }

      html += '</div>';

      html +=
        '<div class="jdm-form-label"><i data-lucide="message-circle"></i> Mensajes y Argumentos de Mediación</div>' +
        '<div class="jdm-disputa-chat" id="jdmDisputaChat">';

      if (data.mensajes && data.mensajes.length) {
        data.mensajes.forEach(function (m) {
          var bubbleType = m.rol === 'administrador' ? 'jdm-bubble-admin' : (m.es_propio ? 'jdm-bubble-own' : 'jdm-bubble-other');
          html +=
            '<div class="jdm-chat-bubble ' + bubbleType + '">' +
              '<div class="jdm-bubble-header">' +
                '<span>' + escapeHtml(m.emisor) + ' (' + escapeHtml(m.rol) + ')</span>' +
                '<span>' + escapeHtml(m.fecha) + '</span>' +
              '</div>' +
              '<div>' + escapeHtml(m.contenido) + '</div>' +
            '</div>';
        });
      } else {
        html += '<div class="jdm-empty" style="padding:20px;"><i data-lucide="message-circle"></i>Aún no hay mensajes en esta sala.</div>';
      }

      html += '</div>';

      if (d.puede_escribir) {
        html +=
          '<form id="jdmFormDisputaMsg" class="jdm-disputa-composer" novalidate>' +
            '<input type="text" id="jdmMsgContenido" name="contenido" class="jdm-input" placeholder="Escribe un mensaje para los participantes y el mediador…" autocomplete="off" required>' +
            '<button type="submit" class="jdm-btn jdm-btn-primary" id="jdmBtnEnviarMsg"><i data-lucide="send"></i></button>' +
          '</form>';
      }

      // Panel de resolución si es Admin y la disputa no está resuelta
      if (d.es_admin && d.resolver_url && d.estado !== 'resuelta' && d.estado !== 'cancelada') {
        var resolucionesOptions = '<option value="">-- Selecciona el sentido de la resolución --</option>';
        (d.resoluciones || []).forEach(function (r) {
          resolucionesOptions += '<option value="' + escapeHtml(r.codigo) + '">' + escapeHtml(r.label) + '</option>';
        });
        html +=
          '<div class="jdm-admin-resolution-box">' +
            '<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;font-weight:700;color:#f87171;margin-bottom:8px;"><i data-lucide="gavel"></i> PANEL DE RESOLUCIÓN ARBITRAL (ADMIN)</div>' +
            '<form id="jdmFormResolverDisputa" novalidate>' +
              '<div class="jdm-form-group">' +
                '<label class="jdm-form-label">Dictamen de Fallo <span class="req">*</span></label>' +
                '<select name="resolucion" class="jdm-select" required>' +
                  resolucionesOptions +
                '</select>' +
              '</div>' +
              '<div class="jdm-form-group">' +
                '<label class="jdm-form-label">Fundamentos / Notas de la resolución <span class="req">*</span></label>' +
                '<textarea name="dictamen" class="jdm-textarea" placeholder="Indica detalladamente los argumentos técnicos y evidencias consideradas para este dictamen…" required></textarea>' +
              '</div>' +
              '<button type="submit" class="jdm-btn jdm-btn-danger" id="jdmBtnResolver"><i data-lucide="gavel"></i> Emitir Resolución Final</button>' +
            '</form>' +
          '</div>';
      }

      setContent(html);
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar Expediente</button>');

      var chatBox = document.getElementById('jdmDisputaChat');
      if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;

      // Listener enviar mensaje
      var formMsg = document.getElementById('jdmFormDisputaMsg');
      if (formMsg) {
        formMsg.addEventListener('submit', async function (e) {
          e.preventDefault();
          var inp = document.getElementById('jdmMsgContenido');
          var txt = inp ? inp.value.trim() : '';
          if (!txt) return;

          var btn = document.getElementById('jdmBtnEnviarMsg');
          btn.disabled = true;

          try {
            var fData = new FormData();
            fData.append('contenido', txt);
            var mRes = await fetch(d.enviar_url, {
              method: 'POST',
              headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
              },
              body: fData,
              credentials: 'same-origin'
            });
            var mJson = await mRes.json();
            if (mJson.ok) {
              inp.value = '';
              cargarSalaDisputa(url);
            } else {
              mostrarToast(mJson.error || 'No se pudo enviar el mensaje', true);
            }
          } catch (err) {
            mostrarToast('Error al enviar mensaje.', true);
          } finally {
            btn.disabled = false;
          }
        });
      }

      // Listener resolver disputa (Admin)
      var formResolver = document.getElementById('jdmFormResolverDisputa');
      if (formResolver) {
        formResolver.addEventListener('submit', async function (e) {
          e.preventDefault();
          var resSel = formResolver.querySelector('[name="resolucion"]').value;
          var dictTxt = formResolver.querySelector('[name="dictamen"]').value.trim();

          if (!resSel || !dictTxt) {
            mostrarToast('Debes seleccionar el fallo y redactar el dictamen.', true);
            return;
          }

          var confirmado = await confirmarAccion({
            kicker: 'RESOLUCIÓN ARBITRAL VINCULANTE',
            titulo: 'Confirmar Emisión de Dictamen',
            mensaje: '¿Confirmas la emisión definitiva de esta resolución arbitral? Esta acción es irreversible y aplicará efectos inmediatos sobre el contrato.',
            textoConfirmar: 'Emitir Resolución',
            peligro: true
          });
          if (!confirmado) {
            return;
          }

          var btnR = document.getElementById('jdmBtnResolver');
          btnR.disabled = true;
          btnR.innerHTML = '<i data-lucide="loader-2"></i> Procesando resolución...';

          try {
            var rData = new FormData(formResolver);
            rData.append('origen', 'dashboard');
            var rRes = await fetch(d.resolver_url, {
              method: 'POST',
              headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
              },
              body: rData,
              credentials: 'same-origin'
            });
            var rJson = await rRes.json();
            if (rJson.ok) {
              mostrarToast(rJson.mensaje || 'Resolución arbitral aplicada.');
              cerrarModal();
              setTimeout(function () { window.location.reload(); }, 1200);
            } else {
              mostrarToast(rJson.mensaje || 'Error al resolver la disputa.', true);
              btnR.disabled = false;
              btnR.innerHTML = '<i data-lucide="gavel"></i> Emitir Resolución Final';
            }
          } catch (err) {
            mostrarToast('Error de red al procesar la resolución.', true);
            btnR.disabled = false;
            btnR.innerHTML = '<i data-lucide="gavel"></i> Emitir Resolución Final';
          }
        });
      }

    } catch (err) {
      setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 7. ABRIR DISPUTA FORMULARIO
  // ─────────────────────────────────────────────────────────────
  async function cargarFormularioAbrirDisputa(url) {
    abrirModal('');
    setHeader('ARBITRAJE CONTRACTUAL', 'Consultando proyecto…');

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      var data = await res.json();
      if (!data.ok || !data.proyecto) throw new Error(data.error || 'No se pudo consultar el proyecto');

      var p = data.proyecto;
      setHeader('ARBITRAJE CONTRACTUAL', 'Apertura de Mediación Formal', 'Proyecto: ' + escapeHtml(p.titulo) + ' · Empresa: ' + escapeHtml(p.empresa));

      var catOptions = '<option value="">-- Selecciona causal de disputa --</option>';
      if (data.categorias && data.categorias.length) {
        data.categorias.forEach(function (c) {
          catOptions += '<option value="' + escapeHtml(c.codigo) + '"' + (c.codigo === data.categoria ? ' selected' : '') + '>' + escapeHtml(c.label) + '</option>';
        });
      }

      var html =
        '<form id="jdmFormNuevaDisputa" novalidate>' +
          '<div id="jdmDisputaError" class="jdm-error" style="display:none;"></div>' +

          '<div style="background:rgba(255, 255, 255, 0.015); border:1px solid rgba(255, 255, 255, 0.08); border-radius:10px; padding:14px 18px; margin-bottom:18px;">' +
            '<div style="display:flex; align-items:center; gap:8px; font-family:var(--font-mono); font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; color:#f87171; margin-bottom:6px;">' +
              '<i data-lucide="alert-triangle" style="width:14px; height:14px; color:#f87171;"></i>' +
              '<span>Efectos Contractuales del Arbitraje</span>' +
            '</div>' +
            '<p style="font-size:12.5px; line-height:1.6; color:#94a3b8; margin:0;">' +
              'La mediación <strong>congela de inmediato</strong> el proyecto y su contratación hasta la emisión del dictamen final. Fuerza mayor permite revisión neutral sin atribuir incumplimiento ni sanciones automáticas.' +
            '</p>' +
          '</div>' +

          '<div class="jdm-form-group">' +
            '<label class="jdm-form-label" for="jdmCatDisputa">Causal de la disputa <span class="req">*</span></label>' +
            '<select id="jdmCatDisputa" name="categoria" class="jdm-select" required>' + catOptions + '</select>' +
          '</div>' +

          '<div class="jdm-form-group">' +
            '<label class="jdm-form-label" for="jdmMotivoDisputa">Motivo y hechos detallados <span class="req">*</span></label>' +
            '<textarea id="jdmMotivoDisputa" name="motivo" class="jdm-textarea" placeholder="Describe los hechos y los intentos de acuerdo previo…" required></textarea>' +
          '</div>' +

          '<div class="jdm-form-group">' +
            '<label class="jdm-form-label" for="jdmEvidenciaDisputa">Enlace a pruebas o evidencias (opcional)</label>' +
            '<input type="url" id="jdmEvidenciaDisputa" name="evidencia_url" class="jdm-input" placeholder="https://drive.google.com/... o enlace de evidencias">' +
          '</div>' +

          '<div style="background:rgba(255, 255, 255, 0.015); border:1px solid rgba(255, 255, 255, 0.08); border-radius:10px; padding:14px 18px; display:flex; flex-direction:column; gap:10px; margin-top:16px;">' +
            '<label style="display:flex; align-items:flex-start; gap:10px; font-size:12.5px; color:#cbd5e1; cursor:pointer;">' +
              '<input type="checkbox" name="confirma_intento_previo" style="margin-top:3px;" required>' +
              '<span>Intenté llegar a un acuerdo por los canales de comunicación directos.</span>' +
            '</label>' +
            '<label style="display:flex; align-items:flex-start; gap:10px; font-size:12.5px; color:#cbd5e1; cursor:pointer;" id="jdmDeclaracionGravedad">' +
              '<input type="checkbox" name="confirma_gravedad" style="margin-top:3px;" required>' +
              '<span>Declaro que existe un conflicto grave que requiere la intervención de un mediador.</span>' +
            '</label>' +
            '<label style="display:flex; align-items:flex-start; gap:10px; font-size:12.5px; color:#cbd5e1; cursor:pointer;">' +
              '<input type="checkbox" id="jdmAceptaSanciones" name="acepta_sanciones" style="margin-top:3px;" required>' +
              '<span>Acepto las reglas de mediación y comprendo que el proyecto quedará congelado hasta el dictamen arbitral vinculante.</span>' +
            '</label>' +
          '</div>' +
        '</form>';

      setContent(html);
      setFooter(
        '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cancelar</button>' +
        '<button type="button" class="jdm-btn" id="jdmBtnConfirmarDisputa" style="background:#e11d48; color:#ffffff; font-weight:600; border:1px solid rgba(225, 29, 72, 0.4);"><i data-lucide="gavel"></i> Abrir Disputa Formal</button>'
      );

      var btnConf = document.getElementById('jdmBtnConfirmarDisputa');
      var formD = document.getElementById('jdmFormNuevaDisputa');

      if (btnConf && formD) {
        var categoriaD = formD.querySelector('[name="categoria"]');
        var gravedadD = formD.querySelector('[name="confirma_gravedad"]');
        function actualizarDeclaraciones() {
          var esFuerzaMayor = categoriaD.value === 'fuerza_mayor';
          gravedadD.disabled = esFuerzaMayor;
          gravedadD.required = !esFuerzaMayor;
          document.getElementById('jdmDeclaracionGravedad').hidden = esFuerzaMayor;
          if (esFuerzaMayor) gravedadD.checked = false;
        }
        categoriaD.addEventListener('change', actualizarDeclaraciones);
        actualizarDeclaraciones();
        btnConf.addEventListener('click', async function () {
          var cat = formD.querySelector('[name="categoria"]').value;
          var mot = formD.querySelector('[name="motivo"]').value.trim();
          var check = formD.querySelector('[name="acepta_sanciones"]').checked;
          var errBox = document.getElementById('jdmDisputaError');

          if (!cat) {
            errBox.style.display = 'flex';
            errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>Debes seleccionar una causal.</span>';
            return;
          }
          if (!mot) {
            errBox.style.display = 'flex';
            errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>Debes relatar el motivo de la disputa.</span>';
            return;
          }
          if (!check) {
            errBox.style.display = 'flex';
            errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>Debes aceptar la declaración de responsabilidad.</span>';
            return;
          }

          if (!formD.reportValidity()) return;

          errBox.style.display = 'none';
          btnConf.disabled = true;
          btnConf.innerHTML = '<i data-lucide="loader-2"></i> Formalizando...';

          try {
            var fData = new FormData(formD);
            fData.append('origen', 'dashboard');

            var postRes = await fetch(data.url_abrir, {
              method: 'POST',
              headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
              },
              body: fData,
              credentials: 'same-origin'
            });

            var resJson = await postRes.json();
            if (resJson.ok) {
              mostrarToast(resJson.mensaje || 'Disputa abierta formalmente.');
              cerrarModal();
              setTimeout(function () { window.location.reload(); }, 1200);
            } else {
              errBox.style.display = 'flex';
              errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>' + escapeHtml(resJson.mensaje || 'Error al abrir disputa') + '</span>';
              btnConf.disabled = false;
              btnConf.innerHTML = '<i data-lucide="gavel"></i> Abrir Disputa Formal';
            }
          } catch (e) {
            errBox.style.display = 'flex';
            errBox.innerHTML = '<i data-lucide="alert-circle"></i><span>Error de red al formalizar la disputa.</span>';
            btnConf.disabled = false;
            btnConf.innerHTML = '<i data-lucide="gavel"></i> Abrir Disputa Formal';
          }
        });
      }

    } catch (err) {
      setContent('<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>' + escapeHtml(err.message) + '</span></div>');
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Event Delegation Global
  // ─────────────────────────────────────────────────────────────
  document.addEventListener('click', function (e) {
    // 1. Contrato Digital
    var btnContrato = e.target.closest('[data-abrir-contrato]');
    if (btnContrato) {
      e.preventDefault();
      var urlContrato = btnContrato.getAttribute('data-url') || btnContrato.getAttribute('href');
      if (urlContrato) cargarContratoDigital(urlContrato, btnContrato);
      return;
    }

    // 2. Avances / Historial
    var btnAvances = e.target.closest('[data-abrir-avances]');
    if (btnAvances) {
      e.preventDefault();
      var urlAvances = btnAvances.getAttribute('data-url') || btnAvances.getAttribute('href');
      if (urlAvances) cargarAvances(urlAvances);
      return;
    }

    // 3. Registrar Avance
    var btnRegAvance = e.target.closest('[data-abrir-registrar-avance]');
    if (btnRegAvance) {
      e.preventDefault();
      var urlRegAvance = btnRegAvance.getAttribute('data-url') || btnRegAvance.getAttribute('href');
      if (urlRegAvance) cargarFormularioAvance(urlRegAvance);
      return;
    }

    // 4. Calificar Empresa
    var btnCalificar = e.target.closest('[data-abrir-calificar]');
    if (btnCalificar) {
      e.preventDefault();
      var urlCalificar = btnCalificar.getAttribute('data-url') || btnCalificar.getAttribute('href');
      if (urlCalificar) cargarCalificarEmpresa(urlCalificar, btnCalificar);
      return;
    }

    // 5. Detalle Empresa
    var btnEmpresa = e.target.closest('[data-abrir-empresa]');
    if (btnEmpresa) {
      e.preventDefault();
      var urlEmpresa = btnEmpresa.getAttribute('data-url') || btnEmpresa.getAttribute('href');
      if (urlEmpresa) cargarDetalleEmpresa(urlEmpresa);
      return;
    }

    // 5B. Detalle Desarrollador
    var btnDev = e.target.closest('[data-abrir-desarrollador]');
    if (btnDev) {
      e.preventDefault();
      var urlDev = btnDev.getAttribute('data-url') || btnDev.getAttribute('href');
      if (typeof window.cerrarModalPerfilDev === 'function') {
        window.cerrarModalPerfilDev();
      }
      if (urlDev) cargarDetalleDesarrollador(urlDev);
      return;
    }

    // 6. Sala de Disputa
    var btnDisputa = e.target.closest('[data-abrir-sala-disputa]');
    if (btnDisputa) {
      e.preventDefault();
      var urlDisputa = btnDisputa.getAttribute('data-url') || btnDisputa.getAttribute('href');
      if (urlDisputa) cargarSalaDisputa(urlDisputa);
      return;
    }

    // 7. Formulario Abrir Disputa
    var btnAbrirDisp = e.target.closest('[data-abrir-formulario-disputa]');
    if (btnAbrirDisp) {
      e.preventDefault();
      var urlAbrir = btnAbrirDisp.getAttribute('data-url') || btnAbrirDisp.getAttribute('href');
      if (urlAbrir) cargarFormularioAbrirDisputa(urlAbrir);
      return;
    }
  });

  // Interceptor global para formularios con data-confirm (reemplaza onsubmit="return confirm(...)")
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || !form.hasAttribute('data-confirm')) return;
    if (form.dataset.confirmed === 'true') {
      form.dataset.confirmed = '';
      return;
    }
    e.preventDefault();
    e.stopPropagation();

    var msg = form.getAttribute('data-confirm');
    var title = form.getAttribute('data-confirm-title') || 'Confirmar acción';
    var danger = form.getAttribute('data-confirm-danger') !== 'false';

    confirmarAccion({
      titulo: title,
      mensaje: msg,
      peligro: danger
    }).then(function (ok) {
      if (ok) {
        form.dataset.confirmed = 'true';
        if (typeof form.requestSubmit === 'function') {
          form.requestSubmit();
        } else {
          form.submit();
        }
      }
    });
  }, true);

  // Exportar API global
  window.JdDashboardModals = {
    abrirContrato: cargarContratoDigital,
    abrirAvances: cargarAvances,
    abrirRegistrarAvance: cargarFormularioAvance,
    abrirCalificar: cargarCalificarEmpresa,
    abrirEmpresa: cargarDetalleEmpresa,
    abrirDesarrollador: cargarDetalleDesarrollador,
    abrirSalaDisputa: cargarSalaDisputa,
    abrirFormularioDisputa: cargarFormularioAbrirDisputa,
    confirmar: confirmarAccion,
    cerrar: cerrarModal,
    toast: mostrarToast
  };
})();
