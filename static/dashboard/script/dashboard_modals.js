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

  function getCsrfToken() {
    var cookie = leerCookie('csrftoken');
    if (cookie) return cookie;
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : '';
  }

  function mostrarToast(mensaje, esError) {
    var toast = document.getElementById('jdmToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'jdmToast';
      toast.className = 'jdm-toast';
      toast.setAttribute('role', 'status');
      document.body.appendChild(toast);
    }
    toast.innerHTML = '<i class="fa-solid ' + (esError ? 'fa-circle-exclamation' : 'fa-circle-check') + '"></i><span>' + escapeHtml(mensaje) + '</span>';
    toast.style.borderColor = esError ? '#ef4444' : '#00e676';
    toast.style.color = esError ? '#f87171' : '#69f0ae';
    toast.classList.add('is-visible');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(function () {
      toast.classList.remove('is-visible');
    }, 4500);
  }

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
          '<div class="jdm-loading"><i class="fa-solid fa-circle-notch"></i><span>Cargando información…</span></div>' +
        '</div>' +
        '<footer class="jdm-footer" id="jdmFooter" hidden></footer>' +
      '</div>';

    document.body.appendChild(modalEl);

    modalEl.addEventListener('click', function (e) {
      if (e.target.closest('[data-jdm-close]')) {
        e.preventDefault();
        cerrarModal();
      }
    });

    document.addEventListener('keydown', function (e) {
      if (!modalEl || modalEl.hidden) return;
      if (e.key === 'Escape') {
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
    body.innerHTML = '<div class="jdm-loading"><i class="fa-solid fa-circle-notch"></i><span>Cargando información…</span></div>';
    footer.hidden = true;
    footer.innerHTML = '';
  }

  function cerrarModal() {
    if (!modalEl) return;
    modalEl.hidden = true;
    document.body.style.overflow = '';
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
    setHeader('CONTRATACIÓN // CONTRATO DIGITAL', 'Cargando contrato…');

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      var data = await res.json();
      if (!data.ok || !data.contrato) throw new Error(data.error || 'No se pudo obtener el contrato');

      var c = data.contrato;
      setHeader('CONTRATACIÓN // CONTRATO DIGITAL', c.codigo + ' — ' + c.proyecto_titulo, 'Estado: ' + c.estado_label);

      var estadoCls = c.estado === 'firmado' ? 'jdm-badge-success' : (c.estado === 'borrador' ? 'jdm-badge-warning' : 'jdm-badge-info');

      var html =
        '<div class="jdm-contract-meta">' +
          '<div class="jdm-meta-box">' +
            '<div class="jdm-meta-label">Código Contrato</div>' +
            '<div class="jdm-meta-value accent">' + escapeHtml(c.codigo) + '</div>' +
          '</div>' +
          '<div class="jdm-meta-box">' +
            '<div class="jdm-meta-label">Monto Acordado</div>' +
            '<div class="jdm-meta-value accent">' + escapeHtml(c.monto_formateado || ('$' + c.monto)) + '</div>' +
          '</div>' +
          '<div class="jdm-meta-box">' +
            '<div class="jdm-meta-label">Fecha de Emisión</div>' +
            '<div class="jdm-meta-value">' + escapeHtml(c.fecha_creacion) + '</div>' +
          '</div>' +
          '<div class="jdm-meta-box">' +
            '<div class="jdm-meta-label">Estado Legal</div>' +
            '<div class="jdm-meta-value"><span class="jdm-badge ' + estadoCls + '">' + escapeHtml(c.estado_label) + '</span></div>' +
          '</div>' +
        '</div>' +

        '<div class="jdm-parties-grid">' +
          '<div class="jdm-party-card">' +
            '<div class="jdm-party-role">[ EMPRESA CONTRATANTE ]</div>' +
            '<div class="jdm-party-name">' + escapeHtml(c.empresa_nombre) + '</div>' +
            '<div class="jdm-party-status">' +
              (c.firmado_empresa ? '<span style="color:#00e676;"><i class="fa-solid fa-check-double"></i> Firmado (' + escapeHtml(c.fecha_firma_empresa || '') + ')</span>' : '<span style="color:#fbbf24;"><i class="fa-solid fa-clock"></i> Pendiente de firma</span>') +
            '</div>' +
          '</div>' +
          '<div class="jdm-party-card">' +
            '<div class="jdm-party-role">[ DESARROLLADOR / APRENDIZ ]</div>' +
            '<div class="jdm-party-name">' + escapeHtml(c.desarrollador_nombre) + '</div>' +
            '<div class="jdm-party-status" id="jdmDevSignStatus">' +
              (c.firmado_desarrollador ? '<span style="color:#00e676;"><i class="fa-solid fa-check-double"></i> Firmado (' + escapeHtml(c.fecha_firma_desarrollador || '') + ')</span>' : '<span style="color:#f87171;"><i class="fa-solid fa-file-signature"></i> Pendiente de tu firma</span>') +
            '</div>' +
          '</div>' +
        '</div>' +

        '<div class="jdm-form-label"><i class="fa-solid fa-scroll"></i> Cláusulas y Términos del Acuerdo</div>' +
        '<div class="jdm-clauses-container">';

      if (c.clausulas && c.clausulas.length) {
        c.clausulas.forEach(function (clausula, i) {
          html += '<div class="jdm-clause-item"><strong>CLÁUSULA ' + (i + 1) + '.</strong> ' + escapeHtml(clausula) + '</div>';
        });
      } else {
        html += '<p>Sin cláusulas adicionales registradas.</p>';
      }
      html += '</div>';

      if (c.puede_firmar) {
        html +=
          '<div class="jdm-sign-callout" id="jdmSignCallout">' +
            '<div>' +
              '<strong style="color:#00e676;display:block;margin-bottom:2px;"><i class="fa-solid fa-fingerprint"></i> Firma electrónica lista para emitir</strong>' +
              '<span style="font-size:12px;color:#a0a0a0;">Al firmar aceptas los términos, plazos y retribución estipulados para este proyecto.</span>' +
            '</div>' +
            '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmBtnFirmar" data-url-firmar="' + escapeHtml(c.firma_url) + '">' +
              '<i class="fa-solid fa-signature"></i> Firmar Contrato Ahora' +
            '</button>' +
          '</div>';
      }

      setContent(html);
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');

      var btnFirmar = document.getElementById('jdmBtnFirmar');
      if (btnFirmar) {
        btnFirmar.addEventListener('click', async function () {
          btnFirmar.disabled = true;
          btnFirmar.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Firmando...';
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
              var callout = document.getElementById('jdmSignCallout');
              if (callout) callout.remove();
              var devStatus = document.getElementById('jdmDevSignStatus');
              if (devStatus) {
                devStatus.innerHTML = '<span style="color:#00e676;"><i class="fa-solid fa-check-double"></i> Firmado ahora</span>';
              }
              if (triggerBtn) {
                triggerBtn.classList.remove('btn-primary');
                triggerBtn.classList.add('btn-secondary');
                triggerBtn.innerHTML = '<i class="fa fa-file-signature"></i> Ver Contrato';
              }
            } else {
              mostrarToast(signData.mensaje || signData.error || 'No se pudo firmar el contrato.', true);
              btnFirmar.disabled = false;
              btnFirmar.innerHTML = '<i class="fa-solid fa-signature"></i> Firmar Contrato Ahora';
            }
          } catch (err) {
            mostrarToast('Error de conexión al firmar.', true);
            btnFirmar.disabled = false;
            btnFirmar.innerHTML = '<i class="fa-solid fa-signature"></i> Firmar Contrato Ahora';
          }
        });
      }

    } catch (err) {
      setContent('<div class="jdm-error"><i class="fa-solid fa-triangle-exclamation"></i><span>' + escapeHtml(err.message) + '</span></div>');
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 2. VER AVANCES & HISTORIAL
  // ─────────────────────────────────────────────────────────────
  async function cargarAvances(url) {
    abrirModal('jdm-card-lg');
    setHeader('PROYECTO // GESTIÓN DE AVANCES', 'Cargando avances…');

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      var data = await res.json();
      if (!data.ok || !data.proyecto) throw new Error(data.error || 'No se pudieron obtener los avances');

      var p = data.proyecto;
      setHeader('PROYECTO // HISTORIAL Y AVANCES', p.titulo, 'Empresa: ' + p.empresa + ' · Estado: ' + p.estado_label);

      var html =
        '<div class="jdm-progress-header">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;font-family:\'JetBrains Mono\',monospace;font-size:12px;">' +
            '<span style="color:#a0a0a0;">PROGRESO GENERAL</span>' +
            '<span style="color:#00e676;font-weight:700;">' + p.progreso + '% (' + p.hitos_completados + ' / ' + p.hitos_totales + ' hitos completados)</span>' +
          '</div>' +
          '<div class="jdm-progress-bar-bg">' +
            '<div class="jdm-progress-bar-fill" style="width:' + p.progreso + '%;"></div>' +
          '</div>' +
        '</div>';

      if (data.hitos && data.hitos.length) {
        html += '<div class="jdm-form-label"><i class="fa-solid fa-list-check"></i> Hitos del Proyecto</div><div class="jdm-hitos-scroll">';
        data.hitos.forEach(function (h) {
          var icon = h.estado === 'completado' ? 'fa-circle-check" style="color:#00e676;' : (h.estado === 'en_revision' ? 'fa-clock" style="color:#fbbf24;' : 'fa-circle" style="color:#666666;');
          html +=
            '<div class="jdm-hito-pill">' +
              '<i class="fa-solid ' + icon + '"></i>' +
              '<div>' +
                '<strong>' + escapeHtml(h.titulo) + '</strong>' +
                '<div style="font-size:10px;color:#a0a0a0;">' + escapeHtml(h.estado_label) + '</div>' +
              '</div>' +
            '</div>';
        });
        html += '</div>';
      }

      html += '<div class="jdm-form-label"><i class="fa-solid fa-timeline"></i> Registro de Entregas y Evidencias (' + (data.avances ? data.avances.length : 0) + ')</div>';

      if (data.avances && data.avances.length) {
        html += '<div class="jdm-advances-feed">';
        data.avances.forEach(function (a) {
          var badgeCls = a.estado === 'aprobado' ? 'jdm-badge-success' : (a.estado === 'rechazado' ? 'jdm-badge-danger' : 'jdm-badge-warning');
          html +=
            '<div class="jdm-advance-card">' +
              '<div class="jdm-advance-head">' +
                '<div>' +
                  '<div class="jdm-advance-title">' + escapeHtml(a.entregable_titulo) + '</div>' +
                  '<div style="font-size:11px;color:#a0a0a0;font-family:\'JetBrains Mono\',monospace;">Por ' + escapeHtml(a.desarrollador) + ' · ' + escapeHtml(a.fecha) + '</div>' +
                '</div>' +
                '<span class="jdm-badge ' + badgeCls + '">' + escapeHtml(a.estado_label) + '</span>' +
              '</div>' +
              '<div class="jdm-advance-desc">' + escapeHtml(a.descripcion) + '</div>';

          if (a.archivo_adjunto_url || a.archivo_url) {
            html += '<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;">';
            if (a.archivo_adjunto_url) {
              html += '<a href="' + escapeHtml(a.archivo_adjunto_url) + '" target="_blank" rel="noopener" class="jdm-advance-attachment"><i class="fa-solid fa-paperclip"></i> ' + escapeHtml(a.archivo_adjunto_nombre || 'Descargar archivo') + '</a>';
            }
            if (a.archivo_url) {
              html += '<a href="' + escapeHtml(a.archivo_url) + '" target="_blank" rel="noopener" class="jdm-advance-attachment"><i class="fa-solid fa-arrow-up-right-from-square"></i> Ver enlace externo</a>';
            }
            html += '</div>';
          }

          if (a.observaciones) {
            html += '<div class="jdm-advance-feedback"><i class="fa-solid fa-comment-dots"></i> Observaciones: ' + escapeHtml(a.observaciones) + '</div>';
          }

          html += '</div>';
        });
        html += '</div>';
      } else {
        html += '<div class="jdm-empty"><i class="fa-solid fa-box-open"></i>No se han registrado entregas para este proyecto aún.</div>';
      }

      var footerBtns = '';
      if (data.puede_registrar && data.registrar_url) {
        footerBtns += '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmBtnIrRegistrar" data-url-registrar="' + escapeHtml(data.registrar_url) + '"><i class="fa-solid fa-pen"></i> Registrar Nuevo Avance</button>';
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
      setContent('<div class="jdm-error"><i class="fa-solid fa-triangle-exclamation"></i><span>' + escapeHtml(err.message) + '</span></div>');
      setFooter('<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 3. REGISTRAR AVANCE FORMULARIO
  // ─────────────────────────────────────────────────────────────
  async function cargarFormularioAvance(url) {
    abrirModal('');
    setHeader('PROYECTO // REGISTRAR AVANCE', 'Cargando hitos pendientes…');

    try {
      var res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
