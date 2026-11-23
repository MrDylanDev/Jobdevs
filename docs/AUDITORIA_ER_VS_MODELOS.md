# Auditoría del diagrama ER (ER.drawio.png) vs. modelos Django de JobDevs

## Actualización del esquema generado

La auditoría de las secciones 1–7 describe el PNG manual y el ORM del 11 de noviembre; se conserva como historial. Después de las decisiones de producto y migraciones posteriores se regeneraron las fuentes desde el ORM actual:

- `ER_JOBDEVS.drawio`: 28 tablas, 251 columnas y 55 FK; `--check` sin diferencias.
- `ER_JOBDEVS_chen.drawio`: 28 entidades, 251 atributos y 55 relaciones; `--check` sin diferencias.
- El modelo físico se exportó nuevamente a PNG y SVG y el PNG fue inspeccionado: no presenta recortes ni superposiciones graves; por su densidad, el SVG es la versión recomendada para lectura con zoom.
- La exportación del Chen actualizado no terminó en el renderer headless (`UnknownVizError`); sus PNG/SVG previos no deben presentarse como derivados vigentes hasta regenerarlos con un renderer compatible.

Las incorporaciones principales frente al inventario histórico de 25 tablas incluyen `SolicitudCancelacion`, `RegularizacionCierreProyecto`, `ConfiguracionNegociacion` y `ConfiguracionReputacion`, además de `Proyecto.proyecto_origen` y los campos de evidencia de disputa.

Fecha: 2026-11-11 · Alcance: `/home/mrdylan/Descargas/ER.drawio.png` contra `/home/mrdylan/Proyectos/Jobdevs`

## Cómo se hizo

- **Diagrama**: PNG con el XML de diagrams.net embebido en el chunk `tEXt/mxfile`
  (URL-encoded). Se extrajo y parseó: 439 `mxCell` → 98 rectángulos, 123 elipses
  de atributo y 216 conectores. Las entidades se reconstruyeron agrupando las
  elipses por conectividad (union-find sobre cadenas elipse↔elipse) y, cuando no
  había conector, por proximidad geométrica.
- **Modelos**: introspección dinámica del ORM (`django.setup()` +
  `_meta.concrete_fields`, `many_to_many`, `db_table`, `column`, `related_model`),
  no lectura estática del código, para incluir herencia (`AbstractUser`) y tablas
  intermedias M2M. Resultado: **25 tablas** (22 de negocio + 2 M2M de auth + 1 M2M de equipos).
- **Comparación**: nombres normalizados (sin tildes, sin sufijos `(PK)`/`(FK)`,
  minúsculas) y alias explícito `historial_estado → historial_estado_proyecto`.

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Tablas en el ORM | 25 (22 de negocio + 3 M2M) |
| Tablas en el diagrama | 17 |
| **Tablas del ORM ausentes en el diagrama** | **6** |
| Tablas del diagrama que no existen en el ORM | 0 |
| Tablas idénticas campo a campo | 9 de 17 |
| **Campos no documentados en el diagrama** | **35** |
| Campos del diagrama inexistentes en el ORM | 0 |
| FKs del ORM no representadas | 5 |
| Atributos dibujados desconectados de su entidad | 14 de 123 |

El diagrama **no está "mal"**: está **desactualizado**. No hay ni una tabla ni un
campo inventado; todo lo que dibuja existe en el ORM (salvo un nombre mal escrito
y un duplicado). Lo que falta son incorporaciones posteriores al trazado del
diagrama: el módulo de verificación SENA, el de disputas, categorías dinámicas,
contratos digitales y un puñado de campos de endurecimiento.

## 1. Tablas del ORM que faltan completas en el diagrama (6)

| Tabla | Modelo | Origen (commit) | Fecha |
|---|---|---|---|
| `fichas_sena` | `usuarios.FichaSena` | feat(usuarios): crear modelo FichaSena… (SCRUM-154) | 2026-10-14 |
| `excepciones_ficha_sena` | `usuarios.ExcepcionFichaSena` | feat(sena): excepciones de fichas… (SCRUM-225, 229) | 2026-10-24 |
| `categorias_solucion` | `proyectos.CategoriaSolucion` | feat(proyectos): gestión dinámica de categorías… (SCRUM-144) | 2026-10-10 |
| `contratos_digitales` | `contrataciones.ContratoDigital` | feat(contrataciones): ContratoDigital… (SCRUM-150, 151) | 2026-10-11 |
| `disputas` | `disputas.Disputa` | feat(disputas): crear app disputas… (SCRUM-155) | 2026-10-11 |
| `mensajes_disputa` | `disputas.MensajeDisputa` | feat(disputas): crear app disputas… (SCRUM-155) | 2026-10-11 |

Observación de riesgo: `disputas` y `mensajes_disputa` no solo faltan en el
diagrama, sino que **no tienen ninguna representación** del subsistema de disputas,
que sí está en producción del código (13 y 5 campos respectivamente).

