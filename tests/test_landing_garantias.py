"""
Landing — S10: la banda de "Garantías de operación" reemplaza la sección de
módulos (`#sistemas` / MODULE_02) y su navbar apunta a `#garantias`.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

METRICAS = [
    'SHA-256',
    'R2 PRIVADO',
    'SENA · DIAN',
    'HITO → APROBACIÓN',
    'PLAZO 7 DÍAS',
    'RTO 6,6 S',
]


@pytest.fixture(scope='module')
def landing_html():
    return render_to_string('publico/index.html')


@pytest.fixture(scope='module')
def bloque_garantias(landing_html):
    inicio = landing_html.index('id="garantias"')
    fin = landing_html.index('id="metodologia"')
    return landing_html[inicio:fin]


class TestGarantiasDeOperacion:
    def test_la_seccion_de_modulos_ya_no_existe(self, landing_html):
        assert 'id="sistemas"' not in landing_html
        assert 'MODULE_02' not in landing_html

    def test_navbar_apunta_a_garantias(self, landing_html):
        assert re.search(r'<a href="#garantias">Garantías</a>', landing_html)

    def test_seis_filas_con_indice_titulo_y_metrica(self, bloque_garantias):
        filas = re.findall(r'class="trust-row"', bloque_garantias)
        assert len(filas) == 6, 'La banda debe listar exactamente seis controles'

        indices = re.findall(r'class="trust-idx">/ (\d{2})<', bloque_garantias)
        assert indices == ['01', '02', '03', '04', '05', '06']

        titulos = re.findall(r'class="trust-title">([^<]+)<', bloque_garantias)
        assert len(titulos) == 6 and all(t.strip() for t in titulos)

        descripciones = re.findall(r'class="trust-desc">([^<]+)<', bloque_garantias)
        assert len(descripciones) == 6 and all(len(d.strip()) > 40 for d in descripciones)

    def test_metricas_duras_en_cada_fila(self, bloque_garantias):
        metricas = re.findall(r'class="trust-metric">([^<]+)<', bloque_garantias)
        assert metricas == METRICAS

    def test_css_del_trust_ledger_y_ausencia_de_flip_cards(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        for regla in ('.trust-ledger', '.trust-row', '.trust-idx', '.trust-title',
                      '.trust-desc', '.trust-metric'):
            assert regla in css, f'Falta la regla {regla}'
        assert '.flip-card' not in css, 'El CSS de las flip cards debe haberse retirado'

    def test_js_sin_manejadores_de_flip(self):
        js = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'script' / 'index.js').read_text()
        assert 'flip' not in js, 'El JS no debe conservar el toggle de flip cards'

    def test_cada_fila_trae_icono_y_estado_activo(self, bloque_garantias):
        assert len(re.findall(r'class="trust-icon"', bloque_garantias)) == 6
        assert len(re.findall(r'lucide-', bloque_garantias)) == 6
        assert len(re.findall(r'class="trust-state"', bloque_garantias)) == 6
        assert len(re.findall(r'class="trust-dot"', bloque_garantias)) == 6

    def test_panel_con_marco_y_linea_de_cierre(self, bloque_garantias):
        assert 'class="trust-panel tech-frame' in bloque_garantias
        assert 'class="trust-foot' in bloque_garantias
        assert 'operan en producción' in bloque_garantias

    def test_css_de_icono_estado_y_marco(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        for regla in ('.trust-icon', '.trust-state', '.trust-dot', '.trust-panel',
                      '.trust-row::before', '.trust-foot'):
            assert regla in css, f'Falta la regla {regla}'
