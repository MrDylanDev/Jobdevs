# Casos de prueba — JobDevs

## 1. Objetivo, alcance y estado

Catálogo de pruebas funcionales y de seguridad basado en las capacidades documentadas en [`TRAZABILIDAD_REQUISITOS.md`](TRAZABILIDAD_REQUISITOS.md) y en las rutas, modelos y pruebas existentes del repositorio. Cubre los roles Desarrollador, Empresa y Administrador; registro, perfiles, proyectos, postulaciones, negociación, contratación, hitos, avances, valoraciones, mensajería, notificaciones, disputas, auditoría y operación.

**Este es un diseño de pruebas, no un acta de ejecución.** Cada resultado esperado debe comprobarse durante la ejecución y registrarse en el formato de la sección 7. La existencia de un test automatizado relacionado no implica que un caso manual haya pasado. Los códigos HTTP descritos para endpoints se verificarán contra la implementación; para pantallas se comprobará además la ausencia de cambios indebidos en la base de datos.

**Control de alcance:** el Excel `Matriz_de_Requisitos_JobDevs_VERIFICADA.xlsx` (en `~/Descargas/Documentación JobDevs.zip`) fue elegido como **fuente oficial** de RF. Este catálogo todavía cubre los **99 identificadores RF de la matriz interna** (68 numerados y 31 RF-N), no los criterios del Excel: allí aparecen 66 RF base enumerados y 31 extensiones; 12 IDs base solo están en el Excel y 14 solo en la matriz interna. La elección de fuente no equivale a aprobar los criterios contradictorios ni a certificar cobertura. Ver [auditoría de fuentes](AUDITORIA_FUENTES_REQUISITOS.md). Los seis casos RNF de la sección 8 son una selección de **38 RNF documentados**, no cobertura RNF completa ni aprobación formal de requisitos.

## 2. Convenciones y preparación

- ID `CP-X`: caso positivo o de regla de negocio vinculado al requisito `RF X`; `CP-NXX` vincula `RF-NXX`. ID `NEG-X`: prueba adversarial o de frontera complementaria.
- Prioridad: P0 = autorización, integridad, dinero/firma, datos privados; P1 = flujo principal; P2 = presentación, filtrado o datos auxiliares.
- Entorno: instancia de pruebas aislada, nunca producción; SQLite para desarrollo o PostgreSQL 16 para integración; base de datos reiniciable y correo de prueba (Mailpit o backend de test). No cargar datos personales reales ni documentos de identidad reales.
- Datos reutilizables: `EMP-A` (empresa verificada, proyecto propio), `EMP-B` (empresa ajena), `DEV-A` (desarrollador SENA habilitado), `DEV-B` (desarrollador ajeno), `ADM-A` (administrador), `ANON` (sin sesión). Crear proyectos de prueba con estados `publicado`, `en_desarrollo`, `en_disputa`, `finalizado`, con vacantes libres y agotadas; contrataciones propias y ajenas; soportes ficticios. Cuando una regla dependa de firma, estado o plazo, crear explícitamente ese estado antes de ejecutar el caso.
- Orden: ejecutar registro y permisos, después flujo completo Empresa → Desarrollador → Empresa → cierre, y finalmente negativos y operación. Restablecer datos o usar registros independientes para que un caso no dependa del resultado no documentado de otro.
- En cada caso registrar URL/pantalla, entrada exacta, usuario, fecha, entorno, versión/commit, resultado observado y evidencia redaccionada. Un `302` por login, `403` de autorización, `404` por recurso ajeno o `400` por datos inválidos se considera correcto **solo cuando coincide con el contrato concreto**; nunca inferir éxito por el código HTTP únicamente.

## 3. Casos funcionales y de reglas de negocio

Cada fila es ejecutable después de preparar su precondición. «Acción» equivale a pasos a realizar en la interfaz o endpoint correspondiente; repetir con los datos indicados cuando se describa más de una variante. Para los tests automatizados relacionados, consultar la columna «Archivo de Pruebas» de [`TRAZABILIDAD_REQUISITOS.md`](TRAZABILIDAD_REQUISITOS.md), contrastando la ruta con el árbol actual antes de citar evidencia.

Formato: `Caso | RF | Prioridad | Precondición | Acción / datos | Resultado esperado`. Cada fila supone el entorno y los usuarios de la sección 2. Las acciones no son una afirmación de que ya se ejecutaron.

