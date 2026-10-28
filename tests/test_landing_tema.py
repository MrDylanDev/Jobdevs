"""
Landing — tema claro / oscuro.

El botón del navbar alterna la paleta completa de la landing. Estos tests fijan
las cuatro cosas que se pueden romper sin que nadie lo note a simple vista:
que el tema se resuelva antes del primer paint, que el tema claro tenga una
paleta propia con contraste AA, que el oscuro no haya cambiado, y que no vuelvan
a colarse literales de color crudos en la piel.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

CSS_PATH = Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css'
JS_PATH = Path(settings.BASE_DIR) / 'static' / 'publico' / 'script' / 'index.js'

# Tokens que el tema oscuro tenía hardcodeados y ahora salen de la capa semántica.
TOKENS_OSCUROS = {
    '--bg': '#000000',
    '--bg-darker': '#050505',
    '--bg-card': '#0a0a0a',
    '--bg-card-hover': '#111111',
    '--fg': '#ffffff',
    '--fg-dim': '#a0a0a0',
    '--muted': '#555555',
    '--border-dim': '#1a1a1a',
    '--border-mid': '#333333',
    '--border-high': '#ffffff',
    '--accent': '#00e676',
    '--accent-dim': '#00c853',
    '--scrim-rgb': '0, 0, 0',
    '--scrim-deep-rgb': '5, 5, 5',
    '--scrim-panel-rgb': '9, 9, 11',
    '--band-bg': '#09090b',
    '--ink-rgb': '255, 255, 255',
    '--on-accent': '#000',
}

BLANCO, NEGRO = '#ffffff', '#000000'


@pytest.fixture(scope='module')
def css():
    return CSS_PATH.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def js():
    return JS_PATH.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def html():
    return render_to_string('publico/index.html')


def bloque(css, selector):
    """Devuelve el cuerpo de un bloque de declaración por su selector exacto."""
    inicio = css.index(selector + ' {')
    return css[inicio:css.index('}', inicio)]


def declaraciones(cuerpo):
    out = {}
    for nombre, valor in re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', cuerpo):
        out[nombre] = valor.strip()
    return out


def rgb(color):
    """Normaliza #rgb / #rrggbb / 'r, g, b' a una tupla de enteros."""
    color = color.strip()
    if color.startswith('#'):
        h = color[1:]
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(p.strip()) for p in color.split(','))


