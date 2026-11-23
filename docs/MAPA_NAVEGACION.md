# Mapa de navegación — JobDevs

## Propósito y alcance

Este documento describe cómo una persona se desplaza entre pantallas, módulos y flujos principales de JobDevs. Complementa los diagramas de casos de uso: estos muestran capacidades por actor; el mapa muestra la secuencia de navegación y las transiciones que dependen de estado o autorización.

La fuente visual editable es [`MAPA_NAVEGACION_JOBDEVS.drawio`](MAPA_NAVEGACION_JOBDEVS.drawio). Sus exportaciones PDF/PNG/SVG son derivados. El generador reproducible es `scripts/generate_navigation_map_drawio.py`.

No representa cada API, petición AJAX, acción masiva ni tarea programada. Tampoco interpreta una transición de estado como una URL accesible a cualquier actor.

## Convenciones

- Rectángulo redondeado: pantalla, sección de dashboard o módulo navegable.
- Hexágono: estado, guarda o transición de negocio.
- Flecha continua: navegación o avance principal.
- Flecha discontinua desde el actor: acceso condicionado a autenticación, rol, objeto y estado.
- Cada página del `.drawio` contiene un actor o una regla transversal, un límite de sistema y flujos independientes para reducir cruces visuales.

## Inventario de páginas

| Página | Actor/tema | Cobertura |
|---|---|---|
| 01 | Visitante | Inicio, catálogo, registro, acceso y recuperación de contraseña. |
| 02 | Empresa | Perfil, ofertas, candidatos, negociación, contrato, ejecución, mensajes, cancelación y disputa. |
| 03 | Desarrollador | Perfil SENA, exploración, favoritos, postulación, contrato, avances, cierre, mensajes, cancelación y disputa. |
| 04 | Administrador | Supervisión, verificaciones, fichas SENA, configuración, cancelaciones, mediación, auditoría y reportes. |
| 05 | Transversal | Doble firma, ejecución por hitos, finalización irreversible, sucesor, cancelación, mediación y guardas. |

## Puntos de entrada y rutas principales

La aplicación se organiza bajo los prefijos de `config/urls.py`: usuarios, proyectos, postulaciones, contrataciones, avances, mensajes, notificaciones, favoritos y disputas. Todo el contenido de aplicación usa prefijo de idioma; español permanece en `/` e inglés en `/en/`.

| Flujo | Entrada o ruta principal | Regla de acceso/navegación |
|---|---|---|
| Inicio y cuenta | `/`, `/registro/`, `/login/`, `/recuperar/`, `/restablecer/<token>/` | Visitante; el login redirige al dashboard correspondiente al rol activo. |
| Empresa | `/empresa/dashboard/`, `/empresa/verificacion/`, `/perfil/editar/` | Cuenta activa con rol `empresa`. Las secciones del dashboard son navegación interna. |
| Desarrollador | `/desarrollador/dashboard/`, `/desarrollador/verificacion/`, `/perfil/editar/` | Cuenta activa con rol `desarrollador`. Las secciones del dashboard son navegación interna. |
| Administrador | `/admin/dashboard/` | Cuenta activa con rol `administrador`; el `django-admin` nativo es una herramienta separada para superusuarios. |
| Proyectos | `/proyectos/`, `/proyectos/crear/`, `/proyectos/editar/<id>/`, `/proyectos/hitos/<id>/`, `/proyectos/equipos/<id>/` | El catálogo es el punto de descubrimiento; edición y gestión dependen de titularidad, rol y estado. |
| Postulación | `/postulaciones/postularse/<proyecto_id>/`, `/postulaciones/proyecto/<proyecto_id>/recibidas/`, `/postulaciones/iniciar-negociacion/<id>/` | Desarrollador postula; empresa revisa e inicia negociación. La ruta histórica `aceptar` también inicia negociación, no contratación directa. |
| Contrato y cancelación | `/contrataciones/contrato-digital/<id>/`, `/contrataciones/cancelaciones/` | Las partes consultan/firman su contrato; la cancelación comienza como solicitud y no termina obligaciones automáticamente. |
| Avances | `/avances/registrar/<proyecto_id>/`, `/avances/proyecto/<proyecto_id>/`, `/avances/revisar/<id>/` | Desarrollador registra; empresa revisa el avance del proyecto correspondiente. |
| Mensajes/notificaciones | `/mensajes/bandeja/`, `/mensajes/chat/...`, `/notificaciones/` | Usuario autorizado; chat directo/grupal depende de participantes y estado del proyecto. |
| Disputas | `/disputas/`, `/disputas/abrir/<proyecto_id>/`, `/disputas/<id>/` | Partes autorizadas abren/participan; administrador resuelve. La evidencia descargable se autoriza por objeto. |

## Flujos que no deben confundirse con una navegación ordinaria

### Contratación por doble firma

1. La empresa inicia negociación desde una postulación elegible.
2. La plataforma reserva el cupo y presenta/permite ajustar el contrato digital.
3. La primera firma preserva evidencia contractual, pero no activa la contratación.
4. Solo la segunda firma activa el contrato, actualiza los estados relacionados y permite el trabajo contractual.

### Finalización irreversible y sucesor

1. El último hito aprobado permite cerrar el proyecto y sus contratos según las reglas aplicables.
2. El proyecto y los contratos originales no se reactivan para continuar el trabajo.
3. Si hay continuación, se crea un proyecto sucesor vinculado. El mapa lo representa como una transición de negocio, no como retorno al proyecto cerrado.

### Cancelación y mediación

1. Una parte propone cancelación con la causal y evidencia o declaración aplicable.
2. La contraparte confirma o rechaza; la propuesta y el silencio no cancelan por sí mismos.
3. Desacuerdo, inactividad o fuerza mayor pueden escalar a mediación.
4. La mediación congela proyecto/contrato y conserva el cupo hasta dictamen.
5. El administrador adopta una resolución de continuidad, terminación o sanción de acuerdo con las reglas aplicables; no existe sanción automática.

## Límites y mantenimiento

- El mapa acredita diseño/navegación local, no aceptación visual ni despliegue.
- Una nueva pantalla, dashboard, ruta navegable o transición de estado debe actualizar este documento, el `.drawio`, sus derivados y los casos de uso del rol afectado.
- Las rutas de API y comandos operativos se documentan en API/configuración/despliegue salvo que introduzcan una pantalla de usuario.
- Revalidar el mapa contra `urls.py`, guards de vistas y enlaces/acciones de los templates antes de cada entrega funcional.
