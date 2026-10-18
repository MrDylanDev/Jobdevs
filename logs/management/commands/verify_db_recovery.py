"""Verificación de recuperación de la base de datos (RNF-14).

Comprueba que el esquema se pueda reconstruir **desde cero en un servidor
nuevo** dentro del objetivo de tiempo del RNF-14 (< 5 minutos):

1. que las migraciones estén sincronizadas con los modelos (el esquema no
   queda desactualizado),
2. que se cree una base de datos vacía,
3. que la estructura se reconstruya ahí ejecutando ``migrate`` en un
   **proceso limpio** apuntado a esa base nueva (o que un respaldo se
   restaure sobre ella),
4. que el tiempo empleado cumpla el objetivo.

Por qué un proceso hijo
-----------------------
Se ejecuta ``manage.py migrate`` en un subproceso con ``DB_NAME`` apuntando a
la base de datos recién creada. Así la prueba reproduce el escenario real
(servidor nuevo, proceso nuevo, sin estado previo), mide el tiempo de reloj
completo —incluido el arranque de Django— y no depende de registrar alias de
conexión dinámicos en el proceso actual.

La base de datos de prueba se elimina al terminar, por lo que el comando es
seguro de ejecutar sobre cualquier entorno (incluida la CI).

Ejemplos::

    python manage.py verify_db_recovery
    python manage.py verify_db_recovery --desde-dump backups/jobdevs_bd_....dump
    python manage.py verify_db_recovery --objetivo 300 --json-out recuperacion.json
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

#: PostgreSQL limita los identificadores a 63 caracteres.
LIMITE_NOMBRE_BD = 63
#: Base de datos de mantenimiento para CREATE/DROP DATABASE en PostgreSQL.
BD_MANTENIMIENTO = "postgres"


class Command(BaseCommand):
    help = (
        "Verifica que el esquema de la base de datos se reconstruya (o que un "
        "respaldo se restaure) dentro del objetivo de tiempo del RNF-14 "
        "(< 5 minutos por defecto)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--desde-dump",
            dest="dump",
            default=None,
            metavar="ARCHIVO",
            help="Restaura este respaldo en lugar de reconstruir el esquema "
            "con migraciones.",
        )
        parser.add_argument(
            "--objetivo",
            type=float,
            default=None,
            help="Tiempo máximo permitido en segundos "
            "(por defecto settings.DB_RECOVERY_TARGET_SECONDS).",
        )
        parser.add_argument(
            "--database",
            default="default",
            help="Alias de la conexión tomada como referencia (por defecto 'default').",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=None,
            help="Tiempo máximo de espera del proceso de reconstrucción "
            "(por defecto el doble del objetivo, mínimo 120 s).",
        )
        parser.add_argument(
            "--json-out",
            dest="json_out",
            default=None,
            metavar="ARCHIVO",
            help="Escribe el informe de la verificación en JSON.",
        )
        parser.add_argument(
            "--no-fallar-si-excede",
            dest="fallar_si_excede",
            action="store_false",
            default=True,
            help="Informa el exceso de tiempo pero termina con código 0.",
        )
        parser.add_argument(
            "--conservar",
            action="store_true",
            help="No elimina la base de datos de prueba (depuración).",
        )
        parser.add_argument(
            "--skip-migration-check",
            dest="skip_migration_check",
            action="store_true",
            help="Omite la comprobación de sincronía entre modelos y migraciones.",
        )

    def handle(self, *args, **options):
        objetivo = (
            options["objetivo"]
            if options["objetivo"] is not None
            else float(settings.DB_RECOVERY_TARGET_SECONDS)
        )
        timeout = options["timeout"] or max(objetivo * 2, 120)
        configuracion = settings.DATABASES[options["database"]]
        motor = self._motor(configuracion)
        ahora = timezone.now()
        modo = "respaldo" if options["dump"] else "migraciones"

        self.stdout.write("[RNF-14] Verificación de recuperación de la base de datos")
        self.stdout.write(
            f"[INFO] Motor: {motor} | objetivo: {objetivo:g} s | modo: {modo}"
        )

        migraciones_sincronizadas = None
        if options["skip_migration_check"]:
            self.stdout.write("[SKIP] Comprobación de migraciones omitida")
        else:
            migraciones_sincronizadas = self._verificar_migraciones()
            if not migraciones_sincronizadas:
                raise CommandError(
                    "Los modelos tienen cambios sin migración: el esquema no se "
                    "puede reconstruir de forma fiel (ejecute makemigrations)."
                )

        scratch = None
        duracion = 0.0
        tablas = 0
        try:
            scratch = self._crear_base_nueva(configuracion, motor)
            self.stdout.write(f"[OK] Base de datos de prueba creada: {scratch}")

            if options["dump"]:
                duracion = self._restaurar(
                    configuracion, motor, scratch, Path(options["dump"])
                )
                detalle = f"Restauración de {Path(options['dump']).name}"
            else:
                duracion = self._reconstruir(configuracion, motor, scratch, timeout)
                detalle = "Reconstrucción del esquema (migrate + createcachetable)"

            tablas = self._contar_tablas(configuracion, motor, scratch)
            if tablas == 0:
                raise CommandError("La base de datos de prueba quedó sin tablas")
            self.stdout.write(f"[OK] {detalle}: {duracion:.1f} s ({tablas} tablas)")
        finally:
            self._limpiar(configuracion, motor, scratch, conservar=options["conservar"])

        cumple = duracion <= objetivo
        informe = {
            "fecha": ahora.isoformat(),
            "modo": modo,
            "archivo": str(options["dump"]) if options["dump"] else None,
            "motor": motor,
            "objetivo_segundos": objetivo,
            "duracion_segundos": round(duracion, 2),
            "tablas": tablas,
            "migraciones_sincronizadas": migraciones_sincronizadas,
            "cumple": cumple,
        }
        if options["json_out"]:
            self._escribir_informe(Path(options["json_out"]), informe)
            self.stdout.write(f"[OK] Informe escrito en {options['json_out']}")

        if cumple:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[RNF-14] CUMPLE: {duracion:.1f} s <= {objetivo:g} s "
                    f"(margen de {objetivo - duracion:.1f} s)"
                )
            )
            return

        mensaje = (
            f"[RNF-14] NO CUMPLE: {duracion:.1f} s > {objetivo:g} s "
            f"(exceso de {duracion - objetivo:.1f} s)"
        )
        if not options["fallar_si_excede"]:
            self.stdout.write(self.style.WARNING(mensaje))
            return
        raise CommandError(mensaje)

    # ------------------------------------------------------------------
    # Comprobaciones y utilidades de configuración
    # ------------------------------------------------------------------
    def _motor(self, configuracion: dict) -> str:
        """Normaliza el motor al nombre que usa Django en ``connection.vendor``."""
        nombre = configuracion["ENGINE"].rsplit(".", 1)[-1]
        if nombre.startswith("sqlite"):
            return "sqlite"
        return nombre

    def _verificar_migraciones(self) -> bool:
        """Devuelve True si no hay cambios de modelo sin migración."""
        try:
            call_command("makemigrations", "--check", "--dry-run", verbosity=0)
        except SystemExit as exc:  # makemigrations --check sale con código 1
            self.stderr.write(
                self.style.WARNING(
                    "[WARN] Hay modelos sin migración: "
                    "ejecute 'python manage.py makemigrations'"
                )
            )
            return not exc.code
        self.stdout.write("[OK] Migraciones sincronizadas con los modelos")
        return True

    def _entorno_del_hijo(self, configuracion: dict, scratch: str) -> dict[str, str]:
        """Entorno para el proceso que reconstruye el esquema en la base nueva."""
        motor = self._motor(configuracion)
        entorno = os.environ.copy()
        entorno["DB_NAME"] = scratch
        entorno["DB_ENGINE"] = configuracion["ENGINE"]
        entorno["DB_HOST"] = str(configuracion["HOST"] or "localhost")
        entorno["DB_PORT"] = str(configuracion["PORT"] or 5432)
        entorno["DB_USER"] = str(configuracion["USER"] or "")
        entorno["DB_PASSWORD"] = str(configuracion["PASSWORD"] or "")
        if motor == "sqlite":
            entorno.pop("DB_HOST", None)
            entorno.pop("DB_PORT", None)
            entorno.pop("DB_PASSWORD", None)
        return entorno

    # ------------------------------------------------------------------
    # Base de datos nueva
    # ------------------------------------------------------------------
    def _crear_base_nueva(self, configuracion: dict, motor: str) -> str:
        if motor == "postgresql":
            nombre = self._nombre_scratch(str(configuracion["NAME"]))
            self._pg_admin(configuracion, f'CREATE DATABASE "{nombre}"')
            return nombre
        if motor == "sqlite":
            directorio = tempfile.mkdtemp(prefix="jobdevs-recuperacion-")
            return str(Path(directorio) / "recuperacion.sqlite3")
        raise CommandError(f"Motor '{motor}' no soportado: use PostgreSQL o SQLite.")

    def _nombre_scratch(self, base: str) -> str:
        sufijo = f"_recuperacion_{os.urandom(3).hex()}"
        return f"{base[: LIMITE_NOMBRE_BD - len(sufijo)]}{sufijo}"

    def _pg_admin(self, configuracion: dict, sentencia: str) -> None:
        """Ejecuta DDL administrativo (CREATE/DROP DATABASE) en la BD de mantenimiento."""
        import psycopg

        try:
            with psycopg.connect(
                host=str(configuracion["HOST"] or "localhost"),
                port=int(configuracion["PORT"] or 5432),
                user=str(configuracion["USER"]),
                password=str(configuracion["PASSWORD"] or ""),
                dbname=BD_MANTENIMIENTO,
                autocommit=True,
                connect_timeout=10,
            ) as admin:
                admin.execute(sentencia)
        except Exception as exc:
            raise CommandError(
                f"No se pudo ejecutar '{sentencia}' en la base de datos "
                f"'{BD_MANTENIMIENTO}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Reconstrucción y restauración
    # ------------------------------------------------------------------
    def _reconstruir(
        self, configuracion: dict, motor: str, scratch: str, timeout: float
    ) -> float:
        """Corre migrate + createcachetable en un proceso limpio."""
        entorno = self._entorno_del_hijo(configuracion, scratch)
        manejador = str(Path(settings.BASE_DIR) / "manage.py")
        inicio = time.perf_counter()
        for argumentos in (["migrate", "--noinput"], ["createcachetable"]):
            comando = [sys.executable, manejador, *argumentos]
            try:
                proceso = subprocess.run(
                    comando,
                    cwd=str(settings.BASE_DIR),
                    env=entorno,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired as exc:
                raise CommandError(
                    f"'{argumentos[0]}' excedió el tiempo máximo de {timeout:g} s"
                ) from exc
            if proceso.returncode != 0:
                detalle = (proceso.stderr.strip() or proceso.stdout.strip())[-800:]
                raise CommandError(
                    f"'{argumentos[0]}' terminó con código {proceso.returncode}: {detalle}"
                )
        return time.perf_counter() - inicio

    def _restaurar(
        self, configuracion: dict, motor: str, scratch: str, archivo: Path
    ) -> float:
        if not archivo.is_file():
            raise CommandError(f"No existe el respaldo '{archivo}'")
        inicio = time.perf_counter()
        if motor == "postgresql":
            self._pg_restore(configuracion, scratch, archivo)
        elif motor == "sqlite":
            self._sqlite_restore(scratch, archivo)
        else:
            raise CommandError(f"Motor '{motor}' no soportado para restauraciones.")
        return time.perf_counter() - inicio

    def _pg_restore(self, configuracion: dict, scratch: str, archivo: Path) -> None:
        binario = os.environ.get("PG_RESTORE_BIN", "pg_restore")
        if shutil.which(binario) is None:
            raise CommandError(f"No se encontró el binario '{binario}'.")
        comando = [
            binario,
            "--exit-on-error",
            "--no-owner",
            "--no-privileges",
            "--dbname",
            scratch,
            "--host",
            str(configuracion["HOST"] or "localhost"),
            "--port",
            str(configuracion["PORT"] or 5432),
            "--username",
            str(configuracion["USER"]),
            str(archivo),
        ]
        entorno = os.environ.copy()
        if configuracion.get("PASSWORD"):
            entorno["PGPASSWORD"] = str(configuracion["PASSWORD"])
        proceso = subprocess.run(comando, env=entorno, capture_output=True, text=True)
        if proceso.returncode != 0:
            detalle = (proceso.stderr.strip() or proceso.stdout.strip())[:800]
            raise CommandError(
                f"pg_restore terminó con código {proceso.returncode}: {detalle}"
            )

    def _sqlite_restore(self, scratch: str, archivo: Path) -> None:
        contenido = archivo.read_text(encoding="utf-8")
        with sqlite3.connect(scratch) as destino:
            destino.executescript(contenido)

    # ------------------------------------------------------------------
    # Verificación posterior
    # ------------------------------------------------------------------
    def _contar_tablas(self, configuracion: dict, motor: str, scratch: str) -> int:
        if motor == "postgresql":
            import psycopg

            with psycopg.connect(
                host=str(configuracion["HOST"] or "localhost"),
                port=int(configuracion["PORT"] or 5432),
                user=str(configuracion["USER"]),
                password=str(configuracion["PASSWORD"] or ""),
                dbname=scratch,
                connect_timeout=10,
            ) as conexion:
                fila = conexion.execute(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                ).fetchone()
            return int(fila[0])
        if motor == "sqlite":
            with sqlite3.connect(scratch) as conexion:
                fila = conexion.execute(
                    "SELECT count(*) FROM sqlite_master "
                    "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                ).fetchone()
            return int(fila[0])
        return 0

    # ------------------------------------------------------------------
    # Limpieza e informe
    # ------------------------------------------------------------------
    def _limpiar(
        self, configuracion: dict, motor: str, scratch: str | None, *, conservar: bool
    ) -> None:
        if not scratch:
            return
        if conservar:
            self.stdout.write("[INFO] Base de datos de prueba conservada (--conservar)")
            return
        try:
            if motor == "postgresql":
                self._pg_admin(
                    configuracion, f'DROP DATABASE IF EXISTS "{scratch}" WITH (FORCE)'
                )
            elif motor == "sqlite":
                shutil.rmtree(Path(scratch).parent, ignore_errors=True)
        except CommandError as exc:  # pragma: no cover - defensivo
            self.stderr.write(self.style.WARNING(f"[WARN] No se pudo eliminar: {exc}"))

    def _escribir_informe(self, destino: Path, informe: dict) -> None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
