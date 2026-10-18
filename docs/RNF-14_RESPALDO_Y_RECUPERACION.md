# RNF-14 — Disponibilidad: recuperación de base de datos en menos de 5 minutos

Documento de referencia del requisito no funcional **RNF-14** del Proyecto
Formativo (JobDevs / TEIR).

- **Criterio de aceptación:** el esquema de la base de datos debe poder
  reconstruirse completo, en un servidor nuevo, en **menos de 5 minutos**.
- **Cumplimiento medido:** reconstrucción completa en **6,6 s** (límite 300 s).
- **Estado:** ✅ CUMPLE.

---

## 1. Qué se implementó

| Componente | Ubicación | Función |
| --- | --- | --- |
| Lógica de respaldos | `logs/backups.py` | Nombres de archivo en UTC, huella SHA-256, política de retención, registro de servicios de respaldo |
| Comando de respaldo | `logs/management/commands/backup_db.py` | Genera el volcado, verifica su integridad, calcula el checksum, aplica la retención y registra el resultado en `CopiaSeguridad` |
| Comando de verificación | `logs/management/commands/verify_db_recovery.py` | Reconstruye el esquema desde cero y/o restaura un respaldo en una base de datos nueva, midiendo el tiempo |
| Respaldos automáticos | `docker/backup/scheduler.sh`, servicio `backup` en `docker-compose.yml` | Respaldo diario automático con retención GFS |
| Verificación continua | `.github/workflows/ci.yml` (job `test-postgres`) | Bloquea el merge si el esquema no se reconstruye en menos de 5 minutos |
| Pruebas | `logs/tests/test_backups.py`, `logs/tests/test_backup_commands.py` | 36 pruebas: política de retención, comandos y contenido del volcado |

### Fuente de verdad del esquema

