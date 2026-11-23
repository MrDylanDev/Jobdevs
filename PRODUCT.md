# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Tres roles con dashboards separados y sin acceso cruzado:

- **Desarrollador** — aprendiz o egresado SENA. Busca experiencia real, portafolio y reputación; se postula a proyectos, trabaja por hitos, sube evidencias, chatea y califica a la empresa al cierre. El registro exige cédula (no NIT), mayoría de 18 años y condición SENA verificable por ficha.
- **Empresa** — organización que necesita software. Publica proyectos con vacantes, revisa candidatos, firma contrato digital, define hitos, acepta o rechaza avances con comentario obligatorio y califica al desarrollador.
- **Administrador** — gestor de la plataforma. Supervisa usuarios y proyectos, activa/suspende cuentas, administra el padrón de fichas SENA y sus excepciones, y audita cambios de estado.

**Usuario primario: la Empresa.** Las decisiones de diseño se optimizan para este rol: juzgar si un candidato es real y verificado, y ejecutar el proyecto sin perder el control de lo entregado. El Desarrollador es la otra mitad del flujo y su experiencia también importa, pero no define la jerarquía. El Administrador es un rol operativo de soporte y control, no el destinatario del flujo principal.

## Product Purpose

JobDevs conecta empresas con aprendices y egresados del SENA para ejecutar proyectos reales, y gestiona el ciclo completo en un solo lugar: publicación → postulación → negociación y firma de contrato → hitos → avances con evidencia → revisión → finalización → calificación mutua.

Existe porque el talento SENA necesita experiencia demostrable y las empresas necesitan talento verificado con entregas trazables; un tablero de ofertas no cubre ninguna de las dos necesidades.

Contexto declarado de producto: existe uso operativo previo con empresas y desarrolladores, pero no lanzamiento público, campaña ni métricas de adopción publicables. El checkout local no verifica por sí mismo el despliegue actual; no debe insinuarse tracción comercial ni disponibilidad de producción sin evidencia del entorno.

## Positioning

Descriptor observado en la landing: «El sistema operativo del talento SENA». Se usa donde el contexto lo respalde; no se asume eslogan registrado ni aval del SENA.

**El diferenciador: la verificación de identidad SENA.** El talento se contrasta contra el **padrón de fichas SENA** con excepciones administradas y auditadas, y el registro exige cédula (NIT rechazado) y mayoría de edad. Un portal de empleo vecino puede copiar los hitos, el chat y las calificaciones mutuas; no puede afirmar con veracidad que la afiliación institucional del candidato y la identidad legal de la empresa fueron revisadas contra documentos fuente. La verificación es el activo durable: todo lo demás depende de saber quiénes son las partes.

Mecanismos que dependen de esa verificación y la sostienen:

- **Contrato digital** cuya firma vincula el perfil profesional vigente (nombre, condición SENA, programa, ficha, habilidades, portafolio e ID) mediante hash, y rechaza una segunda firma si el contenido cambió.
- **Avance por hitos con descripción obligatoria** y URL/archivo opcionales, más flujo de revisión con causa escrita, en lugar de un estado binario de "entregado".
- **Calificación mutua** al cierre y reputación de empresa visible antes de postularse.
- Trazabilidad por recorridos sensibles: historial de estados y logs de auditoría; no se afirma captura universal de escrituras directas.

## Operating Context

- Producto y documentación en **español de Colombia** como locale primario; roles, estados y mensajes usan terminología propia del dominio (postulación, avance, hito, contrato digital, ficha). El inglés existe en `/en/` y **es un requisito real**: una cadena ausente o degradada en inglés es un defecto, no un pendiente.
- Proyecto formativo SENA con **matriz de requisitos como fuente oficial** (`Matriz_de_Requisitos_JobDevs_VERIFICADA.xlsx`, fuera del repo, elegida por el responsable del producto). Las divergencias entre matriz, documentación interna y código se documentan en `docs/CONCILIACION_RF_BASE.md` y `docs/AUDITORIA_FUENTES_REQUISITOS.md`; no se corrigen en silencio.
- Operación esperada en **Docker Compose**: Nginx → Gunicorn → PostgreSQL 16, con Celery/Redis y respaldos automáticos (RNF-14).
- Paquete documental del proyecto: guía de usuario, manual técnico, casos de prueba, trazabilidad de requisitos, manual de marca y diagramas por rol forman parte del entregable y se mantienen junto al código.
- Compatibilidad objetivo: versiones recientes de **Chrome, Firefox y Edge** (RNF-12), con E2E por navegador en CI.

## Capabilities and Constraints

Capacidades confirmadas por código y documentación:

- Registro dual (DEV/CORP) con perfiles independientes, login unificado con redirección automática por rol real de BD.
- Publicación de proyectos con vacantes, tipo de solución y prioridad; edición bloqueada cuando existen contratos activos.
- Postulación con límite de **3** procesos simultáneos (postulaciones pendientes o en negociación + contratos activos) y verificación SENA.
- Contratación en dos firmas; aceptar una postulación inicia negociación y reserva de vacante, no un contrato inmediato.
- Hitos asignables a equipos o al proyecto, avances con descripción obligatoria y evidencia opcional, revisión con comentario obligatorio.
- Chat grupal por proyecto y privado 1‑a‑1; notificaciones en tiempo real por SSE.
- Calificación mutua al finalizar; favoritos; dashboard administrativo con búsqueda, filtros, acciones en lote, estadísticas y ranking de talento; API REST administrativa.
- Recuperación de contraseña por token con expiración de 1 hora.

