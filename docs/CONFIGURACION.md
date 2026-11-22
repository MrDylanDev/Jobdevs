# Configuración de JobDevs

## Reglas

- `.env` no se versiona.
- Los ejemplos usan marcadores, nunca secretos reales.
- Un valor predeterminado de desarrollo no implica que sea seguro en producción.
- Variables booleanas se interpretan como la cadena exacta `True` o como indica el módulo.
- Después de cambiar configuración se ejecutan checks y un smoke test del recorrido afectado.

## Django

| Variable | Requerida | Predeterminado | Sensible | Uso |
|---|---:|---|---:|---|
| `DJANGO_SECRET_KEY` | Sí fuera de debug | ninguno | Sí | Firma criptográfica de Django. |
| `DJANGO_DEBUG` | No | `False` | No | Habilita debug; debe ser `False` en producción. |
| `DJANGO_ALLOWED_HOSTS` | Sí en despliegue | `localhost,127.0.0.1` | No | Hosts separados por coma. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Según proxy/dominio | vacío | No | Orígenes completos separados por coma. |
| `DJANGO_SETTINGS_MODULE` | No | `config.settings` según proceso | No | Módulo de settings. |

## Base de datos

| Variable | Predeterminado | Sensible | Nota |
|---|---|---:|---|
| `DB_ENGINE` | `django.db.backends.postgresql` | No | SQLite solo para pruebas/locales específicas. |
| `DB_NAME` | `teir_db` | No | Base de aplicación. |
| `DB_USER` | `postgres` en settings | Sí operacional | Compose usa `teir_user` si no se define. |
| `DB_PASSWORD` | `postgres` en settings | Sí | Debe reemplazarse; no depender del default. |
| `DB_HOST` | `127.0.0.1` | No | Compose usa `db`. |
| `DB_PORT` | `5432` | No | Compose publica host 5433, pero la red interna usa 5432. |
| `DB_CONN_MAX_AGE` | `60` | No | Reutilización de conexiones. |

Para pruebas PostgreSQL: `USE_POSTGRES=1` o `USE_POSTGRESQL=1`; alternativamente `TEST_DB=postgres`.

## Redis, caché y Channels

| Variable | Predeterminado | Uso |
|---|---|---|
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Caché, channel layer y base para Celery. |
| `DJANGO_CACHE_BACKEND` | `redis` con PostgreSQL; `locmem` en otros casos | Selección de caché. |
| `USE_REDIS_CHANNEL_LAYER` | Depende del backend | `1` habilita Channels sobre Redis. |

En Compose, `REDIS_URL=redis://redis:6379/0`.

## Celery

| Variable | Predeterminado | Uso |
|---|---|---|
| `CELERY_BROKER_URL` | `REDIS_URL` | Cola de tareas. |
| `CELERY_RESULT_BACKEND` | `REDIS_URL` | Resultados. |

El Compose ejecuta `celery -A config worker -B -l info`. Producción debería separar Beat para evitar duplicados al escalar workers.

## Email

| Variable | Predeterminado | Sensible |
|---|---|---:|
| `EMAIL_BACKEND` | SMTP backend | No |
| `EMAIL_HOST` | `smtp.gmail.com` | No |
| `EMAIL_PORT` | `587` | No |
| `EMAIL_USE_TLS` | `True` | No |
| `EMAIL_HOST_USER` | vacío | Sí |
| `EMAIL_HOST_PASSWORD` | vacío | Sí |
| `DEFAULT_FROM_EMAIL` | `JobDevs <noreply@jobdevs.edu.co>` | No |

Compose sustituye host/puerto/backend por Mailpit para desarrollo.

## HTTPS y cookies

| Variable | Predeterminado | Recomendación |
|---|---|---|
| `DJANGO_SECURE_SSL_REDIRECT` | `False` | `True` cuando TLS efectivo esté validado. |
| `DJANGO_SESSION_COOKIE_SECURE` | `False` | `True` con HTTPS. |
| `DJANGO_CSRF_COOKIE_SECURE` | `False` | `True` con HTTPS. |
| `DJANGO_SECURE_HSTS_SECONDS` | no definido | Aumentar gradualmente después de validar dominios. |
| `DJANGO_SECURE_PROXY_SSL_HEADER` | `False` | Solo detrás de proxy que reescriba y controle el header. |

