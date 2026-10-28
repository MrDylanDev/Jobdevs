#!/bin/bash
# ============================================================
# JobDevs - Docker Entrypoint
# Inicializacion automatica del contenedor web
# ============================================================

set -e

# ---- 0. Normalizar permisos del volumen ----
# Arrancamos como root SOLO para dejar el sistema de archivos como debe estar y
# bajamos privilegios antes de cualquier otra cosa. Asi collectstatic no depende
# de como se poblo el volumen (docker cp, corridas previas, restauraciones).
if [ "$(id -u)" -eq 0 ]; then
    mkdir -p /app/staticfiles /app/media /app/backups
    chown -R appuser:appuser /app/staticfiles /app/media /app/backups 2>/dev/null || true
    # HOME apunta al home de appuser: si queda en /root, gunicorn no puede crear
    # su control socket (~/.gunicorn) y ensucia el log con PermissionError.
    export HOME=/app
    exec setpriv --reuid=appuser --regid=appuser --init-groups "$0" "$@"
fi

echo "============================================"
echo "  JobDevs - Iniciando aplicacion..."
echo "============================================"

# ---- 1. Esperar a que PostgreSQL esté listo ----
echo ""
echo "Esperando conexión con PostgreSQL..."

MAX_RETRIES=30
RETRY_COUNT=0

while ! python -c "
import psycopg
conn = psycopg.connect(
    host='${DB_HOST:-db}',
    port=int('${DB_PORT:-5432}'),
    user='${DB_USER:-teir_user}',
    password='${DB_PASSWORD:-teir_password}',
    dbname='${DB_NAME:-teir_db}',
    connect_timeout=3
)
conn.close()
print('OK')
" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "[ERROR] No se pudo conectar a PostgreSQL después de $MAX_RETRIES intentos"
        exit 1
    fi
    echo "   Intento $RETRY_COUNT/$MAX_RETRIES - PostgreSQL no está listo, esperando 2s..."
    sleep 2
done

echo "[OK] Conexión con PostgreSQL establecida"

# ---- 2. Aplicar migraciones ----
echo ""
echo "Aplicando migraciones de Django..."
python manage.py migrate --noinput
echo "[OK] Migraciones aplicadas correctamente"

# ---- 3. Recoger archivos estaticos ----
echo ""
if [ ! -w /app/staticfiles ]; then
    echo "[ERROR] /app/staticfiles no es escribible por $(id -un)."
    echo "        Suele ocurrir cuando el volumen se poblo con archivos de otro usuario."
    echo "        Remedio: docker compose down && docker volume rm teir_static_files && docker compose up -d"
    exit 1
fi
echo "Recolectando archivos estaticos..."
python manage.py collectstatic --noinput
echo "[OK] Archivos estaticos recolectados"

# ---- 4. Iniciar Servicio ----
if [ $# -gt 0 ]; then
    echo ""
    echo "============================================"
    echo "  JobDevs listo - Ejecutando comando:"
    echo "  $@"
    echo "============================================"
    echo ""
    exec "$@"
fi

echo ""
echo "============================================"
echo "  JobDevs listo - Iniciando ASGI (Gunicorn + Uvicorn Workers)"
echo "  Escuchando en 0.0.0.0:8000"
echo "  Workers: 3 (Uvicorn)"
echo "============================================"
echo ""

exec gunicorn config.asgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-tmp-dir /dev/shm \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output
