/**
 * JobDevs — Modales de Dashboard: Avances, Entregables y Disputas
 */

import {
  escapeHtml,
  parseJsonResponse,
  getCsrfToken,
  mostrarToast,
  confirmarAccion,
  abrirModal,
  cerrarModal,
  setHeader,
  setContent,
  setFooter,
} from './modal_core.js';

// ─────────────────────────────────────────────────────────────
// 2. VER AVANCES & HISTORIAL
// ─────────────────────────────────────────────────────────────
export async function cargarAvances(url) {
  abrirModal('jdm-card-lg');
  setHeader('HISTORIAL DE ENTREGAS', 'Cargando avances…');

  try {
    const res = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      credentials: 'same-origin'
    });
    const data = await parseJsonResponse(res, 'No se pudieron obtener los avances (respuesta inesperada del servidor).');
    if (!data.ok || !data.proyecto) throw new Error(data.error || data.mensaje || 'No se pudieron obtener los avances');

    const p = data.proyecto;
    setHeader('HISTORIAL DE ENTREGAS', p.titulo, 'Empresa: ' + p.empresa + ' · Estado: ' + p.estado_label);

    let html =
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
        const iconCls = h.estado === 'completado' ? 'is-done' : (h.estado === 'en_revision' ? 'is-rev' : 'is-wait');
        const iconName = h.estado === 'completado' ? 'check-circle-2' : (h.estado === 'en_revision' ? 'clock' : 'circle');
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
        const badgeCls = a.estado === 'aprobado' ? 'jdm-badge-success' : (a.estado === 'rechazado' ? 'jdm-badge-danger' : 'jdm-badge-warning');
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

    let footerBtns = '';
    if (data.puede_registrar && data.registrar_url) {
      footerBtns += '<button type="button" class="jdm-btn jdm-btn-primary" id="jdmBtnIrRegistrar" data-url-registrar="' + escapeHtml(data.registrar_url) + '"><i data-lucide="pen"></i> Registrar Nuevo Avance</button>';
    }
    footerBtns += '<button type="button" class="jdm-btn jdm-btn-secondary" data-jdm-close>Cerrar</button>';

    setContent(html);
    setFooter(footerBtns);

    const btnIrReg = document.getElementById('jdmBtnIrRegistrar');
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
export async function cargarFormularioAvance(url) {
  abrirModal('');
  setHeader('GESTIÓN DE ENTREGABLES', 'Registrar Avance Técnico', 'Cargando hitos pendientes…');

  try {
    const res = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      credentials: 'same-origin'
    });
    const data = await parseJsonResponse(res, 'No se pudieron consultar los hitos (respuesta inesperada del servidor).');
    if (!data.ok || !data.proyecto) throw new Error(data.error || data.mensaje || 'No se pudieron consultar los hitos');

    setHeader('GESTIÓN DE ENTREGABLES', 'Registrar Avance Técnico', 'Proyecto: ' + data.proyecto.titulo);

    let options = '<option value="">-- Selecciona el hito a reportar --</option>';
    if (data.hitos_pendientes && data.hitos_pendientes.length) {
      data.hitos_pendientes.forEach(function (h) {
        options += '<option value="' + h.id + '">' + escapeHtml(h.titulo) + '</option>';
      });
    }

    const html =
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

    const btnEnviar = document.getElementById('jdmBtnEnviarAvance');
    const form = document.getElementById('jdmFormAvance');

    if (btnEnviar && form) {
      btnEnviar.addEventListener('click', async function () {
        const hito = form.querySelector('[name="entregable_id"]').value;
        const desc = form.querySelector('[name="descripcion"]').value.trim();
        const urlEv = form.querySelector('[name="archivo_url"]').value.trim();
        const file = form.querySelector('[name="archivo_adjunto"]').files[0];
        const errBox = document.getElementById('jdmAvanceError');

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
          const formData = new FormData(form);
          const postRes = await fetch(data.url_registrar, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': getCsrfToken()
            },
            body: formData,
            credentials: 'same-origin'
          });

          const resJson = await postRes.json();
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
// 6. SALA DE DISPUTA & EXPEDIENTE
// ─────────────────────────────────────────────────────────────
export async function cargarSalaDisputa(url) {
  abrirModal('jdm-card-lg');
  setHeader('DISPUTAS // SALA DE MEDIACIÓN', 'Cargando expediente arbitral…');

  try {
    const res = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      credentials: 'same-origin'
    });
    const data = await res.json();
    if (!data.ok || !data.disputa) throw new Error(data.error || 'No se pudo obtener el expediente de disputa');

    const d = data.disputa;
    setHeader('SALA DE MEDIACIÓN #' + d.id, d.proyecto_titulo, 'Causal: ' + d.categoria + ' · Estado: ' + d.estado_label);

    const estadoCls = d.estado === 'resuelta' ? 'jdm-badge-success' : (d.estado === 'cancelada' ? 'jdm-badge-gray' : 'jdm-badge-danger');

    let html =
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
        const bubbleType = m.rol === 'administrador' ? 'jdm-bubble-admin' : (m.es_propio ? 'jdm-bubble-own' : 'jdm-bubble-other');
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
      let resolucionesOptions = '<option value="">-- Selecciona el sentido de la resolución --</option>';
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

    const chatBox = document.getElementById('jdmDisputaChat');
    if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;

    // Listener enviar mensaje
    const formMsg = document.getElementById('jdmFormDisputaMsg');
    if (formMsg) {
      formMsg.addEventListener('submit', async function (e) {
        e.preventDefault();
        const inp = document.getElementById('jdmMsgContenido');
        const txt = inp ? inp.value.trim() : '';
        if (!txt) return;

        const btn = document.getElementById('jdmBtnEnviarMsg');
        btn.disabled = true;

        try {
          const fData = new FormData();
          fData.append('contenido', txt);
          const mRes = await fetch(d.enviar_url, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': getCsrfToken()
            },
            body: fData,
            credentials: 'same-origin'
          });
          const mJson = await mRes.json();
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
    const formResolver = document.getElementById('jdmFormResolverDisputa');
    if (formResolver) {
      formResolver.addEventListener('submit', async function (e) {
        e.preventDefault();
        const resSel = formResolver.querySelector('[name="resolucion"]').value;
        const dictTxt = formResolver.querySelector('[name="dictamen"]').value.trim();

        if (!resSel || !dictTxt) {
          mostrarToast('Debes seleccionar el fallo y redactar el dictamen.', true);
          return;
        }

        const confirmado = await confirmarAccion({
          kicker: 'RESOLUCIÓN ARBITRAL VINCULANTE',
          titulo: 'Confirmar Emisión de Dictamen',
          mensaje: '¿Confirmas la emisión definitiva de esta resolución arbitral? Esta acción es irreversible y aplicará efectos inmediatos sobre el contrato.',
          textoConfirmar: 'Emitir Resolución',
          peligro: true
        });
        if (!confirmado) {
          return;
        }

        const btnR = document.getElementById('jdmBtnResolver');
        btnR.disabled = true;
        btnR.innerHTML = '<i data-lucide="loader-2"></i> Procesando resolución...';

        try {
          const rData = new FormData(formResolver);
          rData.append('origen', 'dashboard');
          const rRes = await fetch(d.resolver_url, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': getCsrfToken()
            },
            body: rData,
            credentials: 'same-origin'
          });
          const rJson = await rRes.json();
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
export async function cargarFormularioAbrirDisputa(url) {
  abrirModal('');
  setHeader('ARBITRAJE CONTRACTUAL', 'Consultando proyecto…');

  try {
    const res = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      credentials: 'same-origin'
    });
    const data = await res.json();
    if (!data.ok || !data.proyecto) throw new Error(data.error || 'No se pudo consultar el proyecto');

    const p = data.proyecto;
    setHeader('ARBITRAJE CONTRACTUAL', 'Apertura de Mediación Formal', 'Proyecto: ' + escapeHtml(p.titulo) + ' · Empresa: ' + escapeHtml(p.empresa));

    let catOptions = '<option value="">-- Selecciona causal de disputa --</option>';
    if (data.categorias && data.categorias.length) {
      data.categorias.forEach(function (c) {
        catOptions += '<option value="' + escapeHtml(c.codigo) + '"' + (c.codigo === data.categoria ? ' selected' : '') + '>' + escapeHtml(c.label) + '</option>';
      });
    }

    const html =
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

    const btnConf = document.getElementById('jdmBtnConfirmarDisputa');
    const formD = document.getElementById('jdmFormNuevaDisputa');

    if (btnConf && formD) {
      const categoriaD = formD.querySelector('[name="categoria"]');
      const gravedadD = formD.querySelector('[name="confirma_gravedad"]');
      function actualizarDeclaraciones() {
        const esFuerzaMayor = categoriaD.value === 'fuerza_mayor';
        gravedadD.disabled = esFuerzaMayor;
        gravedadD.required = !esFuerzaMayor;
        document.getElementById('jdmDeclaracionGravedad').hidden = esFuerzaMayor;
        if (esFuerzaMayor) gravedadD.checked = false;
      }
      categoriaD.addEventListener('change', actualizarDeclaraciones);
      actualizarDeclaraciones();
      btnConf.addEventListener('click', async function () {
        const cat = formD.querySelector('[name="categoria"]').value;
        const mot = formD.querySelector('[name="motivo"]').value.trim();
        const check = formD.querySelector('[name="acepta_sanciones"]').checked;
        const errBox = document.getElementById('jdmDisputaError');

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
          const fData = new FormData(formD);
          fData.append('origen', 'dashboard');

          const postRes = await fetch(data.url_abrir, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': getCsrfToken()
            },
            body: fData,
            credentials: 'same-origin'
          });

          const resJson = await postRes.json();
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
