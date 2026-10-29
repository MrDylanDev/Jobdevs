"""
Landing — el modal de login no depende de Bootstrap (SCRUM-421).

Antes lo abría `bootstrap.Modal`, que costaba 80 KB de JS desde un segundo CDN y
sólo se usaba para este modal. Ahora hay un controlador propio; estos tests fijan
el checklist de accesibilidad que Bootstrap cubría, para que sacarlo no degrade
el comportamiento.
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


class TestLoginModalSinBootstrap:
    def test_no_queda_ninguna_referencia_a_bootstrap(self, landing_js):
        assert 'bootstrap.Modal' not in landing_js, (
            'Mientras quede una referencia, el bundle sigue siendo necesario'
        )
        assert 'data-bs-' not in landing_js

    def test_un_unico_par_de_apertura_y_cierre(self, landing_js):
        assert landing_js.count('function abrirLoginModal()') == 1
        assert landing_js.count('function cerrarLoginModal()') == 1
        assert landing_js.count('abrirLoginModal()') == 4, (
            'Se define una vez y se usa en los tres puntos de apertura: mensajes '
            'de Django, el parámetro ?login=1 y el botón [ INGRESAR ]'
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


class TestChecklistDelModal:
    """El checklist de accesibilidad del ticket, punto por punto. El e2e lo prueba
    además en navegador con teclado real."""

    def test_escape_cierra(self, landing_js):
        assert "e.key === 'Escape'" in landing_js

    def test_clic_en_el_fondo_cierra_y_dentro_no(self, landing_js):
        assert 'e.target === loginModalEl' in landing_js, (
            'El velo lo pinta el propio .modal, así que el fondo es el elemento'
        )

    def test_bloquea_el_scroll_del_body(self, landing_js):
        assert "classList.add('modal-open')" in landing_js
        assert "classList.remove('modal-open')" in landing_js

    def test_la_clase_de_bloqueo_hace_algo(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()
        assert 'body.modal-open { overflow: hidden; }' in css, (
            'La clase la ponía Bootstrap y el overflow venía de su CSS'
        )

    def test_aria_al_abrir_y_cerrar(self, landing_js, landing_html):
        assert "setAttribute('aria-hidden', 'false')" in landing_js
        assert "setAttribute('aria-hidden', 'true')" in landing_js
        assert 'aria-modal="true"' in landing_html
        assert 'role="dialog"' in landing_html

    def test_el_foco_entra_al_primer_campo(self, landing_js):
        assert "querySelector('#username')" in landing_js

    def test_el_foco_vuelve_al_que_abrio(self, landing_js):
        assert 'focoPrevio = document.activeElement' in landing_js
        assert 'focoPrevio.focus()' in landing_js

    def test_tabulacion_contenida(self, landing_js):
        assert "e.key !== 'Tab'" in landing_js
        assert 'e.shiftKey' in landing_js

    def test_el_foco_sale_antes_de_ocultar_el_modal(self, landing_js):
        # Al revés, el foco queda dentro de un nodo aria-hidden y los lectores de
        # pantalla lo pierden.
        cuerpo = landing_js[landing_js.index('function cerrarLoginModal()'):]
        cuerpo = cuerpo[:cuerpo.index('document.querySelectorAll')]
        assert cuerpo.index('focoPrevio.focus()') < cuerpo.index("setAttribute('aria-hidden', 'true')")
