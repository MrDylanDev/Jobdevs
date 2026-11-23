# Cierre autónomo de JobDevs

## Actualización de estado posterior

Este archivo conserva el diario del cierre anterior. Posteriormente, el responsable del producto aprobó el paquete consolidado en [`DECISIONES_PRODUCTO_APROBADAS.md`](DECISIONES_PRODUCTO_APROBADAS.md). Las referencias históricas a decisiones pendientes sobre comparación, cierre/reactivación, auditoría sensible, plazo de negociación, familias de disputa, evidencia, cancelación justificada y reputación quedan sustituidas por ese documento.

Parte de la implementación local cambió después de las verificaciones registradas aquí. Por tanto, los conteos de pruebas y checks de este diario no certifican el checkout actual. Los pendientes vigentes son repetir la regresión global/E2E/checks, validar migraciones en PostgreSQL, completar la integración de reputación bayesiana en todas las superficies y demostrar la cobertura de auditoría por recorrido sensible.

## Autorización y límites

El responsable del proyecto autorizó ejecutar los pendientes de cierre sin solicitar permiso entre módulos. La implementación debe realizarse con GPT-5.6 Sol (`gpt-5.6-sol`, proveedor `openai-codex`). La coordinación y verificación pueden hacerse desde la sesión principal.

Permitido: inspeccionar, corregir código, crear migraciones, añadir/ejecutar pruebas y actualizar documentación, conservando los cambios previos.

Prohibido: commits, push, despliegues, cambios en producción, gastos o nuevas suscripciones, operaciones destructivas, modificación del Excel oficial, lectura o impresión de secretos. No debilitar pruebas para conseguir una ejecución verde. No sustituir el modelo solicitado sin informar. Las decisiones de negocio no aprobadas se registran y no se implementan por inferencia; continuar con tareas independientes.

## Orden de ejecución

1. Reproducir y corregir los dos fallos del dashboard: presupuesto de consultas y expectativa del texto HTML de mediación. Investigar la causa antes de modificar código o prueba.
2. Conciliar por módulos los criterios del Excel oficial aún pendientes: hitos/avances/evidencias; cierre/calificaciones; mensajes/notificaciones; auditoría/reportes; contratos; verificación; disputas. Que falte conciliación no implica que falte implementación.
3. Corregir incumplimientos demostrados que no requieran nuevas decisiones de negocio. Aplicar TDD y preservar las políticas aprobadas.
4. Alinear la matriz interna y casos con la fuente oficial, sin renumeraciones ambiguas ni declaraciones de cumplimiento no probado. Evaluar las 31 extensiones y RNF de forma explícita, distinguiendo evidencia existente y faltante.
5. Actualizar manuales y diagramas afectados, verificar migraciones en una base descartable y ejecutar regresión relevante y global. No aplicar migraciones en la base configurada de operación.
6. Entregar informe con cambios, comandos/resultados reales, decisiones pendientes y bloqueos. No presentar validación local como validación de producción.

## Referencias

- Fuente oficial intacta: `/home/mrdylan/Proyectos/Documentación JobDevs/Matriz_de_Requisitos_JobDevs_VERIFICADA.xlsx`.
- `docs/AUDITORIA_FUENTES_REQUISITOS.md`.
- `docs/CONCILIACION_RF_BASE.md`.
- `docs/TRAZABILIDAD_REQUISITOS.md` y `docs/CASOS_DE_PRUEBA.md`.
- `PRODUCT.md` contiene decisiones y también discrepancias a conciliar, no autorización para inventar criterios.

## Base conocida antes de esta misión

La ejecución anterior de `uv run pytest -q --tb=short` terminó en 1341 aprobadas, 1 omitida y 2 fallidas, con 43 E2E deseleccionadas. Fallos: `tests/test_rnf10_escalabilidad.py::TestNumeroDeQueries::test_dashboard_empresa_queries_acotadas` (48 consultas, máximo 40) y `usuarios/tests/test_dashboard.py::test_empresa_dashboard_historial_reorganizado_y_disputas_sin_cerradas` (cadena HTML). No asumir estas cifras vigentes sin repetir.

El flujo de terminación bilateral/fuerza mayor ya está implementado: 239 pruebas de contratación/disputas y 4 E2E Chromium aprobadas en la ejecución anterior. No reconstruirlo ni revertirlo.

