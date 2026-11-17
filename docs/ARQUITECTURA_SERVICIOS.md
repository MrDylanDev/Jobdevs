# Arquitectura de servicios y políticas (SCRUM-156)

Documento de decisión y estado de las **fases 1 y 2** de la hoja de ruta
«Recomendaciones arquitectónicas para TEIR». Registra qué se decidió, qué se
implementó, qué queda pendiente y cómo se reparte en issues derivados.

## 1. Premisa y decisión

El problema no es Django sino que la lógica de negocio, la autorización y las
decisiones de estado vivían dentro de las vistas. Eso produjo bugs como el
`Count` inflado, postulaciones sobre proyectos finalizados, race conditions de
vacantes y el bypass de mensajería.

**Decisión:** introducir de forma incremental una capa de aplicación
(`services.py`) y una capa de autorización (`policies.py`) **por app**, sin
reescribir la aplicación ni cambiar el framework.

Ya existía un precedente en el repo (`disputas/services.py`), así que se adoptó
ese mismo estilo para no crear un patrón paralelo:

- una transacción (`transaction.atomic`) por operación mutadora;
- `select_for_update` sobre el recurso compartido antes de decidir;
- fallos comunicados con `PermissionDenied` (autorización) y
  `ValidationError` (regla de negocio);
- la vista traduce la excepción en `messages` + `redirect`.

## 2. Fase 1 — Fundamentos (estado)

| Ítem | Estado |
| --- | --- |
| Arreglos críticos de la auditoría | Hecho (auditoría, PR de hallazgos) |
| `SECRET_KEY` sin fallback insegura en producción | Hecho (`config/settings.py` falla explícito sin la variable) |
| `DEBUG` y `ALLOWED_HOSTS` por entorno | Hecho |
| TLS/HTTPS obligatorio y `SECURE_*` | Pendiente → issue derivado |
| Base de datos y media gestionadas (no contenedor local) | Pendiente → issue derivado |

## 3. Fase 2 — Capa de servicios (implementado)

Cuatro flujos críticos salieron de las vistas:

| Flujo | Servicio | Política | Vista (después) |
| --- | --- | --- | --- |
| Aceptar postulación y contratar | `postulaciones/services.py::aceptar_postulacion` | `postulaciones/policies.py::puede_aceptar_postulacion` | valida rol + 404, delega, traduce excepción |
| Finalizar proyecto | `proyectos/services.py::finalizar_proyecto` | `proyectos/policies.py::puede_finalizar_proyecto` | prevalidación de UX, delega, traduce |
| Registrar valoración y cerrar | `proyectos/services.py::valorar_y_finalizar_si_ultima` | (misma política + hitos) | idem |
| Cancelar contratación | `contrataciones/services.py::cancelar_contratacion` | `contrataciones/policies.py::puede_cancelar_contratacion` | idem |
| Enviar mensaje directo | `mensajes/services.py::enviar_mensaje` | `mensajes/policies.py::puede_comunicarse` | gate 403 + delega |
| Enviar mensaje grupal | `mensajes/services.py::enviar_mensaje_grupal` | `mensajes/policies.py::puede_participar_en_chat_grupal` | idem |

Además se centralizó la autorización de mensajería, que antes estaba duplicada
y con variantes:

- `puede_enviar_mensaje` / `puede_comunicarse`
- `puede_participar_en_chat_grupal`
- `puede_ver_mensaje` (cierra el IDOR del detalle de mensaje)

### Reparto de responsabilidades

```
Vista         → sesión/rol, 404 de propiedad, parseo del input, messages + redirect
Servicio      → reglas de negocio autoritativas, transacción, locks, efectos secundarios
Policy        → ¿puede este usuario hacer esta acción? (una sola definición)
Modelo/Manager→ datos y helpers de consulta
```

La vista puede prevalidar para ofrecer mejores redirecciones, pero **la
validación que manda es la del servicio**, que vuelve a comprobar el estado
bajo lock. Nada que dependa del estado se decide solo en la vista.

### Regla de oro para transacciones

Si una operación toca más de una tabla o consume un recurso compartido
(vacantes, cupos, estados), va dentro de `transaction.atomic()` y bloquea con
`select_for_update()` la fila que contiene el dato disputado (por eso
`aceptar_postulacion` bloquea primero el `Proyecto`).

## 4. Tests

Los flujos tienen tests unitarios de servicio, no solo de vista:

