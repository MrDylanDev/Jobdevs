"""
Landing — S17: el hero queda fijado durante el scroll (sticky) y expone un
progreso 0..1 que anima reel, contenido y barra inferior.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string


@pytest.fixture(scope='module')
def landing_html():
    return render_to_string('publico/index.html')


@pytest.fixture(scope='module')
def landing_css():
    return (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()


@pytest.fixture(scope='module')
def landing_js():
    return (Path(settings.BASE_DIR) / 'static' / 'publico' / 'script' / 'index.js').read_text()


class TestHeroStickyScroll:
    def test_hero_envuelto_en_contenedor_sticky(self, landing_html):
        assert re.search(r'<div class="hero-sticky" id="heroSticky">', landing_html)
        inicio_wrap = landing_html.index('id="heroSticky"')
        inicio_hero = landing_html.index('id="inicio"')
        assert inicio_wrap < inicio_hero, 'El hero debe quedar dentro del contenedor sticky'

    def test_barra_de_progreso_presente(self, landing_html):
        assert 'class="hero-progress"' in landing_html

    def test_css_pinnea_el_hero_y_expone_el_progreso(self, landing_css):
        assert '.hero-sticky' in landing_css
        assert re.search(r'\.hero-section\s*\{[^}]*position:\s*sticky', landing_css)
        assert re.search(r'\.hero-section\s*\{[^}]*top:\s*0', landing_css)
        assert 'var(--hero-progress' in landing_css
        assert re.search(r'\.hero-progress\s*\{[^}]*scaleX\(var\(--hero-progress', landing_css)

    def test_degradaciones_por_movimiento_reducido_y_movil(self, landing_css):
        bloque = landing_css[landing_css.index('HERO STICKY: degradaciones'):]
        assert '@media (prefers-reduced-motion: reduce)' in bloque
        assert '@media (max-width: 860px)' in bloque
        assert 'position: relative' in bloque

    def test_js_calcula_el_progreso_y_respeta_movimiento_reducido(self, landing_js):
        assert "getElementById('heroSticky')" in landing_js
        assert "--hero-progress" in landing_js
        assert "prefers-reduced-motion: reduce" in landing_js
        assert 'requestAnimationFrame' in landing_js
        assert '{ passive: true }' in landing_js

    def test_body_no_rompe_sticky_con_overflow(self, landing_css):
        cuerpo = landing_css[landing_css.index('body {'):landing_css.index('}', landing_css.index('body {'))]
        assert 'overflow-x: clip' in cuerpo, (
            'body debe usar overflow-x: clip: overflow-x: hidden rompe position: sticky'
        )