## Seguimiento

Estado inicial: autorización registrada; acceso a `gpt-5.6-sol` comprobado mediante una invocación real que respondió `MODELO_DISPONIBLE` con código de salida 0.

Agente de implementación iniciado y comprobado en ejecución: proveedor `openai-codex`, modelo `gpt-5.6-sol`, razonamiento `high`. Sesión `local-cbf7a35baec1ae4f43c44e669429e8a8bd730179c9b2cf135ade07101bebb72a`; proceso supervisado `proc_a95c9bc2bfa8`. El registro de inicio confirma el modelo y las primeras llamadas de herramientas. No se cambió el modelo predeterminado ni la configuración global de Hermes.

El agente de implementación debe actualizar este seguimiento al completar cada lote, indicando archivos, pruebas y decisiones bloqueadas. Los resultados parciales no son una certificación de cierre general.

### Lote 1 — dashboard de empresa y semántica HTML

Estado: completado y verificado localmente.

- `usuarios/views/empresa_dashboard.py`: consolidó conteos de proyectos, postulaciones y contratos; evita crear perfiles como efecto lateral de un GET para cuentas heredadas; reutiliza la evaluación del historial para su total.
- `disputas/services.py`: carga una sola vez las disputas visibles y deriva en memoria listas y conteos que antes ejecutaban tres consultas equivalentes.
- `usuarios/tests/test_dashboard.py`: la aserción del rótulo de mediación ahora compara el texto visible mediante `html.unescape`, sin exigir `&amp;` cuando `{% trans %}` conserva el `&` literal. Un render aislado de Django produjo `'<span>Casos Activos & En Mediación</span>'` (`raw_amp=True`, `entity_amp=False`).
- El caso RNF-10 pasó de 48 a 39 consultas, por debajo del máximo existente de 40, sin elevar el presupuesto.

Pruebas reales:

- Reproducción inicial: los dos casos indicados fallaron con 48 consultas y por ausencia de la cadena codificada `&amp;`.
- `uv run pytest -q --tb=short usuarios/tests/test_dashboard.py disputas/tests/test_dashboard_disputas.py tests/test_rnf10_escalabilidad.py`: 79 aprobadas.
- Instrumentación aislada de `CaptureQueriesContext` sobre el caso RNF-10: `QUERY_DUMP_TOTAL=39`, 1 aprobada.
- `uv run ruff check usuarios/views/empresa_dashboard.py disputas/services.py usuarios/tests/test_dashboard.py`: sin hallazgos.

Bloqueos o decisiones pendientes de este lote: ninguno. Esta verificación no certifica todavía los módulos restantes ni despliegue.

### Lote 2 — conciliación oficial del módulo 4 (hitos, avances y evidencias)

Estado: implementado, documentado y verificado localmente.

- Se contrastaron uno a uno los 8 RF oficiales 4.1.1–4.3.4 de las filas 33–40 del XLSX, sin equiparar por nombre los IDs internos que describen capacidades diferentes.
- `avances/views.py` y `templates/avances/registrar.html`: se eliminó la exigencia adicional de URL/archivo. La descripción obligatoria puede constituir por sí sola la evidencia, mientras URL y archivo continúan como alternativas opcionales validadas, conforme al RF 4.2.1 oficial.
- `avances/tests/test_avances.py`: añadió regresión de evidencia por descripción sola y fortaleció la comprobación de timestamp, paso a `en_revision`, rechazo con comentario, notificación y retorno a `en_desarrollo`. Los casos de error AJAX/preservación de formulario ahora ejercitan una URL inválida real.
- `proyectos/tests/test_views.py`: añadió cobertura integrada de creación de un equipo con contratados activos y asignación de un hito a sus miembros.
- `docs/CONCILIACION_RF_BASE.md`, `docs/TRAZABILIDAD_REQUISITOS.md`, `docs/CASOS_DE_PRUEBA.md` y `docs/AUDITORIA_FUENTES_REQUISITOS.md`: registran el mapeo fuente/código/prueba, los 8 casos oficiales X33–X40 y los límites de evidencia.

Pruebas reales:

