/**
 * JobDevs - Notificaciones en tiempo real con Server-Sent Events (SSE) (ES Module Orchestrator)
 * Conexión continua unidireccional HTTP con reconexión automática y toasts accesibles.
 */

import { createToastApi, setOnWsMessageToast } from './modules/toast_manager.js';
import { createSseApi, initSSEClient, registrarMensajeWS } from './modules/sse_client.js';

setOnWsMessageToast(registrarMensajeWS);

window.JobDevsToast = createToastApi();
window.JobDevsSSE = createSseApi();

initSSEClient();
