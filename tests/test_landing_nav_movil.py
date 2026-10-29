"""
Landing — navegación móvil: el botón [ MENU ] no debe quedar oculto y el
breakpoint no puede solaparse con el `md` de Bootstrap (768px), que esconde el
link de ingreso del menú.
"""

from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string


@pytest.fixture(scope='module')
def css():
    return (Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css').read_text()


@pytest.fixture(scope='module')
def html():
    return render_to_string('publico/index.html')


class TestNavMovil:
    def test_el_contenedor_de_la_nav_no_se_oculta_en_movil(self, css):
        assert '.nav-right { display: none; }' not in css, (
            'Ocultar .nav-right esconde también el botón [ MENU ]'
        )
        assert '.nav-right .nav-cta { display: none; }' in css, (
            'En móvil debe ocultarse solo el CTA de escritorio'
        )

    def test_el_boton_de_menu_queda_visible(self, css):
        bloque = css[css.index('@media (max-width: 767.98px)'):]
        assert '.btn-mobile-menu { display: flex' in bloque

    def test_breakpoint_alineado_con_bootstrap(self, css):
        assert '@media (max-width: 767.98px)' in css
        assert '@media (max-width: 768px)' not in css, (
            'A 768px se solapaba con el md de Bootstrap y no había acceso al login'
        )

    def test_markup_del_menu_con_ingreso(self, html):
        assert 'id="mobileMenuBtn"' in html
        assert 'id="navLinks"' in html
        assert 'data-bs-target="#loginModal"' in html
