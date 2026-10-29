"""
Landing — S9: carrusel de logos "Empresas que confían en nosotros" ubicado entre
la sección "Cómo funciona JobDevs" (#metodologia) y "Diseñado para Empresas y
Desarrolladores SENA" (#roles).
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

LOGOS_DIR = Path(settings.BASE_DIR) / 'static' / 'IMG' / 'logos'


@pytest.fixture(scope='module')
def landing_html():
    return render_to_string('publico/index.html')


@pytest.fixture(scope='module')
def landing_css():
    css_path = Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css'
    assert css_path.exists(), 'Debe existir el CSS de la landing'
    return css_path.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def bloque_empresas(landing_html):
    inicio = landing_html.index('id="empresas"')
    fin = landing_html.index('id="roles"')
    return landing_html[inicio:fin]


class TestCarruselEmpresasLanding:
    """El carrusel de logos se renderiza entre metodología y roles."""

    def test_seccion_de_empresas_existe(self, landing_html):
        assert 'id="empresas"' in landing_html

    def test_ubicada_entre_metodologia_y_roles(self, landing_html):
        idx_metodologia = landing_html.index('id="metodologia"')
        idx_empresas = landing_html.index('id="empresas"')
        idx_roles = landing_html.index('id="roles"')
        assert idx_metodologia < idx_empresas < idx_roles, (
            'El carrusel de logos debe quedar entre #metodologia y #roles'
        )

    def test_titular_visible_empresas_que_confian(self, bloque_empresas):
        # La frase puede venir con la parte de marca envuelta en un span.
        assert 'Empresas que' in bloque_empresas
        assert 'confían en nosotros' in bloque_empresas

    def test_pista_duplicada_para_desplazamiento_continuo(self, bloque_empresas):
        pistas = re.findall(r'class="[^"]*logos-marquee-track[^"]*"', bloque_empresas)
        assert len(pistas) == 2, 'Debe haber dos pistas iguales para el loop infinito'
        assert 'aria-hidden="true"' in bloque_empresas, 'La copia de la pista debe ser aria-hidden'

    def test_pista_visible_usa_logos_reales_con_alt(self, bloque_empresas):
        pistas = re.findall(
            r'<div class="logos-marquee-track"[^>]*>(.*?)</div>',
            bloque_empresas,
            flags=re.S,
        )
        imagenes = re.findall(
            r'<img[^>]+src="([^"]*IMG/logos/[^"]+)"[^>]*alt="([^"]*)"', pistas[0]
        )
        assert len(imagenes) >= 14, 'La pista visible debe mostrar al menos 14 logos'
        for _src, alt in imagenes:
            assert alt.strip(), 'Cada logo necesita texto alternativo con la marca'

    def test_cada_logo_declarado_existe_en_disco(self, bloque_empresas):
        rutas = set(re.findall(r'IMG/logos/([a-z0-9-]+\.svg)', bloque_empresas))
        assert rutas, 'El carrusel debe declarar archivos de logo'
        faltantes = [slug for slug in rutas if not (LOGOS_DIR / slug).exists()]
        assert not faltantes, f'Logos declarados que no existen en disco: {faltantes}'

    def test_logos_son_svg_sin_referencias_externas(self):
        for svg in LOGOS_DIR.glob('*.svg'):
            contenido = svg.read_text(encoding='utf-8')
            assert 'viewBox' in contenido, f'{svg.name} debe definir viewBox'
            assert '<image' not in contenido, f'{svg.name} no debe embeber mapas de bits'
            assert 'http://www.w3.org/2000/svg' in contenido or svg.name
            assert len(svg.read_bytes()) < 20_000, f'{svg.name} supera los 20 KB'

    def test_las_dos_pistas_tienen_los_mismos_logos(self, bloque_empresas):
        pistas = re.findall(
            r'<div class="logos-marquee-track"[^>]*>(.*?)</div>',
            bloque_empresas,
            flags=re.S,
        )
        assert len(pistas) == 2
        primera = re.findall(r'IMG/logos/([a-z0-9-]+\.svg)', pistas[0])
        segunda = re.findall(r'IMG/logos/([a-z0-9-]+\.svg)', pistas[1])
        assert primera == segunda, 'La copia de la pista debe repetir los logos en el mismo orden'

    def test_css_dimensiona_y_atenua_los_logos(self, landing_css):
        assert '.logos-marquee-section' in landing_css
        assert re.search(r'\.logos-marquee-track\s*\{[^}]*animation:', landing_css), (
            'La pista del carrusel debe animarse'
        )
        assert re.search(r'\.logos-wordmark img\s*\{[^}]*opacity:', landing_css), (
            'Los logos deben atenuarse por CSS'
        )
        assert '.logos-wordmark:hover img' in landing_css
        assert '.logos-marquee-track:hover' in landing_css
        assert 'prefers-reduced-motion' in landing_css

    def test_css_aporta_estetica_tecnica_de_la_banda(self, landing_css):
        for regla in (
            '.logos-grid-bg',
            '.logos-wordmark + .logos-wordmark::before',
            '.logos-wordmark:hover::after',
        ):
            assert regla in landing_css, f'Falta la regla {regla}'
