/**
 * ============================================================
 * JobDevs - Dashboard Empresa: Contratos Digitales & Hitos
 * (Expediente Contractual, Firma Electrónica y Rechazo de Avances)
 * ============================================================
 */

import {
  t,
  csrfTokenActual,
  escaparHtml,
  mostrarToastCorp,
  prefersReducedMotion,
  EASE_OUT_EXPO,
} from './ui_core.js';

function endpointContratoDigital(contratoId) {
  const seccion = document.getElementById('contratos');
  let base = seccion ? (seccion.getAttribute('data-contrato-endpoint') || '') : '';
  if (!base) base = '/contrataciones/contrato-digital/0/';
  return base.replace(/0\/$/, '') + contratoId + '/';
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

export function abrirModalContrato(event, contratoId) {
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
}

export function cerrarModalContrato() {
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
}

export function validarRechazoAvance(form, event) {
  const submitter = event && event.submitter ? event.submitter : document.activeElement;
  if (submitter && submitter.name === 'accion' && submitter.value === 'rechazar') {
    const ta = form.querySelector('textarea[name="comentario"]');
    if (ta && !ta.value.trim()) {
      event.preventDefault();
      const toastEl = document.getElementById('corpToast');
      const msg = (toastEl && toastEl.dataset.msgRechazo) || 'Debes escribir un comentario explicando los ajustes solicitados.';
      let errEl = form.querySelector('.form-error-inline');
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
      mostrarToastCorp(msg, true);
      return false;
    }
  }
  return true;
}

// --- Global Window Contracts ---

window.abrirModalContrato = abrirModalContrato;
window.cerrarModalContrato = cerrarModalContrato;
window.validarRechazoAvance = validarRechazoAvance;

// --- DOM Initialization ---

export function initContratosHitos() {
  // Backdrop del modal de contrato digital in-situ
  const modalContratoDigital = document.getElementById('modalContratoDigital');
  if (modalContratoDigital) {
    modalContratoDigital.addEventListener('click', function (e) {
      if (e.target === modalContratoDigital) {
        cerrarModalContrato();
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
          abrirModalContrato(null, contratoId);
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
          abrirModalContrato(null, contratoId);
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
}
