# Contribuir a JobDevs

## Alcance

Estas reglas aplican a cambios de código, migraciones, pruebas, configuración, documentación y diagramas. No autorizan commit, push, despliegue o acceso a producción fuera del proceso acordado.

## Preparación

```bash
uv sync --extra dev
cp docker/.env.docker.example .env
```

Nunca usar secretos reales en fixtures, documentación, capturas o mensajes. Los valores de ejemplo se escriben como `<PASSWORD>`, `<TOKEN>` o `[REDACTED]`.

## Flujo de trabajo

1. Leer requisito, decisión y código relacionado.
2. Identificar permisos, estados, datos históricos y efectos secundarios.
3. Escribir o ajustar una prueba que falle por la razón esperada.
4. Implementar el cambio mínimo.
5. Ejecutar prueba focalizada.
6. Ejecutar pruebas relacionadas y checks.
7. Actualizar documentación, migraciones y diagramas afectados.
8. Revisar diff y excluir cambios ajenos.
9. Solicitar revisión antes de integrar.

## Arquitectura

- Vistas: autenticación básica, parseo, respuesta y delegación.
- Policies: autorización de actor y objeto.
- Services: reglas de negocio, transacciones, locks y efectos.
- Modelos/constraints: invariantes persistentes.
- Templates/JavaScript: presentación; nunca autoridad final de permisos.

Una operación que toca varias tablas o consume vacantes/estados debe usar transacción y, cuando aplique, `select_for_update` sobre la fila que gobierna el recurso.

## Pruebas

```bash
# Focalizada
uv run pytest ruta/al/test.py::TestClase::test_caso -q --tb=short

# Suite predeterminada
uv run pytest -q --tb=short

# E2E
uv run pytest -m e2e tests/e2e -q --tb=short

# Calidad
uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

Reglas:

- No debilitar una aserción para obtener verde.
- Probar autorización, estados inválidos, rollback y efectos secundarios.
- Para locks/concurrencia, usar PostgreSQL real.
- Un E2E que pasa aserciones pero falla en teardown no cuenta como salida limpia.
- No sumar ejecuciones solapadas como si fueran casos únicos.
- Registrar entorno y checkout cuando se publiquen cifras.

## Migraciones

- No editar migraciones desplegadas.
- Revisar defaults y registros históricos.
- No inventar fechas o evidencia para backfills.
- Probar desde cero y actualización en PostgreSQL descartable.
- Definir respaldo y rollback.
- Actualizar [Migraciones y compatibilidad](docs/MIGRACIONES_Y_COMPATIBILIDAD.md) y ER.

## Seguridad y privacidad

- Autorizar por recurso, no solo por rol.
- No servir archivos privados desde rutas públicas.
- No registrar contraseñas, tokens, documentos completos ni chat confidencial.
- Tratar URL prefirmada como credencial temporal.
- Revisar revocación de sesiones y conexiones persistentes.
- Neutralizar contenido controlado por usuarios en CSV/HTML/exports.
- Consultar [Privacidad](docs/PRIVACIDAD_Y_TRATAMIENTO_DE_DATOS.md) y [Seguimiento de seguridad](docs/SEGUIMIENTO_HALLAZGOS_SEGURIDAD.md).

## Documentación

Actualizar según el cambio:

- decisiones y conciliación si cambia política;
- trazabilidad y casos si cambia criterio;
- guía de usuario si cambia experiencia;
- manual/API/configuración si cambia interfaz técnica;
- despliegue si cambia infraestructura;
- privacidad/seguridad si cambia dato o acceso;
- migraciones y ER si cambia esquema.

Los `.drawio`, `.docx`, `.pptx` y Markdown son fuentes. PDF/PNG/SVG se regeneran desde ellas. Un derivado que no se pudo regenerar debe marcarse como no vigente.

## Estilo y alcance

- Mantener estilo de archivos vecinos.
- No realizar refactors ajenos al objetivo.
- No renombrar rutas heredadas sin plan de compatibilidad.
- No añadir dependencia sin justificarla y actualizar `pyproject.toml`/lock.
- No mezclar correcciones funcionales con regeneraciones masivas sin explicarlas.

## Pull request

La descripción debe incluir:

- problema y criterio;
- decisión de producto relacionada;
- archivos/capas afectados;
- migraciones y compatibilidad;
- riesgos de seguridad/privacidad;
- comandos y resultados reales;
- capturas o aceptación visual cuando aplique;
- pendientes y límites;
- rollback.

Checklist:

- [ ] Prueba roja observada cuando aplica TDD.
- [ ] Pruebas focalizadas verdes.
- [ ] Regresión aplicable ejecutada.
- [ ] Ruff/checks correctos.
- [ ] Migraciones verificadas.
- [ ] Documentación actualizada.
- [ ] Sin secretos ni datos personales.
- [ ] `git diff --check` correcto.
- [ ] No se incluyeron cambios ajenos.

## Fuentes documentales

Comenzar por [Índice de documentación](docs/README.md). La matriz externa oficial permanece intacta; las excepciones aprobadas se documentan en [Decisiones de producto](docs/DECISIONES_PRODUCTO_APROBADAS.md).
