#!/bin/bash
# ============================================================
# TEIR - Docker Entrypoint
# Inicializacion automatica del contenedor web
# ============================================================

set -e

echo "============================================"
echo "  TEIR - Iniciando aplicacion..."
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
python manage.py createcachetable || true
echo "[OK] Migraciones aplicadas correctamente"

# ---- 3. Recoger archivos estaticos ----
echo ""
echo "Recolectando archivos estaticos..."
python manage.py collectstatic --noinput
echo "[OK] Archivos estaticos recolectados"

# ---- 4. Iniciar Gunicorn ----
echo ""
echo "============================================"
echo "  TEIR listo - Iniciando Gunicorn"
echo "  Escuchando en 0.0.0.0:8000"
echo "  Workers: 3"
echo "============================================"
echo ""

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class gthread \
    --threads 2 \
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
