#!/bin/bash
# ============================================================
# JobDevs - Planificador del respaldo diario de la base de datos (RNF-14)
# ============================================================
# Contenedor de un solo propósito: ejecuta `manage.py backup_db` todos los días
# a la hora configurada (UTC) y, opcionalmente, un respaldo inmediato al
# arrancar.
#
# Por qué no hay un demonio cron: la imagen corre con un usuario no-root
# (appuser) y cron requiere privilegios de root. Este contenedor hace una sola
# cosa, así que un bucle de espera cumple la misma función, hereda el entorno
# del contenedor (sin credenciales en disco) y registra todo en stdout, visible
# con `docker compose logs backup`.
#
# Variables de entorno:
#   BACKUP_HOUR    hora del respaldo diario, 0-23 (por defecto 3)
#   BACKUP_MINUTE  minuto del respaldo diario, 0-59 (por defecto 0)
#   BACKUP_ON_START  1 para respaldar al arrancar el contenedor (por defecto 0)
set -euo pipefail

HORA="${BACKUP_HOUR:-3}"
MINUTO="${BACKUP_MINUTE:-0}"

log() {
    echo "[$(date -Is)] $*"
}

ejecutar_respaldo() {
    log "Ejecutando respaldo de la base de datos..."
    if python manage.py backup_db; then
        log "Respaldo finalizado correctamente"
    else
        # No se aborta el contenedor: un respaldo fallido se registra en
        # CopiaSeguridad y en los logs, y el programador sigue activo para el
        # siguiente intento.
        log "ERROR: el respaldo falló (revise los mensajes anteriores)" >&2
    fi
}

log "Planificador de respaldos iniciado (diario a las ${HORA}:${MINUTO} UTC)"

if [ "${BACKUP_ON_START:-0}" = "1" ]; then
    ejecutar_respaldo
fi

while true; do
    ahora="$(date +%s)"
    objetivo="$(date -d "today ${HORA}:${MINUTO}" +%s)"
    if [ "$objetivo" -le "$ahora" ]; then
        objetivo="$(date -d "tomorrow ${HORA}:${MINUTO}" +%s)"
    fi
    espera=$(( objetivo - ahora ))
    log "Próximo respaldo en ${espera}s (hoy/mañana a las ${HORA}:${MINUTO} UTC)"
    sleep "$espera"
    ejecutar_respaldo
done
