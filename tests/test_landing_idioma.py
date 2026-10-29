"""
Idioma de la landing pública: español en `/` e inglés en `/en/`.

Cubren lo que puede romperse sin que se note: que el español no cambie de URL,
que el inglés exista y se sirva con el atributo `lang` correcto, que el
conmutador del navbar apunte al idioma opuesto, y que las pantallas de acceso
existan en los dos idiomas.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

TEMPLATE = Path(settings.BASE_DIR) / 'templates' / 'publico' / 'index.html'

pytestmark = pytest.mark.django_db


class TestDosIdiomas:
    def test_configuracion(self):
        codigos = [codigo for codigo, _ in settings.LANGUAGES]
        assert codigos == ['es-co', 'en']
        assert settings.LANGUAGE_CODE == 'es-co'
        assert any('locale' in str(ruta) for ruta in settings.LOCALE_PATHS)

    def test_el_middleware_de_idioma_esta_instalado(self):
        assert 'django.middleware.locale.LocaleMiddleware' in settings.MIDDLEWARE
        indice_sesion = settings.MIDDLEWARE.index('django.contrib.sessions.middleware.SessionMiddleware')
        indice_idioma = settings.MIDDLEWARE.index('django.middleware.locale.LocaleMiddleware')
        assert indice_idioma > indice_sesion, 'LocaleMiddleware va después de SessionMiddleware'


class TestUrls:
    def test_el_espanol_sigue_en_la_raiz(self, client):
        respuesta = client.get('/')
        assert respuesta.status_code == 200
        assert '<html lang="es-co">' in respuesta.content.decode()

    def test_el_ingles_vive_en_el_prefijo_en(self, client):
        respuesta = client.get('/en/')
        assert respuesta.status_code == 200
        assert '<html lang="en">' in respuesta.content.decode()

    def test_las_rutas_de_acceso_existen_en_los_dos_idiomas(self, client):
        assert client.get('/registro/').status_code == 200
        assert client.get('/en/registro/').status_code == 200

    def test_el_prefijo_por_defecto_no_se_agrega(self):
        from django.utils.translation import override

        with override(settings.LANGUAGE_CODE):
            assert reverse('inicio') == '/', 'El español no lleva prefijo'
        with override('en'):
            assert reverse('inicio') == '/en/'


class TestConmutador:
    def test_en_espanol_lleva_al_ingles(self, client):
        contenido = client.get('/').content.decode()
        enlace = re.search(r'<a class="lang-switch" href="([^"]+)"[^>]*>', contenido)
        assert enlace, 'Falta el conmutador de idioma en el navbar'
        assert enlace.group(1) == '/en/'
        assert 'lucide-globe' in contenido, 'El conmutador tiene que llevar el icono de idioma'
        assert '>EN<' in contenido

    def test_en_ingles_vuelve_al_espanol(self, client):
        contenido = client.get('/en/').content.decode()
        enlace = re.search(r'<a class="lang-switch" href="([^"]+)"[^>]*>', contenido)
        assert enlace, 'Falta el conmutador de idioma en el navbar'
        assert enlace.group(1) == '/'
        assert '>ES<' in contenido

    def test_el_conmutador_tiene_hreflang_y_nombre_accesible(self, client):
        contenido = client.get('/').content.decode()
        etiqueta = re.search(r'<a class="lang-switch"[^>]*>', contenido).group(0)
        assert 'hreflang="en"' in etiqueta
        assert 'aria-label=' in etiqueta

    def test_en_movil_el_conmutador_vive_en_el_menu(self):
        plantilla = TEMPLATE.read_text(encoding='utf-8')
        menu = plantilla[plantilla.index('id="navLinks"'):plantilla.index('class="nav-right"')]
        assert 'English' in menu or 'Español' in menu, (
            'En móvil el conmutador se esconde de la barra: tiene que estar en el menú'
        )
