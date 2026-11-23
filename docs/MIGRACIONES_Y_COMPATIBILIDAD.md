# Migraciones y compatibilidad histórica

## 1. Fuente de verdad

El esquema de JobDevs se define por los modelos y migraciones Django. Los SQL históricos de `database/` no sustituyen `manage.py migrate` ni deben aplicarse sobre una base actual sin revisión.

PostgreSQL 16 es la base objetivo. SQLite sirve para pruebas rápidas, pero no demuestra locks de fila, concurrencia, tipos específicos ni restauración PostgreSQL.

## 2. Reglas de trabajo

- Nunca editar una migración ya desplegada para cambiar su significado.
- Generar una migración nueva y revisable.
- No usar `--fake` salvo procedimiento documentado y evidencia de que el esquema coincide.
- Respaldar y verificar recuperación antes de una migración de operación.
- Revisar datos legados, nulos, constraints y duración.
- Separar migración de esquema y backfill grande cuando reduzca riesgo.
- Validar ida y vuelta solo si la operación es realmente reversible.
- No ejecutar `makemigrations` automáticamente al arrancar producción.

## 3. Migraciones recientes relevantes

| App/migración | Propósito | Compatibilidad |
|---|---|---|
| `proyectos/0021_regularizacion_cierre_historico.py` | Fecha real de cierre para registros legados sin historial fiable | No inventa fecha; requiere decisión administrativa con motivo/evidencia |
| `proyectos/0022_proyecto_proyecto_origen.py` | Vínculo del proyecto sucesor al original | Nullable para proyectos existentes; `PROTECT` preserva la referencia |
| `proyectos/0023_configuracionreputacion.py` | Singleton de mínimo de confianza bayesiano | Default 5; cambios posteriores auditados por servicio |
| `postulaciones/0008_configuracionnegociacion.py` | Singleton de plazo global | Default 7 y rango 1–30; negociaciones existentes conservan su fecha absoluta |
| `contrataciones/0017_contratodigital_perfil_profesional.py` | Snapshot profesional contractual | Registros firmados legados deben conservar validación de hash histórica |
| `contrataciones/0018_solicitud_cancelacion.py` | Solicitud bilateral/revisable | No cancelar automáticamente contratos históricos |
| `contrataciones/0019_confirmacion_contraparte.py` | Confirmación inequívoca de contraparte | Registros existentes requieren default compatible |
| `disputas/0005_disputa_declara_evidencia_no_disponible.py` | Declaración explícita para fuerza mayor | Default falso para expedientes anteriores |
| `disputas/0006_disputa_evidencia_archivo.py` | Archivo privado de evidencia | Nullable; no reconstruye archivos históricos |
| `disputas/0007_alter_disputa_categoria.py` | Catálogo con causal de inactividad | Conserva valores existentes |

Los nombres anteriores fueron inventariados en el checkout. Su aplicación conjunta todavía debe verificarse en una base PostgreSQL descartable posterior a todos los cambios recientes.

## 4. Datos legados

### Cierre de proyectos

No usar `fecha_publicacion` como sustituto del cierre. Un proyecto finalizado sin transición fiable debe pasar por `RegularizacionCierreProyecto` con:

- fecha real sustentada;
- motivo;
- referencia de evidencia;
- actor administrativo;
- fecha de registro.

Consultar [Valoraciones históricas](VALORACIONES_HISTORICAS.md).

### Proyectos sucesores

- Los proyectos existentes tienen `proyecto_origen=NULL`.
- Continuar un finalizado crea una fila nueva.
- No cambiar el estado del original ni de sus contratos.
- No encadenar o duplicar sucesores sin una decisión explícita de negocio.

### Negociaciones

`Postulacion.fecha_limite_negociacion` es la fuente para cada negociación iniciada. Crear `ConfiguracionNegociacion` no recalcula fechas existentes. Cambiar el plazo global solo afecta nuevas negociaciones.

### Reputación

Agregar `ConfiguracionReputacion` no transforma automáticamente todas las métricas almacenadas o interfaces. Deben distinguirse:

- puntuaciones fuente;
- promedio simple;
- cantidad;
- promedio global por cohorte;
- reputación bayesiana;
- valor `m` vigente al calcular.

Antes de un backfill, definir si se persiste o se calcula en lectura y cómo se reproducen resultados históricos.

### Contratos firmados

Un snapshot nuevo no debe invalidar hashes legados. La serialización canónica debe aplicarse según la versión del contrato. Nunca reconstruir evidencia histórica con el perfil mutable actual.

### Disputas

Los campos de evidencia nuevos son opcionales para expedientes históricos. No inferir que una disputa antigua incumplía la política actual por no tener archivo o declaración.

## 5. Procedimiento de validación

### Antes

```bash
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py showmigrations --plan
uv run python manage.py migrate --plan
```

Revisar cada operación SQL esperada, constraints, defaults y dependencia entre apps.

### Base PostgreSQL descartable

1. Crear base vacía aislada.
2. Aplicar todas las migraciones desde cero.
3. Ejecutar `check` y pruebas relevantes.
4. Cargar una copia anonimizada o fixtures representativos.
5. Probar actualización desde el esquema anterior.
6. Verificar conteos, nulos, relaciones y restricciones.
7. Ejecutar smoke tests de lectura/escritura.
8. Eliminar la base aislada.

### Evidencia

Registrar:

- versión de PostgreSQL y cliente;
- checkout;
- plan de migración;
- duración;
- filas afectadas;
- warnings/errores;
- pruebas ejecutadas;
- rollback ensayado;
- responsable y fecha.

## 6. Despliegue

Orden de referencia:

1. detener o limitar escrituras si la migración lo exige;
2. obtener respaldo verificado;
3. desplegar código compatible hacia atrás cuando sea posible;
4. aplicar migración una sola vez;
5. ejecutar backfill idempotente si existe;
6. comprobar constraints y métricas;
7. habilitar procesos/worker;
8. smoke test;
9. retirar compatibilidad antigua en una versión posterior.

Para cambios grandes, preferir expandir → migrar datos → cambiar lecturas → contraer.

## 7. Rollback

Una migración marcada reversible puede seguir perdiendo información. Antes de revertir:

- leer `reverse_code`/operación inversa;
- comprobar dependencias aplicadas después;
- detener procesos que escriban el esquema nuevo;
- respaldar el estado fallido;
- ensayar en copia;
- decidir entre reversión, corrección hacia adelante o restauración.

La restauración completa se guía por [RNF-14](RNF-14_RESPALDO_Y_RECUPERACION.md) y [Despliegue y operación](DESPLIEGUE_Y_OPERACION.md).

## 8. Checklist de nueva migración

- [ ] Modelo y migración coinciden.
- [ ] Default y nullabilidad son compatibles con datos existentes.
- [ ] Índices/constraints tienen costo revisado.
- [ ] Backfill es idempotente y por lotes si aplica.
- [ ] No se inventan hechos históricos.
- [ ] Pruebas cubren registros nuevos y legados.
- [ ] PostgreSQL descartable fue ejercitado.
- [ ] Respaldo y rollback están definidos.
- [ ] ER y diccionario técnico se regeneraron.
- [ ] Documentación y trazabilidad se actualizaron.
