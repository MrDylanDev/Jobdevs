"""Utilidades de respaldo y recuperación de la base de datos (RNF-14).

Este módulo concentra la lógica *pura* (sin acceso a la base de datos ni a
Django) para poder probarla de forma aislada:

* convención de nombres de los archivos de respaldo,
* cálculo del checksum de integridad (SHA-256),
* política de retención (capa diaria + capa semanal + purga).

Los archivos se nombran ``jobdevs_bd_AAAAMMDD_HHMMSS.dump`` y su marca de
tiempo está en **UTC**, igual que ``auto_now_add`` del modelo ``CopiaSeguridad``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from collections.abc import Iterable, Sequence
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

#: Prefijo de los archivos de respaldo.
BACKUP_PREFIX = "jobdevs_bd_"
#: Extensión de los respaldos (formato custom de pg_dump / volcado SQLite).
BACKUP_SUFFIX = ".dump"
#: Sufijo del archivo que guarda el checksum SHA-256.
CHECKSUM_SUFFIX = ".sha256"
#: Formato de la marca de tiempo incluida en el nombre.
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

#: Días de la capa diaria: se conservan todos los respaldos de la última semana.
DEFAULT_DAILY_DAYS = 7
#: Días totales de retención: más antiguos que esto se purgan.
DEFAULT_TOTAL_DAYS = 30

_NAME_RE = re.compile(
    rf"^{re.escape(BACKUP_PREFIX)}(\d{{8}}_\d{{6}}){re.escape(BACKUP_SUFFIX)}$"
)


def to_utc(moment: dt.datetime) -> dt.datetime:
    """Normaliza ``moment`` a UTC (los ingenuos se asumen ya en UTC)."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=dt.timezone.utc)
    return moment.astimezone(dt.timezone.utc)


def backup_filename(moment: dt.datetime) -> str:
    """Devuelve el nombre de archivo de respaldo para ``moment`` (siempre en UTC)."""
    return f"{BACKUP_PREFIX}{to_utc(moment).strftime(TIMESTAMP_FORMAT)}{BACKUP_SUFFIX}"


def checksum_filename(name: str) -> str:
    """Devuelve el nombre del archivo de checksum de un respaldo."""
    return f"{name}{CHECKSUM_SUFFIX}"


def is_backup_file(name: str) -> bool:
    """Indica si ``name`` sigue la convención de nombres de respaldo."""
    return _NAME_RE.match(name) is not None


def parse_backup_datetime(name: str) -> dt.datetime | None:
    """Extrae la marca de tiempo (UTC) del nombre de un respaldo.

    Devuelve ``None`` cuando el nombre no sigue la convención.
    """
    coincidencia = _NAME_RE.match(name)
    if coincidencia is None:
        return None
    try:
        ingenuo = dt.datetime.strptime(coincidencia.group(1), TIMESTAMP_FORMAT)
    except ValueError:  # pragma: no cover - protegido por la expresión regular
        return None
    return ingenuo.replace(tzinfo=dt.timezone.utc)


def sha256_of(path: Path, *, bloque: int = 1024 * 1024) -> str:
    """Calcula el SHA-256 de ``path`` leyéndolo por bloques."""
    digest = hashlib.sha256()
    with path.open("rb") as archivo:
        for trozo in iter(lambda: archivo.read(bloque), b""):
            digest.update(trozo)
    return digest.hexdigest()


def megabytes(size_bytes: int) -> Decimal:
    """Convierte bytes a MB con dos decimales (como ``CopiaSeguridad.tamano_mb``)."""
    return (Decimal(size_bytes) / Decimal(1024 * 1024)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def servicios_de_respaldo(directorio: Path) -> list[tuple[dt.datetime, Path]]:
    """Lista los respaldos de ``directorio`` como pares ``(fecha_utc, ruta)``."""
    entradas: list[tuple[dt.datetime, Path]] = []
    if not directorio.is_dir():
        return entradas
    for archivo in directorio.iterdir():
        if not archivo.is_file():
            continue
        momento = parse_backup_datetime(archivo.name)
        if momento is not None:
            entradas.append((momento, archivo))
    return entradas


def plan_retention(
    entries: Iterable[tuple[dt.datetime, Path]],
    now: dt.datetime,
    daily_days: int = DEFAULT_DAILY_DAYS,
    total_days: int = DEFAULT_TOTAL_DAYS,
) -> tuple[list[Path], list[Path]]:
    """Decide qué respaldos se conservan y cuáles se purgan (RNF-14).

    Política de retención:

    * **Capa diaria** (antigüedad <= ``daily_days``): se conservan todos.
    * **Capa semanal** (``daily_days`` < antigüedad <= ``total_days``): se
      conserva únicamente el respaldo más reciente de cada semana ISO.
    * **Purga** (antigüedad > ``total_days``): se eliminan.

    Con los valores por defecto (7 y 30 días) el resultado es como máximo
    7 respaldos diarios + 4 semanales, cubriendo el mes completo.

    Devuelve la tupla ``(conservar, purgar)`` con rutas.
    """
    if daily_days < 0 or total_days < 0:
        raise ValueError("Los días de retención no pueden ser negativos")
    if daily_days > total_days:
        raise ValueError("daily_days no puede ser mayor que total_days")

    conservar: list[Path] = []
    purgar: list[Path] = []
    semanales: dict[tuple[int, int], Path] = {}

    # De más reciente a más antiguo: el primero de cada semana ISO es el que se queda.
    ordenados = sorted(entries, key=lambda entrada: entrada[0], reverse=True)
    for momento, ruta in ordenados:
        antiguedad = (now - momento).total_seconds() / 86400
        if antiguedad > total_days:
            purgar.append(ruta)
        elif antiguedad <= daily_days:
            conservar.append(ruta)
        else:
            clave = momento.isocalendar()[:2]
            if clave in semanales:
                purgar.append(ruta)
            else:
                semanales[clave] = ruta

    conservar.extend(semanales.values())
    return conservar, purgar


def ordenar_por_fecha(
    entradas: Sequence[tuple[dt.datetime, Path]],
) -> list[tuple[dt.datetime, Path]]:
    """Devuelve las entradas ordenadas de la más reciente a la más antigua."""
    return sorted(entradas, key=lambda entrada: entrada[0], reverse=True)
