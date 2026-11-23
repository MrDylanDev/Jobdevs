# Estado de verificación actual

## Regla de lectura

Este documento separa resultados históricos, pruebas focalizadas y verificación integral. Una casilla pendiente no significa fallo; significa que no existe evidencia posterior al último cambio relevante.

## Identificación del ciclo

| Campo | Valor |
|---|---|
| Rama observada | `feat/empresa-dashboard-ui` |
| Commit base | Pendiente de registrar al ejecutar |
| Fecha/hora y zona | Pendiente |
| Sistema operativo | Pendiente |
| Python/Django | 3.14.9 / 6.1.2 observados durante actualización documental |
| Base de datos | Pendiente |
| Navegadores | Pendiente |
| Responsable | Pendiente |

## Estado por nivel

### Decisión de producto

Las ocho políticas están aprobadas en [Decisiones de producto](DECISIONES_PRODUCTO_APROBADAS.md).

### Implementación local conocida

- proyecto sucesor: implementado localmente;
- comparador 2–4: implementado localmente;
- auditoría administrativa sensible: ampliada, cobertura exhaustiva pendiente;
- plazo de negociación configurable/congelado: implementado localmente;
- familias de disputa: implementadas localmente;
- evidencia privada por causal: implementada localmente;
- cancelación sustantiva: flujo bilateral/mediación y evidencia relacionados;
- reputación bayesiana: fórmula/configuración implementadas; integración uniforme de UI/reportes pendiente.

### Pruebas focalizadas registradas antes de este ciclo documental

Existen resultados focalizados verdes en el historial de trabajo para sucesión, comparador, auditoría administrativa, negociación, disputas/evidencia y cálculo/configuración bayesiana. No se reinterpretan como regresión integral del checkout actual.

### Verificación integral posterior

No ejecutada durante el ciclo documental actual.

## Matriz a completar

| Verificación | Comando/entorno | Resultado | Código de salida | Evidencia |
|---|---|---|---|---|
| Enlaces Markdown | Script local sobre documentos modificados | Pendiente de ejecución final | Pendiente | Pendiente |
| Espacios/diff | `git diff --check` | Pendiente de ejecución final | Pendiente | Pendiente |
| Ruff | `uv run ruff check .` | No ejecutado en ciclo documental | — | — |
| Django check | `uv run python manage.py check` | No ejecutado | — | — |
| Check de despliegue | `manage.py check --deploy` con entorno real | No ejecutado | — | — |
| Drift de migraciones | `makemigrations --check --dry-run` | No ejecutado después del paquete | — | — |
| Migraciones desde cero SQLite | Base descartable | No ejecutado después del paquete | — | — |
| Migración PostgreSQL | PostgreSQL 16 descartable | No ejecutado después del paquete | — | — |
| Suite sin E2E | `uv run pytest -q --tb=short` | No ejecutada después del paquete | — | — |
| E2E Chromium | `pytest -m e2e` | No ejecutada después del paquete | — | — |
| E2E Chrome/Firefox/Edge | CI/matriz real | No verificada | — | — |
| Celery/Beat/Redis | Stack integrado | No verificado después del paquete | — | — |
| SSE detrás de proxy | Entorno integrado | No verificado | — | — |
| WebSocket detrás de ASGI/Redis | Entorno integrado | No verificado | — | — |
| Backup/restauración PostgreSQL | Base aislada | Evidencia histórica; repetir para checkout actual | — | — |
| R2 real | Bucket de prueba | No verificado | — | — |
| Aceptación visual | Multidispositivo | No ejecutada | — | — |
| Aceptación de producto | Acta | Pendiente | — | [Acta](ACTA_ACEPTACION_PRODUCTO.md) |

## Resultados históricos

Los conteos de `INFORME_CIERRE_AUTONOMO.md` pertenecen a un checkout anterior al paquete reciente. Se conservan como evidencia histórica y no se copian aquí como estado actual.

## Criterio de cierre técnico

Requiere como mínimo:

1. migraciones sin drift y aplicables desde cero/actualización en PostgreSQL;
2. pruebas focalizadas y globales con salida limpia;
3. E2E aplicable sin errores de teardown;
4. Ruff y checks Django;
5. diagramas/documentos sincronizados o pendientes señalados;
6. hallazgos de seguridad críticos evaluados;
7. smoke test del stack integrado;
8. evidencia registrada con checkout y entorno.

## Criterio de aceptación de producto

Es independiente del cierre técnico. Requiere que el responsable pruebe los recorridos y complete [Acta de aceptación](ACTA_ACEPTACION_PRODUCTO.md).
