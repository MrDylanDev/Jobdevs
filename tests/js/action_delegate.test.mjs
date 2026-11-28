import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const MODULE_URL = pathToFileURL(
  path.resolve('static/dashboard/script/action_delegate.js')
).href;

function makeDomEnv() {
  const listeners = new Map();
  const elementsById = new Map();

  const doc = {
    addEventListener(type, fn) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(fn);
    },
    getElementById(id) {
      return elementsById.get(id) || null;
    },
    dispatch(type, event) {
      for (const fn of listeners.get(type) || []) {
        fn(event);
      }
    },
  };

  globalThis.window = globalThis;
  delete globalThis.__jobdevsActionDelegateBound;
  globalThis.document = doc;

  return { doc, elementsById };
}

function makeEl(attrs = {}, extra = {}) {
  const dataset = {};
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith('data-')) {
      const camel = k.slice(5).replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());
      dataset[camel] = v;
    }
  }
  const el = {
    tagName: 'BUTTON',
    dataset,
    getAttribute: (name) => (name in attrs ? attrs[name] : null),
    closest: () => null,
    ...extra,
  };
  return el;
}

test('action_delegate handles data-action, data-call, indexed args, chained data-then, and blocks unallowlisted calls', async () => {
  const { doc, elementsById } = makeDomEnv();
  const calls = [];

  globalThis.closeModal = (id) => calls.push(['closeModal', id]);
  globalThis.switchTab = (tab) => calls.push(['switchTab', tab]);
  globalThis.syncCreateUserDocField = () => calls.push(['syncCreateUserDocField']);
  globalThis.validarRechazoAvance = () => false;
  globalThis.showSection = (sec, el) => calls.push(['showSection', sec, el?.tagName]);
  globalThis.closeAdminUserDropdown = () => calls.push(['closeAdminUserDropdown']);
  globalThis.debouncedFilterUsers = () => calls.push(['debouncedFilterUsers']);
  globalThis.evilUnallowlistedFn = () => calls.push(['EVIL']);

  await import(`${MODULE_URL}?t=${Date.now()}`);
  assert.equal(globalThis.__jobdevsActionDelegateBound, true);

  // 1. Standard data-action close-modal click
  const closeBtn = makeEl(
    { 'data-action': 'close-modal', 'data-target': 'editUserModal' },
    { closest: (sel) => (sel === '[data-action]' ? closeBtn : null) }
  );
  doc.dispatch('click', { target: closeBtn, preventDefault() {} });
  assert.deepEqual(calls.at(-1), ['closeModal', 'editUserModal']);

  // 2. data-self-only ignores clicks from inner child
  const overlay = makeEl(
    { 'data-action': 'close-modal', 'data-target': 'editUserModal', 'data-self-only': 'true' },
    { tagName: 'DIV', closest: (sel) => (sel === '[data-action]' ? overlay : null) }
  );
  const innerChild = { closest: (sel) => (sel === '[data-action]' ? overlay : null) };
  const beforeLen = calls.length;
  doc.dispatch('click', { target: innerChild, preventDefault() {} });
  assert.equal(calls.length, beforeLen);
  doc.dispatch('click', { target: overlay, preventDefault() {} });
  assert.equal(calls.length, beforeLen + 1);

  // 3. data-remove removes element before switching tab
  let removed = false;
  elementsById.set('inicioActionPopup', { remove() { removed = true; } });
  const tabBtn = makeEl(
    { 'data-action': 'switch-tab', 'data-target': 'ofertas', 'data-remove': 'inicioActionPopup' },
    { closest: (sel) => (sel === '[data-action]' ? tabBtn : null) }
  );
  doc.dispatch('click', { target: tabBtn, preventDefault() {} });
  assert.equal(removed, true);
  assert.deepEqual(calls.at(-1), ['switchTab', 'ofertas']);

  // 4. data-call with indexed args + chained data-then
  const navBtn = makeEl(
    {
      'data-call': 'closeAdminUserDropdown',
      'data-then': 'showSection',
      'data-then-arg-0': 'configSection',
      'data-then-arg-1': '$el',
    },
    { closest: (sel) => (sel === '[data-call]' ? navBtn : null) }
  );
  doc.dispatch('click', { target: navBtn, preventDefault() {} });
  assert.deepEqual(calls.slice(-2), [
    ['closeAdminUserDropdown'],
    ['showSection', 'configSection', 'BUTTON'],
  ]);

  // 5. Security: unallowlisted function name is blocked
  const evilBtn = makeEl(
    { 'data-call': 'evilUnallowlistedFn' },
    { closest: (sel) => (sel === '[data-call]' ? evilBtn : null) }
  );
  doc.dispatch('click', { target: evilBtn, preventDefault() {} });
  assert.equal(calls.some((c) => c[0] === 'EVIL'), false);

  // 6. data-if-no-htmx skips when window.htmx exists
  globalThis.htmx = {};
  const inputEl = makeEl(
    { 'data-input-call': 'debouncedFilterUsers', 'data-if-no-htmx': 'true' },
    { closest: (sel) => (sel === '[data-input-call]' ? inputEl : null) }
  );
  const countWithHtmx = calls.length;
  doc.dispatch('input', { target: inputEl });
  assert.equal(calls.length, countWithHtmx);
  delete globalThis.htmx;
  doc.dispatch('input', { target: inputEl });
  assert.deepEqual(calls.at(-1), ['debouncedFilterUsers']);

  // 7. Enter key on role="button" triggers click()
  let clicked = false;
  let prevented = false;
  const kpiCard = makeEl(
    { 'data-call': 'seleccionarCandidato' },
    {
      closest: (sel) => (sel.includes('[role="button"]') ? kpiCard : null),
      click() { clicked = true; },
    }
  );
  doc.dispatch('keydown', {
    key: 'Enter',
    target: kpiCard,
    preventDefault() { prevented = true; },
  });
  assert.equal(prevented, true);
  assert.equal(clicked, true);

  // 8. Submit delegation cancels when validator returns false
  let submitPrevented = false;
  const formEl = makeEl(
    { 'data-submit-action': 'validar-rechazo-avance' },
    { closest: (sel) => (sel === 'form[data-submit-action]' ? formEl : null) }
  );
  doc.dispatch('submit', {
    target: formEl,
    preventDefault() { submitPrevented = true; },
  });
  assert.equal(submitPrevented, true);
});
