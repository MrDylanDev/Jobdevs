"""
Landing — S15: la banda se reduce a titular y una línea de texto.
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
def bloque_que_es(landing_html):
    inicio = landing_html.index('id="que-es"')
    fin = landing_html.index('id="metodologia"')
    return landing_html[inicio:fin]


class TestQueEsJobDevs:
    def test_seccion_existe_y_reemplaza_las_anteriores(self, landing_html):
        assert 'id="que-es"' in landing_html
        assert 'id="garantias"' not in landing_html
        assert 'id="sistemas"' not in landing_html

    def test_navbar_apunta_a_que_es(self, landing_html):
        assert re.search(r'<a href="#que-es">Qué es</a>', landing_html)

    def test_titular_pregunta_que_es_jobdevs(self, bloque_que_es):
        assert re.search(r'<h2[^>]*class="sh-title"[^>]*>¿Qué es ', bloque_que_es)
        assert 'JobDevs' in bloque_que_es

    def test_solo_un_parrafo_de_texto(self, bloque_que_es):
        parrafos = re.findall(r'<p class="desc-mono">([^<]+)</p>', bloque_que_es)
        assert len(parrafos) == 1, 'La sección debe tener un único párrafo'
        texto = parrafos[0].strip()
        assert 80 <= len(texto) <= 320, 'El texto debe ser breve'

    def test_sin_ficha_manifiesto_ni_negacion(self, bloque_que_es):
        for resto in ('what-spec', 'what-principle', 'what-numeral', 'what-negation',
                      'what-chips'):
            assert resto not in bloque_que_es, f'Quedó rastro: {resto}'

    def test_no_repite_el_proceso_de_como_funciona(self, bloque_que_es):
        for palabra in ('FASE_01', 'FASE_02', 'Publicar Proyecto', 'Postulación'):
            assert palabra not in bloque_que_es

    def test_css_minimo_de_la_seccion(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        for regla in ('.what-section', '.what-head', '.what-grid-bg'):
            assert regla in css, f'Falta la regla {regla}'
        for resto in ('.what-spec', '.what-principle', '.what-negation', '.what-inner'):
            assert resto not in css

    def test_banda_de_metricas_sigue_fuera(self, landing_html):
        for resto in ('stats-section', 'stats-grid', 'data-count', 'stat-number'):
            assert resto not in landing_html, f'Quedó rastro de la banda de métricas: {resto}'

    def test_js_sin_contador_animado(self):
        js = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'script' / 'index.js').read_text()
        assert 'number-display' not in js and 'counterObserver' not in js

    def test_testimonios_comparte_la_piel_de_la_banda(self, landing_html):
        inicio = landing_html.index('id="testimonios"')
        fin = landing_html.index('id="comenzar"') if 'id="comenzar"' in landing_html else len(landing_html)
        bloque = landing_html[inicio:fin]
        assert 'class="story-grid-bg"' in bloque, 'Casos de éxito debe tener el fondo de rejilla'
        assert 'class="section-inner story-head reveal"' in bloque, 'El encabezado debe usar story-head'
        assert 'section-marker' in bloque and 'sh-title' in bloque and 'desc-mono' in bloque
        assert 'style="margin-bottom: 48px;"' not in bloque, 'Sin estilos inline del encabezado viejo'

    def test_css_agrupa_las_bandas(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        assert '.logos-marquee-section,\n.what-section,\n.story-section {' in css
        assert '.logos-grid-bg,\n.what-grid-bg,\n.story-grid-bg {' in css
        assert '.logos-marquee-head,\n.what-head,\n.story-head {' in css


    def test_sin_manifiesto(self, bloque_que_es):
        """El manifiesto se retiró a pedido del operador; no debe volver por accidente."""
        assert 'what-manifesto' not in bloque_que_es
        assert 'MANIFIESTO' not in bloque_que_es
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        assert '.what-manifesto' not in css


    def test_css_sin_reglas_de_la_version_dual(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        assert 'booking-layout-dual' not in css
        # el layout de paneles se retiro con el cierre full-bleed: su CSS tambien
        for regla in ('.booking-layout', '.booking-panel', '.booking-info',
                      '.info-card', '.info-row'):
            assert regla not in css, f'Quedo CSS muerto: {regla}'

    def test_cierre_con_imagen_full_bleed(self, landing_html):
        inicio = landing_html.index('id="comenzar"')
        bloque = landing_html[inicio:]
        assert 'class="section-tech cta-hero"' in bloque
        assert 'cta-hero-img' in bloque and 'IMG/cta-final.jpg' in bloque
        assert 'cta-hero-overlay' in bloque
        assert 'alt="Equipo de desarrollo trabajando en una oficina"' in bloque

    def test_cierre_titulo_centrado_y_boton_a_registro(self, landing_html):
        inicio = landing_html.index('id="comenzar"')
        bloque = landing_html[inicio:]
        assert 'cta-hero-content' in bloque
        assert 'id="tituloComenzar"' in bloque
        assert re.search(r'<a href="[^"]*registro[^"]*" class="cta-hero-btn">\[ CREAR CUENTA \]</a>', bloque), (
            'El botón debe apuntar al registro y decir CREAR CUENTA'
        )
        assert 'booking-layout' not in bloque, 'La sección ya no usa el layout de paneles'

    def test_css_del_cierre(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        for regla in ('.cta-hero {', '.cta-hero-img', '.cta-hero-overlay',
                      '.cta-hero-content', '.cta-hero-btn'):
            assert regla in css, f'Falta la regla {regla}'
        assert 'object-fit: cover' in css