- TDD: `test_registrar_avance_acepta_descripcion_como_evidencia` falló primero contra la validación anterior y pasó después de corregir el flujo.
- `uv run pytest -q --tb=short avances/tests/test_avances.py::TestRegistrarAvance::test_registrar_avance_acepta_descripcion_como_evidencia avances/tests/test_avances.py::TestRegistrarAvance::test_registrar_avance_preserva_datos_en_error_sin_redireccion avances/tests/test_avances.py::TestRegistrarAvance::test_registrar_avance_ajax_retorna_json_error_sin_recarga`: aprobado.
- `uv run pytest -q --tb=short proyectos/tests/test_views.py::TestGestionarHitosAsignacionIndividual::test_crea_equipo_y_asigna_hito_a_sus_miembros`: aprobado.
- `uv run pytest -q --tb=short avances/tests/test_avances.py proyectos/tests/test_views.py::TestGestionarHitosAsignacionIndividual && uv run ruff check avances/views.py avances/tests/test_avances.py`: código de salida 0.

Bloqueos o decisiones pendientes de este lote: la aceptación de producto de textos/experiencia y la precisión del reloj en un entorno desplegado no se infieren de las pruebas locales. No bloquean la conciliación ni los módulos independientes siguientes. El cierre general continúa pendiente para módulos 5–10, extensiones, RNF y regresión global.

### Lote 3 — conciliación oficial del módulo 5 (cierre y valoraciones)

Estado: implementado, documentado y verificado localmente.

- Se conciliaron los 6 RF oficiales de las filas 41–46. El cierre quedó separado de las valoraciones posteriores, como exige la fuente.
- `avances/views.py`: aprobar el último hito llama al cierre transaccional; ya no espera que la empresa valore al último colaborador.
- `proyectos/views.py` y `proyectos/services.py`: empresa y desarrolladores valoran después del cierre; se admiten participantes con contrato finalizado y se bloquean valoraciones pasados 30 días. La ruta manual solo conserva un cierre previo para proyectos heredados con hitos ya aprobados.
- `proyectos/models.py`: una `Valoracion` ya persistida rechaza cambios por la API de modelo. No se afirma protección frente a escritura SQL administrativa directa.
- `proyectos/tests/test_services.py`, `proyectos/tests/test_views.py` y `avances/tests/test_avances.py`: cubren cierre al aprobar el último hito, valoración posterior, plazo e inmutabilidad.
- Los documentos de conciliación, trazabilidad y casos incorporan las filas X41–X46 y corrigen referencias anteriores a funciones inexistentes.

Pruebas reales:

- TDD: el cierre automático falló inicialmente porque el proyecto permanecía `en_desarrollo`; las tres pruebas de valoración posterior/plazo/inmutabilidad también fallaron antes de implementar sus reglas.
- `uv run pytest -q --tb=short avances/tests/test_avances.py proyectos/tests/test_services.py proyectos/tests/test_views.py::TestFinalizarProyecto proyectos/tests/test_views.py::TestCalificarEmpresa`: 64 aprobadas.
- `uv run pytest -q --tb=short usuarios/tests/test_detalle_desarrollador.py usuarios/tests/test_detalle_empresa.py`: 15 aprobadas.
- `uv run ruff check avances/views.py avances/tests/test_avances.py proyectos/models.py proyectos/services.py proyectos/views.py proyectos/tests/test_services.py proyectos/tests/test_views.py`: sin hallazgos.

Nota histórica: inicialmente los registros heredados sin transición `finalizado` usaban `fecha_publicacion` como sustituto. Esta política fue reemplazada: no se acepta valoración nueva hasta registrar el cierre real con fecha, motivo, actor y evidencia por el panel administrativo. El plazo sigue corriendo desde el cierre real. Falta aceptación visual y verificación en despliegue.

### Lote 4 — conciliación oficial del módulo 6 (mensajes y notificaciones)

Estado: implementado, documentado y verificado localmente.

- Se conciliaron los 6 RF oficiales de las filas 47–52, separándolos de las extensiones internas WebSocket, chat grupal y SSE.
- `mensajes/policies.py` y `mensajes/views.py`: se eliminó la regla interna que obligaba a usar exclusivamente chat grupal cuando había varios desarrolladores. Los participantes conservan el canal privado directo exigido por RF 6.1.1; el grupal sigue disponible como extensión.
- `contrataciones/views.py`: al llenarse el cupo, cada postulación pendiente rechazada automáticamente genera ahora su notificación al desarrollador; antes el `update()` masivo cambiaba estado sin aviso.
- `mensajes/tests/test_mensajes.py` y `contrataciones/tests/test_contrato_digital.py`: añadieron las regresiones de privacidad directa y rechazo automático notificado.
- Documentación de conciliación/trazabilidad/casos incorporó X47–X52 y dejó explícito que la evidencia local de SSE no valida proxies ni infraestructura de despliegue.