### M1. Cuenta, perfiles y sesión
Los casos de esta sección siguen IDs **internos**. La [revisión de los 17 RF 1.* oficiales](CONCILIACION_RF_BASE.md#revisión-del-módulo-1-usuarios-frente-al-excel-oficial) registra la decisión de conservar login unificado como excepción al RF 1.4.1 literal; RF 1.2.4 ahora permite ingresar habilidades, ficha y programa opcionales en el registro. Para RF 1.4.3 existe prueba de cookie de sesión sin `Expires`/`Max-Age`, pero queda pendiente ejecutar y registrar cierre/reapertura real de navegador. No marcar estos casos como aceptación de la fuente sin adaptar sus criterios.

| Caso | RF | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| CP-1.1.1 | RF 1.1.1 | P1 | ANON; identificaciones ficticias disponibles | Registrar Empresa y Dev con tipos e identificaciones válidos; repetir una identificación | Cada cuenta válida se crea una vez; el duplicado o tipo inválido se rechaza. |
| CP-1.1.2 | RF 1.1.2 | P0 | Formulario de registro | Enviar clave insegura, confirmación diferente y luego clave segura coincidente | Los dos primeros intentos no crean cuenta; el válido sí. |
| CP-1.2.1 | RF 1.2.1 | P1 | Catálogo SENA disponible | Registrar aprendiz con programa/ficha válidos y con programa ajeno al catálogo | Datos válidos aceptados; selección no permitida rechazada. |
| CP-1.2.2 | RF 1.2.2 | P1 | DEV-A autenticado | Editar habilidades, teléfono y portafolio; volver al perfil | Cambios propios persisten y se muestran; otro usuario no puede editarlos. |
| CP-1.2.3 | RF 1.2.3 | P1 | DEV-A con postulación vigente, contrato e historial | Abrir dashboard | Vigentes e históricos se separan sin duplicados y corresponden al DEV-A. |
| CP-1.3.1 | RF 1.3.1 | P1 | ADM-A; cuentas en estados distintos | Abrir panel estadístico | Totales por estado reflejan las cuentas preparadas y no incluyen otro estado por error. |
| CP-1.3.2 | RF 1.3.2 | P0 | ADM-A; usuario activo | Suspenderlo, comprobar acceso y reactivarlo | Estado persistido; suspendido pierde acceso; reactivado recupera acceso. |
| CP-1.3.3 | RF 1.3.3 | P1 | ADM-A; usuarios de varios roles y fechas | Filtrar por rol, estado y rango; combinar filtros | Solo aparecen cuentas que satisfacen todos los filtros. |
| CP-1.4.1 | RF 1.4.1 | P1 | Cuentas en tres roles | Iniciar sesión con credenciales válidas de cada rol | Cada usuario llega a su panel real; no puede elegir un rol ajeno desde el cliente. |
| CP-1.4.2 | RF 1.4.2 | P0 | Cuenta activa sin fallos recientes | Fallar la contraseña cinco veces y probar acceso | Se aplica el bloqueo según política; no se revela si existe otra cuenta. |
| CP-1.4.3 | RF 1.4.3 | P0 | Sesión activa | Cerrar sesión y abrir ruta privada o reutilizar sesión anterior | Acceso privado denegado/redirigido; sesión invalidada. |
| CP-1.4.4 | RF 1.4.4 | P0 | Correo de pruebas configurado | Solicitar recuperación, usar token y reusarlo o dejarlo caducar | Cambio válido una vez; token usado o vencido no cambia clave. |

### M2. Proyectos y trabajo colaborativo

Estos casos siguen los IDs **internos**, no la [revisión de los 6 RF 2.* oficiales](CONCILIACION_RF_BASE.md#revisión-del-módulo-2-proyectos-frente-al-excel-oficial). Se decidió separar cierre de postulaciones y fecha de cumplimiento (RF 2.1.3 externo), limitar la edición de condiciones comprometidas (RF 2.2.2 externo) y permitir retiro directo solo de publicados sin contratos, reservando proyectos en ejecución/revisión al flujo contractual (RF 2.2.3 externo). Hay implementación y pruebas automatizadas relacionadas, pero faltan casos manuales adaptados a todos los criterios y aceptación del Excel.

| Caso | RF | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| CP-2.1.1 | RF 2.1.1 | P1 | EMP-A autenticada | Publicar proyecto con título, descripción, solución y vacantes; omitir obligatorio | Registro completo publicado; entrada inválida no crea proyecto. |
| CP-2.1.2 | RF 2.1.2 | P2 | EMP-A creando proyecto | Seleccionar alta, media y baja en publicaciones independientes | La prioridad elegida persiste y se representa correctamente. |
| CP-2.1.3 | RF 2.1.3 | P1 | Categorías creadas y activas | Abrir selector; crear/modificar categoría con autorización y actualizar selector | La lista refleja categorías vigentes; usuario no autorizado no las administra. |
| CP-2.2.1 | RF 2.2.1 | P1 | EMP-A con proyectos inactivos, cancelados y en disputa | Abrir dashboard e historial | Cada proyecto aparece en sección/estado apropiado; no muestra proyectos de EMP-B. |
| CP-2.2.2 | RF 2.2.2 | P0 | Proyectos propios publicados sin negociar, con negociación, con contrato histórico y activo; otro en revisión sin contrato; EMP-B | Intentar cambiar título/prioridad y descripción/vacantes/fechas desde interfaz y POST forjado | Sin negociación ni contrato, el publicado admite cambios completos; con negociación/histórico solo título/prioridad; con contrato activo, estado terminal o empresa ajena no se edita. En revisión sin contrato solo admite título/prioridad. |
| CP-2.3.1 | RF 2.3.1 | P1 | EMP-A con proyecto y equipo | Crear hito general, individual y de equipo; consultar y eliminar uno permitido | Cada hito conserva tipo, proyecto y alcance; cambios visibles sin afectar otros. |
| CP-2.3.2 | RF 2.3.2 | P0 | Contratado DEV-A; DEV-B no contratado | Asignar hito individual a DEV-A y probar DEV-B | Solo DEV-A contratado puede ser asignado; la asignación se muestra. |
| CP-2.3.3 | RF 2.3.3 | P1 | Proyectos publicados con y sin cupo, en desarrollo con cupo, vencidos y cerrados | Abrir vitrina pública y exploración del desarrollador | Solo aparecen publicados y en desarrollo con cupo y plazo vigente; los sin cupo, vencidos y estados no ofertables no aparecen. |

### M3. Postulaciones, negociación y selección
Estos CP usan el significado **interno** de sus IDs. El Excel oficial enumera [7 RF 3.* diferentes](CONCILIACION_RF_BASE.md#revisión-del-módulo-3-postulaciones-y-contratación-frente-al-excel-oficial), en particular 3.1.1, 3.2.1 y 3.4.1 no equivalen a los CP homónimos. Son casos diseñados, no resultados ejecutados ni aprobación de la fuente. Los casos externos X28-EVIDENCIA y X29-COMPARACION documentan por separado los recorridos de perfil y comparación.

| Caso | RF | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| CP-3.1.1 | RF 3.1.1 | P0 | DEV-A verificado; cuatro ofertas y contador inicial conocido | Postularse hasta sumar tres entre postulaciones pendientes/en negociación y contratos activos; intentar otra y duplicar una | No supera tres compromisos activos; nuevo intento y duplicado no se crean. |
| CP-3.1.2 | RF 3.1.2 | P2 | Empresa con perfil público y reseñas | Abrir ficha desde una oferta | Se ven identidad institucional y reputación pública de esa empresa. |
| CP-3.2.1 | RF 3.2.1 | P1 | EMP-A con postulantes en varios estados | Filtrar postulaciones de proyecto propio | Solo aparecen candidatos coincidentes; EMP-B no accede a los datos privados. |
| CP-3.2.2 | RF 3.2.2 | P2 | Candidato verificado y otro sin verificar | Abrir lista de recibidas y leer tooltip | Insignia/fecha solo corresponden a la verificación vigente del candidato correcto. |
| CP-3.3.1 | RF 3.3.1 | P0 | Postulación pendiente en proyecto EMP-A | Iniciar negociación y repetir por la URL heredada de aceptación; intentar contratar antes de las firmas | Ambas rutas reservan cupo y crean contrato borrador; ninguna crea contratación activa ni cambia el proyecto a desarrollo antes de ambas firmas. |
| CP-3.3.2 | RF 3.3.2 | P0 | Proyecto EMP-A con todas sus vacantes ocupadas por contratos activos o negociaciones | Intentar iniciar otra negociación o formalizar otra contratación | La operación se rechaza; el número de contratos y negociaciones no sobrepasa el límite de vacantes. |
| CP-3.4.1 | RF 3.4.1 | P1 | EMP-A con postulación pendiente | Rechazar una candidatura y consultar ambas vistas | Solo esa postulación queda rechazada; no se crea contratación. |
| CP-3.4.2 | RF 3.4.2 | P0 | Contratación activa de EMP-A; plazo de postulación vencido | Cancelar con motivo de al menos 10 caracteres; comprobar que el plazo no cambia; ampliar explícitamente solo ese plazo como EMP-A y probar POST ajeno o fecha inválida | Contratación cancelada y cupo liberado; solo una ampliación válida y autorizada vuelve a admitir postulaciones. Motivo y ampliación auditados, sin cambiar fecha de cumplimiento ni requerimientos técnicos. |

Caso de la fuente oficial, no renumera la matriz interna:

| Caso | RF oficial | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| X28-EVIDENCIA | RF 3.2.1, fila 28 | P0 | Cuenta activa y verificada; empresa y desarrollador en negociación | Ver perfil en candidatura y antes de firma; firmar por una parte, cambiar perfil y mensaje; consultar desde ambas partes y firmar de nuevo; intentar alterar evidencia; probar sin portafolio y cuenta suspendida | Mensaje y perfil visibles; primera firma fija datos profesionales y hash; segunda firma conserva evidencia y se bloquea ante alteración; los campos opcionales no bloquean. Cuenta suspendida no postula. Excepción al «perfil adjunto» literal pendiente de aceptación. |
| X29-COMPARACION | RF 3.2.2, fila 29 | P1 | Empresa con cinco postulantes de distinta formación/habilidades; otra empresa ajena | Seleccionar uno, dos, cuatro y luego intentar cinco; comparar; filtrar; intentar acceso ajeno | Con 0–1 el comparador no se habilita; con 2–4 muestra tarjetas simultáneas con criterios homogéneos; el quinto se bloquea; no hay ranking ni recomendación; el ajeno no accede. |

### M4. Hitos, evidencias y revisión

Estos CP conservan los IDs internos. La [conciliación M4](CONCILIACION_RF_BASE.md#revisión-del-módulo-4-hitos-avances-y-evidencias-frente-al-excel-oficial) relaciona por separado los 8 IDs oficiales de las filas 33–40. En el criterio oficial, una descripción de tareas realizadas es evidencia válida por sí misma; URL y archivo son alternativas opcionales.

| Caso | RF | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| CP-4.1.1 | RF 4.1.1 | P1 | DEV-A con contrato e hito pendiente | Enviar descripción sola; repetir con URL y con archivo permitido | Cada alternativa registra el avance; la descripción sigue obligatoria y URL/archivo inválidos se rechazan. |
| CP-4.1.2 | RF 4.1.2 | P0 | Hito individual asignado a DEV-A | DEV-A envía avance; DEV-B intenta el mismo hito | Solo DEV-A puede registrar evidencia; rechazo no muta el hito. |
| CP-4.2.1 | RF 4.2.1 | P1 | Avances pendientes de revisión | EMP-A aprueba uno y solicita corrección de otro con comentario | Estados y comentario reflejan cada decisión; DEV-A ve el resultado. |
| CP-4.2.2 | RF 4.2.2 | P0 | Un avance pendiente | Repetir aprobación o simular dos revisiones simultáneas | Una sola transición válida; sin doble efecto ni eventos duplicados. |
| CP-4.2.3 | RF 4.2.3 | P0 | Proyectos en finalizado, inactivo y cancelado | Intentar registrar/revisar avances en cada estado | Todas las mutaciones se rechazan; estados y auditoría permanecen íntegros. |
| CP-4.3.1 | RF 4.3.1 | P1 | Hito pendiente con avance enviado | Aprobar avance y recargar hito | Hito queda completado solo después de la aprobación. |
| CP-4.3.2 | RF 4.3.2 | P2 | Proyectos en desarrollo con último hito creado hace 14 y 16 días | Consultar alertas de ADM-A con umbral 15 días | Solo el que tiene último hito anterior al umbral aparece como retrasado. El cálculo actual usa fecha de creación del hito, no fecha del último Avance. |

Casos de la fuente oficial (no renumeran los CP internos):

| Caso | RF oficial | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| X33-HITOS | RF 4.1.1, fila 33 | P1 | Proyecto propio editable | Crear hitos con título y descripción; intentar sobre proyecto ajeno | Los hitos quedan ligados solo al proyecto de la empresa autenticada. |
| X34-EQUIPO | RF 4.1.2, fila 34 | P0 | Dos contratados activos y un equipo | Crear equipo y asignarle un hito; intentar equipo de otro proyecto | Miembros y hito pertenecen al proyecto correcto; asignación cruzada se rechaza. |
| X35-EVIDENCIA | RF 4.2.1, fila 35 | P0 | DEV-A autorizado para hito pendiente | Entregar descripción sola, URL, archivo y luego forjar hito ajeno | Las tres formas válidas se guardan; el ajeno no crea avance ni cambia estado. |
| X36-TIMESTAMP | RF 4.2.2, fila 36 | P1 | Hito pendiente | Enviar avance y consultar persistencia | La fecha/hora se genera en servidor al crear la entrega. |
| X37-APROBAR | RF 4.3.1, fila 37 | P0 | Avance pendiente | Aprobar y repetir revisión/envío | Hito completado una vez; no se revierte ni admite otra entrega ordinaria. |
| X38-RECHAZAR | RF 4.3.2, fila 38 | P0 | Avance pendiente | Rechazar sin y con comentario | Sin comentario no cambia; con comentario deja hito pendiente y avisa al autor. |
| X39-REABRIR | RF 4.3.3, fila 39 | P0 | Proyecto en revisión final | Rechazar un avance | Proyecto vuelve a `en_desarrollo` con historial de transición. |
| X40-REVISION | RF 4.3.4, fila 40 | P0 | Todos los hitos salvo uno ya enviados | Entregar el último pendiente | Proyecto pasa a `en_revision`; todavía no se marca finalizado. |

### M5. Cierre y reputación

| Caso | RF | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| CP-5.1.1 | RF 5.1.1 | P0 | Proyecto EMP-A con hitos pendientes; luego todos enviados | Aprobar avances hasta el último hito | Antes del 100 % no finaliza; al aprobar el último finaliza proyecto y contratos sin esperar valoraciones. |
| CP-5.2.1 | RF 5.2.1 | P1 | Proyecto finalizado y DEV-A aún sin valorar | EMP-A califica 1–5 con comentario de al menos 20 caracteres; repetir | Valoración única y reputación actualizada; 0/6 estrellas o reseña corta rechazadas; el estado ya finalizado no depende de la nota. |
| CP-5.2.2 | RF 5.2.2 | P1 | Proyecto finalizado con DEV-A | DEV-A califica EMP-A con reseña de al menos 20 caracteres; intenta segundo envío | Reseña propia persiste una sola vez y actualiza reputación. |
| CP-5.3.1 | RF 5.3.1 | P2 | DEV-A con insignia, reseñas y métricas conocidas | Consultar perfil público como ANON y EMP-A | Se muestran únicamente datos públicos y, por separado, reputación bayesiana, promedio simple y cantidad. |
| CP-5.3.2 | RF 5.3.2 | P1 | Valoraciones por cohorte con `R=5`, `v=1`, `C=4`, `m=5` | Calcular reputación y comparar empresa/desarrollador | Resultado `4.17`; cada tipo usa su propia cohorte y no mezcla roles. Con cero valoraciones se muestra `C` como referencia, no mérito personal. |
| CP-5.3.3 | RF 5.3.3 | P2 | EMP-A y DEV-A con reseñas históricas | Abrir dashboards | Historial muestra autor, proyecto y calificación correspondientes, sin ajenos. |

Casos de la fuente oficial:

| Caso | RF oficial | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| X41-CIERRE | RF 5.1.1, fila 41 | P0 | Último avance pendiente de aprobación | Aprobarlo | Proyecto e hitos quedan finalizados, contratos activos se cierran y se registra historial. |
| X42-NOTA-DEV | RF 5.2.1, fila 42 | P1 | Proyecto finalizado dentro de ventana | Empresa valora cada colaborador con 1–5 y comentario | Una valoración por colaborador; promedio se recalcula sin cambiar el cierre. |
| X43-NOTA-EMP | RF 5.2.2, fila 43 | P1 | Contratado en proyecto finalizado | Desarrollador valora la empresa; repetir | Una valoración válida y reputación de empresa actualizada. |
| X44-PROMEDIO | RF 5.3.1, fila 44 | P1 | Perfiles con varias notas recibidas y configuración `m` conocida | Abrir perfiles públicos, listados y reportes | Reputación bayesiana, promedio simple y número corresponden al destinatario; la interfaz explica `R`, `v`, `C` y `m`. Marcar pendiente cualquier superficie que aún muestre solo promedio simple. |
| X45-HISTORIAL | RF 5.3.2, fila 45 | P1 | Dos reseñas por proyectos diferentes | Consultar perfil | Historial presenta autor, proyecto, nota, comentario y fecha sin mezclar roles. |
| X46-INMUTABLE | RF 5.3.3, fila 46 | P0 | Valoración creada / proyecto finalizado hace 31 días | Intentar editar y crear fuera de plazo | La existente no cambia y la extemporánea no se registra. |

### M6. Mensajes y notificaciones

| Caso | RF | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| CP-6.1.1 | RF 6.1.1 | P0 | EMP-A y DEV-A autorizados; DEV-B ajeno | Enviar mensaje directo entre partes e intentar con DEV-B | Partes ven el mensaje; ajeno no lee ni envía. |
| CP-6.1.2 | RF 6.1.2 | P0 | Proyecto con participantes y un usuario ajeno | Enviar mensaje directo entre participantes e intentar como ajeno | Solo quienes comparten proyecto envían/leen; el equipo múltiple conserva chat privado. |
| CP-6.1.3 | RF 6.1.3 | P0 | Misma pareja en dos proyectos | Abrir historial privado de cada proyecto y marcar uno leído | Cada conversación contiene solo su sala; timestamp y leído cambian en el contexto correcto. |
| CP-6.2.1 | RF 6.2.1 | P1 | Receptor con cero avisos | Enviar mensaje autorizado y consultar campana/badge | Notificación tipo mensaje y contador no leído aumentan; SSE local emite la actualización. |
| CP-6.2.2 | RF 6.2.2 | P1 | DEV-A verificado; proyecto publicado de EMP-A y EMP-B con proyecto distinto | Postular DEV-A al proyecto de EMP-A; consultar notificaciones de ambas empresas | Se crea una notificación de tipo postulación para EMP-A asociada al proyecto; EMP-B no recibe ninguna por ese evento. |
| CP-6.3.1 | RF 6.3.1 | P1 | Dos sesiones; SSE activo | Crear notificación para DEV-A mientras escucha el stream | Llega solo a DEV-A sin recarga y se conserva al consultar historial. |
| CP-6.3.2 | RF 6.3.2 | P2 | DEV-A con mensajes leídos y no leídos | Leer uno y consultar barra lateral | Contador decrece correctamente, no incluye mensajes ajenos. |

Casos de la fuente oficial:

| Caso | RF oficial | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| X47-PRIVADO | RF 6.1.1, fila 47 | P0 | Empresa y dev vinculados; equipo con varios devs | Abrir chat 1:1 y enviar | Mensaje permanece privado; no se fuerza la sala grupal. |
| X48-PARTES | RF 6.1.2, fila 48 | P0 | Participantes en proyectos distintos y un ajeno | Forjar proyecto/receptor | Solo una relación del mismo proyecto autoriza; no se crea mensaje ajeno. |
| X49-LECTURA | RF 6.1.3, fila 49 | P1 | Mensaje nuevo | Consultar fecha, abrir sala y recargar | Fecha se genera al enviar y `leido` cambia solo para el receptor/contexto. |
| X50-AVISO-MSG | RF 6.2.1, fila 50 | P1 | Receptor autenticado | Recibir mensaje | Se crea aviso interno y aumenta contador; al leer disminuye. |
| X51-AVISO-POST | RF 6.2.2, fila 51 | P1 | Proyecto abierto | Desarrollador se postula | Solo la empresa titular recibe aviso ligado al proyecto. |
| X52-ESTADO-POST | RF 6.2.3, fila 52 | P0 | Postulaciones pendiente/en negociación | Negociar, aceptar, rechazar, expirar y llenar cupo | Cada desarrollador afectado recibe el estado correspondiente, incluido rechazo automático. |

### M7. Administración, auditoría y reportes

Los casos `CP-*` siguientes pertenecen al inventario interno histórico. Los casos `X53`–`X56` posteriores reproducen las cuatro filas realmente presentes en la fuente oficial; no deben intercambiarse por coincidencia de ID.

| Caso | RF | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| CP-7.1.1 | RF 7.1.1 | P0 | ADM-A y estados conocidos | Cambiar rol/estado de usuario, proyecto, contrato, disputa y configuración por sus recorridos autorizados | Cada cambio sensible crea log central con actor, recurso y valores anterior/nuevo cuando aplican. |
| CP-7.1.2 | RF 7.1.2 | P1 | Evento auditable con contraseña, token, documento o chat en la solicitud | Consultar detalle de auditoría | Actor, acción y fecha/hora están presentes; contraseña, token, documento completo y contenido confidencial no aparecen. |
| CP-7.2.1 | RF 7.2.1 | P1 | Logs de varios actores/tipos/fechas | Combinar filtros como administrador y como usuario común | Admin recibe solo coincidencias; usuario común obtiene 403. |
| CP-7.2.2 | RF 7.2.2 | P1 | Datos del mes | Exportar PDF mensual y abrirlo | Archivo PDF válido contiene los totales requeridos. |
| CP-7.3.1 | RF 7.3.1 | P1 | Panel admin consultado y cacheado | Cambiar estado de usuario y consultar de nuevo | Conteos y filas se actualizan, sin lectura obsoleta. |
| CP-7.3.2 | RF 7.3.2 | P1 | Notificaciones viejas y recientes | Depurar desde UI autorizada | Solo antiguas elegibles se eliminan y queda rastro de la operación. |
| CP-7.3.3 | RF 7.3.3 | P1 | DEV-A con proyecto publicado | Marcar y desmarcar favorito; consultar lista | Se crea y retira una sola marca; contador/lista sincronizados. |

Casos de la fuente oficial:

| Caso | RF oficial | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| X53-AUDITORIA | RF 7.1.2, fila 53 | P0 | Datos conocidos en cada dominio sensible | Ejercitar identidad/rol/estado, verificación, proyecto, contrato/firma/cancelación, disputa/sanción, valoración/regularización y configuración | Cada recorrido sensible deja `LogAuditoria` suficiente sin copiar secretos ni contenido confidencial; los recorridos no ejercitados se reportan como cobertura pendiente. |
| X54-RENDIMIENTO | RF 7.2.1, fila 54 | P1 | Aprendiz valorado y contador de proyectos completados | Descargar CSV como admin y como usuario común | Admin recibe promedio y total correctos; usuario común no descarga. |
| X55-EMPRESAS | RF 7.2.2, fila 55 | P1 | Empresa con publicaciones y valoración | Descargar CSV como admin y como usuario común | Admin recibe volumen y reputación correctos; usuario común no descarga. |
| X56-PROYECTOS | RF 7.2.3, fila 56 | P1 | Proyectos en estados distintos | Descargar CSV como admin y comparar todas las filas | Cada proyecto aparece con estado y detalle; usuario común no descarga. |

### M8–M10. Contratos, verificación y disputas

| Caso | RF | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| CP-8.1.1 | RF 8.1.1 interno | P0 | Negociación válida | Consultar contrato generado | Existe un contrato único ligado a la postulación; no se presenta este ID como fila oficial. |
| CP-8.1.2 | RF 8.1.2 | P0 | ADM-A configura 15 días; EMP-A tiene vacante y postulación; después se configura 2 días | Iniciar negociación, guardar fecha límite, cambiar configuración y volver a consultar | La negociación queda a 15 días y no cambia; una negociación posterior usa 2. Solo admin configura, rango 1–30; el cambio queda auditado. |
| CP-8.2.1 | RF 8.2.1 | P0 | Contrato borrador | Editar monto, COP/USD, forma de pago, cláusulas y comentarios; consultar disclaimer | Template conserva todos los términos y declara que la plataforma no procesa pagos ni sustituye contrato laboral. |
| CP-8.2.2 | RF 8.2.2 | P0 | Contrato listo para firmar | Firmar como cada parte, intentar como ajeno y alterar términos entre firmas | Dos aceptaciones atribuidas con timestamps; `hash_documento` permanece fijo; ajeno/edición indebida se rechazan. |
| CP-8.3.1 | RF 8.3.1 | P0 | Contrato sin firma y postulaciones pendientes | Firmar una vez y luego completar la segunda firma | Solo la segunda activa contratación, acepta postulación, pasa proyecto a desarrollo y rechaza pendientes al llenar cupo dentro de la transacción. |

Casos directos de la fuente oficial M8: `X59-NEGOCIACION`, `X60-TEMPLATE`, `X61-FIRMAS` y `X62-ACTIVACION` corresponden respectivamente a los cuatro `CP-8.*` oficiales anteriores; `CP-8.1.1` se mantiene únicamente como inventario interno.
| CP-9.1.1 | RF 9.1.1 | P0 | Lista blanca con ficha/programa y desarrollador nuevo | Registrar con combinación coincidente, contradictoria y ausente; intentar postular sin verificar | Solo combinación coherente se verifica; perfiles no verificados no postulan; revisión manual autorizada queda disponible. |
| CP-9.1.2 | RF 9.1.2 | P0 | ADM-A; ficha ausente del padrón | Crear/desactivar ficha, autorizar excepción, comprobar y revocarla | Solo admin gestiona; cambios quedan auditados y la revocación surte efecto. |
| CP-9.2.1 | RF 9.2.1 | P0 | EMP-A no verificada con documentos ficticios | Publicar, observar advertencia y solicitar revisión; separar revisión local de consulta externa | Publicación continúa con aviso. La revisión documental local no se marca como prueba de RUES/Cámara. |
| CP-9.2.2 | RF 9.2.2 | P1 | Dev/empresa verificados y pendientes | Consultar perfiles, listados de proyecto y postulaciones | Cada superficie muestra el badge/advertencia correspondiente sin elevar un pendiente a verificado. |

Casos directos de la fuente oficial M9: `X64-SENA`, `X65-LISTA-BLANCA`, `X66-RUES` y `X67-BADGES`. `X66-RUES` permanece pendiente de una integración externa verificable; las pruebas documentales actuales cubren únicamente la publicación con advertencia y la revisión humana.
| CP-10.1.1 | RF 10.1.1 | P0 | Contrato activo propio y otro ajeno | Abrir incumplimiento/inactividad sin y con URL/archivo; fuerza mayor sin evidencia/declaración y con cada alternativa; intentar como ajeno | Causales obligatorias rechazan ausencia de evidencia sin congelar; fuerza mayor admite evidencia o declaración; solo titulares abren y la apertura válida congela/notifica. |
| CP-10.1.2 | RF 10.1.2 | P1 | ADM-A; disputas abiertas, en mediación y resueltas | Abrir una disputa y filtrar panel por cada estado | Notificación interna se crea en la apertura y conteos/lista coinciden. |
| CP-10.2.1 | RF 10.2.1 | P0 | Disputa en mediación | Mensajes de partes/admin, intento ajeno y cierre no admin | Solo tres participantes acceden; eventos quedan auditados y solo admin resuelve/cierra. |
| CP-10.2.2 | RF 10.2.2 | P0 | Cuatro disputas mediadas | Resolver una por cada acción local y consultar acción/familia | `reanudar_proyecto`→continuidad; `cancelar_contrato`→terminación; ambas sanciones→sanción. Se conserva la acción concreta, auditoría y avisos. |
| CP-10.3.1 | RF 10.3.1 | P0 | Proyecto con contrato y avances en estados contrastantes | Ejecutar cada resolución en transacción e inspeccionar efectos/rollback | Proyecto, contrato y rechazos siguen regla local; aceptación de avances y calificación quedan pendientes hasta definir política. |

Casos directos de la fuente oficial M10: `X69-APERTURA`, `X70-CENTRO`, `X71-SALA`, `X72-RESOLUCION` y `X73-EFECTOS`. X69 y el mapeo de X72 ya tienen política aprobada. X73 permanece parcial porque no se autorizó aceptación automática de avances ni ajuste automático de calificaciones.

### Extensiones de la matriz (RF-N01–RF-N31)

| Caso | RF | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| CP-N01 | RF-N01 | P0 | Hito individual de DEV-A, DEV-B ajeno | DEV-A envía avance; DEV-B intenta repetir en ese hito | Solo la entrega del asignado se admite; el intento ajeno no altera el hito. |
| CP-N02 | RF-N02 | P1 | Proyecto de EMP-A y dos dev contratados | Crear equipo y asignar miembros/hito | Equipo y asignaciones se reflejan solo en ese proyecto. |
| CP-N03 | RF-N03 | P0 | Categoría de prueba; admin y no admin | Crear, editar y consultar por API; repetir como no admin | Solo operación autorizada persiste; respuesta contiene categoría actual. |
| CP-N04 | RF-N04 | P0 | Proyecto finalizado con contratos finalizados; ADM-A | Solicitar continuación desde panel; intentar como EMP-A | Admin crea un proyecto sucesor con `proyecto_origen`; original y contratos permanecen finalizados; EMP-A no fuerza la operación. |
| CP-N05 | RF-N05 | P1 | Oferta vigente y oferta vencida | Consultar vitrina pública | No aparece la vencida, incluso si su estado quedó publicado. |
| CP-N06 | RF-N06 | P0 | Contrato con primera firma | Comparar `hash_documento` y `hash_contrato` tras cada firma; intentar alterar contenido | El primero queda fijo desde la primera firma; el segundo refleja los timestamps de firmas; no se cambia contenido silenciosamente. |
| CP-N07 | RF-N07 | P1 | Dos negociaciones: fecha límite vigente y fecha límite vencida | Ejecutar expiración | Solo caduca la vencida elegible; no expira la vigente. |
| CP-N08 | RF-N08 | P0 | PostgreSQL aislado, una vacante y dos postulaciones válidas | Intentar firmar/contratar en paralelo desde dos transacciones | Como máximo una contratación consume la vacante; SQLite no cierra este caso. |
| CP-N09 | RF-N09 | P0 | Contrato activo | Probar acuerdo mutuo sin confirmación y confirmado; fuerza mayor con/sin evidencia; incumplimiento/inactividad con/sin evidencia | Longitud nunca basta: acuerdo exige contraparte, fuerza mayor evidencia o declaración, incumplimiento/inactividad evidencia y dictamen; no hay sanción automática. |
| CP-N10 | RF-N10 | P0 | Ficha fuera de lista blanca | Autorizar excepción como admin y repetir verificación | Validación funciona solo bajo excepción autorizada; sin excepción falla. |
| CP-N11 | RF-N11 | P0 | Solicitud empresarial y soportes ficticios | Revisar como admin y registrar decisión | Insignia/estado solo cambian tras evaluación humana y quedan trazables. |
| CP-N12 | RF-N12 | P0 | Egresado SENA con soporte ficticio | Solicitar verificación manual; admin decide | Estado distingue pendiente/aprobada/rechazada; no se autoaprueba. |
| CP-N13 | RF-N13 | P0 | Soporte privado EMP-A | Descargar como titular/admin y como DEV-B | Solo autorizados reciben bytes; ajeno no conoce contenido ni URL pública útil. |
| CP-N14 | RF-N14 | P0 | Archivo permitido y archivo renombrado con cabecera inválida | Cargar ambos en formulario de soporte | Validador rechaza cabecera no permitida; el servidor vuelve a validar. |
| CP-N15 | RF-N15 | P1 | NIT de prueba con DV conocido | Calcular DV con algoritmo DIAN y caso inválido | Valor coincide con vector esperado; no presentar el checksum como prueba de existencia legal. |
| CP-N16 | RF-N16 | P0 | Disputa activa | Resolver con opción de reanudar o terminar en casos separados | Proyecto/contratos y efectos secundarios siguen cada resolución sin efectos dobles. |
| CP-N17 | RF-N17 | P0 | Disputa en mediación | Publicar intervención autorizada y consultar rastro | Se auditan emisor, disputa y canal sin copiar texto confidencial al log; mensaje visible solo a participantes. |
| CP-N18 | RF-N18 | P1 | Disputas en tres estados | Consultar tablero con cada filtro | Totales por estado y subconjunto mostrado coinciden. |
| CP-N19 | RF-N19 | P1 | Entorno integrado con proxy/worker y SSE conectado | Escuchar stream autenticado y generar evento | Destinatario recibe evento una vez; registrar salida limpia y no inferir despliegue desde el test HTTP aislado. |
| CP-N20 | RF-N20 | P0 | ASGI y Redis aislado real preparados | Establecer WebSocket autorizado y probar canal ajeno | Se transmite al canal correcto; suscripción no autorizada denegada; registrar latencia/versión de Redis. |
| CP-N21 | RF-N21 | P2 | DEV-A con dos mensajes sin leer | Abrir uno y actualizar dashboard | Indicador pasa de dos a uno; otros usuarios no afectan su conteo. |
| CP-N22 | RF-N22 | P1 | EMP-A y DEV-A autorizados | Componer/enviar, abrir recibidos y enviados | Mensaje se guarda en ambas bandejas correctas y respeta permisos. |
| CP-N23 | RF-N23 | P1 | Oferta publicada y DEV-A | Marcar dos veces y consultar favoritos | Una sola relación de favorito; segundo cambio la retira. |
| CP-N24 | RF-N24 | P0 | ADM-A y DEV-A | Abrir y refrescar visor de logs del servidor | Solo admin puede verlo; contenido acotado sin rutas arbitrarias. El tail por petición no demuestra streaming continuo. |
| CP-N25 | RF-N25 | P1 | Notificaciones antiguas y recientes | Depurar desde panel | Solo registros elegibles se borran; acción auditada. |
| CP-N26 | RF-N26 | P0 | Conversaciones de varios usuarios | Auditar como ADM-A; abrir como EMP-B | Admin recibe vista permitida; EMP-B no ve conversaciones ajenas. |
| CP-N27 | RF-N27 | P1 | Cache admin precalentada | Hacer alta, cambio de estado o baja autorizada | Panel siguiente refleja mutación sin información anterior. |
| CP-N28 | RF-N28 | P0 | PostgreSQL de prueba y destino temporal de respaldo | Generar copia, verificar integridad y restaurar en entorno aislado | Respaldo verificable y esquema/datos recuperables; registrar duración real. |
| CP-N29 | RF-N29 | P0 | Proyecto en estado conocido | Cambiar estado; intentar editar/eliminar la entrada por modelo | Entrada cronológica conserva actor, delta y fecha; mutaciones ordinarias fallan. SQL/QuerySet administrativo queda fuera. |
| CP-N30 | RF-N30 | P0 | ADM-A; lista mixta de cuentas | Enviar activación/suspensión masiva por API y repetir como no admin | Solo IDs válidos cambian según contrato; no admin no altera ninguna cuenta. |
| CP-N31 | RF-N31 | P1 | Valoraciones conocidas y `m=5`; ADM-A cambia a `m=8` | Calcular, cambiar configuración y volver a calcular; comparar métricas expuestas | Fórmula bayesiana usa `Decimal`, cambio de `m` queda auditado y la salida conserva reputación, promedio simple y cantidad por separado. Integración total de UI/comando permanece pendiente. |

## 4. Escenarios negativos y límites transversales

| Caso | RF relacionados | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| NEG-01 | RF 1.4.1, RF 1.4.3 | P0 | ANON | Abrir URL privada de cada rol y API administrativa | Sin contenido privado; redirección o 401/403 según ruta; sin mutación. |
| NEG-02 | RF 1.3.2, RF-N30 | P0 | DEV-A, EMP-A y ADM-A | Enviar solicitud de cambio de rol/estado y acción masiva desde cuenta no admin | No se altera ninguna cuenta; error de autorización. |
| NEG-03 | RF 2.2.2, RF 3.2.1, RF 4.2.1 | P0 | EMP-B y datos de EMP-A | Cambiar ID de proyecto, candidato y avance en URL/JSON | Sin lectura ni mutación de recurso ajeno; respuesta no revela datos. |
| NEG-04 | RF 3.1.1, RF-N05 | P0 | DEV-A con proyecto vencido/finalizado o vacantes agotadas | Forzar POST de postulación fuera de la vitrina | Postulación no creada; estado/vacantes intactos. |
| NEG-05 | RF 3.3.1, RF 8.2.1 | P0 | DEV-B no contratado | Forzar inicio de negociación o firma de postulación ajena | Sin transición ni firma; solo partes autorizadas participan. |
| NEG-06 | RF 4.1.2, RF 4.2.3, RF-N01 | P0 | DEV-B ajeno, hito de DEV-A | Forzar envío de avance a hito ajeno/finalizado | Sin nuevo avance ni cambio de hito. |
| NEG-07 | RF 5.2.1, RF 5.2.2 | P0 | Contrato no finalizado o valoración existente | Calificar antes del cierre, dos veces o como tercero | No se crea valoración fuera de reglas; promedio no cambia. |
| NEG-08 | RF 6.1.3, RF-N20 | P0 | Sala/grupo de proyecto ajeno | Probar HTTP y WebSocket con ID de otra sala | No se entregan mensajes pasados ni futuros; sin conexión no autorizada. |
| NEG-09 | RF 6.3.1, RF-N19 | P0 | ANON y DEV-B | Suscribirse a SSE de DEV-A | Stream privado no accesible; ninguna notificación ajena expuesta. |
| NEG-10 | RF 8.2.2, RF-N06 | P0 | Contrato con al menos una firma | Alterar monto, moneda, términos o hash por petición forjada | Documento firmado no cambia; hash previo y firmas permanecen íntegros. |
| NEG-11 | RF 9.2.1, RF-N13, RF-N14 | P0 | Soporte ficticio propio y ajeno | Enviar archivo ejecutable renombrado y descargar soporte ajeno | Archivo inválido rechazado en servidor; ajeno no accede al documento. |
| NEG-12 | RF 10.1.1, RF 10.2.1 | P0 | Contrato ajeno/cerrado, disputa resuelta | Abrir disputa ajena o duplicada y publicar en sala cerrada | No hay segunda disputa ni mensajes posteriores indebidos. |
| NEG-13 | RF-N08 | P0 | Una vacante y varias sesiones | Ejecutar aceptación/firma simultánea, refrescar desde DB | Nunca hay dos contrataciones activas para una vacante; sin escritura parcial. |
| NEG-14 | RF-N28 | P0 | Copia de prueba verificada; entorno desechable | Corromper copia y ejecutar verificación de recuperación | La copia alterada se detecta y no se declara restauración exitosa. |
| NEG-15 | RF 1.4.4, RF 6.1.1 | P0 | Formularios/JSON con texto malicioso | Introducir HTML/script y cadena excesiva en campos permitidos | Validación y escape impiden ejecución en UI; no se exponen secretos. |

Estas filas **no sustituyen** pruebas de carga, pentest, accesibilidad o verificación jurídica; son escenarios de aceptación y regresión. En las pruebas de concurrencia usar PostgreSQL, no inferir locks de `select_for_update` a partir de SQLite.

## 5. Prueba integral de aceptación de los tres roles

| Paso | Actor | Acción | Comprobación |
|---|---|---|---|
| E2E-01 | Empresa | Registrar/verificar empresa y publicar un proyecto con vacante e hito | Proyecto visible al desarrollador habilitado; empresa propietaria y cupos correctos. |
| E2E-02 | Desarrollador | Consultar proyecto y empresa; postularse | Postulación registrada una sola vez, con estado correcto y aviso a la empresa. |
| E2E-03 | Empresa | Revisar candidato, iniciar negociación y acordar términos | Participantes autorizados; propuesta y contrato coherentes. |
| E2E-04 | Empresa y Desarrollador | Firmar cada uno el contrato | Hash inmutable; contratación activa solo tras ambas firmas; sin sobrepasar vacantes. |
| E2E-05 | Desarrollador | Consultar hito y registrar avance con evidencia ficticia | Avance asociado al hito correcto; empresa puede revisarlo. |
| E2E-06 | Empresa | Rechazar con motivo, recibir corrección y aprobar avance | Estado y comentario visibles al desarrollador; hito completado solo tras aprobación. |
| E2E-07 | Empresa y Desarrollador | Empresa valora a cada contratado y cierra al valorar al último; después el dev valora empresa | Estados, reputación e historial coherentes; no hay duplicidad de calificaciones. |
| E2E-08 | Ambos y Administrador | Abrir disputa en **otra contratación activa**; mediar y resolver | Acceso restringido a partes y admin; estado de disputa y efectos de resolución auditados. |

E2E-08 requiere un contrato distinto al finalizado en E2E-07; no se debe simular una disputa sobre un contrato cerrado para forzar un resultado.

## 6. Evidencia automatizada y límites de cobertura

- Suite y configuración: `pyproject.toml` (pytest y markers), `conftest.py`, `.github/workflows/ci.yml` (SQLite, PostgreSQL 16 y E2E); el documento de requisitos vincula RF con archivos de pruebas, no con cada función individual.
- **Ejecución local de referencia (commit `1b7a2ac`, sin E2E):** `uv run pytest . --ignore=tests/e2e -q` → **1242 pasaron, 1 omitida**. Solo acredita la suite automatizada recogida en ese entorno y ese commit; no acredita las filas manuales, PostgreSQL de CI ni E2E.
- Comandos de referencia: `uv run pytest . --ignore=tests/e2e`; para E2E, `uv run pytest tests/e2e -m e2e` con navegador y servicios preparados; en CI se ejecutan comprobaciones adicionales. No confundir «recolectado» con «ejecutado/aprobado».
- Antes de declarar una fila «automatizada», vincularla a un test específico (`ruta::Clase::función`), comprobar que existe y que verifica exactamente el resultado esperado. En la reconciliación se corrigieron tres referencias obsoletas de la matriz: `favoritos/tests/test_views.py`, `postulaciones/tests/test_tasks.py` y `postulaciones/tests/test_views.py`.
- Fuera del alcance de una certificación solo por software: verificación contra servicios externos oficiales, validez jurídica de firmas, RPO/RTO real de infraestructura, accesibilidad con usuarios y seguridad ofensiva completa. Requieren evidencias y entornos específicos.

## 7. Registro de ejecución y criterio de salida

Copiar esta ficha para **cada ID** ejecutado (incluidos NEG y E2E). No dejar «Pasó» prellenado.

| Campo | Valor a registrar |
|---|---|
| ID del caso / RF | |
| Fecha, ejecutor y versión/commit | |
| Entorno (motor BD, navegador y servicios) | |
| Usuario/rol y datos preparados | |
| Resultado observado frente al esperado | |
| Estado: No ejecutado / Pasó / Falló / Bloqueado | |
| Evidencia o enlace (sin secretos ni PII real) | |
| Defecto/incidencia y repetición | |

**Cierre:** ninguna falla P0 abierta; los casos P0 y P1 aprobados o bloqueos justificados; defectos P2 triados; cobertura de IDs comprobada contra la matriz corregida; pruebas automáticas y E2E ejecutadas en los entornos declarados. No emitir un porcentaje global a partir de casos diseñados sin actas de ejecución.

## 8. Casos no funcionales identificados en el repositorio

Casos para los **38 RNF-01 a RNF-38** enumerados en `../Documentación JobDevs/Documentacion Mark/MatrizRNF.md`; **no se cuentan como RF**. La fuente marca todos como cumplidos, pero los casos distinguen pruebas locales de las validaciones que requieren navegador, PostgreSQL, Redis, R2, proxy o CI reales.

| Caso | RNF | P | Precondición | Acción / datos | Resultado esperado |
|---|---|---|---|---|---|
| CP-RNF-01 | RNF-01 | P0 | Cuenta activa | Fallar autenticación cinco veces y repetir con sexto intento | Cuenta se bloquea en el umbral sin revelar si existía. |
| CP-RNF-02 | RNF-02 | P1 | Configuración de sesión cargada | Inspeccionar cookie/edad y cerrar navegador simulado | Cierre y edad respetan configuración; no llamar “rotación” a simple expiración. |
| CP-RNF-03 | RNF-03 | P1 | Tres roles y datos; warm-up | Medir dashboards con método idéntico | Menos de 2 s local y queries acotadas; no extrapolar a producción. |
| CP-RNF-04 | RNF-04 | P1 | Navegadores/resoluciones objetivo | Ejecutar flujos y revisión visual | Sin pérdida funcional ni desbordes; conservar capturas por viewport. |
| CP-RNF-05 | RNF-05 | P0 | Proyecto existente | Cambiar estado e intentar editar/borrar historial | Delta/autor/fecha persistentes; API ordinaria rechaza mutación. |
| CP-RNF-06 | RNF-06 | P0 | Operaciones críticas preparadas | Forzar excepción intermedia en contrato, valoración y disputa | Transacción revierte todos los efectos del recorrido probado. |
| CP-RNF-07 | RNF-07 | P1 | Checkout actual | Ejecutar Ruff y revisar workflow/módulos | Ruff verde en alcance; registrar deuda, no inferir mantenibilidad absoluta. |
| CP-RNF-08 | RNF-08 | P1 | Settings de test | Consultar idioma, zona y timestamp consciente | `es-co`, `America/Bogota` y timezone-aware activos. |
| CP-RNF-09 | RNF-09 | P1 | Acciones éxito/error representativas | Ejecutar POST y renderizar respuesta | Mensaje comprensible visible en recorridos cubiertos. |
| CP-RNF-10 | RNF-10 | P1 | BD aislada con >10 000 filas | Medir queries/plan de listados y dashboards | Índices y conteo acotado; documentar motor/tiempo, sin extrapolar carga. |
| CP-RNF-11 | RNF-11 | P0 | Usuario de prueba y repo | Guardar contraseña; inspeccionar hash y tracking sin leer secretos | Contraseña no reversible y `.env` no versionado. |
| CP-RNF-12 | RNF-12 | P1 | Chrome, Firefox y Edge declarados | Ejecutar el mismo E2E y registrar versiones | Flujo pasa en cada navegador real. |
| CP-RNF-13 | RNF-13 | P0 | Archivos válidos, renombrados y >10 MB | Cargar por recorridos públicos | Magic bytes/cuota se aplican y media no ejecuta contenido. |
| CP-RNF-14 | RNF-14 | P0 | PostgreSQL aislado y destino desechable | Respaldar, verificar hash, restaurar y medir | Datos íntegros recuperados en <300 s con evidencia. |
| CP-RNF-15 | RNF-15 | P1 | Notificaciones leídas/no leídas | Listar, paginar, marcar y purgar propias | Estado persiste y no afecta terceros. |
| CP-RNF-16 | RNF-16 | P0 | Correo existente e inexistente | Solicitar recuperación para ambos | Misma respuesta observable, sin enumeración. |
| CP-RNF-17 | RNF-17 | P0 | Cuenta suspendida y correo desconocido | Probar claves válidas/inválidas y medir muestras | Sin fuga de estado; timing estadístico requiere ensayo dedicado. |
| CP-RNF-18 | RNF-18 | P0 | Bloqueo automático y suspensión admin | Restablecer clave | Reset/reactivación solo para bloqueo automático. |
| CP-RNF-19 | RNF-19 | P0 | Token válido | Consumir token dos veces | Primera cambia clave; segunda es inválida. |
| CP-RNF-20 | RNF-20 | P0 | Roles y cuenta suspendida | Recorrer endpoints privados/API | Rol ajeno denegado y suspendido expulsado; repetir al añadir vistas. |
| CP-RNF-21 | RNF-21 | P0 | Caché admin precalentada | Alta/cambio/baja y consulta tras cada una | Lista coincide de inmediato con BD. |
| CP-RNF-22 | RNF-22 | P0 | IP de prueba | Superar límite de API admin | Respuesta 429 sin mutación; validar IP real tras proxy por separado. |
| CP-RNF-23 | RNF-23 | P0 | Contrato con primera firma | Alterar contenido y firmar contraparte | Hash documental permanece y alteración se rechaza. |
| CP-RNF-24 | RNF-24 | P0 | Respuesta HTTPS en entorno objetivo | Inspeccionar headers/cookies/CSRF | Valores defensivos presentes; incluir proxy/TLS en validación de despliegue. |
| CP-RNF-25 | RNF-25 | P0 | Chats de dos proyectos | Consultar/enviar con IDs cruzados | Ningún mensaje de otro tenant aparece ni se altera. |
| CP-RNF-26 | RNF-26 | P0 | PostgreSQL y dos transacciones | Competir por vacante/revisión | Solo una transición válida; sin sobrecupo ni doble revisión. |
| CP-RNF-27 | RNF-27 | P1 | Pasarela simulada con fallos temporales | Provocar fallos y recuperación | Backoff acotado y fallback local según contrato, sin autoaprobar. |
| CP-RNF-28 | RNF-28 | P1 | Worker/Beat/Redis aislados | Encolar purga, expiración y correo | HTTP no ejecuta trabajo pesado; worker procesa una vez y Beat agenda. |
| CP-RNF-29 | RNF-29 | P1 | ASGI, Redis y proxy aislados | Generar SSE/chat y medir extremo a extremo | Evento autorizado llega sin polling; registrar latencia y desconexión. |
| CP-RNF-30 | RNF-30 | P1 | Log >500 líneas; admin/no admin | Abrir/refrescar visor y rotar archivo | Solo admin ve tail acotado; rotación conserva límites. |
| CP-RNF-31 | RNF-31 | P0 | Mutaciones instrumentadas | Cambiar estados/usuarios y consultar log | Antes/después reconstruyen el recorrido cubierto; SQL directo excluido. |
| CP-RNF-32 | RNF-32 | P0 | Checkout y CI accesible | Ejecutar suite completa y consultar pipeline | Registrar conteo/duración/código reales; no repetir cifras históricas. |
| CP-RNF-33 | RNF-33 | P1 | SQLite y PostgreSQL aislados | Ejecutar checks/migraciones/suite cronometrada | Ambos motores soportados; comparar duración real con 90 s. |
| CP-RNF-34 | RNF-34 | P1 | Bucket R2 de prueba y fallback local | Generar PUT/GET, expirar URL y simular indisponibilidad | URLs/plazos/permisos correctos; fallback protegido sin exposición pública. |
| CP-RNF-35 | RNF-35 | P0 | Recursos en estados mutables | Ejecutar GET de vistas críticas y comparar BD | Ningún GET cambia estado; POST+CSRF requerido. |
| CP-RNF-36 | RNF-36 | P0 | Notificación con HTML/script | Emitir SSE | Payload escapa contenido y no ejecuta XSS. |
| CP-RNF-37 | RNF-37 | P0 | Suspensión manual | Recuperar contraseña | Intentos se reinician pero cuenta sigue suspendida. |
| CP-RNF-38 | RNF-38 | P0 | Común, staff, superusuario activo/inactivo | Acceder `/django-admin/` | Solo superusuario activo entra. |
