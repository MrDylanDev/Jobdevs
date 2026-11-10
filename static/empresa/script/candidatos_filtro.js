/**
 * ============================================================
 * JobDevs - Filtro reactivo de candidatos (Empresa)
 * ------------------------------------------------------------
 * Filtra en el cliente las tarjetas de postulaciones por nombre,
 * ficha SENA y habilidades, con debounce de 300 ms.
 * ============================================================ */

(function () {
  'use strict';

  const ESPERA_DEBOUNCE_MS = 300;
  const estados = new WeakMap();

  /**
   * Normaliza texto para comparaciones: minusculas, sin acentos y sin
   * espacios sobrantes.
   */
  function normalizar(texto) {
    return String(texto === null || texto === undefined ? '' : texto)
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim();
  }

  /**
   * Envuelve una funcion para ejecutarla solo tras `espera` ms sin
   * nuevas invocaciones.
   */
  function crearDebounce(fn, espera) {
    let temporizador = null;
    return function () {
      const args = arguments;
      window.clearTimeout(temporizador);
      temporizador = window.setTimeout(function () {
        fn.apply(null, args);
      }, espera);
    };
  }

  function resolverElemento(scope, selector) {
    if (!selector) return null;
    if (typeof selector === 'string') return scope.querySelector(selector);
    return selector;
  }

  function recolectarTarjetas(scope) {
    const tarjetas = [];
    scope.querySelectorAll('.candidate-card').forEach(function (nodo) {
      const datos = nodo.matches('[data-candidato]')
        ? nodo
        : nodo.querySelector('[data-candidato]');
      if (!datos) return;
      tarjetas.push({
        nodo: nodo,
        texto: normalizar([
          datos.getAttribute('data-nombre'),
          datos.getAttribute('data-ficha'),
          datos.getAttribute('data-habilidades')
        ].join(' '))
      });
    });
    return tarjetas;
  }

  /**
   * Oculta las tarjetas que no coinciden con todos los terminos escritos.
   */
  function aplicarFiltro(estado) {
    const consulta = normalizar(estado.buscador.value);
    const tokens = consulta.split(/\s+/).filter(Boolean);
    let visibles = 0;

    estado.tarjetas.forEach(function (tarjeta) {
      const coincide = tokens.every(function (token) {
        return tarjeta.texto.indexOf(token) !== -1;
      });
      tarjeta.nodo.classList.toggle('is-oculto', !coincide);
      if (coincide) visibles += 1;
    });

    actualizarResumen(estado, consulta, visibles);
  }

  /**
   * Actualiza el contador de resultados y el mensaje de lista vacia.
   */
  function actualizarResumen(estado, consulta, visibles) {
    const total = estado.tarjetas.length;

    if (estado.contador) {
      estado.contador.textContent = consulta
        ? 'Mostrando ' + visibles + ' de ' + total + ' candidatos'
        : total + (total === 1 ? ' candidato' : ' candidatos');
    }

    if (estado.vacio) {
      estado.vacio.hidden = !(consulta && visibles === 0);
    }

    if (estado.termino) {
      estado.termino.textContent = estado.buscador.value.trim();
    }

    if (estado.limpiar) {
      estado.limpiar.hidden = !consulta;
    }
  }

  /**
   * Vacia el buscador, restaura la lista y devuelve el foco al input.
   */
  function limpiarBusqueda(estado) {
    estado.buscador.value = '';
    aplicarFiltro(estado);
    estado.buscador.focus();
  }

  /**
   * Inicializa (o refresca) el filtro de candidatos dentro de `scope`.
   * Es idempotente: llamarlo de nuevo solo vuelve a recolectar tarjetas.
   */
  window.inicializarFiltroCandidatos = function (opciones) {
    const config = opciones || {};
    const scope = config.scope || document;
    const panel = config.panel || document.querySelector('[data-candidato-panel]');
    if (!panel) return null;

    const buscador = resolverElemento(panel, '[data-candidato-input]');
    if (!buscador) return null;

    let estado = estados.get(scope);
    if (!estado) {
      estado = { scope: scope, panel: panel, buscador: buscador, tarjetas: [] };
      estados.set(scope, estado);
    }

    estado.panel = panel;
    estado.buscador = buscador;
    estado.tarjetas = recolectarTarjetas(scope);
    estado.contador = panel.querySelector('[data-candidato-contador]');
    estado.vacio = panel.querySelector('[data-candidato-vacio]');
    estado.termino = panel.querySelector('[data-candidato-termino]');
    estado.limpiar = panel.querySelector('[data-candidato-limpiar]');

    if (!estado.inicializado) {
      estado.inicializado = true;
      estado.aplicarFiltroDebounced = crearDebounce(function () {
        aplicarFiltro(estado);
      }, ESPERA_DEBOUNCE_MS);
      estado.buscador.addEventListener('input', estado.aplicarFiltroDebounced);
      estado.buscador.addEventListener('keydown', function (evento) {
        if (evento.key === 'Escape' && estado.buscador.value) {
          evento.preventDefault();
          limpiarBusqueda(estado);
        }
      });
      if (estado.limpiar) {
        estado.limpiar.addEventListener('click', function () {
          limpiarBusqueda(estado);
        });
      }
    }

    aplicarFiltro(estado);
    return estado;
  };

  /**
   * Reaplica el filtro sobre el estado ya inicializado de un scope.
   */
  window.refrescarFiltroCandidatos = function (scope) {
    const estado = estados.get(scope || document);
    if (!estado) return false;
    estado.tarjetas = recolectarTarjetas(estado.scope);
    aplicarFiltro(estado);
    return true;
  };
})();
