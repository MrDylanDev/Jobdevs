"""Tests de la lógica pura de respaldos y retención (RNF-14)."""

from __future__ import annotations

import datetime as dt

import pytest

from logs import backups

UTC = dt.timezone.utc
#: Lunes de referencia para las pruebas de la capa semanal.
LUNES = dt.datetime(2026, 6, 15, 3, 0, tzinfo=UTC)


def _respaldo(dias_atras: int, *, horas: int = 0) -> tuple[dt.datetime, object]:
    momento = LUNES + dt.timedelta(days=30) - dt.timedelta(days=dias_atras, hours=horas)
    return momento, f"/respaldos/{backups.backup_filename(momento)}"


class TestNombresDeArchivo:
    """Convención de nombres de los respaldos."""

    def test_genera_nombre_en_utc(self):
        momento = dt.datetime(2026, 6, 15, 3, 5, 6, tzinfo=UTC)
        assert backups.backup_filename(momento) == "jobdevs_bd_20260615_030506.dump"

    def test_normaliza_a_utc(self):
        # 2026-06-14 22:05 en Bogotá (UTC-5) es 2026-06-15 03:05 UTC.
        momento = dt.datetime(
            2026, 6, 14, 22, 5, 6, tzinfo=dt.timezone(dt.timedelta(hours=-5))
        )
        assert backups.backup_filename(momento) == "jobdevs_bd_20260615_030506.dump"

    def test_interpreta_ingenuo_como_utc(self):
        momento = dt.datetime(2026, 6, 15, 3, 5, 6)
        assert backups.backup_filename(momento) == "jobdevs_bd_20260615_030506.dump"

    def test_nombre_de_checksum(self):
        assert (
            backups.checksum_filename("jobdevs_bd_20260615_030506.dump")
            == "jobdevs_bd_20260615_030506.dump.sha256"
        )

    def test_reconoce_solo_la_convencion(self):
        assert backups.is_backup_file("jobdevs_bd_20260615_030506.dump")
        assert not backups.is_backup_file("respaldo.sql")
        assert not backups.is_backup_file("jobdevs_bd_20260615_030506.sql")
        assert not backups.is_backup_file(
            "jobdevs_bd_20260615_030506.dump.sha256"
        )

    def test_parsea_marca_de_tiempo(self):
        momento = backups.parse_backup_datetime("jobdevs_bd_20260615_030506.dump")
        assert momento == dt.datetime(2026, 6, 15, 3, 5, 6, tzinfo=UTC)
        assert momento.tzinfo is not None

    def test_parsea_nombre_invalido(self):
        assert backups.parse_backup_datetime("cualquiera.dump") is None


class TestIntegridadYTamano:
    """Checksum y conversión de tamaño."""

    def test_sha256_de_archivo_vacio(self, tmp_path):
        vacio = tmp_path / "vacio.dump"
        vacio.write_bytes(b"")
        assert backups.sha256_of(vacio) == (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def test_sha256_de_archivo_con_contenido(self, tmp_path):
        archivo = tmp_path / "dato.dump"
        archivo.write_bytes(b"jobdevs")
        assert len(backups.sha256_of(archivo)) == 64
        assert backups.sha256_of(archivo) == backups.sha256_of(archivo)

    def test_convierte_bytes_a_mb(self):
        assert backups.megabytes(0) == pytest.approx(0.0, abs=0.001)
        assert backups.megabytes(1024 * 1024) == pytest.approx(1.0, abs=0.001)
        assert backups.megabytes(int(1.5 * 1024 * 1024)) == pytest.approx(1.5, abs=0.01)

    def test_mb_con_dos_decimales(self):
        assert str(backups.megabytes(1024 * 1024 + 512 * 1024)) == "1.50"


class TestRetencion:
    """Política de retención: capa diaria, capa semanal y purga."""

    def test_conserva_todos_los_diarios(self):
        entradas = [_respaldo(dias) for dias in range(1, 8)]
        conservar, purgar = backups.plan_retention(entradas, LUNES + dt.timedelta(days=30))
        assert len(conservar) == 7
        assert purgar == []

    def test_purga_mas_antiguo_que_el_total(self):
        entradas = [_respaldo(dias) for dias in (1, 31, 45, 90)]
        conservar, purgar = backups.plan_retention(entradas, LUNES + dt.timedelta(days=30))
        assert len(conservar) == 1
        assert len(purgar) == 3
        assert all("jobdevs_bd" in str(ruta) for ruta in purgar)

    def test_colapsa_dos_respaldos_de_la_misma_semana(self):
        # Dos respaldos separados por una hora, dentro de la ventana semanal.
        entradas = [_respaldo(10, horas=0), _respaldo(10, horas=1)]
        conservar, purgar = backups.plan_retention(entradas, LUNES + dt.timedelta(days=30))
        assert len(conservar) == 1
        assert len(purgar) == 1
        # Se conserva el más reciente de la semana.
        assert conservar[0] == entradas[0][1]

    def test_politica_completa_7_diarios_mas_semanales(self):
        # 30 respaldos diarios: la capa diaria conserva 7 y la semanal uno por semana.
        entradas = [_respaldo(dias) for dias in range(1, 31)]
        conservar, purgar = backups.plan_retention(entradas, LUNES + dt.timedelta(days=30))
        assert len(conservar) + len(purgar) == 30
        assert 7 <= len(conservar) <= 12  # 7 diarios + hasta 5 semanas parciales
        assert len(conservar) == 7 + len({m.isocalendar()[:2] for m, _ in entradas[7:]})

    def test_borde_exacto_de_la_capa_diaria(self):
        exacto = [(LUNES + dt.timedelta(days=30) - dt.timedelta(days=7), "a")]
        conservar, purgar = backups.plan_retention(exacto, LUNES + dt.timedelta(days=30))
        assert conservar == ["a"] and purgar == []

    def test_rechaza_parametros_invalidos(self):
        with pytest.raises(ValueError):
            backups.plan_retention([], LUNES, daily_days=30, total_days=7)
        with pytest.raises(ValueError):
            backups.plan_retention([], LUNES, daily_days=-1, total_days=7)


class TestListadoDeRespaldos:
    """Detección de respaldos en disco."""

    def test_ignora_archivos_ajenos(self, tmp_path):
        (tmp_path / "jobdevs_bd_20260615_030506.dump").write_text("x")
        (tmp_path / "jobdevs_bd_20260615_030506.dump.sha256").write_text("x")
        (tmp_path / "notas.txt").write_text("x")
        (tmp_path / "subdirectorio").mkdir()

        entradas = backups.servicios_de_respaldo(tmp_path)
        assert len(entradas) == 1
        assert entradas[0][1].name == "jobdevs_bd_20260615_030506.dump"

    def test_directorio_inexistente(self, tmp_path):
        assert backups.servicios_de_respaldo(tmp_path / "no-existe") == []
