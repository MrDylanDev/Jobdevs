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


class TestCacheDeLosEstaticos:
    """nginx sirve /static/ con `immutable, max-age=30d`. Sin versión en la URL,
    un cambio de CSS no llega al navegador aunque se recargue."""

    def test_el_css_del_registro_lleva_version(self, html):
        assert "{% asset 'publico/css/styleregistro.css' %}" in html, (
            'La URL del CSS tiene que cambiar cuando cambia el archivo'
        )

    def test_la_landing_tambien_versiona_css_y_js(self):
        landing = (Path(settings.BASE_DIR) / 'templates' / 'publico' / 'index.html').read_text(encoding='utf-8')
        assert "{% asset 'publico/css/index.css' %}" in landing
        assert "{% asset 'publico/script/index.js' %}" in landing

    def test_la_etiqueta_agrega_la_fecha_de_modificacion(self):
        from django.template import Context, Template

        salida = Template("{% load assets %}{% asset 'publico/css/styleregistro.css' %}").render(Context())
        assert salida.startswith('/static/publico/css/styleregistro.css?v='), salida
        assert salida.split('?v=')[1].isdigit()


class TestPanelSobreLaFoto:
    """El panel izquierdo del registro vive siempre sobre la foto: su texto no
    puede heredar el color del tema o queda oscuro sobre una imagen oscura."""

    def test_el_texto_del_panel_es_blanco_en_claro(self, css):
        bloque = css[css.index('[data-theme="light"] .register-image-content,'):]
        bloque = bloque[:bloque.index('}')]
        assert '.register-image-content .logo' in bloque
        assert '.register-image-content h2' in bloque
        assert 'color: #ffffff' in bloque
        assert '[data-theme="light"] .register-image-content p { color: rgba(255, 255, 255, 0.80); }' in css

    def test_el_oscuro_no_cambia(self, css):
        assert '[data-theme="light"] .register-image-content' in css
        assert '.register-image-content h2 {\n  font-family: var(--font-main);\n  font-size: 2.2rem;\n  font-weight: 700;\n  color: var(--fg);' in css, (
            'La regla base del oscuro tiene que seguir usando --fg'
        )


class TestJsDelRegistro:
    """El JS del registro no guarda copias en español y su URL lleva versión."""

    def test_el_script_lleva_version(self, html):
        assert "{% asset 'publico/script/registro.js' %}" in html, (
            'Sin versión en la URL, el navegador sigue usando el JS viejo'
        )

    def test_los_textos_viven_en_el_bloque_traduducible(self, html):
        assert 'id="textos-i18n"' in html
        for clave in ('docNit', 'docNumero', 'passwordMismatch'):
            assert f'"{clave}"' in html, f'Falta el texto {clave}'

    def test_el_js_ya_no_hardcodea_etiquetas(self):
        js = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'script' / 'registro.js').read_text(encoding='utf-8')
        assert "texto('docNit'" in js and "texto('passwordMismatch'" in js
        assert "innerText = 'NIT O NÚMERO" not in js
        assert "alert('Las contraseñas" not in js

    def test_en_ingles_sirve_los_textos_en_ingles(self, client):
        contenido = client.get('/en/registro/').content.decode()
        assert '"docNit": "NIT OR ID NUMBER"' in contenido
        assert 'The passwords you entered do not match' in contenido

    def test_en_espanol_sirve_los_textos_en_espanol(self, client):
        contenido = client.get('/registro/').content.decode()
        assert '"docNit": "NIT O NÚMERO DE IDENTIFICACIÓN"' in contenido


class TestRegistroSinCdn:
    """El registro no debe depender de Font Awesome ni CDNs externos."""

    def test_no_queda_enlace_a_font_awesome(self, html):
        assert 'font-awesome' not in html.lower()
        assert 'cdnjs.cloudflare.com' not in html

    def test_css_sin_import_bloqueante(self, css):
        assert '@import' not in css

