# Seguimiento de hallazgos de seguridad

## Alcance

Este registro acompaña al informe histórico `INFORME_SEGURIDAD_JOBDEVS.docx` del 12 de noviembre de 2026. No modifica sus conclusiones ni supone que un cambio posterior haya mitigado un hallazgo. El estado «pendiente de reverificación» significa que hace falta volver a inspeccionar el recorrido y ejecutar la evidencia indicada.

## Estados

- **Abierto:** riesgo demostrado o no mitigado.
- **Mitigación parcial:** existe cambio relacionado, pero falta criterio de cierre.
- **Pendiente de reverificación:** el checkout cambió desde el informe y no se ha repetido la prueba.
- **Cerrado:** mitigación y criterio de cierre verificados en el entorno definido.
- **Aceptado:** riesgo residual aprobado por autoridad identificada, con vencimiento/revisión.

## Registro

| ID | Prioridad | Hallazgo histórico | Estado documental actual | Criterio de cierre |
|---|---|---|---|---|
| H-01 | Alta | Evidencias de avances servidas desde `/media/` sin autorización de descarga | Pendiente de reverificación; la privacidad de evidencia de disputa no demuestra privacidad de avances | Petición anónima, usuario ajeno y usuario revocado reciben denegación; participante autorizado descarga; Nginx no expone el objeto directamente |
| H-02 | Alta condicionada | Compose publicado solo por HTTP | Abierto para cualquier exposición directa; TLS externo no verificado | HTTPS extremo a extremo, redirección, cookies Secure, HSTS aprobado, proxy confiable y `check --deploy` con entorno real |
| H-03 | Alta | Edición concurrente puede sobrescribir firma contractual | Pendiente de reverificación | Prueba PostgreSQL de intercalación; bloqueo/relectura bajo transacción; firma nunca se revierte por edición obsoleta |
| H-04 | Alta | Creación/eliminación de hitos durante disputa | Pendiente de reverificación | POST y concurrencia en `en_disputa` rechazados sin mutación; estados permitidos explícitos bajo lock |
| H-05 | Alta | Inyección de fórmulas en CSV | Pendiente de reverificación | Todos los reportes neutralizan `=`, `+`, `-`, `@` tras espacios/tabuladores y pruebas abren valores como texto |
| M-01 | Media | Bloqueo inducido y recuperación sin rate limit suficiente | Pendiente de reverificación | Límites por IP/cuenta, respuesta no enumerativa, alertas y recuperación resistente a reinicios maliciosos |
| M-02 | Media | WebSocket continúa recibiendo tras revocación | Pendiente de reverificación | Conexión se cierra o revalida tras cancelación, suspensión y cierre de sesión |
| M-03 | Media | Doble avance concurrente sobre un hito | Pendiente de reverificación | Prueba PostgreSQL; lock/relectura; máximo un avance válido según regla |
| M-04 | Media | URL R2 sin cuota/tamaño verificable en emisión directa | Abierto si R2 se habilita; bucket real no verificado | Autorización por rol/finalidad, cuota, tamaño verificable y validación posterior antes de asociar |
| M-05 | Media | GET de chat marca mensajes leídos | Pendiente de reverificación | Visualización no muta estado o la confirmación usa operación explícita protegida |
| M-06 | Media | Token de recuperación en path y posibles access logs | Pendiente de reverificación | Ruta sensible redactada, acceso/retención de logs limitados y prueba sin token en logs |
| B-01 | Baja | Validación administrativa incompleta de rol/estado/contraseña | Pendiente de reverificación; se amplió auditoría pero eso no prueba validación | Validadores centrales, whitelist y pruebas negativas de create/update/bulk |

## Cambios posteriores relacionados, no equivalentes a cierre

- Evidencia de disputa: archivo privado, formatos/tamaño y descarga autorizada para partes/administración.
- Auditoría administrativa: altas, cambios, bajas y toggles registran actor y deltas sin contraseña.
- Configuraciones de negociación/reputación: cambios administrativos auditados.
- Privacidad documental: política y matriz creadas, todavía sin prueba operativa de retención.

Estos cambios reducen riesgos en recorridos concretos, pero no cierran automáticamente los hallazgos históricos.

## Riesgos de despliegue aún no demostrados

- TLS, HSTS, cookies seguras y encabezados efectivos.
- Redis, SSE y WebSocket detrás del proxy real.
- R2 real, expiración y permisos del bucket.
- Rotación y acceso a logs.
- Backup fuera del host, cifrado y restauración periódica.
- Escaneo vigente de dependencias e imágenes.
- Monitoreo y respuesta a incidentes.

## Evidencia mínima para cerrar un hallazgo

1. Identificar commit/imagen y entorno.
2. Reproducir condición original o justificar por qué ya no es alcanzable.
3. Ejecutar prueba positiva y negativa relevante.
4. Para concurrencia/locks, usar PostgreSQL real.
5. Para proxy/TLS/WebSocket/R2, usar entorno desplegado equivalente.
6. Revisar regresión de permisos y efectos secundarios.
7. Registrar resultado, fecha, responsable y riesgo residual.
8. Obtener aceptación del riesgo si no se elimina completamente.

## Registro de revisiones

| Fecha | Checkout/entorno | Alcance | Resultado | Responsable |
|---|---|---|---|---|
| Pendiente | Pendiente | Reverificación H-01–B-01 | No ejecutada | Pendiente |

## Relación con otros documentos

- [Privacidad y tratamiento](PRIVACIDAD_Y_TRATAMIENTO_DE_DATOS.md).
- [Matriz de acceso y retención](MATRIZ_ACCESO_Y_RETENCION.md).
- [Despliegue y operación](DESPLIEGUE_Y_OPERACION.md).
- [Estado de verificación](ESTADO_VERIFICACION_ACTUAL.md).

Este documento es un registro de seguimiento, no un certificado de seguridad.