No activar HSTS preload sin revisar subdominios y recuperación. Ejecutar `manage.py check --deploy` con valores reales.

## Logging

| Variable | Predeterminado | Uso |
|---|---|---|
| `DJANGO_LOG_FILE` | `var/log/jobdevs.log` | Archivo de aplicación. |
| `DJANGO_LOG_LEVEL` | `INFO` | Nivel general. |
| `USUARIOS_LOG_LEVEL` | `INFO` | Nivel del módulo usuarios. |

Los logs no deben incluir contraseñas, tokens, URLs prefirmadas, documentos completos ni mensajes confidenciales. Definir rotación, retención y acceso en el entorno.

## Respaldos y recuperación

| Variable | Predeterminado | Uso |
|---|---|---|
| `DJANGO_BACKUP_DIR` | `backups` | Directorio de dumps. |
| `BACKUP_HOUR` | `3` | Hora UTC del scheduler Docker. |
| `BACKUP_MINUTE` | `0` | Minuto. |
| `BACKUP_ON_START` | `0` | `1` ejecuta al iniciar. |
| `BACKUP_RETENTION_DAILY_DAYS` | `7` | Capa diaria completa. |
| `BACKUP_RETENTION_TOTAL_DAYS` | `30` | Antigüedad máxima. |
| `DB_RECOVERY_TARGET_SECONDS` | `300` | Objetivo RNF-14. |
| `PG_DUMP_BIN` | `pg_dump` | Binario de respaldo. |
| `PG_RESTORE_BIN` | `pg_restore` | Binario de integridad/restauración. |

El cliente PostgreSQL debe ser compatible con la versión mayor del servidor.

## Cloudflare R2

| Variable | Predeterminado | Sensible |
|---|---|---:|
| `CLOUDFLARE_R2_ACCOUNT_ID` | vacío | Sí operacional |
| `CLOUDFLARE_R2_ACCESS_KEY_ID` | vacío | Sí |
| `CLOUDFLARE_R2_SECRET_ACCESS_KEY` | vacío | Sí |
| `CLOUDFLARE_R2_BUCKET_NAME` | vacío | Sí operacional |
| `CLOUDFLARE_R2_ENDPOINT_URL` | derivado cuando hay account ID | Sí operacional |
| `R2_UPLOAD_URL_EXPIRACION_SEGUNDOS` | `300` | No |
| `R2_DOWNLOAD_URL_EXPIRACION_SEGUNDOS` | `900` | No |

Sin credenciales completas, el servicio puede degradar a almacenamiento local. Esta degradación debe ser explícita en producción: no asumir que un archivo quedó privado solo porque R2 estaba planeado.

## Integraciones institucionales

| Variable | Predeterminado | Estado |
|---|---|---|
| `SENA_API_URL` | vacío | Pasarela opcional; el padrón interno sigue siendo el mecanismo local. |
| `DIAN_API_URL` | vacío | Cliente previsto; no equivale a consulta registral demostrada. |

No declarar integración con SOFIA Plus, RUES o DIAN sin credenciales, contrato, disponibilidad y evidencia real.

## Reglas funcionales configurables

- `ConfiguracionNegociacion.plazo_dias`: administrable en la base, default 7, rango 1–30; no es variable de entorno.
- `ConfiguracionReputacion.minimo_confianza`: singleton, default 5, rango técnico 1–100; cambio auditado.
- `PROYECTO_DIAS_ALERTA_RETRASO`: default 15 para alertas administrativas.

Las configuraciones de negocio persistidas no deben duplicarse como variables de entorno sin una política de precedencia.

## E2E y pruebas

| Variable | Uso |
|---|---|
| `E2E_BROWSERS` | Navegadores separados por coma. |
| `TMPDIR` | Salidas temporales de QA. |
| `USE_POSTGRES`, `USE_POSTGRESQL`, `TEST_DB` | Selección PostgreSQL en settings de prueba. |

## Checklist de cambio

1. Actualizar `.env.docker.example` si la variable es operable por el equipo.
2. Actualizar este documento y el runbook.
3. No escribir el secreto en commits o tickets.
4. Validar arranque sin la variable cuando sea opcional.
5. Validar fallo explícito cuando sea obligatoria.
6. Ejecutar checks y pruebas del servicio afectado.
7. Registrar la configuración efectiva sin revelar valores sensibles.
