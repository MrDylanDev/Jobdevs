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
    return estado;
  };
})();
