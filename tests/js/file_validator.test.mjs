import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const MODULE_URL = pathToFileURL(
  path.resolve('static/dashboard/script/file_validator_async.js')
).href;

class MockFileReader {
  readAsArrayBuffer(blob) {
    queueMicrotask(() => {
      this.result = blob._bytes.buffer.slice(
        blob._bytes.byteOffset,
        blob._bytes.byteOffset + blob._bytes.byteLength
      );
      this.onload?.();
    });
  }
  readAsDataURL() {
    queueMicrotask(() => {
      this.result = 'data:image/png;base64,MOCK';
      this.onload?.();
    });
  }
  readAsText() {
    queueMicrotask(() => {
      this.result = 'mock';
      this.onload?.();
    });
  }
}

function makeFile({ name, size, bytes, type = '' }) {
  const arr = new Uint8Array(bytes);
  return {
    name,
    size,
    type,
    _bytes: arr,
    slice(start, end) {
      return { _bytes: arr.slice(start, end) };
    },
  };
}

globalThis.window = globalThis;
globalThis.FileReader = MockFileReader;
globalThis.document = {
  readyState: 'complete',
  querySelectorAll: () => [],
  addEventListener: () => {},
};

await import(MODULE_URL);
const { validarYLeerArchivo } = globalThis.JobDevsFileValidator;

test('rejects missing file, oversized file, and disallowed extension', async () => {
  await assert.rejects(() => validarYLeerArchivo(null), /No se seleccionó/);

  const huge = makeFile({
    name: 'doc.pdf',
    size: 6 * 1024 * 1024,
    bytes: [0x25, 0x50, 0x44, 0x46],
  });
  await assert.rejects(() => validarYLeerArchivo(huge, { maxMb: 5 }), /supera el límite/);

  const wrongExt = makeFile({
    name: 'script.exe',
    size: 100,
    bytes: [0x4d, 0x5a, 0x90, 0x00],
  });
  await assert.rejects(
    () => validarYLeerArchivo(wrongExt, { allowedExts: ['pdf', 'png'] }),
    /no permitido/
  );
});

test('accepts valid PDF and PNG magic bytes and rejects spoofed headers', async () => {
  const validPdf = makeFile({
    name: 'soporte.pdf',
    size: 1024,
    bytes: [0x25, 0x50, 0x44, 0x46, 0x2d, 0x31],
    type: 'application/pdf',
  });
  const pdfRes = await validarYLeerArchivo(validPdf, { allowedExts: ['pdf'] });
  assert.equal(pdfRes.valido, true);
  assert.equal(pdfRes.extension, 'pdf');
  assert.equal(pdfRes.dataUrl, null);

  const validPng = makeFile({
    name: 'avatar.png',
    size: 2048,
    bytes: [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a],
    type: 'image/png',
  });
  const pngRes = await validarYLeerArchivo(validPng, { allowedExts: ['png'] });
  assert.equal(pngRes.valido, true);
  assert.equal(pngRes.dataUrl, 'data:image/png;base64,MOCK');

  const fakePdf = makeFile({
    name: 'fake.pdf',
    size: 512,
    bytes: [0x00, 0x01, 0x02, 0x03],
    type: 'application/pdf',
  });
  await assert.rejects(() => validarYLeerArchivo(fakePdf), /no coincide con su extensión/);
});