## 2. Campos del ORM no documentados, por tabla (35)

| Tabla | ORM | Diag | Campos faltantes |
|---|---|---|---|
| `usuarios` | 17 | 16 | `bloqueado_por_intentos` |
| `proyectos` | 13 | 10 | `categoria_id` (FK), `modalidad`, `ciudad` |
| `entregables` | 8 | 7 | `desarrollador_id` (FK) |
| `postulaciones` | 7 | 6 | `fecha_limite_negociacion` |
| `contrataciones` | 7 | 6 | `motivo_cancelacion` |
| `avances` | 10 | 9 | `archivo_adjunto` |
| `logs_auditoria` | 8 | 6 | `valor_anterior`, `valor_nuevo` |
| `equipos_miembros` | 3 | 2 | `id` (PK de la tabla intermedia) |
| `perfil_desarrollador` | 19 | 8 | `condicion_sena`, `telefono`, `calificacion_promedio`, `estado_verificacion`, `ficha_sena_id` (FK), `documento_soporte`, `fecha_solicitud_verificacion`, `fecha_verificacion`, `verificado_por_id` (FK), `notas_auditoria`, `dictamen_ia` |
| `perfil_empresa` | 22 | 10 | `stack_interes`, `tipo_persona`, `tipo_documento`, `numero_documento`, `digito_verificacion`, `razon_social`, `documento_soporte`, `estado_verificacion`, `fecha_solicitud_verificacion`, `fecha_verificacion`, `verificado_por_id` (FK), `notas_auditoria`, `dictamen_ia` |

Correspondencia con el historial del repo:

| Campo | Commit que lo introdujo | Fecha |
|---|---|---|
| `bloqueado_por_intentos` | fix(auth): persistir bloqueado_por_intentos… (SCRUM-158) | 2026-10-10 |
| `archivo_adjunto` | feat(avances): subida de archivos adjuntos reales (SCRUM-64) | 2026-10-15 |
| `condicion_sena` | feat(usuarios): condicion_sena y badges SENA (SCRUM-154) | 2026-10-15 |
| `estado_verificacion` y bloque de verificación | feat(usuarios): ampliar PerfilEmpresa… (SCRUM-154) | 2026-10-11 |
| `fecha_limite_negociacion` | feat(contrataciones): ContratoDigital… (SCRUM-150, 151) | 2026-10-11 |
| `motivo_cancelacion`, `valor_anterior`, `valor_nuevo` | feat(backend): guardas de estado y trazabilidad (SCRUM-220/221/223/224/233) | 2026-10-24 |
| `modalidad`, `ciudad` | feat(proyectos): modalidad operativa y ciudad | 2026-10-31 |
| `stack_interes` | fix(usuarios): preservar stack_interes… (migración 0022) | 2026-11-06 |

Conclusión: el diagrama refleja el estado del esquema **anterior al 10 de octubre
de 2026**; todo lo añadido desde entonces no está representado.

## 3. Tablas que coinciden exactamente (9)

`copias_seguridad`, `equipos`, `favoritos`, `historial_estado_proyecto`,
`mensajes`, `notificaciones`, `valoraciones` y —con salvedad de nomenclatura—
`usuarios` y `proyectos`. Son las de menor riesgo: o no han cambiado, o solo
cambiaron campos listados arriba.

## 4. Problemas de nomenclatura en el diagrama

| Diagrama | ORM | Acción |
|---|---|---|
| `data_joined` | `date_joined` | errata (falta la "e") |
| `historial_estado` | `historial_estado_proyecto` | el nombre real de la tabla difiere |
| `descripción` (proyectos, avances) | `descripcion` | tilde en el nombre de columna; inconsistente con `descripcion` en `entregables` y `perfil_empresa` |

## 5. Defectos de dibujo (no del modelo)

1. **14 de 123 atributos (11%) están dibujados sin conector a su entidad.** Se
   resolvieron por proximidad: `proyectos` (estado, fecha_limite, empresa_id FK),
   `perfil_desarrollador` (ficha, id PK, habilidades, num_proyectos_completados),
   `perfil_empresa` (foto_perfil, portafolio_url, calificacion_promedio, logo),
   `postulaciones` (mensaje, fecha), `avances` (fecha_hora). Las dos de
   `postulaciones` sí existen en el modelo (`mensaje` TextField, `fecha`
   DateTimeField auto_now_add): el único defecto es que están dibujadas sueltas,
   sin conector a la entidad.
2. **`calificacion_promedio` aparece dos veces** en `perfil_empresa`. Una de las
   dos copias pertenece realmente a `perfil_desarrollador` (que sí tiene el campo
   en el ORM), donde el diagrama no la muestra.
3. Los dos perfiles (`perfil_empresa`, `perfil_desarrollador`) están a **85 px de
   distancia**, lo que impide atribuir por posición qué atributo es de cuál; se
   desambigüaron con evidencia del ORM.
