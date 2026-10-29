"""
Pantalla de acceso del admin: sigue el tema claro/oscuro.

La plantilla `templates/admin/login.html` es autocontenida (paleta en línea), así
que necesita su propio arranque del tema y su propio juego de tokens, igual que
el registro.
"""

from pathlib import Path

import pytest
from django.conf import settings

TEMPLATE = Path(settings.BASE_DIR) / 'templates' / 'admin' / 'login.html'
URL = '/login/?next=/admin/dashboard/'

pytestmark = pytest.mark.django_db


@pytest.fixture(scope='module')
def html():
    return TEMPLATE.read_text(encoding='utf-8')


class TestArranqueDelTema:
    def test_la_vista_sirve_la_plantilla(self, client):
        respuesta = client.get(URL)
        assert respuesta.status_code == 200
        assert 'data-theme' in respuesta.content.decode()

    def test_el_script_va_antes_del_estilo(self, html):
        assert html.index('jobdevs-theme') < html.index('<style>'), (
            'Sin el script antes del CSS se ve el flash del tema equivocado'
        )

    def test_la_precedencia_es_guardado_sistema_oscuro(self, html):
        assert "localStorage.getItem('jobdevs-theme')" in html
        assert 'prefers-color-scheme: light' in html
        assert "var tema = 'dark';" in html

    def test_el_lang_usa_el_idioma_activo(self, html):
        assert '<html lang="{{ LANGUAGE_CODE }}">' in html


class TestPaletaClara:
    def test_existe_el_bloque_de_tema_claro(self, html):
        assert '[data-theme="light"] {' in html

    def test_los_tokens_se_invierten(self, html):
        bloque = html[html.index('[data-theme="light"] {'):]
        bloque = bloque[:bloque.index('}')]
        for par in ('--bg: #ffffff', '--text: #0b0f0c', '--border: #e4e7e5',
                    '--accent: #00713f', '--danger: #b91c1c'):
            assert par in bloque, f'Falta {par} en la paleta clara'

    def test_la_reticula_de_fondo_se_invierte(self, html):
        assert '[data-theme="light"] .bg-grid {' in html
        assert 'rgba(0,0,0,0.035) 1px' in html, (
            'La retícula era blanca: sobre blanco desaparece'
        )

    def test_el_boton_lleva_texto_blanco_en_claro(self, html):
        assert '[data-theme="light"] .btn-login { color: #ffffff; }' in html, (
            'El texto negro sobre el verde oscuro del tema claro queda en 3.4:1'
        )
