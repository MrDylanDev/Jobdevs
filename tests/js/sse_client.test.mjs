import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const MODULE_URL = pathToFileURL(
  path.resolve('static/dashboard/script/modules/sse_client.js')
).href;

globalThis.window = globalThis;
globalThis.document = {
  cookie: 'other=1; csrftoken=abc%20123; theme=dark',
  querySelector: () => null,
  querySelectorAll: () => [],
};

const {
  registrarMensajeWS,
  esMensajeRecienteWS,
  getCookie,
  getCsrfToken,
  actualizarBadges,
} = await import(MODULE_URL);

test('WS message deduplication records and consumes recent messages once', () => {
  registrarMensajeWS('  Hola mundo  ');
  assert.equal(esMensajeRecienteWS('Hola mundo'), true);
  assert.equal(esMensajeRecienteWS('Hola mundo'), false);
  assert.equal(esMensajeRecienteWS(''), false);
});

test('getCookie and getCsrfToken decode cookies and prefer hidden CSRF input', () => {
  assert.equal(getCookie('csrftoken'), 'abc 123');
  assert.equal(getCookie('missing'), null);
  assert.equal(getCsrfToken(), 'abc 123');

  globalThis.document.querySelector = (sel) =>
    sel === '[name=csrfmiddlewaretoken]' ? { value: 'input-token-xyz' } : null;
  assert.equal(getCsrfToken(), 'input-token-xyz');
  globalThis.document.querySelector = () => null;
});

test('actualizarBadges toggles display and text for positive and zero counts', () => {
  const styles = [];
  const badge = {
    textContent: '0',
    style: {
      setProperty(prop, val, prio) {
        styles.push([prop, val, prio]);
      },
    },
  };
  globalThis.document.querySelectorAll = () => [badge];

  actualizarBadges(4);
  assert.equal(badge.textContent, 4);
  assert.deepEqual(styles.at(-1), ['display', 'inline-flex', 'important']);

  actualizarBadges(0);
  assert.equal(badge.textContent, '0');
  assert.deepEqual(styles.at(-1), ['display', 'none', 'important']);
});