4. No hay PK `id` dibujada en `equipos_miembros` (la tabla intermedia M2M sí la
   tiene en el ORM).

## 6. FKs del ORM sin representación en el diagrama

| Tabla | FK | Apunta a |
|---|---|---|
| `proyectos` | `categoria_id` | `categorias_solucion` |
| `entregables` | `desarrollador_id` | `usuarios` |
| `perfil_desarrollador` | `ficha_sena_id` | `fichas_sena` |
| `perfil_desarrollador` | `verificado_por_id` | `usuarios` |
| `perfil_empresa` | `verificado_por_id` | `usuarios` |

No hay FKs al revés: ningún campo marcado `(FK)` en el diagrama deja de ser FK en
el ORM. Las cardinalidades 1:N dibujadas son coherentes con las 17 tablas
existentes, pero incompletas por lo anterior.

## 7. Recomendación de actualización

Orden sugerido para regenerar el diagrama:

1. Añadir las 6 tablas ausentes con sus FKs (`disputas` → `proyectos`/`usuarios`,
   `mensajes_disputa` → `disputas`, `contratos_digitales` → `contrataciones`,
   `categorias_solucion` ← `proyectos.categoria_id`, `fichas_sena` ←
   `perfil_desarrollador.ficha_sena_id`, `excepciones_ficha_sena`).
2. Completar los dos perfiles (24 campos entre ambos) — es el bloque más grande y
   el más expuesto comercialmente (verificación de identidad y SENA).
3. Corregir las 3 erratas de la sección 4 y el duplicado de
   `calificacion_promedio`.
4. Conectar los 14 atributos flotantes o eliminarlos si son restos obsoletos.
5. Añadir la PK `id` a `equipos_miembros`.

Alternativa más sostenible que mantener el dibujo a mano: generar el diagrama
desde el propio ORM (script de introspección → `.drawio`/Mermaid) y versionarlo en
`docs/`, de modo que cada migración nueva pueda regenerarlo.

## 8. Artefacto generado (implementado)

La alternativa del punto 7 ya está implementada y ejecutada:

| Archivo | Contenido |
|---|---|
| `scripts/generate_er_drawio.py` | Generador: introspección del ORM → `.drawio` (XML sin comprimir) |
| `docs/ER_JOBDEVS.drawio` | Modelo físico: tablas con PK/FK dentro y flechas de FK |
| `docs/ER_JOBDEVS.png` / `.svg` | Export vigente del modelo físico; SVG recomendado para lectura con zoom |
| `docs/ER_JOBDEVS_chen.drawio` | Modelo conceptual Chen vigente: 28 entidades, 251 atributos y 55 relaciones |
| `docs/ER_JOBDEVS_chen.png` | Export anterior; pendiente regenerar desde la fuente Chen vigente |

Uso:

```
.venv/bin/python scripts/generate_er_drawio.py                       # modelo físico
.venv/bin/python scripts/generate_er_drawio.py --notacion chen        # modelo Chen
.venv/bin/python scripts/generate_er_drawio.py --notacion chen --check # CI
.venv/bin/python scripts/generate_er_drawio.py --con-auth             # + tablas de auth
```

Notas sobre el Chen: los atributos van en dos columnas flanqueando cada entidad
(no en abanico) para que 216 elipses quepan sin solaparse; la PK se subraya y las
columnas foráneas se marcan `(FK)`. Cada FK se dibuja como un rombo con `N` del
lado que guarda la FK y `1` del lado referenciado (1:1 en los OneToOne). Las
relaciones de un mismo par de entidades se reparten en carriles y los puertos se
distribuyen por el perímetro para que las cardinalidades no se apilen. Limitación
conocida: draw.io no evita obstáculos en el ruteo ortogonal, así que algunas
líneas largas cruzan por encima de tablas/elipses intermedias; el modelo es
correcto y legible a 100 %, pero para imprimir conviene mover bloques a mano.

Verificaciones ejecutadas:

- **Ida y vuelta actual**: ambos `.drawio` se regeneraron y `--check` confirmó 28/28 tablas/entidades, 251/251 columnas/atributos y 55/55 FK/relaciones, **0 diferencias**.
- **Determinismo**: dos corridas seguidas producen el mismo SHA-256.
- **`--check`**: alterando una columna del archivo, el comando sale con código 1
  y señala la desincronización.
- **Render real físico**: exportado con draw.io desktop 32.6.10 a PNG/SVG; se comprobó visualmente que tablas, cabeceras, marcas PK/FK y aristas no tienen recortes ni superposiciones graves. El render Chen actual queda pendiente por el fallo headless indicado en la actualización.

El PNG manual auditado (`/home/mrdylan/Descargas/ER.drawio.png`) queda superado
por este artefacto: no conviene seguir editando el dibujo a mano.

