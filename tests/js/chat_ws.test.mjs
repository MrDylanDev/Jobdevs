import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const MODULE_URL = pathToFileURL(
  path.resolve('static/mensajes/script/modules/chat_ws.js')
).href;

globalThis.window = {
  location: { protocol: 'https:', host: 'jobdevs.edu.co' },
  clearTimeout: globalThis.clearTimeout,
  setTimeout: globalThis.setTimeout,
};

const { wsUrl, createChatWs } = await import(MODULE_URL);

test('wsUrl builds wss/ws URLs with optional proyecto_id and rejects missing receptor', () => {
  const makeItem = (attrs) => ({ getAttribute: (k) => attrs[k] ?? null });

  assert.equal(wsUrl(makeItem({})), null);
  assert.equal(
    wsUrl(makeItem({ 'data-receptor': '42' })),
    'wss://jobdevs.edu.co/ws/chat/42/'
  );
  assert.equal(
    wsUrl(makeItem({ 'data-receptor': '42', 'data-proyecto': '9' })),
    'wss://jobdevs.edu.co/ws/chat/42/?proyecto_id=9'
  );

  globalThis.window.location = { protocol: 'http:', host: 'localhost:8000' };
  assert.equal(
    wsUrl(makeItem({ 'data-receptor': '7' })),
    'ws://localhost:8000/ws/chat/7/'
  );
});

test('createChatWs buffers incoming messages while historyLoading and flushes cleanly', () => {
  const appended = [];
  const previews = [];
  const state = {
    yoId: 10,
    active: { id: 'conv-1' },
    historyLoading: true,
    incomingBuffer: [],
    socketGeneration: 0,
    reconnectAttempts: 2,
    reconnectTimer: null,
    socket: { close() {} },
    pendingText: 'draft',
  };

  const ws = createChatWs({
    root: {},
    input: {},
    sessionUrl: null,
    state,
    renderer: {
      appendMessage: (m) => appended.push(m),
      scrollToBottom: () => {},
      showError: () => {},
    },
    onUpdatePreview: (_item, text, hora) => previews.push([text, hora]),
  });

  ws.handleIncoming({ id: 1, contenido: 'Hola', hora: '10:00', remitente_id: 10 });
  assert.equal(appended.length, 0);
  assert.equal(state.incomingBuffer.length, 1);

  state.historyLoading = false;
  ws.flushIncomingBuffer();
  assert.equal(appended.length, 1);
  assert.equal(appended[0].es_propio, true);
  assert.equal(state.pendingText, '');
  assert.deepEqual(previews, [['Hola', '10:00']]);

  ws.closeSocket();
  assert.equal(state.socket, null);
  assert.equal(state.socketGeneration, 1);
  assert.equal(state.reconnectAttempts, 0);
});
