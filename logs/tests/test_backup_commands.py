"""Tests de los comandos de respaldo y verificación de recuperación (RNF-14).

El comando ``verify_db_recovery`` reconstruye el esquema en una base de datos
**nueva** (alias temporal). El framework de pruebas de Django solo permite
acceder a los alias declarados en ``settings.DATABASES``, por lo que su camino
real (crear la base de datos, migrar y medir) se verifica ejecutando el
comando por la CLI en un subproceso, igual que lo hacen el programador diario
y la CI.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import override_settings
from django.utils import timezone

from logs import backups
from logs.management.commands import backup_db as backup_db_module
from logs.models import CopiaSeguridad

User = get_user_model()
BASE_DIR = Path(__file__).resolve().parents[2]


def _crear_archivo_antiguo(directorio, dias_atras: int):
    """Crea un respaldo falso con la antigüedad indicada."""
    momento = timezone.now() - dt.timedelta(days=dias_atras)
    respaldo = directorio / backups.backup_filename(momento)
    respaldo.write_text("respaldo antiguo", encoding="utf-8")
    checksum = respaldo.with_name(backups.checksum_filename(respaldo.name))
    checksum.write_text("checksum antiguo", encoding="utf-8")
    return respaldo, checksum


def _capturar(nombre: str, **opciones) -> str:
    """Ejecuta un comando de gestión y devuelve su salida estándar."""
    buffer = StringIO()
    call_command(nombre, stdout=buffer, **opciones)
    return buffer.getvalue()


class TestComandoBackupDb:
    """``manage.py backup_db``."""

    def test_genera_respaldo_y_registra_copia(self, db, tmp_path):
        call_command("backup_db", output_dir=str(tmp_path))

        respaldos = list(tmp_path.glob(f"{backups.BACKUP_PREFIX}*{backups.BACKUP_SUFFIX}"))
        assert len(respaldos) == 1
        assert respaldos[0].stat().st_size > 0

        checksum = tmp_path / backups.checksum_filename(respaldos[0].name)
        assert checksum.exists()
        assert backups.sha256_of(respaldos[0]) in checksum.read_text(encoding="utf-8")

        copia = CopiaSeguridad.objects.get()
        assert copia.estado == "exitoso"
        assert copia.archivo_url.endswith(respaldos[0].name)
        assert copia.tamano_mb is not None
        assert copia.tamano_mb > 0
        assert copia.ejecutado_por is None

    def test_respaldo_contiene_el_esquema(self, db, tmp_path):
        call_command("backup_db", output_dir=str(tmp_path))
        respaldo = next(tmp_path.glob(f"{backups.BACKUP_PREFIX}*{backups.BACKUP_SUFFIX}"))
        if connection.vendor == "postgresql":
            # En PostgreSQL el volcado usa el formato personalizado de pg_dump,
            # que es binario: comienza con el número mágico "PGDMP" y su
            # contenido se consulta con `pg_restore --list`, no leyéndolo como
            # texto. La comprobación de que el esquema esté dentro se hace en
            # test_volcado_postgresql_incluye_las_tablas.
            assert respaldo.read_bytes()[:5] == b"PGDMP"
        else:
            contenido = respaldo.read_text(encoding="utf-8")
            assert "CREATE TABLE" in contenido
            assert "COMMIT;" in contenido

    @pytest.mark.skipif(
        connection.vendor != "postgresql" or not shutil.which("pg_restore"),
        reason="Requiere PostgreSQL y el cliente pg_restore",
    )
    def test_volcado_postgresql_incluye_las_tablas(self, db, tmp_path):
        """El volcado binario contiene realmente el esquema de la aplicación."""
        call_command("backup_db", output_dir=str(tmp_path))
        respaldo = next(tmp_path.glob(f"{backups.BACKUP_PREFIX}*{backups.BACKUP_SUFFIX}"))
        tablas = subprocess.run(
            ["pg_restore", "--list", str(respaldo)],
            capture_output=True, text=True, check=True,
        ).stdout
        assert "TABLE" in tablas
        # Una tabla propia de la aplicación, no solo del esquema interno.
        assert "copias_seguridad" in tablas

    def test_registra_usuario_ejecutor(self, db, tmp_path):
        User.objects.create_user(
            username="adminbk", email="adminbk@test.jobdevs",
            nombre="Admin BK", rol="administrador", estado="activo",
            password="TestPass123!",
        )
        call_command("backup_db", output_dir=str(tmp_path), usuario="adminbk")
        copia = CopiaSeguridad.objects.get()
        assert copia.ejecutado_por is not None
        assert copia.ejecutado_por.username == "adminbk"

    def test_usuario_inexistente_no_rompe_el_respaldo(self, db, tmp_path):
        call_command("backup_db", output_dir=str(tmp_path), usuario="no-existe")
        assert CopiaSeguridad.objects.get().ejecutado_por is None

    def test_purga_respaldos_mas_antiguos_que_la_retencion(self, db, tmp_path):
        viejo, checksum_viejo = _crear_archivo_antiguo(tmp_path, dias_atras=45)
        reciente, _ = _crear_archivo_antiguo(tmp_path, dias_atras=3)

        call_command("backup_db", output_dir=str(tmp_path))

        assert not viejo.exists()
        assert not checksum_viejo.exists()
        assert reciente.exists()
        assert CopiaSeguridad.objects.count() == 1

    def test_dry_run_no_escribe_ni_borra(self, db, tmp_path):
        viejo, checksum_viejo = _crear_archivo_antiguo(tmp_path, dias_atras=45)

        call_command("backup_db", output_dir=str(tmp_path), dry_run=True)

        assert viejo.exists()
        assert checksum_viejo.exists()
        assert CopiaSeguridad.objects.count() == 0

    def test_dry_run_no_genera_respaldos_nuevos(self, db, tmp_path):
        call_command("backup_db", output_dir=str(tmp_path), dry_run=True)
        assert not list(tmp_path.glob(f"{backups.BACKUP_PREFIX}*"))

    def test_falla_y_registra_estado_fallido(self, db, tmp_path, monkeypatch):
        def _falla(self, conexion, destino):
            raise CommandError("pg_dump simulado")

        monkeypatch.setattr(backup_db_module.Command, "_generar", _falla)

        with pytest.raises(CommandError, match="El respaldo falló"):
            call_command("backup_db", output_dir=str(tmp_path))

        assert CopiaSeguridad.objects.get().estado == "fallido"

    def test_rechaza_retencion_incoherente(self, db, tmp_path):
        with pytest.raises(CommandError, match="no puede ser mayor"):
            call_command(
                "backup_db",
                output_dir=str(tmp_path),
                daily_days=20,
                total_days=10,
            )

    def test_omite_verificacion_de_integridad(self, db, tmp_path):
        call_command("backup_db", output_dir=str(tmp_path), skip_integrity=True)
        assert CopiaSeguridad.objects.get().estado == "exitoso"

    def test_usa_backup_dir_de_settings(self, db, tmp_path):
        with override_settings(BACKUP_DIR=tmp_path / "respaldos"):
            call_command("backup_db")
        assert list((tmp_path / "respaldos").glob(f"{backups.BACKUP_PREFIX}*"))


class TestComandoVerifyDbRecovery:
    """Comprobaciones de ``verify_db_recovery`` que fallan antes de crear nada."""

    def test_rechaza_respaldo_inexistente(self, db, tmp_path):
        with pytest.raises(CommandError, match="No existe el respaldo"):
            call_command(
                "verify_db_recovery",
                dump=str(tmp_path / "no-existe.dump"),
                objetivo=300,
            )

    def test_rechaza_motor_no_soportado(self, db):
        with pytest.raises(CommandError, match="no soportado"):
            with override_settings(
                DATABASES={
                    "default": {"ENGINE": "django.db.backends.oracle", "NAME": "x"}
                }
            ):
                call_command("verify_db_recovery", objetivo=300)


class TestVerifyDbRecoveryCli:
    """Camino real del comando: crear la BD de prueba, migrar y medir."""

    def test_reconstruye_el_esquema_dentro_del_objetivo(self, tmp_path):
        informe = tmp_path / "recuperacion.json"
        proceso = _ejecutar_verify(
            tmp_path,
            "--objetivo",
            "600",
            "--json-out",
            str(informe),
        )

        assert proceso.returncode == 0, proceso.stderr
        assert "CUMPLE" in proceso.stdout
        assert "Migraciones sincronizadas con los modelos" in proceso.stdout
        datos = json.loads(informe.read_text(encoding="utf-8"))
        assert datos["cumple"] is True
        assert datos["modo"] == "migraciones"
        assert datos["tablas"] > 0
        assert datos["objetivo_segundos"] == 600

    def test_falla_e_informa_si_se_supera_el_objetivo(self, tmp_path):
        proceso = _ejecutar_verify(tmp_path, "--objetivo", "0", "--skip-migration-check")

        assert proceso.returncode != 0
        assert "NO CUMPLE" in (proceso.stdout + proceso.stderr)
        # El salto del chequeo de migraciones también queda registrado
        assert "[SKIP] Comprobación de migraciones omitida" in proceso.stdout

    def test_restaura_un_volcado_existente(self, tmp_path):
        volcado = tmp_path / "jobdevs_bd_20260101_000000.dump"
        volcado.write_text(
            "BEGIN TRANSACTION;\n"
            "CREATE TABLE demo (id integer primary key, nombre varchar(10));\n"
            "INSERT INTO demo VALUES (1, 'jobdevs');\n"
            "COMMIT;\n",
            encoding="utf-8",
        )
        proceso = _ejecutar_verify(
            tmp_path,
            "--desde-dump",
            str(volcado),
            "--objetivo",
            "600",
            "--skip-migration-check",
        )

        assert proceso.returncode == 0, proceso.stderr
        assert "Restauración de" in proceso.stdout
        assert "(1 tablas)" in proceso.stdout
        assert "CUMPLE" in proceso.stdout


def _ejecutar_verify(tmp_path, *args) -> subprocess.CompletedProcess:
    """Ejecuta ``manage.py verify_db_recovery`` con SQLite, como en la CI."""
    entorno = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "DJANGO_SECRET_KEY": "test-secret-key-rnf14",
        "DJANGO_DEBUG": "True",
        "DB_ENGINE": "sqlite3",
        "DB_NAME": str(tmp_path / "base.sqlite3"),
        "DB_HOST": "",
        "DB_PORT": "",
    }
    entorno.pop("USE_POSTGRES", None)
    entorno.pop("TEST_DB", None)
    return subprocess.run(
        [sys.executable, "manage.py", "verify_db_recovery", *args],
        cwd=BASE_DIR,
        env=entorno,
        capture_output=True,
        text=True,
        timeout=300,
    )