El esquema **no** se reconstruye con un archivo `Tem_bd.sql` (ya no existe en el
repositorio). La fuente de verdad son las **migraciones de Django** sobre
PostgreSQL 16, y por eso la verificación se hace con `manage.py migrate` y no
comparando un archivo SQL estático. Esto además resuelve el pendiente del
llamado de atención ("no hay verificación de que el archivo de esquema esté
actualizado"): las migraciones son ejecutables y su consistencia con los modelos
se comprueba con `makemigrations --check` en la integración continua.

---

## 2. Comandos

### 2.1 Respaldo

```bash
# Respaldo con la configuración del entorno (directorio BACKUP_DIR)
python manage.py backup_db

# Respaldo en un directorio concreto
python manage.py backup_db --output-dir /tmp/respaldos

# Ajustar la retención para una ejecución concreta
python manage.py backup_db --retention-daily-days 7 --retention-total-days 30

# Registrar quién ejecutó el respaldo
python manage.py backup_db --usuario "nombre.apellido"

# Ver qué haría el comando, sin generar ni eliminar archivos
python manage.py backup_db --dry-run

# Omitir la comprobación de integridad del volcado (no recomendado)
python manage.py backup_db --skip-integrity-check
```

Cada respaldo produce:

- `<base>_<fecha>_<hora>.dump` — volcado en formato personalizado (`pg_dump -Fc`);
- `<base>_<fecha>_<hora>.dump.sha256` — huella de integridad;
- una fila en la tabla `copias_seguridad` con fecha, tamaño, checksum, duración y
  estado (`completado` / `fallido`).

### 2.2 Verificación de la recuperación

```bash
# Reconstruir el esquema desde cero y medir (criterio del RNF-14)
python manage.py verify_db_recovery

# Igual que lo anterior, con resultado en JSON (para la integración continua)
python manage.py verify_db_recovery --json-out recuperacion-esquema.json

# Medir además la restauración de un respaldo real
python manage.py verify_db_recovery --desde-dump /ruta/al/respaldo.dump

# Fijar el objetivo en segundos (por defecto 300)
python manage.py verify_db_recovery --objetivo 300
```

La verificación crea una base de datos temporal, aplica las migraciones (o
restaura el volcado), cuenta las tablas creadas, mide el tiempo y **elimina la
base de datos temporal** al terminar. El comando devuelve código de salida
distinto de cero si no se cumple el objetivo, de modo que la integración
continua falla el trabajo en ese caso.

---

## 3. Automatización

El servicio `backup` del stack Docker ejecuta el respaldo todos los días a las
**03:00 UTC** y aplica esta política de retención (GFS simplificado):

| Antigüedad | Retención |
| --- | --- |
| Hasta 7 días | Se conservan **todos** los respaldos diarios |
| De 7 a 30 días | Se conserva **el más reciente de cada semana ISO** (cubre el mes completo) |
| Más de 30 días | Se eliminan automáticamente |

Configuración (variables de entorno, ver `.env`):

| Variable | Por defecto | Descripción |
| --- | --- | --- |
| `BACKUP_HOUR` | `3` | Hora del respaldo diario (UTC) |
| `BACKUP_MINUTE` | `0` | Minuto del respaldo diario |
| `BACKUP_ON_START` | `0` | `1` para respaldar también al arrancar el contenedor |
| `BACKUP_RETENTION_DAILY_DAYS` | `7` | Días con respaldo diario completo |
| `BACKUP_RETENTION_TOTAL_DAYS` | `30` | Antigüedad máxima conservada |
| `DJANGO_BACKUP_DIR` | `backups` | Directorio de respaldos |
| `DB_RECOVERY_TARGET_SECONDS` | `300` | Objetivo de recuperación en segundos (criterio del RNF-14) |

El planificador es un bucle de espera dentro del contenedor, no un demonio
`cron`: la imagen se ejecuta con un usuario sin privilegios (`appuser`) y `cron`
requiere root. El contenedor tiene un solo propósito, hereda las credenciales
del entorno (sin secretos escritos en disco) y registra todo en la salida
estándar, visible con `docker compose logs -f backup`.

---

## 4. Evidencia de las mediciones

Medición sobre PostgreSQL 16 real (contenedor `postgres:16-alpine`, 32 tablas de
la aplicación):

| Prueba | Resultado | Objetivo | Estado |
| --- | --- | --- | --- |
| Reconstrucción del esquema con `migrate` | **6,6 s** | < 300 s | ✅ CUMPLE |
| Restauración del respaldo en una base nueva | **1,2 s** | < 300 s | ✅ CUMPLE |
| Integridad del volcado (`pg_restore --list`) | 307 objetos | sin error | ✅ |
| Generación del respaldo | 1,1 s / 0,12 MB | — | ✅ |
| Eliminación de la base temporal tras la verificación | sin residuos | — | ✅ |
| Pruebas automatizadas | 36 pasaron, sin fallos | ✅ |

La comprobación se repite en cada ejecución de la integración continua (job
`test-postgres`), cuyos resultados quedan como artefactos
(`recuperacion-*.json`).

---

## 5. Nota para el equipo: versiones del cliente de PostgreSQL

El cliente (`pg_dump` / `pg_restore`) **debe ser de la misma versión mayor que el
servidor**. Un cliente más reciente genera volcados que el servidor 16 rechaza
al restaurar, por ejemplo por el parámetro `transaction_timeout`, que existe
desde PostgreSQL 17.

Por eso la imagen instala `postgresql-client-16` desde el repositorio PGDG en
lugar del cliente por defecto de la distribución. Si en algún momento se
actualiza la versión del servidor (`db` en `docker-compose.yml`), hay que
actualizar también el cliente en el `Dockerfile`.

---

## 6. Recuperación manual (procedimiento de emergencia)

```bash
# 1. Detener la aplicación para evitar escrituras
docker compose stop web

# 2. Copiar el respaldo desde el volumen
docker compose exec backup ls -lh /app/backups
docker compose cp backup:/app/backups/<archivo>.dump ./respaldo.dump

# 3. Restaurar sobre la base de datos
docker compose exec -T db pg_restore -U teir_user -d teir_db --clean --if-exists < respaldo.dump

# 4. Volver a levantar la aplicación
docker compose start web
```