Pruebas reales:

- TDD: ambas regresiones fallaron inicialmente (política devolvía `False` y no existía notificación) y pasaron tras las correcciones.
- `uv run pytest -q --tb=short mensajes/tests notificaciones/tests/test_sse.py postulaciones/tests/test_postulaciones.py postulaciones/tests/test_services.py contrataciones/tests/test_contrato_digital.py`: 174 aprobadas.
- `uv run ruff check mensajes/policies.py mensajes/views.py mensajes/tests/test_mensajes.py contrataciones/views.py contrataciones/tests/test_contrato_digital.py`: sin hallazgos.

Bloqueos o decisiones pendientes de este lote: `en_negociacion` funciona como la revisión contractual mencionada por la fuente; no se añadió un estado paralelo `en_revision` porque duplicaría el flujo sin una decisión de migración/UX. WebSocket/SSE detrás de Redis/proxy y la aceptación visual siguen sin verificación de despliegue. El cierre general continúa pendiente para módulos 7–10, extensiones, RNF y regresión global.

### Lote 5 — conciliación oficial del módulo 7 (auditoría y reportes)

Estado: reconciliado, documentado y verificado localmente.

- Se inspeccionó antes de continuar el trabajo parcial de `logs/models.py`, `logs/views.py`, `logs/urls.py` y `logs/tests/test_logs.py`; sus 21 pruebas iniciales pasaron y Ruff no encontró problemas.
- La lectura directa del XLSX oficial corrigió una premisa del avance interrumpido: el módulo 7 contiene **4 RF en las filas 53–56** (`7.1.2`, `7.2.1`, `7.2.2`, `7.2.3`); las filas 57–58 están vacías. No se usaron los seis criterios de otro inventario histórico como si fueran oficiales.
- Las adiciones parciales de historial filtrable, inmutabilidad de aplicación, auditoría de estados y PDF mensual se conservaron como endurecimiento/capacidades internas. Sus docstrings y documentos ya no las presentan como sustitutos de los RF oficiales.
- `logs/tests/test_logs.py` añadió evidencia de contenido para los tres CSV realmente exigidos: promedio y proyectos completados de aprendices; publicaciones y reputación de empresas; estado y detalle de todos los proyectos. También verifica que usuarios no administradores no descarguen esos reportes.
- `docs/CONCILIACION_RF_BASE.md`, `docs/TRAZABILIDAD_REQUISITOS.md` y `docs/CASOS_DE_PRUEBA.md` fueron corregidos con las filas X53–X56 reales y distinguen el inventario interno de la fuente oficial.

Pruebas reales:

- Reconciliación inicial del parcial: `uv run pytest -q --tb=short logs/tests/test_logs.py`: 21 aprobadas; `uv run ruff check logs/models.py logs/views.py logs/urls.py logs/tests/test_logs.py`: sin hallazgos.
- Nuevas pruebas de contenido/autorización de reportes: 6 aprobadas.
- `uv run pytest -q --tb=short logs/tests/test_logs.py usuarios/tests/test_dashboard.py usuarios/tests/test_admin.py::TestAdminToggleUsuario usuarios/tests/test_verificacion_empresa_views.py usuarios/tests/test_admin_verificacion_empresa.py usuarios/tests/test_admin_verificacion_desarrollador.py usuarios/tests/test_services_sena.py`: 173 aprobadas.
- `uv run ruff check ...` sobre los cuatro archivos de logs y `git diff --check` sobre código/documentos del lote: código de salida 0.

Bloqueos o decisiones pendientes de este lote: el Excel no enumera qué modificaciones de cuenta/perfil considera «críticas». Los recorridos ordinarios de edición, cambio administrativo de estado y verificación dejan auditoría, pero no se afirma captura universal de escrituras ORM/SQL administrativas. Delimitar ese conjunto requiere decisión de producto; no bloquea los reportes ni los módulos independientes siguientes. El cierre general continúa para módulos 8–10, extensiones, RNF y regresión global.

