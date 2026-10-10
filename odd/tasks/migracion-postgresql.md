# Feature: Migración a PostgreSQL

## Contexto
Migración del motor de base de datos de MySQL 8.0 a PostgreSQL 16 para TEIR.
Esta migración atiende y resuelve directamente los hallazgos críticos de seguridad (SCRUM-157, SCRUM-135, SCRUM-147), elimina hacks frágiles de runtime (pymysql version spoofing) y prepara la arquitectura para transacciones ACID robustas.

## Tareas

- [ ] **Tarea 1: Actualizar dependencias y `.gitignore`**
  - Reemplazar `pymysql` por `psycopg[binary]>=3.2` en `requirements.txt`.
  - Asegurar `.venv/`, `postgres_data/`, `staticfiles/`, `*.log` en `.gitignore`.
  - Evidencia esperada: `requirements.txt` y `.gitignore` actualizados; dependencias instaladas.

- [ ] **Tarea 2: Configurar Django para PostgreSQL**
  - Remover el monkeypatch de PyMySQL en `config/settings.py`.
  - Configurar `DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'` con puerto por defecto `5432`.
  - Ajustar `config/settings_test.py` para soportar `DB_ENGINE=postgresql` y conservar SQLite in-memory para tests rápidos.
  - Evidencia esperada: `settings.py` y `settings_test.py` sin referencias a PyMySQL; arranque de Django sin advertencias de driver.

- [ ] **Tarea 3: Actualizar infraestructura Docker y entrypoint**
  - Cambiar el servicio `db` en `docker-compose.yml` de `mysql:8.0` a `postgres:16-alpine`.
  - Configurar variables `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` y volumen `postgres_data`.
  - Actualizar healthcheck a `pg_isready -U ${DB_USER:-postgres}`.
  - Adaptar `docker/entrypoint.sh` para verificar conectividad con PostgreSQL.
  - Actualizar `docker/.env.docker.example`.
  - Evidencia esperada: Archivos de Docker actualizados y coherentes con PostgreSQL.

- [ ] **Tarea 4: Desacoplar `init.sql` y crear seeding anónimo**
  - Desacoplar `database/init.sql` del compose para evitar siembra de PII y credenciales comprometidas.
  - Proporcionar mecanismo de inicialización limpio basado en `python manage.py migrate` y fixtures/seed anónimos si se requieren datos iniciales.
  - Evidencia esperada: Base de datos parte de esquema limpio vía migraciones.

- [ ] **Tarea 5: Verificación de migraciones y suite de pruebas**
  - Validar generación/aplicación de migraciones de Django sin errores.
  - Ejecutar la suite completa de pruebas con pytest para garantizar regresión cero.
  - Evidencia esperada: Tests pasando y reporte limpio de ejecución.
