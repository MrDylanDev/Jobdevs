# Índice maestro de documentación de JobDevs

## Uso de este índice

Este archivo identifica la fuente vigente, el estado y la audiencia de cada artefacto. La presencia de un documento no implica que su contenido haya sido aceptado en producción. Los estados usados son:

- **Vigente:** fuente documental que debe mantenerse sincronizada.
- **Parcial:** contiene información válida y pendientes explícitos.
- **Histórico:** evidencia de un checkout o momento anterior; no describe automáticamente el estado actual.
- **Derivado:** se genera desde otra fuente editable y no debe editarse de forma independiente.
- **Pendiente de evidencia:** plantilla o política definida sin ejecución/aceptación demostrada.

## 1. Producto y requisitos

| Documento | Estado | Propósito |
|---|---|---|
| [Decisiones de producto aprobadas](DECISIONES_PRODUCTO_APROBADAS.md) | Vigente | Fuente canónica de las ocho decisiones aprobadas y sus límites. |
| [Matriz de reglas de negocio](MATRIZ_REGLAS_NEGOCIO.md) | Vigente/parcial | Consolida 103 reglas, su autoridad, pruebas relacionadas, límites y brechas. |
| `MATRIZ_REGLAS_NEGOCIO_JOBDEVS.xlsx` | Derivado vigente | Seguimiento filtrable de reglas y brechas; se regenera desde la matriz Markdown. |
| [Auditoría de fuentes](AUDITORIA_FUENTES_REQUISITOS.md) | Vigente | Define fuentes oficiales, diferencias y alcance de la evidencia. |
| [Conciliación de RF base](CONCILIACION_RF_BASE.md) | Vigente | Mapea los RF oficiales contra código, pruebas y diferencias. |
| [Trazabilidad](TRAZABILIDAD_REQUISITOS.md) | Vigente/parcial | Relaciona requisitos, implementación, pruebas y veredictos. |
| [Casos de prueba](CASOS_DE_PRUEBA.md) | Vigente | Catálogo diseñado; no confundir caso escrito con caso ejecutado. |
| `CASOS_DE_PRUEBA_JOBDEVS_V4.xlsx` | Derivado canónico actual | Presentación tabular más reciente de casos. Debe regenerarse cuando cambie el Markdown. |
| `CASOS_DE_PRUEBA_JOBDEVS.xlsx`, `V2`, `V3` | Histórico | Versiones anteriores; no usar como fuente vigente. |

La matriz oficial externa permanece en solo lectura fuera del repositorio. No se reemplaza por los inventarios internos.

## 2. Manuales funcionales y técnicos

| Documento | Estado | Audiencia |
|---|---|---|
| [Guía de usuario](GUIA_USUARIO.md) | Vigente/parcial | Desarrolladores, empresas y administradores. |
| [Manual técnico](MANUAL_TECNICO.md) | Vigente/parcial | Equipo de desarrollo y mantenimiento. |
| [API](API.md) | Vigente/parcial | Desarrollo frontend/backend e integraciones internas. |
| [Arquitectura de servicios](ARQUITECTURA_SERVICIOS.md) | Vigente con secciones históricas | Desarrollo y revisión arquitectónica. |
| [Configuración](CONFIGURACION.md) | Vigente | Desarrollo, operaciones y seguridad. |
| [Migraciones y compatibilidad](MIGRACIONES_Y_COMPATIBILIDAD.md) | Vigente | Desarrollo y operación de datos. |
| [Valoraciones históricas](VALORACIONES_HISTORICAS.md) | Vigente | Administración y mantenimiento de datos legados. |

## 3. Operación, despliegue y continuidad

| Documento | Estado | Propósito |
|---|---|---|
| [Guía Docker](DOCKER_README.md) | Vigente | Stack local/integrado de contenedores. |
| [Despliegue y operación](DESPLIEGUE_Y_OPERACION.md) | Vigente/parcial | Runbook, verificación, rollback y mantenimiento. |
| [RNF-14: respaldo y recuperación](RNF-14_RESPALDO_Y_RECUPERACION.md) | Histórico con procedimiento vigente | Evidencia medida y operación de respaldos. |
| [Estado de verificación actual](ESTADO_VERIFICACION_ACTUAL.md) | Pendiente de evidencia | Registro del próximo ciclo integral de pruebas/checks. |
| `ESTADO_VERIFICACION_ACTUAL_JOBDEVS.xlsx` | Derivado vigente | Registro operativo de verificaciones, responsables, checkout y evidencias. |
| [Acta de aceptación](ACTA_ACEPTACION_PRODUCTO.md) | Pendiente de firma | Aceptación funcional/visual separada de pruebas técnicas. |

## 4. Seguridad, privacidad y auditoría

