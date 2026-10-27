"""
Landing — S9: carrusel "Empresas que confían en nosotros" ubicado entre la
sección "Cómo funciona JobDevs" (#metodologia) y "Diseñado para Empresas y
Desarrolladores SENA" (#roles).
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
    css_path = Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css'
    assert css_path.exists(), 'Debe existir el CSS de la landing'
    return css_path.read_text(encoding='utf-8')


class TestCarruselEmpresasLanding:
    """El carrusel de empresas se renderiza entre metodología y roles."""

    def test_seccion_de_empresas_existe(self, landing_html):
        assert 'id="empresas"' in landing_html

    def test_ubicada_entre_metodologia_y_roles(self, landing_html):
        idx_metodologia = landing_html.index('id="metodologia"')
        idx_empresas = landing_html.index('id="empresas"')
        idx_roles = landing_html.index('id="roles"')
        assert idx_metodologia < idx_empresas < idx_roles, (
            'El carrusel de empresas debe quedar entre #metodologia y #roles'
        )

    def test_titular_visible_empresas_que_confian(self, landing_html):
        inicio = landing_html.index('id="empresas"')
        fin = landing_html.index('id="roles"')
        bloque = landing_html[inicio:fin]
        assert 'Empresas que confían en nosotros' in bloque

    def test_pista_duplicada_para_desplazamiento_continuo(self, landing_html):
        inicio = landing_html.index('id="empresas"')
        fin = landing_html.index('id="roles"')
        bloque = landing_html[inicio:fin]
        pistas = re.findall(r'class="[^"]*logos-marquee-track[^"]*"', bloque)
        assert len(pistas) == 2, 'Debe haber dos pistas iguales para el loop infinito'
        assert 'aria-hidden="true"' in bloque, 'La copia de la pista debe ser aria-hidden'

    def test_wordmarks_de_empresas_presentes(self, landing_html):
        inicio = landing_html.index('id="empresas"')
        fin = landing_html.index('id="roles"')
        bloque = landing_html[inicio:fin]
        marcas = re.findall(r'class="logos-wordmark"[^>]*>([^<]+)<', bloque)
        assert len(marcas) >= 8, 'El carrusel debe mostrar al menos 8 empresas'
        assert all(marca.strip() for marca in marcas)

    def test_css_define_animacion_y_accesibilidad(self, landing_css):
        assert '.logos-marquee-section' in landing_css
        assert re.search(r'\.logos-marquee-track\s*\{[^}]*animation:', landing_css), (
            'La pista del carrusel debe animarse'
        )
        assert 'prefers-reduced-motion' in landing_css, (
            'El carrusel debe respetar prefers-reduced-motion'
        )
        assert '.logos-marquee-track:hover' in landing_css
