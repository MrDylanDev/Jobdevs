"""Respaldo de la base de datos con verificación de integridad y rotación (RNF-14).

Genera un respaldo, comprueba que el archivo sea restaurable, guarda su
checksum SHA-256, aplica la política de retención y registra el resultado en
el modelo ``CopiaSeguridad`` (app ``logs``).

Ejemplos::

    python manage.py backup_db
    python manage.py backup_db --output-dir /var/respaldos --usuario admin
    python manage.py backup_db --dry-run
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import time
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.utils import timezone

from logs import backups
from logs.models import CopiaSeguridad

#: Longitud máxima de ``CopiaSeguridad.archivo_url``.
LIMITE_ARCHIVO_URL = 500


class Command(BaseCommand):
    help = (
        "Genera un respaldo de la base de datos, verifica su integridad, "
        "aplica la política de retención y registra el resultado en "
        "CopiaSeguridad (RNF-14)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            dest="output_dir",
            default=None,
            help="Directorio destino de los respaldos (por defecto settings.BACKUP_DIR).",
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Alias de la conexión a respaldar (por defecto 'default').",
        )
        parser.add_argument(
            "--retention-daily-days",
            dest="daily_days",
            type=int,
            default=None,
            help="Días de la capa diaria; dentro de este rango se conservan todos "
            "(por defecto settings.BACKUP_RETENTION_DAILY_DAYS).",
        )
        parser.add_argument(
            "--retention-total-days",
            dest="total_days",
            type=int,
            default=None,
            help="Días totales de retención; lo más antiguo se purga "
            "(por defecto settings.BACKUP_RETENTION_TOTAL_DAYS).",
        )
        parser.add_argument(
            "--usuario",
            default=None,
            help="Username que se registra en CopiaSeguridad.ejecutado_por.",
        )
        parser.add_argument(
            "--skip-integrity-check",
            dest="skip_integrity",
            action="store_true",
            help="Omite la verificación de que el archivo generado sea restaurable.",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="No genera ni elimina archivos: solo informa qué haría.",
        )

    def handle(self, *args, **options):
        daily_days = (
            options["daily_days"]
            if options["daily_days"] is not None
            else settings.BACKUP_RETENTION_DAILY_DAYS
        )
        total_days = (
            options["total_days"]
            if options["total_days"] is not None
            else settings.BACKUP_RETENTION_TOTAL_DAYS
        )
        if daily_days > total_days:
            raise CommandError(
                "--retention-daily-days no puede ser mayor que --retention-total-days"
            )

        conexion = connections[options["database"]]
        directorio = Path(options["output_dir"] or settings.BACKUP_DIR).expanduser()

        if options["dry_run"]:
            self._informar_dry_run(directorio, daily_days, total_days)
            return

        ahora = timezone.now()
        destino = directorio / backups.backup_filename(ahora)
        self.stdout.write(f"[RNF-14] Generando respaldo en {self._ruta_relativa(destino)}")

        inicio = time.perf_counter()
        try:
            directorio.mkdir(parents=True, exist_ok=True)
            self._generar(conexion, destino)
            objetos = None
            if not options["skip_integrity"]:
                objetos = self._verificar_integridad(conexion, destino)
            checksum = backups.sha256_of(destino)
        except Exception as exc:
            self._registrar(
                estado="fallido",
                destino=destino,
                tamano=self._tamano_mb(destino),
                usuario=options["usuario"],
            )
            raise CommandError(f"El respaldo falló: {exc}") from exc

        duracion = time.perf_counter() - inicio
        tamano = backups.megabytes(destino.stat().st_size)
        self._escribir_checksum(destino, checksum)
        self._registrar(
            estado="exitoso",
            destino=destino,
            tamano=tamano,
            usuario=options["usuario"],
        )
        conservar, purgar = self._rotar(
            directorio,
            backups.to_utc(ahora),
            daily_days,
            total_days,
            dry_run=False,
        )

        if objetos is not None:
            self.stdout.write(f"[OK] Integridad verificada: {objetos} objetos en el archivo")
        else:
            self.stdout.write("[SKIP] Verificación de integridad omitida por --skip-integrity-check")
        self.stdout.write(f"[OK] SHA-256: {checksum}")
        self.stdout.write(
            f"[OK] Retención aplicada: {len(conservar)} respaldos conservados, "
            f"{len(purgar)} purgados ({daily_days}/{total_days} días)"
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] Respaldo '{destino.name}' listo en {duracion:.1f} s ({tamano} MB)"
            )
        )

    # ------------------------------------------------------------------
    # Generación del respaldo
    # ------------------------------------------------------------------
    def _generar(self, conexion, destino: Path) -> None:
        motor = conexion.vendor
        if motor == "postgresql":
            self._pg_dump(conexion, destino)
        elif motor == "sqlite":
            self._sqlite_dump(conexion, destino)
        else:
            raise CommandError(
                f"Motor '{motor}' no soportado para respaldos: use PostgreSQL o SQLite."
            )

    def _entorno_pg(self, conexion) -> dict[str, str]:
        entorno = os.environ.copy()
        password = conexion.settings_dict.get("PASSWORD")
        if password:
            entorno["PGPASSWORD"] = str(password)
        return entorno

    def _pg_dump(self, conexion, destino: Path) -> None:
        binario = os.environ.get("PG_DUMP_BIN", "pg_dump")
        if shutil.which(binario) is None:
            raise CommandError(
                f"No se encontró el binario '{binario}'. Instale el cliente de "
                "PostgreSQL (versión igual o superior al servidor)."
            )
        cfg = conexion.settings_dict
        comando = [
            binario,
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(destino),
            "--host",
            str(cfg["HOST"] or "localhost"),
            "--port",
            str(cfg["PORT"] or "5432"),
            "--username",
            str(cfg["USER"]),
            str(cfg["NAME"]),
        ]
        proceso = subprocess.run(
            comando, env=self._entorno_pg(conexion), capture_output=True, text=True
        )
        if proceso.returncode != 0:
            destino.unlink(missing_ok=True)
            detalle = proceso.stderr.strip() or proceso.stdout.strip()
            raise CommandError(
                f"pg_dump terminó con código {proceso.returncode}: {detalle}"
            )

    def _sqlite_dump(self, conexion, destino: Path) -> None:
        conexion.ensure_connection()
        with destino.open("w", encoding="utf-8") as archivo:
            archivo.write(f"-- Respaldo JobDevs - {timezone.now().isoformat()}\n")
            archivo.write("-- Motor: SQLite\n")
            for sentencia in conexion.connection.iterdump():
                archivo.write(f"{sentencia}\n")

    # ------------------------------------------------------------------
    # Verificación de integridad
    # ------------------------------------------------------------------
    def _verificar_integridad(self, conexion, destino: Path) -> int:
        if conexion.vendor == "sqlite":
            return self._verificar_sqlite(destino)
        return self._verificar_pg(destino)

    def _verificar_pg(self, destino: Path) -> int:
        binario = os.environ.get("PG_RESTORE_BIN", "pg_restore")
        if shutil.which(binario) is None:
            raise CommandError(
                f"No se encontró el binario '{binario}' para verificar el respaldo."
            )
        proceso = subprocess.run(
            [binario, "--list", str(destino)], capture_output=True, text=True
        )
        if proceso.returncode != 0:
            detalle = proceso.stderr.strip() or proceso.stdout.strip()
            raise CommandError(
                f"El respaldo no es un archivo restaurable (pg_restore "
                f"código {proceso.returncode}): {detalle}"
            )
        objetos = [
            linea
            for linea in proceso.stdout.splitlines()
            if linea.strip() and not linea.startswith(";")
        ]
        if not objetos:
            raise CommandError("El catálogo del respaldo está vacío")
        return len(objetos)

    def _verificar_sqlite(self, destino: Path) -> int:
        contenido = destino.read_text(encoding="utf-8")
        if "COMMIT;" not in contenido:
            raise CommandError("El respaldo SQLite está incompleto (no contiene COMMIT;)")
        memoria = sqlite3.connect(":memory:")
        try:
            memoria.executescript(contenido)
        except sqlite3.Error as exc:
            raise CommandError(f"El respaldo SQLite no se puede reejecutar: {exc}") from exc
        finally:
            memoria.close()
        return contenido.count("CREATE TABLE")

    def _escribir_checksum(self, destino: Path, checksum: str) -> None:
        archivo = destino.with_name(backups.checksum_filename(destino.name))
        archivo.write_text(f"{checksum}  {destino.name}\n", encoding="utf-8")

    # ------------------------------------------------------------------
    # Retención y registro
    # ------------------------------------------------------------------
    def _rotar(
        self,
        directorio: Path,
        ahora,
        daily_days: int,
        total_days: int,
        *,
        dry_run: bool,
    ) -> tuple[list[Path], list[Path]]:
        entradas = backups.servicios_de_respaldo(directorio)
        conservar, purgar = backups.plan_retention(entradas, ahora, daily_days, total_days)
        for ruta in purgar:
            if dry_run:
                self.stdout.write(f"[DRY-RUN] se purgaría {ruta.name}")
                continue
            ruta.unlink(missing_ok=True)
            ruta.with_name(backups.checksum_filename(ruta.name)).unlink(missing_ok=True)
        return conservar, purgar

    def _informar_dry_run(self, directorio: Path, daily_days: int, total_days: int) -> None:
        ahora = timezone.now()
        entradas = backups.servicios_de_respaldo(directorio)
        conservar, purgar = backups.plan_retention(
            entradas, backups.to_utc(ahora), daily_days, total_days
        )
        self.stdout.write(f"[DRY-RUN] Directorio: {directorio}")
        self.stdout.write(
            f"[DRY-RUN] Respaldo que se generaría: {backups.backup_filename(ahora)}"
        )
        self.stdout.write(
            f"[DRY-RUN] Retención {daily_days}/{total_days} días: "
            f"{len(conservar)} respaldos se conservarían y {len(purgar)} se purgarían"
        )
        for ruta in sorted(purgar, key=lambda item: item.name):
            self.stdout.write(f"[DRY-RUN]   purgaría {ruta.name}")

    def _registrar(self, *, estado: str, destino: Path, tamano, usuario: str | None):
        ejecutado_por = None
        if usuario:
            modelo_usuario = get_user_model()
            ejecutado_por = modelo_usuario.objects.filter(username=usuario).first()
            if ejecutado_por is None:
                self.stderr.write(
                    self.style.WARNING(
                        f"No existe el usuario '{usuario}': se registra sin responsable."
                    )
                )
        try:
            return CopiaSeguridad.objects.create(
                estado=estado,
                archivo_url=self._ruta_relativa(destino)[:LIMITE_ARCHIVO_URL],
                tamano_mb=tamano,
                ejecutado_por=ejecutado_por,
            )
        except Exception as exc:  # pragma: no cover - defensivo
            self.stderr.write(
                self.style.WARNING(f"No se pudo registrar la copia de seguridad: {exc}")
            )
            return None

    def _tamano_mb(self, destino: Path) -> Decimal | None:
        if not destino.exists():
            return None
        return backups.megabytes(destino.stat().st_size)

    def _ruta_relativa(self, destino: Path) -> str:
        try:
            return destino.resolve().relative_to(Path(settings.BASE_DIR).resolve()).as_posix()
        except ValueError:
            return destino.as_posix()