### Lote 6 — conciliación oficial del módulo 8 (negociación y contrato digital)

Estado: conciliado y verificado localmente; sin cambio de comportamiento requerido.

- Se contrastaron los 4 RF oficiales de las filas 59–62. Se corrigió la colisión documental: el template contractual es `RF 8.2.1`; doble aceptación, timestamps y hash forman juntos `RF 8.2.2`. `RF 8.1.1` queda identificado como inventario interno.
- La implementación existente conserva `en_negociacion`, chat, reserva de cupo, expiración, monto, COP/USD, forma/medio de pago, cláusulas, comentarios, disclaimer, doble firma, hash documental y activación atómica con efectos sobre postulación/proyecto/cupos.
- No se reconstruyó el flujo ya aprobado de ambas firmas ni se modificó la política contractual.
- Los documentos de conciliación, trazabilidad y casos incorporaron X59–X62 y los límites de evidencia.

Pruebas reales:

- `uv run pytest -q --tb=short contrataciones/tests/test_contrato_digital.py postulaciones/tests/test_postulaciones.py postulaciones/tests/test_expiracion_negociaciones.py`: 90 aprobadas.
- `uv run ruff check` sobre modelos, vistas, servicios y pruebas relacionadas, más `git diff --check` de los documentos del lote: código de salida 0.

Bloqueos o decisiones pendientes de este lote: el Excel pide un plazo «configurable» y cita siete días como ejemplo. La implementación fija siete días en la vista; no se inventó una preferencia administrativa ni su política de cambio. La firma es evidencia electrónica de aplicación, no certificación criptográfica externa ni validación legal. El cierre general continúa para módulos 9–10, extensiones, RNF y regresión global.

### Lote 7 — conciliación oficial del módulo 9 (verificación SENA y empresarial)

Estado: conciliado y verificado localmente; un incumplimiento interno corregido y un bloqueo externo registrado.

- Se contrastaron los 4 RF oficiales de las filas 64–67. Se separó una lista blanca administrada dentro de JobDevs de una consulta en vivo a fuentes institucionales.
- TDD en `usuarios/services_sena.py`: una nueva prueba demostró que el servicio aceptaba una ficha activa aun si el programa suministrado era contradictorio. `validar_ficha_sena_en_lista_blanca` ahora rechaza esa combinación; si no se suministra programa, conserva el programa oficial de la ficha.
- Se verificaron el registro, bloqueo de postulación para no verificados, gestión de fichas/excepciones, revisión manual, advertencias de empresa no verificada y badges SENA/empresa.
- La documentación ya no afirma que la revisión humana de documentos equivale a validar NIT contra RUES/Cámara de Comercio.

Pruebas reales:

- RED: `test_ficha_activa_rechaza_programa_que_no_coincide` falló porque devolvía la ficha activa.
- GREEN: el caso nuevo y `TestVerificacionDesarrolladorAutomatica`: 3 aprobadas.
- `uv run pytest -q --tb=short` sobre registro, servicios SENA, verificaciones de desarrollador/empresa, integraciones, badges y postulaciones: 192 aprobadas.
- `uv run ruff check usuarios/services_sena.py usuarios/tests/test_services_sena.py` y `git diff --check` del lote: código de salida 0.

Bloqueos o decisiones pendientes de este lote: `RF 9.2.1` exige consulta a RUES/Cámara de Comercio, que no existe ni puede simularse como cumplida con revisión documental. Requiere definir proveedor/fuente, acceso, tratamiento de indisponibilidad y aceptación de producto; no se usaron credenciales ni suscripciones. La lista blanca SENA es interna y no prueba sincronización en vivo con SOFIA Plus. El cierre general continúa para módulo 10, extensiones, RNF y regresión global.

### Lote 8 — conciliación oficial del módulo 10 (mediación y resolución)

Estado: conciliado y verificado localmente; diferencias de política registradas sin inventar efectos.