- `postulaciones/tests/test_services.py`
- `proyectos/tests/test_services.py`
- `contrataciones/tests/test_services.py`
- `mensajes/tests/test_services.py`

Cubren camino feliz, reglas de negocio y **rollback** (p. ej. sin vacantes no
queda ni contratación ni cambio de estado).

## 5. Pendiente (issues derivados)

Fases 3 a 10 de la hoja de ruta, cada una como issue propio:

1. **Fase 3 — Máquina de estados**: migrar `Proyecto`, `Postulacion` y
   `Contratacion` a `django-fsm` y prohibir asignaciones directas de estado.
2. **Fase 4 — ViewModels/Presenters**: sacar consultas y decisiones de los
   templates (N+1 en chat, favoritos y notificaciones).
3. **Fase 5 — Eventos de dominio**: notificaciones vía eventos/handlers y luego
   cola (`django-q2`) para no bloquear la request.
4. **Fase 6 — Pirámide de tests**: `factory-boy` + más unitarios, menos e2e con
   `sleep`.
5. **Fase 7 — Infra**: TLS obligatorio, media en S3/MinIO, CI con
   `bandit`/`pip-audit`, dependencias pinnadas con `pip-tools`.
6. **Fase 8 — Ratelimit y CSP**: `django-ratelimit` en login y `django-csp`.
7. **Fase 9 — Read models/CQRS**: solo si el listado público se vuelve pesado.
8. **Fase 10 — HTMX**: reemplazar los links GET contra vistas `@require_POST`.

## 6. Checklist para nuevos aportes

- ¿La vista solo autoriza, parsea y delega? Si tiene reglas de estado, muévelas
  a un `services.py`.
- ¿La operación toca más de una tabla o un recurso compartido? `atomic()` +
  `select_for_update()`.
- ¿La autorización se pregunta en más de un sitio? Va a `policies.py`.
- ¿La operación tiene tests de camino feliz, de regla de negocio y de rollback?

---

## Criterio de Views (Thin Controller vs Service) y Registro en Django Admin (SCRUM-449)

### 1. Patrón de Views (`views.py`)
Toda vista Django debe actuar exclusivamente como **controlador delgado (Thin Controller)**:

1. **Autenticación y permisos**: validar `@login_required`, rol o pertenencia básica al recurso (`PermissionDenied` / `403`).
2. **Parseo y validación de entrada HTTP**: extraer parámetros de `request.GET`, `request.POST` o `request.FILES`.
3. **Delegación al servicio (`services.py`)**: invocar la función de dominio encargada de transacciones (`@transaction.atomic`), reglas de negocio, auditoría (`LogAuditoria`) y notificaciones.
4. **Respuesta HTTP**: devolver `JsonResponse` (para peticiones AJAX/fetch) o `render`/`redirect` con `messages`.

**Prohibido en `views.py`:**
- Consultas complejas o mutaciones multi-modelo directas sin servicio.
- Lógica de negocio (> ~40 líneas de reglas condicionales o cálculos de dominio): debe extraerse a `<app>/services.py`.

### 2. Criterio de Registro en `admin.py`
Los modelos de dominio de las apps cubiertas por el estándar (`avances`, `favoritos`, `contrataciones`, `postulaciones`, `notificaciones`) se registran en `<app>/admin.py` con `list_display` y, cuando el modelo lo permite, `list_filter` y `search_fields`, para inspección y soporte operativo en `/admin/` (por ejemplo: `Avance`, `Favorito`, `ContratoDigital`, `SolicitudCancelacion`, `Postulacion`, `Notificacion`, `AvisoCumplimiento`). Hoy los nueve modelos de esas cinco apps están registrados y exponen `list_display`.

Los modelos nuevos que se creen en esas apps —y los de cualquier app que se incorpore al estándar— nacen ya registrados con esos atributos. Los modelos de configuración que se publican en modo solo lectura (por ejemplo `ConfiguracionNegociacion`) se registran sin `list_filter` ni `search_fields`, porque no admiten edición.

Si un modelo del estándar se excluye intencionalmente del admin (tablas efímeras o de solo lectura externa), se documenta con un comentario explicativo en `<app>/admin.py`. Hoy no hay ningún modelo excluido.

Las apps fuera del estándar (`disputas`, `mensajes`, `logs`, `proyectos`, `usuarios`) son legado pendiente de migración incremental: no están obligadas a este criterio hasta que se incorporen.
