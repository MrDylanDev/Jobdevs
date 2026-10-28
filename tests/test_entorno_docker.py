"""
Entorno — el arranque del contenedor web no puede depender del dueno del volumen
de estaticos: cualquier archivo ajeno en /app/staticfiles rompia collectstatic y
dejaba teir_web en crash-loop.
"""

import subprocess
from pathlib import Path

import pytest
from django.conf import settings

RAIZ = Path(settings.BASE_DIR)


@pytest.fixture(scope='module')
def entrypoint():
    return (RAIZ / 'docker' / 'entrypoint.sh').read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def dockerfile():
    return (RAIZ / 'Dockerfile').read_text(encoding='utf-8')


class TestArranqueDelContenedorWeb:
    def test_normaliza_el_dueno_del_volumen_como_root(self, entrypoint):
        assert 'if [ "$(id -u)" -eq 0 ]' in entrypoint
        assert 'appuser:appuser /app/staticfiles' in entrypoint

    def test_baja_privilegios_con_setpriv(self, entrypoint):
        assert 'exec setpriv --reuid=appuser --regid=appuser --init-groups "$0" "$@"' in entrypoint

    def test_home_apunta_al_home_de_appuser(self, entrypoint):
        assert 'export HOME=/app' in entrypoint, (
            'Con HOME=/root gunicorn no puede crear su control socket'
        )

    def test_guardia_de_escritura_antes_de_collectstatic(self, entrypoint):
        assert 'if [ ! -w /app/staticfiles ]' in entrypoint
        assert 'docker volume rm teir_static_files' in entrypoint, (
            'La guardia debe indicar el remedio'
        )
        posicion_guardia = entrypoint.index('if [ ! -w /app/staticfiles ]')
        posicion_collect = entrypoint.index('collectstatic --noinput')
        assert posicion_guardia < posicion_collect, 'La guardia va antes de collectstatic'

    def test_dockerfile_no_fija_usuario_para_permitir_el_ajuste(self, dockerfile):
        assert '\nUSER appuser' not in dockerfile, (
            'El entrypoint necesita arrancar como root para normalizar el volumen'
        )
        assert 'setpriv' in dockerfile

    def test_el_entrypoint_es_bash_valido(self):
        resultado = subprocess.run(
            ['bash', '-n', str(RAIZ / 'docker' / 'entrypoint.sh')],
            capture_output=True, text=True,
        )
        assert resultado.returncode == 0, resultado.stderr
