# ============================================================
# TEIR - Dockerfile Multi-Stage
# Proyecto Django + MySQL (PyMySQL) + Gunicorn
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
RUN uv venv /opt/venv && \
    uv sync --frozen --no-dev --no-install-project


# -------------------- STAGE 2: Production --------------------
FROM python:3.14-slim AS production

# Metadatos de la imagen
LABEL maintainer="TEIR Team"
LABEL description="TEIR - Plataforma de Gestión de Proyectos"
LABEL version="1.0"

# Evitar prompts interactivos y configurar Python
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

# Instalar dependencias mínimas de runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    curl \
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
RUN mkdir -p /app/staticfiles /app/media/perfiles && \
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
