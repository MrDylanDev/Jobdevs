"""
Landing — S11: la banda "¿Qué es JobDevs?" se compone de statement, ficha
técnica, tres principios y una línea de negación. No narra el proceso.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

ESPEC = [
    ('PLATAFORMA', 'JobDevs'),
    ('CATEGORÍA', 'Infraestructura de trabajo'),
    ('MODELO', 'Contrato por hitos'),
    ('MERCADO', 'Colombia'),
    ('VERIFICACIÓN', 'SENA · DIAN'),
    ('RESPALDO', 'RTO 6,6 s'),
]


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

    def test_statement_y_entradilla(self, bloque_que_es):
        assert 'El sistema operativo' in bloque_que_es
        assert 'talento SENA' in bloque_que_es
        assert 'what-lede' in bloque_que_es

    def test_ficha_tecnica_con_seis_campos(self, bloque_que_es):
        filas = re.findall(
            r'class="what-spec-row"><dt>([^<]+)</dt><dd>([^<]+)</dd>', bloque_que_es
        )
        assert filas == ESPEC

    def test_tres_principios_numerados(self, bloque_que_es):
        numerales = re.findall(r'class="what-numeral" aria-hidden="true">(\d{2})<', bloque_que_es)
        assert numerales == ['01', '02', '03']

        titulos = re.findall(r'class="what-principle-title">([^<]+)<', bloque_que_es)
        assert titulos == ['Contratos, no favores', 'Evidencia, no promesas', 'Reputación, no contactos']

        descripciones = re.findall(r'class="what-principle-desc">([^<]+)<', bloque_que_es)
        assert len(descripciones) == 3 and all(len(d) > 50 for d in descripciones)

    def test_linea_de_negacion(self, bloque_que_es):
        assert 'what-negation' in bloque_que_es
        assert 'No es una bolsa de empleo' in bloque_que_es

    def test_no_repite_el_proceso_de_como_funciona(self, bloque_que_es):
        for palabra in ('FASE_01', 'FASE_02', 'Publicar Proyecto', 'Postulación'):
            assert palabra not in bloque_que_es, f'La sección no debe narrar el proceso ({palabra})'

    def test_css_de_la_composicion(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        for regla in ('.what-section', '.what-head', '.what-statement', '.what-spec',
                      '.what-spec-row', '.what-principles', '.what-numeral',
                      '.what-principle-title', '.what-negation'):
            assert regla in css, f'Falta la regla {regla}'
        assert '.trust-' not in css, 'No deben quedar reglas del ledger anterior'
