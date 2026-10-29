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


class TestTextosDelJs:
    """El JS no guarda copias en español: los textos traducibles viven en un
    bloque JSON que llena el template."""

    CLAVES = ('authTitle', 'recoveryTitle', 'sending', 'recoveryOk', 'backToLogin', 'connectionError')

    def _json(self, contenido):
        import json

        trozo = contenido.split('id="textos-i18n">', 1)[1].split('</script>', 1)[0]
        return json.loads(trozo)

    def test_el_bloque_de_textos_existe_y_esta_completo(self, client):
        datos = self._json(client.get('/').content.decode())
        for clave in self.CLAVES:
            assert datos.get(clave), f'Falta el texto {clave}'

    def test_en_espanol_trae_los_textos_en_espanol(self, client):
        datos = self._json(client.get('/').content.decode())
        assert datos['authTitle'] == 'AUTENTICACIÓN SEGURA'
        assert datos['sending'] == '[ ENVIANDO... ]'

    def test_en_ingles_trae_los_textos_en_ingles(self, client):
        datos = self._json(client.get('/en/').content.decode())
        assert datos['authTitle'] == 'SECURE AUTHENTICATION'
        assert datos['sending'] == '[ SENDING... ]'

    def test_el_js_ya_no_hardcodea_los_titulos(self):
        from django.conf import settings

        js = (Path(settings.BASE_DIR) / 'static' / 'publico' / 'script' / 'index.js').read_text(encoding='utf-8')
        assert "texto('authTitle'" in js and "texto('recoveryTitle'" in js
        assert "= 'AUTENTICACIÓN SEGURA'" not in js, 'Quedó el literal en español en el JS'


class TestUrlDeterminaElIdioma:
    """La URL manda: `/` es español aunque el navegador pida inglés, y `/en/` es
    inglés aunque el navegador pida español. Sin esto, Accept-Language decidía el
    contenido de la raíz y el español se quedaba sin URL canónica."""

    def test_la_raiz_ignora_accept_language_ingles(self, client):
        respuesta = client.get('/', headers={'accept-language': 'en-US,en;q=0.9'})
        contenido = respuesta.content.decode()
        assert '<html lang="es-co">' in contenido
        assert 'Qué es' in contenido and 'What it is' not in contenido

    def test_el_prefijo_ingles_ignora_accept_language_espanol(self, client):
        respuesta = client.get('/en/', headers={'accept-language': 'es-CO,es;q=0.9'})
        contenido = respuesta.content.decode()
        assert '<html lang="en">' in contenido
        assert 'What it is' in contenido

    def test_el_middleware_esta_despues_del_de_idioma(self):
        middleware = settings.MIDDLEWARE
        assert 'config.middleware_idioma.IdiomaPorDefectoSinPrefijo' in middleware
        assert middleware.index('django.middleware.locale.LocaleMiddleware') < middleware.index(
            'config.middleware_idioma.IdiomaPorDefectoSinPrefijo'
        )
