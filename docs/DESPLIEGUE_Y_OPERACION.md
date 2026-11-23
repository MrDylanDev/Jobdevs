# Despliegue y operación de JobDevs

## Estado y alcance

Este documento es un runbook de referencia. El checkout actual no aporta evidencia de un despliegue de producción verificado. Los comandos deben adaptarse al proveedor, dominio, almacenamiento y política de secretos aprobados.

## 1. Roles operativos

Antes de desplegar se deben identificar:

- responsable de aprobar la versión;
- operador del despliegue;
- responsable de base de datos y respaldo;
- responsable de seguridad/incidentes;
- contacto de producto para smoke test y rollback.

No iniciar una ventana sin responsable de decisión y canal de comunicación.

## 2. Prerrequisitos

- imagen o commit identificable;
- documentación y migraciones revisadas;
- suite requerida y CI en estado conocido;
- respaldo reciente verificado fuera del host de aplicación;
- acceso al gestor de secretos sin copiar valores al chat o logs;
- dominio, DNS y certificado TLS;
- PostgreSQL 16 y cliente compatible;
- Redis disponible y no expuesto públicamente;
- almacenamiento privado para documentos/evidencias;
- proveedor SMTP;
- monitoreo, alertas y destino de logs;
- plan de rollback y ventana de mantenimiento.

## 3. Variables y secretos

Consultar [Configuración](CONFIGURACION.md). Como mínimo:

- `DJANGO_SECRET_KEY` de alta entropía;
- `DJANGO_DEBUG=False`;
- hosts y orígenes CSRF explícitos;
- credenciales PostgreSQL;
- Redis/Celery;
- SMTP;
- almacenamiento R2 si se habilita;
- endurecimiento HTTPS/cookies/HSTS;
- directorio y retención de respaldos.

Los secretos no se escriben en imágenes, Compose versionado, tickets, capturas ni documentos. Rotar cualquier valor expuesto.

## 4. Preflight

En un entorno de staging equivalente:

```bash
uv sync --frozen --extra dev
uv run ruff check .
uv run pytest -q --tb=short
uv run pytest -m e2e tests/e2e -q --tb=short
uv run python manage.py check
uv run python manage.py check --deploy
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --plan
```

Registrar resultados en [Estado de verificación actual](ESTADO_VERIFICACION_ACTUAL.md). Una ejecución SQLite no sustituye migraciones, locks, backup y recuperación sobre PostgreSQL.

## 5. Respaldo previo

```bash
python manage.py backup_db
python manage.py verify_db_recovery --desde-dump /ruta/al/respaldo.dump
```

Verificar:

- checksum;
- lectura con `pg_restore --list`;
- restauración en base aislada;
- ubicación fuera del host primario;
- fecha y responsable;
- tiempo de recuperación.

No aplicar migraciones si el único respaldo no ha sido verificado.

## 6. Despliegue de contenedores

Secuencia de referencia:

```bash
# Obtener la versión aprobada y construir sin imprimir secretos
docker compose build --pull

# Revisar configuración materializada sin imprimir secretos
docker compose config --quiet

# Servicios de datos
docker compose up -d db redis
docker compose ps

# Migraciones en una sola instancia controlada
docker compose run --rm web python manage.py migrate --noinput

# Estáticos
docker compose run --rm web python manage.py collectstatic --noinput

# Aplicación y procesos auxiliares
docker compose up -d web celery_worker backup nginx
```

El Compose del repositorio es de referencia local. Producción debería separar Beat del worker, usar servicios gestionados cuando corresponda y no exponer Mailpit.

## 7. Verificación posterior

Comprobar infraestructura:

```bash
curl -fsS https://<dominio>/health/
docker compose ps
docker compose logs --tail=200 web celery_worker nginx
```

Smoke test funcional con cuentas de prueba autorizadas:

1. iniciar sesión por cada rol;
2. abrir dashboards;
3. publicar y consultar un proyecto de prueba;
4. verificar notificación/correo de prueba;
5. comprobar acceso autorizado y denegado a un archivo privado;
6. probar conexión SSE y WebSocket detrás del proxy;
7. ejecutar una tarea Celery controlada;
8. verificar escritura y lectura en PostgreSQL;
9. confirmar que logs no exponen secretos ni tokens;
10. comprobar métricas y alertas.

No usar datos personales reales para el smoke test.

## 8. Criterios de rollback

Considerar rollback inmediato ante:

- migración fallida o inconsistencia de datos;
- errores 5xx sostenidos;
- autenticación/autorización rota;
- exposición de archivos o datos;
- tareas duplicadas por Beat;
- pérdida de conectividad con PostgreSQL/Redis;
- degradación severa o corrupción del contrato/firma;
- smoke test crítico fallido.

## 9. Rollback

### Aplicación sin migración destructiva

1. detener nuevas escrituras o poner mantenimiento;
2. volver a la imagen anterior identificada;
3. reiniciar web/worker;
4. repetir health check y smoke test;
5. conservar logs y evidencia del incidente.

### Migración incompatible

No ejecutar `migrate <app> <migración_anterior>` sin revisar `reversible` y la pérdida potencial. Opciones:

- migración correctiva hacia adelante;
- reversión Django solo si está probada y no pierde datos;
- restauración del respaldo en base aislada y cambio controlado;
- recuperación completa conforme a RNF-14.

La decisión requiere al responsable de base de datos y producto. Documentar RPO/RTO real.

## 10. Operación cotidiana

Diario:

- estado de web, PostgreSQL, Redis, worker y Beat;
- errores de aplicación/proxy;
- tareas fallidas;
- último respaldo y checksum;
- espacio de volúmenes;
- alertas de seguridad.

Semanal:

- prueba de restauración aislada según política;
- revisión de cuentas administrativas;
- revisión de logs de auditoría y anomalías;
- capacidad de disco/base/Redis;
- dependencias e imágenes con avisos.

Por versión:

- notas de cambio;
- migraciones;
- cambios de variables;
- documentación y diagramas;
- evidencia de pruebas;
- aceptación de producto cuando aplique.

## 11. Incidentes

Ante sospecha de exposición:

1. preservar evidencia y hora;
2. limitar acceso sin destruir logs;
3. rotar secretos comprometidos;
4. invalidar sesiones/tokens cuando corresponda;
5. identificar datos, usuarios y periodo afectados;
6. activar responsables legales y de seguridad;
7. restaurar servicio de forma controlada;
8. documentar causa raíz, impacto y acciones.

Consultar [Privacidad](PRIVACIDAD_Y_TRATAMIENTO_DE_DATOS.md) y [Seguimiento de seguridad](SEGUIMIENTO_HALLAZGOS_SEGURIDAD.md).

## 12. Registro de despliegue

| Campo | Valor |
|---|---|
| Fecha/hora y zona | Pendiente |
| Entorno | Pendiente |
| Commit/imagen | Pendiente |
| Responsable | Pendiente |
| Respaldo verificado | Pendiente |
| Migraciones aplicadas | Pendiente |
| Resultado de health check | Pendiente |
| Resultado de smoke test | Pendiente |
| Rollback requerido | Pendiente |
| Incidentes/observaciones | Pendiente |

Esta tabla es plantilla. No constituye evidencia hasta completarse durante una ejecución real.
