# Informe de cierre autónomo de JobDevs

## 1. Resultado

Estado: **cierre técnico local alcanzado con pendientes externos y de producto explícitos**.

La misión ejecutó la conciliación pendiente de los módulos 4–10, las 31 extensiones, los 38 RNF, checks de Django, migraciones en SQLite descartable, regresión global, Ruff y E2E Chromium. No se modificó el XLSX oficial, no se usaron secretos, no se aplicaron migraciones a una base de operación y no hubo commit, push ni despliegue.

Este resultado no constituye aprobación de producto, certificación legal, auditoría de producción ni validación de infraestructura externa.

### Actualización posterior al cierre registrado

Después de las ejecuciones de este informe, el responsable del producto aprobó ocho decisiones que antes figuraban como pendientes. Su especificación vigente está en [`DECISIONES_PRODUCTO_APROBADAS.md`](DECISIONES_PRODUCTO_APROBADAS.md): cierre irreversible con proyecto sucesor, comparación simultánea de 2–4 candidatos, catálogo de auditoría sensible, plazo de negociación 1–30 días congelado, tres familias para cuatro acciones de disputa, evidencia privada por causal, cancelación sustantivamente justificada y reputación bayesiana transparente.

También hubo cambios locales posteriores. Por eso:

- las cifras de pruebas, Ruff, migraciones y E2E de las secciones 4 y 7 son evidencia histórica del checkout de entonces, no del estado actual;
- no se declara cierre técnico del paquete posterior hasta repetir la regresión global, E2E, checks y validación de migraciones;
- la reputación bayesiana tiene fórmula y configuración, pero su integración uniforme en todas las interfaces y reportes sigue pendiente;
- la cobertura exhaustiva de auditoría debe verificarse por recorrido sensible;
- no hubo commit, push, despliegue ni migración sobre una base de operación.

## 2. Fuentes y cobertura documental

Fuente oficial de RF base/extensiones, preservada en solo lectura:

`/home/mrdylan/Proyectos/Documentación JobDevs/Matriz_de_Requisitos_JobDevs_VERIFICADA.xlsx`

Resultados de lectura y validación programática:

- La hoja `Requisitos Base (68 RFs)` contiene **66 IDs RF únicos**, no 68.
- La hoja `Extensiones y Nuevos RFs (31)` contiene **31 IDs únicos**, `RF-N01`–`RF-N31`.
- El XLSX no contiene una hoja RNF.
- La fuente RNF identificada es `Documentacion Mark/MatrizRNF.md`, con **38 IDs únicos**, `RNF-01`–`RNF-38`.
- `CASOS_DE_PRUEBA.md` contiene 31 casos únicos `CP-N01`–`CP-N31` y 38 casos únicos `CP-RNF-01`–`CP-RNF-38`.
- `TRAZABILIDAD_REQUISITOS.md` contiene las 31 extensiones y los 38 RNF, sin usar las etiquetas «100% CUMPLE» de las fuentes como evidencia automática.

Documentos actualizados:

- `docs/CONCILIACION_RF_BASE.md`
- `docs/TRAZABILIDAD_REQUISITOS.md`
- `docs/CASOS_DE_PRUEBA.md`
- `docs/AUDITORIA_FUENTES_REQUISITOS.md`
- `docs/CIERRE_AUTONOMO.md`
- este informe

## 3. Trabajo cerrado por lote

### Dashboard y RNF-10

- Se redujo el caso medido del dashboard de empresa de 48 a 39 consultas sin aumentar el presupuesto de 40.
- Se corrigió la expectativa de texto visible de mediación sin exigir una entidad HTML específica.
- El GET del dashboard dejó de crear perfiles como efecto lateral para cuentas heredadas.

### Módulo 4: hitos, avances y evidencias

- Se conciliaron los 8 RF oficiales de las filas 33–40.
- La descripción obligatoria puede constituir evidencia; URL y archivo quedan como alternativas opcionales validadas.
- Se fortaleció la cobertura de equipos, asignación individual, revisión, rechazo, notificación y retorno a desarrollo.

### Módulo 5: cierre y valoraciones

- Se conciliaron los 6 RF oficiales de las filas 41–46.
- La aprobación del último hito cierra el proyecto; las valoraciones se registran después y no gobiernan la transición.
- Se añadió plazo de 30 días e inmutabilidad de valoraciones por API de modelo.