Restricciones y reglas de negocio:

- Contraseña: mínimo 8 caracteres con mayúscula, minúscula y número. Suspensión automática tras 5 intentos fallidos; se reactiva al restablecer la contraseña.
- Sesión: expira al cerrar el navegador y por 1 hora de inactividad.
- Desarrollador: cédula obligatoria, NIT rechazado, mayoría de edad.
- Ficha SENA: padrón oficial administrado por el centro de formación, con mecanismo de excepciones justificadas y con vigencia.
- Terminar una contratación libera la vacante.

Decisiones abiertas (no inventar respuesta):

- Si ficha y programa deben ser obligatorios en el registro o permanecen opcionales.
- Registro de voz: el manual de marca pide segunda persona y la UI usa «tú/tus», mientras `docs/GUIA_USUARIO.md` conserva voseo («podés», «hacé»). El registro canónico del copy de producto es **tú neutro**; la guía queda pendiente de normalizar.
- Aprobación de un archivo maestro de logotipo: el manual de marca es una reconstrucción de trabajo, no un master aprobado.

## Brand Commitments

- Nombre: **JobDevs**, con J y D mayúsculas, sin separación ni pluralización adicional. Módulos como etiquetas de interfaz («JobDevs · Empresas»), no submarcas.
- Descriptor: «El sistema operativo del talento SENA», solo donde el contexto lo respalde y sin tratarlo como eslogan registrado.
- Firma actual: cuadrado verde + «JobDevs» en Space Grotesk bold + punto verde. Es una reconstrucción desde la landing; no existe archivo vectorial maestro aprobado. `static/IMG/Logo.jpg` no es logotipo principal.
- Voz (manual de marca): segunda persona con verbos de acción; explicar la causa de los procesos («Tu documento está en revisión», no «Solicitud fallida»); evitar garantías no demostrables («sin riesgo», «aval oficial», «contratación asegurada»); decir «desarrollador» o «aprendiz/egresado», nunca «recurso» para personas.
- Límite institucional: no usar logos, escudos ni la palabra «oficial» para insinuar aval del SENA sin autorización. El vínculo con SENA se expresa por capacidades reales (ficha verificada).
- Referencia completa: `docs/MANUAL_MARCA_JOBDEVS.pdf` (versión de trabajo, noviembre 2026).

## Evidence on Hand

- Contexto declarado de uso operativo previo con empresas y desarrolladores, sin lanzamiento público; no verificado desde este checkout y sin métricas de adopción publicables.
- `docs/GUIA_USUARIO.md` — flujos por rol, reglas de registro, sesión y contraseña.
- `docs/MANUAL_TECNICO.md` — arquitectura, modelos, API, testing, despliegue, compatibilidad de navegadores.
- `docs/API.md` — endpoints JSON, streams, descargas y reportes internos.
- `docs/CASOS_DE_PRUEBA.md` — escenarios de aceptación y regresión (no certifican carga, pentest ni accesibilidad).
- `docs/TRAZABILIDAD_REQUISITOS.md`, `docs/CONCILIACION_RF_BASE.md`, `docs/AUDITORIA_FUENTES_REQUISITOS.md`, `docs/AUDITORIA_ER_VS_MODELOS.md` — requisitos vs. implementación y divergencias aceptadas.
- `design/system.md` y `design/system.html` — tokens extraídos de CSS; `design/*/design.json` y `handoffs.json` — exploraciones por superficie.
- `static/IMG/JobDevs.png` — pieza de marca usada en README.
- `docs/DESARROLLADOR_*`, `docs/EMPRESA_*`, `docs/ADMIN_*` — diagramas de flujo por rol (drawio/svg/pdf).
- CI definida para SQLite, PostgreSQL 16 y E2E en Chrome/Firefox/Edge. No citar cifras de pruebas como vigentes sin registrar checkout, entorno y ejecución en `docs/ESTADO_VERIFICACION_ACTUAL.md`.

Ausencias que el trabajo futuro no debe fabricar: testimonios o casos de cliente publicables, métricas de impacto o benchmarks, cobertura de prensa, lanzamiento público, auditoría de accesibilidad con usuarios, aprobación legal del logotipo y autorización de uso de la marca SENA.

## Product Principles

1. **La trazabilidad manda sobre la velocidad.** Cada cambio de estado deja evidencia; el contrato congela el perfil con el que se firmó.
2. **Simetría entre las partes.** Ambas califican al cierre y la reputación de la empresa es visible antes de postularse.
3. **Talento verificado, no CVs abiertos.** La ficha SENA y sus excepciones auditadas son la puerta de entrada, no un adorno de perfil.
4. **La matriz de requisitos es un contrato con la institución.** Las divergencias se documentan y se deciden, nunca se maquillan.
5. **Los compromisos acotan la edición.** Un proyecto con contratos activos no se edita; una contratación terminada libera su vacante.

## Accessibility & Inclusion

**WCAG 2.1 AA vinculante.** Hoy no existe auditoría de accesibilidad y la suite de pruebas lo declara fuera de alcance; la operabilidad por teclado se ejercitó puntualmente en el inspector de candidatos. Todo trabajo de UI nuevo o modificado debe cumplir AA y verificarse antes de darse por terminado.