| Documento | Estado | Propósito |
|---|---|---|
| `INFORME_SEGURIDAD_JOBDEVS.docx` | Histórico | Fuente editable del diagnóstico de seguridad del 12 de noviembre de 2026. |
| `INFORME_SEGURIDAD_JOBDEVS.pdf` | Derivado histórico | Export del informe anterior. |
| [Seguimiento de hallazgos](SEGUIMIENTO_HALLAZGOS_SEGURIDAD.md) | Vigente/parcial | Estado verificable de mitigaciones y riesgos residuales. |
| [Privacidad y tratamiento de datos](PRIVACIDAD_Y_TRATAMIENTO_DE_DATOS.md) | Vigente como política interna | Datos, acceso, retención, eliminación y respuesta a incidentes. |
| [Matriz de acceso y retención](MATRIZ_ACCESO_Y_RETENCION.md) | Vigente/parcial | Reglas operativas por clase de dato. |

Estos documentos no sustituyen asesoría jurídica, autorización de tratamiento ni una auditoría de producción.

## 5. Modelo de datos y diagramas

Estado consolidado: [Estado de diagramas](ESTADO_DIAGRAMAS.md).

| Artefacto | Estado | Fuente/derivado |
|---|---|---|
| [Auditoría ER](AUDITORIA_ER_VS_MODELOS.md) | Vigente con historial | Explica alcance, diferencias y regeneración. |
| `ER_JOBDEVS.drawio` | Vigente | Fuente editable física generada desde el ORM. |
| `ER_JOBDEVS.svg`, `ER_JOBDEVS.png` | Derivados vigentes | Exportaciones del ER físico. |
| `ER_JOBDEVS_chen.drawio` | Vigente | Fuente Chen sincronizada con el ORM. |
| `ER_JOBDEVS_chen.svg`, `ER_JOBDEVS_chen.png` | Derivados vigentes | Exportados desde la fuente Chen sincronizada con el ORM. |
| `ADMIN_JOBDEVS.drawio` | Vigente | Diagrama de casos de uso administrativo, actualizado con decisiones aprobadas. |
| `EMPRESA_JOBDEVS.drawio` | Vigente | Diagrama de empresa, actualizado con decisiones aprobadas. |
| `DESARROLLADOR_JOBDEVS.drawio` | Vigente | Diagrama de desarrollador, actualizado con decisiones aprobadas. |
| [Mapa de navegación](MAPA_NAVEGACION.md) | Vigente | Rutas y transiciones de visitante, empresa, desarrollador, administrador y flujos transversales. |
| `MAPA_NAVEGACION_JOBDEVS.drawio` | Vigente | Fuente editable del mapa de navegación; PDF y PNG/SVG por página son derivados. |
| PDF/PNG/SVG por rol | Derivados vigentes | Exportados desde cada fuente `.drawio` vigente. |

## 6. Presentaciones, marca y entregables editables

| Artefacto | Estado | Nota |
|---|---|---|
| `EXPOSICION_JOBDEVS.pptx` | Fuente editable | Presentación del proyecto; revisar antes de exposición final. |
| `EXPOSICION_JOBDEVS.pdf` | Derivado | Regenerar desde PPTX si cambia la fuente. |
| `MANUAL_MARCA_JOBDEVS.docx` | Fuente editable | Manual de identidad. |
| `MANUAL_MARCA_JOBDEVS.pdf` | Derivado | Export del DOCX. |

## 7. Informes de cierre

| Documento | Estado | Nota |
|---|---|---|
| [Cierre autónomo](CIERRE_AUTONOMO.md) | Histórico | Diario de trabajo; sus cifras no certifican el checkout actual. |
| [Informe de cierre autónomo](INFORME_CIERRE_AUTONOMO.md) | Histórico con adenda | Resultado de una ejecución anterior y pendientes posteriores. |

## 8. Gobierno documental

1. La fuente editable se modifica antes que sus derivados.
2. Un resultado de prueba incluye comando, entorno, fecha, checkout y código de salida.
3. Una decisión aprobada no se registra como implementación completa sin evidencia.
4. Una prueba automatizada no equivale a aceptación de producto ni a despliegue.
5. Los documentos históricos se conservan y reciben una adenda; no se reescriben como si hubieran medido el checkout actual.
6. No se incluyen contraseñas, tokens, documentos personales ni datos de producción.
7. Los archivos nuevos deben añadirse deliberadamente al control de versiones; actualmente varios artefactos de `docs/` siguen sin seguimiento en Git.
8. Antes de entregar se ejecutan validación de enlaces locales y `git diff --check`.

## 9. Próximas actualizaciones documentales

- Ejecutar y completar el estado de verificación actual.
- Obtener aceptación funcional/visual del responsable del producto.
- Mantener API, configuración y despliegue sincronizados con nuevas rutas o variables.
