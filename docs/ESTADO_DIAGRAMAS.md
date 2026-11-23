# Estado de diagramas de JobDevs

## Regla de mantenimiento

Los `.drawio` son fuentes editables. PDF, PNG y SVG son derivados y no se corrigen de forma independiente. Todo derivado debe indicar o poder rastrear la fuente y fecha/check de generación.

## Inventario

| Diagrama | Fuente | Derivados | Estado |
|---|---|---|---|
| ER físico | `ER_JOBDEVS.drawio` | `.png`, `.svg` | Vigente: 28 tablas, 251 columnas, 55 FK; `--check` contra ORM aprobado |
| ER Chen | `ER_JOBDEVS_chen.drawio` | `.png`, `.svg` | Fuente y derivados vigentes: 28 entidades, 251 atributos y 55 relaciones. |
| Administrador | `ADMIN_JOBDEVS.drawio` | PDF, 3 PNG, 3 SVG | Fuente y derivados vigentes: 38 casos de uso en 3 páginas. |
| Empresa | `EMPRESA_JOBDEVS.drawio` | PDF, 3 PNG, 3 SVG | Fuente y derivados vigentes: 43 casos de uso en 3 páginas. |
| Desarrollador | `DESARROLLADOR_JOBDEVS.drawio` | PDF, 3 PNG, 3 SVG | Fuente y derivados vigentes: 41 casos de uso en 3 páginas. |
| Mapa de navegación | `MAPA_NAVEGACION_JOBDEVS.drawio` | PDF, 5 PNG, 5 SVG | Fuente y derivados vigentes: visitante, tres roles y flujos transversales en 5 páginas. |

## Cobertura actual por rol

### Administrador

El diagrama vigente incorpora:

- crear proyecto sucesor sin reactivar el original;
- regularizar fecha de cierre histórico;
- configurar plazo global de negociación de 1–30 días;
- configurar mínimo de confianza de reputación;
- revisar evidencia privada de disputas;
- resolver con cuatro acciones y tres familias;
- gestionar solicitudes de cancelación;
- auditar altas, cambios, bajas y acciones masivas;
- excluir secretos y contenido confidencial de auditoría;
- gestionar fichas/excepciones SENA;
- respaldos, reportes y seguimiento operativo.

### Empresa

El diagrama vigente incorpora:

- comparar de 2 a 4 candidatos lado a lado;
- iniciar negociación en vez de contratación directa;
- editar términos y firmar contrato;
- activar solo con doble firma;
- revisar avances y evidencias;
- solicitar/confirmar cancelación según causal;
- aportar/consultar evidencia de disputa;
- continuar trabajo mediante proyecto sucesor;
- consultar reputación bayesiana, promedio y cantidad cuando la UI esté integrada.

### Desarrollador

El diagrama vigente incorpora:

- postular con perfil verificable;
- negociar y revisar contrato;
- primera/segunda firma sin activación prematura;
- registrar avance con descripción y evidencia opcional;
- confirmar o rechazar cancelación bilateral;
- abrir disputa y aportar evidencia privada;
- fuerza mayor con evidencia o declaración de indisponibilidad;
- valorar después del cierre;
- comprender reputación calculada, promedio simple y cantidad.

## Criterios UML y de cobertura

Para cada archivo por rol:

1. Enumerar todas las páginas y detectar duplicadas/vacías.
2. Usar un único actor por rol y un límite de sistema claro.
3. Relacionar cada caso con una ruta o acción de dashboard alcanzable.
4. Usar «include» solo para pasos obligatorios y «extend» para variaciones opcionales.
5. No representar una decisión pendiente como caso implementado.
6. Marcar servicios externos: correo, R2, SENA/DIAN si realmente se integran.
7. Verificar que líneas tengan extremos y que cada relación sea legible.
8. Comparar la lista final contra `urls.py`, guards y acciones sin ruta propia.

## Procedimiento de regeneración

1. Editar el `.drawio` fuente.
2. Validar IDs, endpoints de aristas y solapamientos.
3. Exportar cada página a SVG y PNG.
4. Generar PDF desde la misma fuente.
5. Inspeccionar visualmente cada página.
6. Verificar que el multiset de etiquetas de fuente y derivados coincida.
7. Actualizar este estado y el índice documental.

Comando de referencia para exportación headless:

```bash
drawio.AppImage --no-sandbox --ozone-platform=headless --disable-gpu \
  --export --format png --border 20 \
  -o /ruta/absoluta/salida.png /ruta/absoluta/fuente.drawio
```

## Límites actuales

- La integración completa de reputación bayesiana en UI sigue pendiente; los diagramas la presentan como consulta y no como evidencia de que todas las superficies estén integradas.
- Los diagramas describen acciones y permisos locales; no constituyen evidencia de despliegue, aceptación de producto ni integración con servicios externos.
- La exportación final de Chen escribió e hizo inspeccionables sus PNG/SVG, pero `drawio.AppImage` emitió `UnknownVizError` después de escribirlos y no cerró limpiamente. Para futuras regeneraciones conviene reemplazar o corregir ese renderer antes de automatizar la exportación en CI.

## Evidencia de cierre esperada

| Artefacto | Check estructural | Render inspeccionado | Cobertura contra rutas | Derivados regenerados |
|---|---|---|---|---|
| ER físico | Sí | Sí | No aplica | Sí |
| ER Chen | Sí | Sí | No aplica | Sí |
| Administrador | Sí por página | Sí | Sí, contra rutas/guards y decisiones aprobadas | Sí |
| Empresa | Sí por página | Sí | Sí, contra rutas/guards y decisiones aprobadas | Sí |
| Desarrollador | Sí por página | Sí | Sí, contra rutas/guards y decisiones aprobadas | Sí |
| Mapa de navegación | Sí por página | Sí | Sí, contra rutas, navegación de dashboards y decisiones aprobadas | Sí |