- Se contrastaron los 5 RF oficiales de las filas 69–73 contra apertura, dashboard, sala, resolución y efectos transaccionales.
- Se verificaron apertura por ambos titulares, congelación de proyecto/contrato, avisos internos a contraparte/admin, filtros de estados, aislamiento tripartito, auditoría de mensajes y resolución restringida al administrador.
- La documentación ahora explicita que el Excel define tres resultados (a favor de empresa, a favor de desarrollador y acuerdo mutuo), mientras el modelo mantiene cuatro acciones (reanudar, cancelar, sancionar empresa, sancionar desarrollador). No se eligió un mapeo ni una migración histórica sin aprobación.
- También quedó explícito que `RF 10.3.1` menciona aceptación/rechazo de avances y ajuste de calificaciones: la implementación cubre reanudación/cierre/rechazo, pero no aceptación automática ni cálculo de reputación.

Pruebas reales:

- `uv run pytest -q --tb=short disputas/tests contrataciones/tests/test_cancelacion_disputa_integrada.py`: 163 aprobadas.
- `uv run ruff check` sobre modelos, servicios, vistas y pruebas de disputas/integración, más `git diff --check` de los documentos: código de salida 0.

Bloqueos o decisiones pendientes de este lote: decidir el mapeo de tres resultados oficiales frente a cuatro acciones locales, el tratamiento de expedientes históricos, cuándo aceptar/rechazar avances y si/cómo ajustar calificaciones. La fuerza mayor aprobada no admite sanción automática. `RF 10.1.1` además dice «adjuntando evidencia», mientras la URL es opcional; exigirla necesita política de formatos y excepciones. El cierre general continúa para las 31 extensiones, 38 RNF, migraciones, regresión global y documentación final.

### Lote 9 — conciliación de las 31 extensiones oficiales

Estado: las 31 extensiones fueron contrastadas y documentadas; un incumplimiento corregido por TDD y límites externos/políticos registrados.

- Se leyó directamente la hoja `Extensiones y Nuevos RFs (31)` del XLSX: enumera exactamente `RF-N01`–`RF-N31` en las filas 5–35. Su columna «100% CUMPLE» se trató como declaración de la fuente, no como evidencia.
- `docs/TRAZABILIDAD_REQUISITOS.md`, `docs/CASOS_DE_PRUEBA.md` y `docs/AUDITORIA_FUENTES_REQUISITOS.md` distinguen ahora evidencia local, infraestructura no ensayada y decisiones pendientes para cada extensión.
- TDD para `RF-N29`: la regresión nueva falló porque `HistorialEstadoProyecto` permitía editar y borrar entradas. `save()` y `delete()` rechazan ahora esas mutaciones por la API de modelo; no se sobreafirma protección frente a SQL directo ni operaciones masivas administrativas.
- La regresión amplia descubrió que la tarjeta principal del dashboard abría el modal técnico aun con negociación activa, pese a que la vista solo admite editar título/prioridad. Se condicionó el `onclick` como en la segunda representación del mismo listado; la ruta de edición básica se conserva.
- No se inventó una fórmula para `RF-N31`: el comando reconcilia promedio simple y la fuente dice «promedio ponderado» sin definir pesos. Tampoco se equipararon checksum de NIT con existencia registral ni validación de texto con justificación sustantiva.

Pruebas reales:

- RED de `RF-N29`: 1 fallida antes del cambio; GREEN y regresión de modelos: 10 aprobadas. Ruff de modelo/prueba: sin hallazgos.
- Primera regresión de extensiones: 1 fallida, 806 aprobadas y 1 omitida; el fallo fue el modal de edición durante negociación.
- Reproducción/corrección del fallo del dashboard: 19 aprobadas en `TestEditarProyecto`.
- Regresión repetida: `uv run pytest -q --tb=short` sobre proyectos, avances, contratación, expiración, verificaciones, disputas, SSE/WebSockets, mensajería, favoritos y logs: **807 aprobadas, 1 omitida**, código 0.
- `git diff --check` sobre código/documentos del lote: código 0.

Bloqueos o decisiones pendientes de este lote: `RF-N04` contradice la finalización irreversible; `RF-N09` no define qué constituye motivo justificado; `RF-N31` no aporta fórmula de ponderación. Beat/worker, concurrencia PostgreSQL, SSE/proxy, Redis/latencia, privacidad operativa de chats y restauración PostgreSQL siguen requiriendo entornos/aceptación externos. El cierre continúa con los 38 RNF, checks/migraciones, suite global, E2E y el informe final.

### Lote 10 — auditoría de los 38 RNF y migraciones descartables

