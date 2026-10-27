"""
Landing — S11: la banda "¿Qué es JobDevs?" responde posicionamiento (qué es y
qué no es) sin repetir el proceso de "Cómo funciona".
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

CHIPS = ['SHA-256', 'R2 PRIVADO', 'SENA · DIAN', 'HITO → APROBACIÓN', 'PLAZO 7 DÍAS', 'RTO 6,6 S']


@pytest.fixture(scope='module')
def landing_html():
    return render_to_string('publico/index.html')


@pytest.fixture(scope='module')
def bloque_que_es(landing_html):
    inicio = landing_html.index('id="que-es"')
    fin = landing_html.index('id="metodologia"')
    return landing_html[inicio:fin]


class TestQueEsJobDevs:
    def test_seccion_existe_y_reemplaza_la_anterior(self, landing_html):
        assert 'id="que-es"' in landing_html
        assert 'id="garantias"' not in landing_html
        assert 'id="sistemas"' not in landing_html

    def test_navbar_apunta_a_que_es(self, landing_html):
        assert re.search(r'<a href="#que-es">Qué es</a>', landing_html)

    def test_statement_y_entradilla(self, bloque_que_es):
        assert 'El sistema operativo' in bloque_que_es
        assert 'talento SENA' in bloque_que_es
        assert 'what-lede' in bloque_que_es

    def test_contraste_no_es_y_es(self, bloque_que_es):
        negativos = re.findall(r'what-item--no"><span class="what-mark">−</span>([^<]+)<', bloque_que_es)
        positivos = re.findall(r'what-item--yes"><span class="what-mark">\+</span>([^<]+)<', bloque_que_es)
        assert len(negativos) == 4, 'Debe haber cuatro cosas que JobDevs no es'
        assert len(positivos) == 4, 'Debe haber cuatro cosas que JobDevs sí es'
        assert all(t.strip() for t in negativos + positivos)

    def test_no_repite_el_proceso_de_como_funciona(self, bloque_que_es):
        for palabra in ('FASE_01', 'FASE_02', 'Publicar Proyecto', 'Postulación'):
            assert palabra not in bloque_que_es, f'La sección no debe narrar el proceso ({palabra})'

    def test_conserva_las_metricas_duras_en_chips(self, bloque_que_es):
        chips = re.findall(r'<li>([^<]+)</li>', bloque_que_es)
        assert chips == CHIPS

    def test_css_de_la_seccion(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        for regla in ('.what-section', '.what-statement', '.what-compare',
                      '.what-item--no', '.what-item--yes', '.what-chips-list li'):
            assert regla in css, f'Falta la regla {regla}'
        assert '.trust-' not in css, 'No deben quedar reglas del ledger anterior'
