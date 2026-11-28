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

test('action_delegate handles click, self-only, remove, keyboard, change, and submit', async () => {
  const { doc, elementsById } = makeDomEnv();
  const calls = [];

  globalThis.closeModal = (id) => calls.push(['closeModal', id]);
  globalThis.switchTab = (tab) => calls.push(['switchTab', tab]);
  globalThis.syncCreateUserDocField = () => calls.push(['syncCreateUserDocField']);
  globalThis.validarRechazoAvance = () => false;

  await import(`${MODULE_URL}?t=${Date.now()}`);
  assert.equal(globalThis.__jobdevsActionDelegateBound, true);

  // 1. Standard close-modal click
  const closeBtn = {
    tagName: 'BUTTON',
    dataset: { action: 'close-modal', target: 'editUserModal' },
    closest: (sel) => (sel === '[data-action]' ? closeBtn : null),
  };
  doc.dispatch('click', { target: closeBtn, preventDefault() {} });
  assert.deepEqual(calls.at(-1), ['closeModal', 'editUserModal']);

  // 2. data-self-only ignores clicks from inner child
  const overlay = {
    tagName: 'DIV',
    dataset: { action: 'close-modal', target: 'editUserModal', selfOnly: 'true' },
    closest: (sel) => (sel === '[data-action]' ? overlay : null),
  };
  const innerChild = { closest: (sel) => (sel === '[data-action]' ? overlay : null) };
  const beforeLen = calls.length;
  doc.dispatch('click', { target: innerChild, preventDefault() {} });
  assert.equal(calls.length, beforeLen);
  doc.dispatch('click', { target: overlay, preventDefault() {} });
  assert.equal(calls.length, beforeLen + 1);

  // 3. data-remove removes element before switching tab
  let removed = false;
  elementsById.set('inicioActionPopup', { remove() { removed = true; } });
  const tabBtn = {
    tagName: 'BUTTON',
    dataset: { action: 'switch-tab', target: 'ofertas', remove: 'inicioActionPopup' },
    closest: (sel) => (sel === '[data-action]' ? tabBtn : null),
  };
  doc.dispatch('click', { target: tabBtn, preventDefault() {} });
  assert.equal(removed, true);
  assert.deepEqual(calls.at(-1), ['switchTab', 'ofertas']);

  // 4. Enter key on role="button" triggers click()
  let clicked = false;
  let prevented = false;
  const kpiCard = {
    dataset: { action: 'switch-tab', target: 'contratos' },
    closest: (sel) => (sel === '[role="button"][data-action]' ? kpiCard : null),
    click() { clicked = true; },
  };
  doc.dispatch('keydown', {
    key: 'Enter',
    target: kpiCard,
    preventDefault() { prevented = true; },
  });
  assert.equal(prevented, true);
  assert.equal(clicked, true);

  // 5. Change delegation
  const selectEl = {
    dataset: { changeAction: 'sync-create-user-doc' },
    closest: (sel) => (sel === '[data-change-action]' ? selectEl : null),
  };
  doc.dispatch('change', { target: selectEl });
  assert.deepEqual(calls.at(-1), ['syncCreateUserDocField']);

  // 6. Submit delegation cancels when validator returns false
  let submitPrevented = false;
  const formEl = {
    dataset: { submitAction: 'validar-rechazo-avance' },
    closest: (sel) => (sel === 'form[data-submit-action]' ? formEl : null),
  };
  doc.dispatch('submit', {
    target: formEl,
    preventDefault() { submitPrevented = true; },
  });
  assert.equal(submitPrevented, true);
});