Estado: catálogo completo conciliado y casos diseñados; evidencia local verificada sin certificar infraestructura externa.

- El XLSX oficial no contiene una hoja RNF. La fuente identificada y ya documentada es `Documentacion Mark/MatrizRNF.md`, con 38 IDs únicos `RNF-01`–`RNF-38`.
- Se sustituyó la selección de seis por una evaluación de los 38 RNF en `docs/TRAZABILIDAD_REQUISITOS.md`, y `docs/CASOS_DE_PRUEBA.md` pasó de 6 a 38 casos no funcionales.
- No se heredaron como hechos las etiquetas «100% CUMPLE», «1.240+ tests» o «VERIFICADO» de la fuente. Los veredictos separan pruebas locales de PostgreSQL concurrente/restauración, Redis/ASGI/proxy, navegadores reales, R2, CI remota y despliegue.
- Los límites principales quedaron explícitos: sesión de una hora no implica rotación; pruebas de cliente no son carga real; estructura responsive no es aceptación visual; checksum NIT no es identidad; tail HTTP no es stream continuo; cobertura de recorridos no demuestra «toda vista/acción»; hashes locales no son firma certificada.

Pruebas y checks reales:

- Suite RNF enfocada: `uv run pytest -q --tb=short` sobre rendimiento, responsive, escalabilidad, configuración, Celery, auth, middleware, admin/cache, archivos/storage, cliente externo, atomicidad, SSE/WebSockets, logging y backup: **593 aprobadas, 1 omitida**, código 0.
- `DB_ENGINE=sqlite3 DB_NAME=:memory: uv run python manage.py check`: sin problemas.
- `DB_ENGINE=sqlite3 DB_NAME=:memory: uv run python manage.py makemigrations --check --dry-run`: `No changes detected`.
- Todas las migraciones se aplicaron desde cero con código 0 en la base descartable `/home/mrdylan/.hermes/cache/scratch/jobdevs_migration_check_761562.sqlite3`; `showmigrations --plan` confirmó el plan aplicado. No se tocó una base de operación.

Bloqueos pendientes: ensayo de restauración PostgreSQL <300 s; concurrencia real con bloqueos de fila; workers/Beat/Redis/proxy; matriz E2E Chrome/Firefox/Edge; bucket R2 real; CI remota y controles operativos de privacidad. Son validaciones de entorno o producto, no fallos que deban fingirse resueltos. El cierre continúa con Ruff/suite global, E2E disponible e informe final.

### Lote 11 — regresión global, E2E e informe final

Estado: cierre técnico local completado; pendientes externos y decisiones de producto conservados como tales.

- Suite global predeterminada: **1361 aprobadas, 1 omitida y 43 E2E deseleccionadas** en 80.74 s, código 0.
- La primera ejecución E2E reveló pruebas desalineadas con la UI/reglas vigentes: disputa en modal, chat después del cierre automático, reputación oculta hasta activar pestaña y CTA inestable durante la transición de tab. Se actualizaron los recorridos sin retirar sus aserciones de negocio.
- Suite E2E final: **43 aprobadas** en Chromium 156.0.8078.4, 247.90 s, código 0.
- Total local combinado: **1404 aprobadas y 1 omitida**. La omisión requiere PostgreSQL y `pg_restore`; no se ocultó ni se simuló.
- `uv run ruff check .`: sin hallazgos. `git diff --check`: código 0 después de retirar líneas en blanco finales detectadas en dos archivos ya modificados.
- La cobertura documental fue comprobada programáticamente: XLSX base 66 IDs únicos, XLSX extensiones 31; casos/traza contienen 31 extensiones y 38 RNF únicos con rangos completos.
- Se creó `docs/INFORME_CIERRE_AUTONOMO.md` con cambios, resultados, límites, decisiones pendientes y bloqueos. No declara aprobación de producto, producción ni porcentaje de cobertura.

Cierre: no quedan fallos locales reproducidos dentro de las suites ejecutables en este entorno. Permanecen fuera del cierre local la consulta RUES/SOFIA Plus, restauración/concurrencia PostgreSQL, Redis/ASGI/proxy, workers/Beat, R2, matriz Chrome/Firefox/Edge, CI remota, aceptación visual y las decisiones de negocio enumeradas en el informe.
