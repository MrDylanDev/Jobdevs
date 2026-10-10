# Feature: Migración a PostgreSQL

## Contexto
Migración del motor de base de datos de MySQL 8.0 a PostgreSQL 16 para TEIR.
Esta migración atiende y resuelve directamente los hallazgos críticos de seguridad (SCRUM-157, SCRUM-135, SCRUM-147), elimina hacks frágiles de runtime (pymysql version spoofing) y prepara la arquitectura para transacciones ACID robustas.

## Tareas

- [x] **Tarea 1: Actualizar dependencias y `.gitignore`**
  - Reemplazar `pymysql` por `psycopg[binary]>=3.2` en `requirements.txt`.
  - Asegurar `.venv/`, `postgres_data/`, `staticfiles/`, `*.log` en `.gitignore`.
  - Evidencia: Commit `2389609`. Instalación limpia de psycopg 3.3.6 y psycopg-binary.

- [x] **Tarea 2: Configurar Django para PostgreSQL**
  - Remover el monkeypatch de PyMySQL en `config/settings.py`.
  - Configurar `DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'` con puerto por defecto `5432`.
  - Ajustar `config/settings_test.py` para soportar `DB_ENGINE=postgresql` y conservar SQLite in-memory para tests rápidos.
  - Evidencia: Commit `5c82e5b`. `python manage.py check` pasa con 0 errores.

- [x] **Tarea 3: Actualizar infraestructura Docker y entrypoint**
  - Cambiar el servicio `db` en `docker-compose.yml` de `mysql:8.0` a `postgres:16-alpine`.
  - Configurar variables `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` y volumen `postgres_data`.
  - Actualizar healthcheck a `pg_isready -U ${DB_USER:-postgres}`.
  - Adaptar `docker/entrypoint.sh` para verificar conectividad con PostgreSQL vía `psycopg`.
  - Evidencia: Commit `d36db44`. `docker compose config` válido y sin errores.

- [x] **Tarea 4: Desacoplar `init.sql` y crear seeding anónimo**
  - Desacoplar `database/init.sql` del compose para evitar siembra de PII y credenciales comprometidas.
  - Proporcionar mecanismo de inicialización limpio basado en `python manage.py migrate` y comando `seed_demo_data` sin PII.
  - Adaptar `usuarios/checks.py` para ignorar triggers SQL cuando no se usa backend MySQL.
  - Evidencia: Commit `7895eca`. Pruebas unitarias en `test_seed.py` pasando al 100%.

- [ ] **Tarea 5: Verificación de migraciones y suite de pruebas**
  - Validar generación/aplicación de migraciones de Django sin errores.
  - Ejecutar la suite completa de pruebas con pytest para garantizar regresión cero.
  - Evidencia esperada: Tests pasando y reporte limpio de ejecución.
