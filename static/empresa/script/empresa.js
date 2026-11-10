/**
 * ============================================================
 * JobDevs - Dashboard Empresa (Vanilla JS Moderno)
 * ============================================================
 */

(function () {
  'use strict';

  // --- Modo Claro / Oscuro ---
  const THEME_STORAGE_KEY = 'jobdevs-theme';

  function obtenerTemaActual() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function actualizarBotonTema(tema) {
    const btn = document.getElementById('empresaThemeToggle');
    if (!btn) return;
    btn.setAttribute('aria-pressed', tema === 'light' ? 'true' : 'false');
    btn.setAttribute('aria-label', tema === 'light' ? 'Tema claro activo' : 'Tema oscuro activo');
    btn.title = tema === 'light' ? 'Cambiar a tema oscuro' : 'Cambiar a tema claro';
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

  // --- 1. Tab Switching & URL Persistence ---
  window.switchTab = function (id, btn) {
    if (!id) return;
    if (id === 'reputacion') id = 'inicio';
    if (id === 'historial-disputas') id = 'disputas';

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
  };

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
          previewBox.innerHTML = '<img src="' + e.target.result + '" alt="Vista previa" style="width:100%;height:100%;object-fit:cover;">';
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
  window.abrirDrawerCandidatos = function (event, url, titulo) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    window._ultimoUrlCandidatos = url;

    const buscadorWrapper = document.getElementById('drawerCandidatosBuscador');
    if (buscadorWrapper) {
      buscadorWrapper.hidden = true;
      const buscadorInput = document.getElementById('drawerCandidatoBusqueda');
      if (buscadorInput) buscadorInput.value = '';
    }

    const drawer = document.getElementById('drawerCandidatos');
    const titleEl = document.getElementById('drawerProjectTitle');
    const contentEl = document.getElementById('drawerContent');

    if (titleEl) titleEl.textContent = titulo || 'Candidatos Postulados';
    if (drawer) {
      drawer.classList.add('is-open');
      document.body.style.overflow = 'hidden';
    }

    if (contentEl) {
      contentEl.innerHTML = '<div class="drawer-loading"><i data-lucide="loader-circle" class="corp-spin"></i><p>Cargando postulaciones y perfiles de candidatos...</p></div>';
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }

      fetch(url)
        .then(function (res) {
          if (!res.ok) throw new Error('Error al consultar candidatos');
          return res.text();
        })
        .then(function (html) {
          const parser = new DOMParser();
          const doc = parser.parseFromString(html, 'text/html');
          
          // Buscar contenedor de tarjetas de postulaciones
          const cards = doc.querySelectorAll('.main-content .card');
          const candidateCards = [];

          cards.forEach(function (c) {
            // Descartar tarjeta de título del proyecto y formulario de filtros
            if (c.tagName.toLowerCase() === 'form') return;
            if (c.querySelector('form[method="get"]')) return;
            if (c.querySelector('h2') && c.querySelector('.card-subtitle')) return;
            candidateCards.push(c);
          });

          if (candidateCards.length > 0) {
            const lista = document.createElement('div');
            lista.className = 'drawer-candidates-list';
            candidateCards.forEach(function (c) {
              const tarjeta = c.cloneNode(true);
              tarjeta.classList.remove('card');
              tarjeta.classList.add('drawer-candidate-card');
              lista.appendChild(tarjeta);
            });
            contentEl.replaceChildren(lista);

            // Los enlaces "Ver Contrato" se abren en el modal in-situ; el resto en nueva pestaña
            contentEl.querySelectorAll('a').forEach(function (link) {
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

            if (buscadorWrapper) buscadorWrapper.hidden = false;
            if (typeof window.inicializarFiltroCandidatos === 'function') {
              window.inicializarFiltroCandidatos({ scope: contentEl });
            }

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
              window.lucide.createIcons();
            }
          } else {
            contentEl.innerHTML = '<div class="activity-empty" style="padding:40px 20px;"><i data-lucide="user-x"></i><p>No se encontraron candidatos postulados para este proyecto.</p></div>';
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
              window.lucide.createIcons();
            }
          }
        })
        .catch(function () {
          contentEl.innerHTML = '<div class="activity-empty" style="padding:40px 20px;"><i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i><p>No se pudo cargar la vista previa in-situ.</p></div>';
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
    if (!valor) return 'Pendiente';
    const fecha = new Date(valor);
    if (isNaN(fecha.getTime())) return String(valor);
    try {
      return fecha.toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' });
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
      ? '<span class="signature-badge-corp is-signed"><i data-lucide="check-circle-2"></i><span>Firmado</span></span>'
      : '<span class="signature-badge-corp is-pending"><i data-lucide="clock"></i><span>Pendiente de firma</span></span>';
    return '' +
      '<div class="contract-signature-block">' +
        '<div class="contract-signature-block-label">' + escaparHtml(etiqueta) + '</div>' +
        '<div class="contract-signature-block-name">' + escaparHtml(nombre) + '</div>' +
        '<div class="contract-signature-block-stamp">' +
          '<span class="contract-signature-script">' + (firmado ? 'Firmado digitalmente' : '—') + '</span>' +
        '</div>' +
        estado +
        '<div class="contract-signature-block-date">' + escaparHtml(formatearFechaFirma(fecha)) + '</div>' +
      '</div>';
  }

  function htmlFormularioFirma(contrato) {
    if (contrato.esta_firmado) {
      return '<div class="contract-sign-done"><i data-lucide="shield-check"></i>' +
        '<p>Contrato firmado por ambas partes. La contratación quedó formalizada.</p></div>';
    }
    if (contrato.ya_firmo) {
      return '<div class="contract-sign-done"><i data-lucide="check-circle-2"></i>' +
        '<p>Ya firmaste este contrato. Queda pendiente la firma de la otra parte.</p></div>';
    }
    if (!contrato.puede_firmar) {
      return '<div class="contract-sign-done is-muted"><i data-lucide="lock"></i>' +
        '<p>Este contrato ya no está disponible para firma electrónica.</p></div>';
    }
    return '' +
      '<form id="formFirmarContrato" class="contract-sign-form" method="post" action="' +
        escaparHtml(contrato.url_firmar) + '" data-contrato-id="' + escaparHtml(contrato.id) + '">' +
        '<input type="hidden" name="csrfmiddlewaretoken" value="' + escaparHtml(csrfTokenActual()) + '">' +
        '<label class="contract-sign-check">' +
          '<input type="checkbox" name="acepta_terminos" value="1" required>' +
          '<span>Acepto los términos y condiciones y firmo electrónicamente este contrato.</span>' +
        '</label>' +
        '<div id="contratoFirmaError" class="contract-sign-error" style="display:none;"></div>' +
        '<button type="submit" class="btn-corp-primary contract-sign-submit">' +
          '<i data-lucide="pen-tool"></i>' +
          '<span>Firmar Electrónicamente</span>' +
        '</button>' +
      '</form>';
  }

  function htmlDocumentoContrato(contrato) {
    const hashDocumento = contrato.hash_documento
      ? escaparHtml(contrato.hash_documento)
      : 'Se generará con la primera firma electrónica';
    const hashContrato = contrato.hash_contrato ? escaparHtml(contrato.hash_contrato) : 'Sin sello definitivo';
    const comentarios = contrato.comentarios_adicionales
      ? '<div class="contract-clause-box"><strong>Comentarios adicionales</strong><p>' +
        escaparHtml(contrato.comentarios_adicionales) + '</p></div>'
      : '';

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
        '<div class="contract-edit-terms-box" style="background:#ffffff; border:1px solid #00c853; border-radius:12px; padding:20px; margin-bottom:18px; box-shadow:0 2px 8px rgba(0,200,83,0.08);">' +
          '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">' +
            '<div style="display:flex; align-items:center; gap:8px; font-size:13px; font-weight:700; color:#007c34;">' +
              '<i data-lucide="sliders-horizontal"></i>' +
              '<span>Definición de Términos Contractuales (Editable por la Empresa)</span>' +
            '</div>' +
            '<span class="badge" style="background:#e6faf0; color:#007c34; font-size:11px; padding:3px 8px; border-radius:10px;">Fase de Negociación</span>' +
          '</div>' +
          '<form id="formEditarTerminosContrato" method="post" action="' + escaparHtml(contrato.url_editar) + '">' +
            '<div style="display:grid; grid-template-columns: 2fr 1fr; gap:12px; margin-bottom:12px;">' +
              '<div class="form-group-corp" style="margin-bottom:0;">' +
                '<label class="form-label-corp">Monto del Contrato</label>' +
                '<input type="number" step="0.01" min="0" name="monto" class="form-input-corp" value="' + escaparHtml(contrato.monto) + '" required placeholder="Ej: 2500000">' +
              '</div>' +
              '<div class="form-group-corp" style="margin-bottom:0;">' +
                '<label class="form-label-corp">Moneda</label>' +
                '<select name="moneda" class="form-input-corp">' + opcionesMonedas + '</select>' +
              '</div>' +
            '</div>' +
            '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:12px;">' +
              '<div class="form-group-corp" style="margin-bottom:0;">' +
                '<label class="form-label-corp">Forma de Pago (Cronograma)</label>' +
                '<select name="forma_pago" class="form-input-corp">' + opcionesFormas + '</select>' +
              '</div>' +
              '<div class="form-group-corp" style="margin-bottom:0;">' +
                '<label class="form-label-corp">Medio de Pago</label>' +
                '<select name="medio_pago" class="form-input-corp">' + opcionesMedios + '</select>' +
              '</div>' +
            '</div>' +
            '<div class="form-group-corp" style="margin-bottom:14px;">' +
              '<label class="form-label-corp">Comentarios adicionales o condiciones de entrega (Opcional)</label>' +
              '<textarea name="comentarios_adicionales" class="form-input-corp" rows="2" placeholder="Notas sobre desembolsos, cuentas o entregas intermedias...">' + escaparHtml(contrato.comentarios_adicionales || '') + '</textarea>' +
            '</div>' +
            '<div style="display:flex; justify-content:flex-end;">' +
              '<button type="submit" class="btn-corp-primary btn-sm">' +
                '<i data-lucide="save"></i>' +
                '<span>Guardar Términos Contractuales</span>' +
              '</button>' +
            '</div>' +
          '</form>' +
        '</div>';
    } else {
      bloqueTerminos = '' +
        '<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:10px 14px; margin-bottom:12px; display:flex; align-items:center; gap:8px; font-size:12px; color:#64748b;">' +
          '<i data-lucide="lock" style="width:14px; height:14px; flex-shrink:0; color:#94a3b8;"></i>' +
          '<span>Términos sellados: Este contrato ya cuenta con firmas electrónicas o la negociación concluyó; los términos económicos no pueden alterarse.</span>' +
        '</div>' +
        '<div class="contract-terms-grid" style="grid-template-columns: repeat(3, 1fr);">' +
          '<div class="contract-term-box"><span class="contract-term-label">Monto acordado</span>' +
            '<div class="contract-term-value">' + escaparHtml(contrato.monto_formateado) + '</div>' +
            '<span class="contract-term-sub">Moneda: ' + escaparHtml(contrato.moneda) + '</span></div>' +
          '<div class="contract-term-box"><span class="contract-term-label">Forma de pago</span>' +
            '<div class="contract-term-value">' + escaparHtml(contrato.forma_pago_display) + '</div>' +
            '<span class="contract-term-sub">Cronograma de liquidación</span></div>' +
          '<div class="contract-term-box"><span class="contract-term-label">Medio de pago</span>' +
            '<div class="contract-term-value" style="font-size:14px; font-weight:700; color:var(--corp-slate-900);">' + escaparHtml(contrato.medio_pago_display) + '</div>' +
            '<span class="contract-term-sub">Canal acordado</span></div>' +
        '</div>';
    }

    return '' +
      '<article class="contract-doc-paper">' +
        '<header class="contract-doc-header">' +
          '<div>' +
            '<div class="contract-doc-eyebrow">Expediente digital CD-' + escaparHtml(contrato.id) + '</div>' +
            '<h3 class="contract-doc-title">Acuerdo Digital de Servicios Profesionales</h3>' +
            '<div class="contract-doc-project">' + escaparHtml(contrato.proyecto_titulo) + '</div>' +
          '</div>' +
          '<span class="contract-estado-badge estado-' + escaparHtml(contrato.estado) + '">' +
            escaparHtml(contrato.estado_display) + '</span>' +
        '</header>' +
        '<div class="contract-doc-hashes">' +
          '<span class="hash-pill" title="SHA-256 del contenido contractual congelado en la primera firma">' +
            '<i data-lucide="fingerprint"></i> ' + hashDocumento +
          '</span>' +
          '<span class="hash-pill" title="SHA-256 del contrato firmado">' +
            '<i data-lucide="shield-check"></i> ' + hashContrato +
          '</span>' +
        '</div>' +
        '<div class="contract-doc-parties">' +
          '<div class="contract-party-card"><span class="contract-party-label">Empresa contratante</span>' +
            '<strong>' + escaparHtml(contrato.empresa_nombre) + '</strong></div>' +
          '<div class="contract-party-card"><span class="contract-party-label">Desarrollador contratado</span>' +
            '<strong>' + escaparHtml(contrato.desarrollador_nombre) + '</strong></div>' +
          '<div class="contract-party-card"><span class="contract-party-label">Proyecto</span>' +
            '<strong>' + escaparHtml(contrato.proyecto_titulo) + '</strong></div>' +
        '</div>' +
        bloqueTerminos +
        '<div class="contract-clause-box">' +
          '<strong>Cláusulas contractuales</strong>' +
          '<p class="contract-clause-text">' + escaparHtml(contrato.clausulas) + '</p>' +
        '</div>' +
        comentarios +
        '<div class="contract-signatures-row">' +
          bloqueFirmaParte('Firma de la empresa', contrato.empresa_nombre, contrato.firmado_empresa, contrato.fecha_firma_empresa) +
          bloqueFirmaParte('Firma del desarrollador', contrato.desarrollador_nombre, contrato.firmado_desarrollador, contrato.fecha_firma_desarrollador) +
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
      { rol: 'firma-empresa', firmado: contrato.firmado_empresa, etiqueta: 'Empresa' },
      { rol: 'firma-dev', firmado: contrato.firmado_desarrollador, etiqueta: 'Dev' },
    ];
    mapa.forEach(function (item) {
      const badge = fila.querySelector('[data-role="' + item.rol + '"]');
      if (!badge) return;
      badge.classList.toggle('is-signed', !!item.firmado);
      badge.classList.toggle('is-pending', !item.firmado);
      const span = badge.querySelector('span');
      if (span) span.textContent = item.etiqueta + ': ' + (item.firmado ? 'Firmado' : 'Pendiente');
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
      hashPill.textContent = contrato.hash_contrato ? contrato.hash_contrato.slice(0, 12) + '…' : 'Sin sello';
    }
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

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
    bodyEl.innerHTML = '<div class="drawer-loading"><i data-lucide="loader-circle" class="corp-spin"></i><p>Cargando expediente contractual...</p></div>';
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
      })
      .catch(function () {
        bodyEl.innerHTML = '<div class="activity-empty" style="padding:44px 20px;">' +
          '<i data-lucide="alert-triangle" style="color:var(--corp-danger);"></i>' +
          '<p>No se pudo cargar el expediente contractual. Intenta de nuevo.</p></div>';
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
      bodyEl.innerHTML = '<div class="drawer-loading"><i data-lucide="loader-circle" class="corp-spin"></i><p>Cargando expediente contractual...</p></div>';
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
  window.abrirModalEditarProyecto = function (event, id, actionUrl, titulo, descripcion, tipo_solucion, prioridad, modalidad, ciudad, fecha_limite, vacantes) {
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

    const vacantesInput = document.getElementById('edit_vacantes');
    if (vacantesInput) vacantesInput.value = vacantes || '1';

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

    if (titleEl) titleEl.textContent = titulo || 'esta convocatoria';
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

    // Control del empty state
    const emptyMsg = document.getElementById('historialSinResultados');
    if (emptyMsg) {
      emptyMsg.style.display = (visibleCount === 0) ? 'block' : 'none';
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
      emptyMsg.style.display = (totalVisibles === 0) ? 'block' : 'none';
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
  const MESES_ES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
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
        if (displayInput) displayInput.value = d + ' de ' + MESES_ES[m] + ', ' + y;
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
    monthYearEl.textContent = MESES_ES[month] + ' ' + year;

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

      const clickHandler = isPast ? '' : 'onclick="seleccionarFechaDatepicker(\'' + pickerId + '\', ' + year + ', ' + month + ', ' + d + ')"';
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
    if (popover) {
      popover.classList.toggle('is-open');
    }
  };

  window.closeNotifPopover = function () {
    const popover = document.getElementById('notifPopover');
    if (popover) {
      popover.classList.remove('is-open');
    }
  };

  window.limpiarNotificacionesAjax = function (event, form) {
    if (event) event.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    const oldHtml = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = 'Limpiando...';
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
          popoverBody.innerHTML = '<div class="notif-popover-empty"><i data-lucide="bell-off"></i><span>No hay notificaciones</span></div>';
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
          if (toastSpan) toastSpan.textContent = data.message || 'Notificaciones eliminadas';
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
        alert('Error al limpiar las notificaciones.');
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
      btn.title = isCollapsed ? 'Expandir menú lateral' : 'Colapsar menú (solo iconos)';
      const icon = btn.querySelector('[data-lucide], .lucide');
      if (icon) {
        icon.setAttribute('data-lucide', isCollapsed ? 'panel-left-open' : 'panel-left-close');
      }
    }

    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  // --- 5. Event Listeners y Teclado Global ---
  document.addEventListener('DOMContentLoaded', function () {
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
        submitBtn.innerHTML = '<i data-lucide="loader-circle" class="corp-spin"></i><span>Guardando términos...</span>';
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
            return { status: res.ok ? 'ok' : 'error', message: 'No se pudo guardar los términos.' };
          });
        })
        .then(function (data) {
          if (data.status !== 'ok') {
            alert(data.message || 'Error al actualizar los términos.');
            if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = oldBtnHtml; }
            return;
          }

          const toast = document.getElementById('corpToast');
          if (toast) {
            const toastSpan = toast.querySelector('span');
            if (toastSpan) toastSpan.textContent = data.message || 'Términos del contrato actualizados exitosamente';
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
          alert('Error de conexión al guardar los términos del contrato.');
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
        submitBtn.innerHTML = '<i data-lucide="loader-circle" class="corp-spin"></i><span>Firmando...</span>';
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
            return { status: res.ok ? 'ok' : 'error', message: 'No se pudo procesar la firma.' };
          });
        })
        .then(function (data) {
          if (data.status !== 'ok') {
            if (errorEl) {
              errorEl.textContent = data.message || 'No se pudo firmar el contrato.';
              errorEl.style.display = 'block';
            }
            mostrarToastCorp(data.message || 'No se pudo firmar el contrato.', true);
            if (submitBtn) {
              submitBtn.disabled = false;
              submitBtn.innerHTML = oldBtnHtml;
            }
            return;
          }
          mostrarToastCorp(data.message || 'Contrato firmado electrónicamente.', false);
          if (contratoId) {
            window.abrirModalContrato(null, contratoId);
          }
        })
        .catch(function () {
          if (errorEl) {
            errorEl.textContent = 'Error de red al firmar el contrato. Intenta de nuevo.';
            errorEl.style.display = 'block';
          }
          mostrarToastCorp('Error de red al firmar el contrato.', true);
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
            submitBtn.innerHTML = '<i data-lucide="loader-circle" class="corp-spin"></i> Procesando...';
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
                return { status: res.ok ? 'ok' : 'error', message: res.ok ? 'Acción procesada exitosamente' : 'Error al procesar la solicitud' };
              });
            })
            .then(function (data) {
              if (data.status === 'error') {
                alert(data.message || 'Error al procesar la acción.');
                if (submitBtn) {
                  submitBtn.disabled = false;
                  submitBtn.innerHTML = oldBtnHtml;
                }
                return;
              }
              const toast = document.getElementById('corpToast');
              if (toast) {
                const toastSpan = toast.querySelector('span');
                if (toastSpan) toastSpan.textContent = data.message || 'Acción procesada exitosamente';
                toast.classList.add('show');
                setTimeout(function () { toast.classList.remove('show'); }, 3000);
              }

              // Re-cargar contenido del drawer usando el proyecto actual
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
              alert('Error al procesar la acción. Intente de nuevo.');
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
        window.cerrarDrawerCandidatos();
        window.closeNotifPopover();
        window.closeSidebar();
      }
    });

    // Restaurar pestaña activa desde URL: el hash o la sección actual mandan
    const params = new URLSearchParams(window.location.search);
    const hash = window.location.hash ? window.location.hash.substring(1) : null;
    const sectionParam = params.get('section');
    const initialTab = hash || sectionParam || 'inicio';

    window.switchTab(initialTab);

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
            btn.title = 'Expandir menú lateral';
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

    // Inicializar íconos Lucide
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  });
})();