def luminancia(color):
    def canal(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(v) for v in rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    la, lb = luminancia(a), luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


@pytest.fixture(scope='module')
def claro(css):
    return declaraciones(bloque(css, '[data-theme="light"]'))


class TestArranqueSinFlash:
    """S4: el tema se decide antes de que se pinte la página."""

    def test_script_de_tema_va_antes_de_la_hoja_de_estilos(self, html):
        idx_script = html.index("localStorage.getItem('jobdevs-theme')")
        idx_css = html.index('publico/css/index.css')
        assert idx_script < idx_css, (
            'Si el tema se resuelve después de cargar el CSS se ve el flash del tema equivocado'
        )

    def test_el_script_fija_el_atributo_en_el_elemento_raiz(self, html):
        assert "document.documentElement.setAttribute('data-theme', tema)" in html

    def test_prioridad_guardado_sobre_sistema(self, html):
        idx_guardado = html.index("localStorage.getItem('jobdevs-theme')")
        idx_sistema = html.index('(prefers-color-scheme: light)')
        assert idx_guardado < idx_sistema, 'La elección guardada debe ganarle al sistema'

    def test_localstorage_bloqueado_no_rompe_el_arranque(self, html):
        assert 'catch (e)' in html, 'En modo privado localStorage lanza: hay que tolerarlo'


class TestBotonDeTema:
    """S1 y S7: el control existe, es accesible y está en el navbar."""

    def test_el_boton_esta_en_el_navbar(self, html):
        navbar = html[html.index('id="navbar"'):html.index('id="inicio"')]
        assert 'id="themeToggle"' in navbar, 'El botón de tema tiene que vivir en el navbar'

    def test_expone_el_estado_con_aria_pressed(self, html):
        assert 'id="themeToggle"' in html
        assert 'aria-pressed="false"' in html

    def test_tiene_nombre_accesible_que_no_cambia(self, html):
        assert 'aria-label="Tema claro"' in html, (
            'Con aria-pressed el nombre accesible debe ser estable, no la acción'
        )

    def test_es_un_button_de_verdad(self, html):
        assert re.search(r'<button[^>]*type="button"[^>]*id="themeToggle"', html) or \
               re.search(r'<button[^>]*id="themeToggle"[^>]*type="button"', html), (
            'Debe ser <button type="button"> para ser operable por teclado'
        )

    def test_no_se_oculta_en_movil(self, css):
        movil = css[css.index('@media (max-width: 767.98px)'):]
        assert '.nav-right .nav-cta { display: none; }' in movil
        assert '.theme-toggle-label { display: none; }' in movil, (
            'En móvil se achica a icono, pero no desaparece'
        )
        assert '.theme-toggle { display: none' not in css, 'El botón nunca se oculta'


class TestPaletaClara:
    """S1 y S5: el tema claro es una paleta propia, no una inversión a ciegas."""

    def test_el_bloque_de_tema_claro_existe(self, css):
        assert '[data-theme="light"] {' in css

    def test_invierte_la_capa_semantica(self, claro):
        assert rgb(claro['--scrim-rgb']) == rgb(BLANCO)
        assert rgb(claro['--scrim-deep-rgb']) == rgb(BLANCO)
        assert rgb(claro['--scrim-panel-rgb']) == rgb(BLANCO)
        assert rgb(claro['--band-bg']) == rgb(BLANCO)
        assert rgb(claro['--ink-rgb']) == rgb(NEGRO)

    def test_el_acento_tiene_su_propio_verde(self, claro):
        assert rgb(claro['--accent']) != rgb('#00e676'), (
            'El verde fosforescente sobre blanco da 1.6:1: ilegible'
        )

    def test_fondo_y_texto_se_invierten(self, claro):
        assert rgb(claro['--bg']) == rgb(BLANCO)
        assert luminancia(claro['--fg']) < 0.05, 'El texto del tema claro debe ser oscuro'

    def test_declara_color_scheme_para_controles_nativos(self, css):
        assert 'color-scheme: dark;' in css
        assert 'color-scheme: light;' in css, 'Sin esto, scrollbars y autofill siguen oscuros'


class TestContrasteAA:
    """S5: el modo claro no puede ser bonito e ilegible."""

    @pytest.mark.parametrize('token,minimo', [
        ('--fg', 4.5),
        ('--fg-dim', 4.5),
        ('--muted', 4.5),
        ('--accent', 4.5),
    ])
    def test_texto_sobre_fondo_principal(self, claro, token, minimo):
        for fondo in ('--bg', '--bg-darker'):
            ratio = contraste(claro[token], claro[fondo])
            assert ratio >= minimo, (
                f'{token} sobre {fondo} da {ratio:.2f}:1, por debajo de {minimo}:1'
            )

    def test_texto_sobre_relleno_de_acento(self, claro):
        ratio = contraste(claro['--on-accent'], claro['--accent'])
        assert ratio >= 4.5, f'Texto sobre el acento da {ratio:.2f}:1'

    def test_acento_tambien_legible_como_texto(self, claro):
        assert contraste(claro['--accent'], claro['--bg']) >= 4.5


class TestSinRegresionEnOscuro:
    """S6: migrar literales a tokens no podía cambiar el tema oscuro."""

    @pytest.mark.parametrize('token,valor', sorted(TOKENS_OSCUROS.items()))
    def test_token_conserva_su_valor_original(self, css, token, valor):
        raiz = declaraciones(bloque(css, ':root'))
        assert token in raiz, f'Falta {token} en :root'
        assert rgb(raiz[token]) == rgb(valor), f'{token} cambió en el tema oscuro'

    def test_no_quedan_literales_de_las_familias_migradas(self, css):
        # La piel base y los componentes deben salir de tokens. Los bloques del
        # tema claro quedan afuera a propósito: ahí una sombra negra o un velo
        # blanco explícito son correctos y no tienen por qué invertirse.
        cuerpo = re.sub(r':root\s*\{.*?\n\}', '', css, count=1, flags=re.S)
        cuerpo = re.sub(r'\[data-theme="light"\][^{]*\{[^}]*\}', '', cuerpo)
        for familia, nombre in (
            (r'rgba\(\s*0\s*,\s*0\s*,\s*0', '--scrim-rgb'),
            (r'rgba\(\s*5\s*,\s*5\s*,\s*5', '--scrim-deep-rgb'),
            (r'rgba\(\s*9\s*,\s*9\s*,\s*11', '--scrim-panel-rgb'),
            (r'rgba\(\s*255\s*,\s*255\s*,\s*255', '--ink-rgb'),
        ):
            assert not re.search(familia, cuerpo), (
                f'Quedó un literal que debería usar {nombre}; en claro no se invierte'
            )

    def test_las_mascaras_siguen_usando_negro_como_canal_alfa(self, css):
        assert 'mask-image: radial-gradient(ellipse 75% 70% at 50% 45%, #000 25%' in css, (
            'El #000 de mask-image es canal alfa: tokenizarlo deja la máscara plana'
        )


class TestComportamiento:
    """S4: alternar, recordar y seguir al sistema cuando no hay elección."""

    def test_el_clic_alterna_y_recuerda(self, js):
        assert "getItem('jobdevs-theme')" in js or "getItem(CLAVE_TEMA)" in js
        assert "setItem(CLAVE_TEMA, tema)" in js
        assert "temaActual() === 'light' ? 'dark' : 'light'" in js

    def test_actualiza_aria_pressed_al_pintar(self, js):
        assert "setAttribute('aria-pressed'" in js

    def test_sigue_al_sistema_solo_sin_eleccion_guardada(self, js):
        assert 'prefers-color-scheme: light' in js
        assert "if (guardado === 'light' || guardado === 'dark') return;" in js

    def test_la_transicion_respeta_prefers_reduced_motion(self, css):
        assert 'prefers-reduced-motion: no-preference' in css
