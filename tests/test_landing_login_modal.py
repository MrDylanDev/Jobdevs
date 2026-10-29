"""
Landing — el modal de login debe usar una sola instancia de Bootstrap.

Instanciar el modal varias veces sobre el mismo elemento producía dos backdrops
y dejaba el `body` con `modal-open` después de cerrar (página bloqueada).
"""

from pathlib import Path

import pytest
from django.conf import settings


@pytest.fixture(scope='module')
def landing_js():
    return (Path(settings.BASE_DIR) / 'static' / 'publico' / 'script' / 'index.js').read_text()


@pytest.fixture(scope='module')
def landing_html():
    from django.template.loader import render_to_string
    return render_to_string('publico/index.html')


class TestLoginModalInstanciaUnica:
    def test_usa_get_or_create_instance(self, landing_js):
        assert 'bootstrap.Modal.getOrCreateInstance' in landing_js

    def test_no_crea_instancias_sueltas(self, landing_js):
        sueltas = [
            linea.strip()
            for linea in landing_js.splitlines()
            if 'bootstrap.Modal(' in linea and not linea.strip().startswith('//')
        ]
        assert not sueltas, f'No debe instanciarse el modal directamente: {sueltas}'

    def test_un_unico_helper_de_apertura(self, landing_js):
        assert landing_js.count('function abrirLoginModal()') == 1
        assert landing_js.count('abrirLoginModal()') == 3, (
            'El helper se define una vez y se usa en los dos puntos de apertura'
        )

    def test_el_parametro_login_se_atiende_una_sola_vez(self, landing_js):
        assert landing_js.count("get('login')") == 1
        assert "includes('login=1')" not in landing_js, (
            'El auto-open duplicado por ?login=1 se eliminó a propósito'
        )

    def test_el_modal_existe_y_recibe_los_mensajes(self, landing_html):
        assert 'id="loginModal"' in landing_html
        # El contenedor de mensajes sólo se renderiza si hay mensajes: se valida
        # en la plantilla, no en el HTML renderizado sin contexto.
        plantilla = (Path(settings.BASE_DIR) / 'templates' / 'publico' / 'index.html').read_text()
        assert '{% if messages %}' in plantilla
        assert 'id="django-messages"' in plantilla

    def test_puntero_visible_dentro_del_modal(self):
        """El cursor custom queda debajo del modal: dentro debe volver el nativo."""
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        assert '.modal-open .cursor-dot' in css and '.modal-open .cursor-ring' in css
        assert 'body.modal-open' in css
        assert '.modal-open .modal input' in css
        assert 'cursor: text !important' in css
        assert '.modal-open .modal button' in css
        assert 'cursor: pointer !important' in css


class TestMarqueeHeroInfinito:
    """La banda del hero debe rellenarse para no cortarse en pantallas anchas."""

    @pytest.fixture(scope='class')
    def js(self):
        return (Path(settings.BASE_DIR) / 'static' / 'publico' / 'script' / 'index.js').read_text()

    def test_rellena_hasta_cubrir_la_pantalla(self, js):
        assert 'armarMarquee' in js
        assert 'marqueeTrack.scrollWidth < window.innerWidth' in js, (
            'Debe repetir el contenido hasta cubrir el ancho de la pantalla'
        )

    def test_duplica_la_mitad_y_fija_duracion(self, js):
        assert 'marqueeTrack.innerHTML += marqueeTrack.innerHTML' in js
        assert 'animationDuration' in js

    def test_se_rearma_al_redimensionar(self, js):
        assert "addEventListener('resize'" in js
        assert 'armarMarquee' in js.split("addEventListener('resize'")[1]
