"""
Landing — metadatos sociales (Open Graph / Twitter) y limpieza del CSS muerto.

Sin estas etiquetas, compartir la landing por WhatsApp o LinkedIn mostraba un
enlace sin imagen ni descripción.
"""

from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

RAIZ = Path(settings.BASE_DIR)


@pytest.fixture(scope='module')
def html():
    return render_to_string('publico/index.html')


@pytest.fixture(scope='module')
def plantilla():
    return (RAIZ / 'templates' / 'publico' / 'index.html').read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def css():
    return (RAIZ / 'static' / 'publico' / 'css' / 'index.css').read_text(encoding='utf-8')


class TestMetadatosSociales:
    def test_open_graph_principal(self, html):
        assert 'property="og:type" content="website"' in html
        assert 'property="og:site_name" content="JobDevs"' in html
        assert 'property="og:title"' in html
        assert 'property="og:description"' in html
        assert 'property="og:locale" content="es_CO"' in html

    def test_imagen_de_prevista_con_dimensiones(self, html):
        assert 'property="og:image"' in html
        assert 'IMG/og-preview.jpg' in html
        assert 'property="og:image:width" content="1200"' in html
        assert 'property="og:image:height" content="630"' in html

    def test_twitter_card(self, html):
        assert 'name="twitter:card" content="summary_large_image"' in html
        assert 'name="twitter:title"' in html
        assert 'name="twitter:image"' in html

    def test_la_url_absoluta_usa_el_request(self, plantilla):
        assert '{{ request.scheme }}://{{ request.get_host }}' in plantilla
        assert 'rel="canonical"' in plantilla

    def test_la_imagen_de_prevista_existe_y_es_jpeg(self):
        imagen = RAIZ / 'static' / 'IMG' / 'og-preview.jpg'
        assert imagen.exists(), 'Falta static/IMG/og-preview.jpg'
        datos = imagen.read_bytes()
        assert datos[:2] == b'\xff\xd8', 'Debe ser un JPEG real'
        assert len(datos) > 20_000, 'La tarjeta debe tener calidad suficiente para redes'


class TestCssSinCodigoMuerto:
    MUERTAS = [
        '.booking-layout', '.booking-panel', '.booking-info', '.info-card',
        '.info-row', '.form-disclaimer', '.section-head', '.sh-label',
        '.module-card', '.module-grid', '.flip-card', '.stats-section',
        '.text-muted',
    ]

    def test_no_quedan_selectores_de_secciones_eliminadas(self, css):
        presentes = [sel for sel in self.MUERTAS if sel in css]
        assert not presentes, f'Quedaron reglas de secciones eliminadas: {presentes}'
