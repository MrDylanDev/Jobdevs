# ============================================================
# JobDevs - Dockerfile Multi-Stage
# Proyecto Django + PostgreSQL 16 + Gunicorn
# ============================================================

# -------------------- STAGE 1: Builder --------------------
FROM python:3.14-slim AS builder

# Instalar binario oficial de uv desde su imagen
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Evitar prompts interactivos y optimizaciones de uv
ENV DEBIAN_FRONTEND=noninteractive \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Instalar dependencias del sistema necesarias para compilar paquetes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /build

# Copiar archivos de dependencias e instalar con uv en /opt/venv
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv sync --frozen --no-dev --no-install-project


# -------------------- STAGE 2: Production --------------------
FROM python:3.14-slim AS production

# Metadatos de la imagen
LABEL maintainer="JobDevs Team"
LABEL description="JobDevs - Plataforma de Gestión de Proyectos"
LABEL version="1.0"

# Evitar prompts interactivos y configurar Python
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

# Instalar dependencias mínimas de runtime
#
# RNF-14: se instala el cliente de PostgreSQL 16 (pg_dump/pg_restore) desde PGDG
# para que su versión coincida con el servidor del stack (postgres:16-alpine).
# Un cliente de versión mayor genera respaldos que un servidor 16 no puede
# restaurar (por ejemplo el parámetro "transaction_timeout", que existe desde
# PostgreSQL 17), y eso rompería la recuperación.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    curl \
    ca-certificates \
    gnupg \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(. /etc/os-release && echo $VERSION_CODENAME)-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client-16 \
    && apt-get purge -y --auto-remove gnupg \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Directorio de trabajo
WORKDIR /app

# Copiar el venv desde el builder
COPY --from=builder /opt/venv /opt/venv

# Copiar el código de la aplicación
COPY . .

# Copiar y configurar el entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Crear directorios necesarios con permisos correctos
# /app/backups es el punto de montaje del volumen de respaldos (RNF-14); se crea
# con el propietario del usuario de la aplicación para que el volumen lo herede.
RUN mkdir -p /app/staticfiles /app/media/perfiles /app/backups && \
    chown -R appuser:appuser /app

# Asegurar permisos en directorios de runtime
RUN chown -R appuser:appuser /app/staticfiles /app/media

# Cambiar al usuario no-root
USER appuser

# Exponer el puerto de Gunicorn
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]