### Módulo 6: mensajes y notificaciones

- Se conciliaron los 6 RF oficiales de las filas 47–52.
- El chat directo privado se conserva aunque exista chat grupal.
- El rechazo automático por cupo lleno notifica individualmente a cada postulante afectado.

### Módulo 7: auditoría y reportes

- Se inspeccionó y verificó el trabajo parcial previo de `logs/` antes de continuar.
- El módulo oficial contiene 4 RF en las filas 53–56; las filas 57–58 están vacías.
- Se verificaron los CSV de aprendices, empresas y proyectos, su contenido y autorización.
- Las capacidades adicionales de historial filtrable, PDF e inmutabilidad se documentaron como extensiones, no como RF oficiales inexistentes.

### Módulo 8: negociación y contrato

- Se conciliaron los 4 RF oficiales de las filas 59–62.
- `RF 8.2.1` corresponde al template contractual; `RF 8.2.2` agrupa doble aceptación, timestamps y hash.
- Se preservó la política aprobada de doble firma para activar toda contratación.

### Módulo 9: verificación

- Se conciliaron los 4 RF oficiales de las filas 64–67.
- TDD corrigió la aceptación de una ficha SENA activa con programa contradictorio.
- La lista blanca interna no se presentó como sincronización en vivo con SOFIA Plus.
- La revisión documental empresarial no se presentó como consulta RUES/Cámara de Comercio.

### Módulo 10: disputas

- Se conciliaron los 5 RF oficiales de las filas 69–73.
- Se verificaron apertura, congelación, avisos, mediación tripartita, resolución administrativa y efectos transaccionales.
- No se inventó un mapeo entre los tres resultados del XLSX y las cuatro acciones locales.

### Extensiones `RF-N01`–`RF-N31`

- Las 31 se contrastaron individualmente.
- TDD corrigió `RF-N29`: `HistorialEstadoProyecto` rechaza modificación y eliminación por su API de modelo.
- `RF-N31` quedó parcial: existe reconciliación por promedio simple, pero la fuente pide promedio ponderado y no define fórmula ni pesos.
- Una regresión detectó y corrigió que el dashboard abriera el modal técnico durante una negociación; la edición básica por ruta permanece disponible.

### RNF-01–RNF-38

- Se documentaron los 38, sustituyendo la selección previa de seis.
- Se diseñaron los 38 casos no funcionales.
- Se separó evidencia local de validaciones de infraestructura, visuales, de carga, privacidad y despliegue.

## 4. Verificación ejecutada

### Regresión de extensiones

`uv run pytest -q --tb=short` sobre proyectos, avances, contratación, expiración, verificaciones, disputas, SSE/WebSockets, mensajería, favoritos y logs:

- **807 aprobadas**
- **1 omitida**
- código 0

### Suite RNF enfocada

- **593 aprobadas**
- **1 omitida**
- código 0

### Suite global sin E2E

`uv run pytest -q --tb=short`:

- 1405 recolectadas
- 43 E2E deseleccionadas por la configuración predeterminada
- **1361 aprobadas**
- **1 omitida**
- duración: **80.74 s**
- código 0

El umbral de 90 s de RNF-33 se cumplió en esta ejecución SQLite local, pero no certifica otros hosts ni PostgreSQL.

### E2E Chromium

`uv run pytest -q --tb=short -m e2e tests/e2e`:

- navegador: Chromium **156.0.8078.4**
- **43 aprobadas**
- duración final: **247.90 s**
- código 0

Los E2E se alinearon con la UI vigente sin retirar garantías: disputa dentro de modal, chat antes del cierre automático por último hito, pestaña explícita de reputación y selección estable de la CTA de nueva convocatoria.

### Total local combinado

- **1404 aprobadas**
- **1 omitida**
- la omitida es `logs/tests/test_backup_commands.py:91`: requiere PostgreSQL y `pg_restore`.

No se suma una ejecución duplicada: el total combina los 1362 casos no E2E seleccionados y los 43 E2E ejecutados aparte.

### Calidad y consistencia

