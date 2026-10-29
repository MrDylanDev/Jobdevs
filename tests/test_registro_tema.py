"""
Registro: el tema claro/oscuro de la landing también aplica acá.

El registro tiene su propia piel (`styleregistro.css`), separada de `index.css`,
así que necesita su propio juego de tokens y su propio arranque sin flash.
"""

from pathlib import Path

import pytest
from django.conf import settings

CSS = Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'styleregistro.css'
TEMPLATE = Path(settings.BASE_DIR) / 'templates' / 'publico' / 'registro.html'


@pytest.fixture(scope='module')
def css():
    return CSS.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def html():
    return TEMPLATE.read_text(encoding='utf-8')


class TestArranqueDelTema:
    def test_resuelve_el_tema_antes_del_primer_paint(self, html):
        assert html.index('jobdevs-theme') < html.index('styleregistro.css'), (
            'El script del tema tiene que ir antes del CSS o se ve el flash del tema equivocado'
        )

    def test_la_precedencia_es_guardado_sistema_oscuro(self, html):
        assert "localStorage.getItem('jobdevs-theme')" in html
        assert "prefers-color-scheme: light" in html
        assert "var tema = 'dark';" in html

    def test_el_lang_usa_el_idioma_activo(self, html):
        assert '<html lang="{{ LANGUAGE_CODE }}">' in html


class TestPaletaClara:
    def test_existe_el_bloque_de_tema_claro(self, css):
        assert '[data-theme="light"] {' in css

    def test_los_tokens_se_invierten(self, css):
        bloque = css[css.index('[data-theme="light"] {'):]
        bloque = bloque[:bloque.index('}')]
        for par in ('--bg: #ffffff', '--fg: #0b0f0c', '--border-dim: #e4e7e5',
                    '--accent: #00713f', '--accent-rgb: 0, 113, 63'):
            assert par in bloque, f'Falta {par} en la paleta clara'

    def test_el_grano_no_se_pinta_en_claro(self, css):
        assert '[data-theme="light"] body::before { display: none; }' in css

    def test_el_boton_principal_lleva_texto_blanco(self, css):
        assert '[data-theme="light"] .register-wrapper.theme-dev button[type="submit"] { color: #ffffff; }' in css, (
            'El verde oscuro del tema claro con texto negro queda en 3.4:1'
        )