- `uv run ruff check .`: `All checks passed!`.
- `git diff --check`: código 0 tras retirar espacios finales ajenos detectados en dos archivos ya modificados.
- `DB_ENGINE=sqlite3 DB_NAME=:memory: uv run python manage.py check`: sin problemas.
- `DB_ENGINE=sqlite3 DB_NAME=:memory: uv run python manage.py makemigrations --check --dry-run`: `No changes detected`.
- Todas las migraciones se aplicaron desde cero y se listaron como aplicadas en `/home/mrdylan/.hermes/cache/scratch/jobdevs_migration_check_761562.sqlite3`.

## 5. Pendientes y bloqueos reales

### Decisiones de producto

Esta lista era válida al producir el informe y queda sustituida por las decisiones aprobadas posteriores. Se resolvieron comparación lado a lado, cierre irreversible con sucesor, catálogo de cambios sensibles, plazo administrativo congelado, mapeo de familias, política de evidencia, justificación de cancelación y fórmula bayesiana. El tratamiento histórico sin fecha de cierre fiable se resolvió mediante regularización administrativa documentada en `VALORACIONES_HISTORICAS.md`.

Pendientes actuales de implementación/verificación, no de definición de política:

- integrar reputación bayesiana de forma consistente en todas las interfaces, rankings, comandos y reportes;
- demostrar cobertura de auditoría para cada recorrido sensible;
- repetir regresión global y E2E después del paquete;
- validar las migraciones recientes en PostgreSQL y en el entorno de despliegue;
- realizar aceptación visual/funcional del responsable del producto.

### Dependencias o entornos externos

- Consulta real a RUES/Cámara de Comercio para `RF 9.2.1`.
- Sincronización institucional en vivo con SOFIA Plus.
- Concurrencia real y bloqueos de fila en PostgreSQL.
- Restauración integral de respaldo PostgreSQL con `pg_restore` en menos de 300 s.
- Celery worker/Beat y Redis desplegados.
- SSE y WebSockets detrás de proxy/ASGI/Redis, incluida medición de latencia.
- Matriz real Chrome, Firefox y Edge; en esta misión solo se ejecutó Chromium.
- Bucket Cloudflare R2 real y expiración externa de URLs prefirmadas.
- Aceptación visual multidispositivo y controles operativos de privacidad.
- Estado de CI remota y despliegue.

## 6. Límites de las garantías

- La inmutabilidad de historial, valoraciones, logs y contratos es una garantía de aplicación; no impide SQL directo ni toda operación administrativa fuera de los recorridos instrumentados.
- El hash contractual no equivale a firma digital certificada ni dictamen legal.
- El dígito de verificación NIT es un checksum; no demuestra existencia o identidad registral.
- Las pruebas locales de tiempo, consultas y HTML/CSS no certifican rendimiento, accesibilidad visual o comportamiento en producción.
- No se afirma porcentaje global de cobertura, cero defectos, aprobación del responsable de producto ni cumplimiento de despliegue.

## 7. Repetición independiente desde la sesión coordinadora

Después de finalizar el agente GPT-5.6 Sol, la sesión coordinadora repitió las verificaciones sobre el checkout actual, sin modificar código:

- `uv run pytest -q --tb=short`: **1361 aprobadas, 1 omitida y 43 E2E deseleccionadas**, código 0; duración **97.25 s**.
- `uv run pytest -q --tb=short -m e2e tests/e2e`: **43 aprobadas** en Chromium 156.0.8078.4, código 0; duración **217.86 s**.
- `uv run ruff check .`: sin hallazgos.
- `git diff --check`: código 0.
- `DB_ENGINE=sqlite3 DB_NAME=:memory: uv run python manage.py check`: sin problemas.
- `DB_ENGINE=sqlite3 DB_NAME=:memory: uv run python manage.py makemigrations --check --dry-run`: `No changes detected`.

Total combinado comprobado de nuevo: **1404 aprobadas y 1 omitida**. La prueba omitida requiere PostgreSQL y `pg_restore`, según su condición en `logs/tests/test_backup_commands.py`.

Las suites general y E2E de esta repetición se ejecutaron concurrentemente. El tiempo general de 97.25 s supera los 90 s citados para RNF-33; por tanto, la medición anterior de 80.74 s no demuestra un presupuesto temporal estable. Para aceptar ese RNF hace falta un protocolo de medición controlado y repetible, sin equiparar éxito funcional con cumplimiento de tiempo.

Esta repetición confirma la ejecución local de pruebas y checks; no es una revisión exhaustiva de cada diff ni verificación de infraestructura o producción. No hubo commit, push ni despliegue desde la sesión coordinadora.
