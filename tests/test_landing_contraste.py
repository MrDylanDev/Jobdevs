"""
Landing — contraste bajo los glifos en el hero y en el modal (SCRUM-424/425).

El hero del tema oscuro es texto blanco sobre una foto con velo. El peor caso no
está en la mediana sino en los píxeles claros de la foto que caen justo debajo de
una letra, así que el velo se especifica por su piso de opacidad, no por su
aspecto promedio: un piso demasiado bajo deja el párrafo en 3.1:1 en un teléfono.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

CSS_PATH = Path(settings.BASE_DIR) / 'static' / 'publico' / 'css' / 'index.css'
PLANTILLA = Path(settings.BASE_DIR) / 'templates' / 'publico' / 'index.html'

# Piso de velo que sostiene AA (4.5:1) para el párrafo del hero sobre cualquier
# píxel de la foto, medido a 390x844 sobre las siete fotos del reel.
PISO_VELO_MOVIL = 0.70


@pytest.fixture(scope='module')
def css():
    return CSS_PATH.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def html():
    return render_to_string('publico/index.html')


def bloque_movil(css):
    """Cuerpo del breakpoint donde el hero pasa a una sola columna."""
    inicio = css.index('@media (max-width: 767.98px) {')
    return css[inicio:]


def regla(css, selector):
    inicio = css.index(selector + ' {')
    return css[inicio:css.index('}', inicio)]


def rgb(color):
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


def tokens_tema(css, tema):
    selector = ':root' if tema == 'oscuro' else '[data-theme="light"]'
    cuerpo = regla(css, selector)
    return dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', cuerpo))


class TestPisoDeVeloEnMovil:
    """S1: a 390px el titular ocupa todo el ancho y el velo horizontal del hero
    queda en 0.02 en el centro. El párrafo cruzaba la foto casi al natural."""

    def test_el_breakpoint_movil_redefine_el_velo_del_hero(self, css):
        assert '.hero-overlay {' in bloque_movil(css), (
            'Sin una regla propia en móvil sigue vigente el velo de escritorio, '
            'que en el centro del ancho es prácticamente transparente'
        )

    def test_el_piso_del_velo_sostiene_el_contraste(self, css):
        movil = bloque_movil(css)
        regla_hero = movil[movil.index('.hero-overlay {'):]
        regla_hero = regla_hero[:regla_hero.index('}')]
        alfas = [float(a) for a in re.findall(r'rgba\(var\(--scrim-rgb\),\s*([\d.]+)\)', regla_hero)]
        assert alfas, 'El velo de móvil tiene que declarar paradas con --scrim-rgb'
        assert min(alfas) >= PISO_VELO_MOVIL, (
            f'El piso del velo ({min(alfas)}) deja el párrafo por debajo de 4.5:1 '
            f'en las fotos claras; medido, 0.55 da 3.72:1'
        )

    def test_el_velo_movil_no_pisa_el_del_tema_claro(self, css):
        # En claro el hero tiene su propio velo sobre la foto. Tiene que seguir
        # declarado con el prefijo del tema: así su especificidad le gana al
        # selector de clase que usa la regla de móvil, sin importar el orden.
        assert '[data-theme="light"] .hero-overlay' in css, (
            'Si el velo del tema claro queda en un selector de clase, la regla de '
            'móvil lo pisa y el texto blanco del hero claro cae sobre la foto'
        )

    def test_el_velo_sigue_saliendo_de_los_tokens(self, css):
        movil = bloque_movil(css)
        regla_hero = movil[movil.index('.hero-overlay {'):]
        regla_hero = regla_hero[:regla_hero.index('}')]
        assert 'rgba(0, 0, 0' not in regla_hero, (
            'Los velos salen de --scrim-rgb para invertirse con el tema'
        )


class TestSeparadorDelModal:
    """S2: el separador entre los enlaces del modal usaba --border-mid, que sobre
    el blanco del tema claro da 1.36:1: quedó prácticamente invisible."""

    @pytest.mark.parametrize('tema', ['oscuro', 'claro'])
    def test_el_separador_se_lee_como_texto_secundario(self, css, tema):
        tokens = tokens_tema(css, tema)
        ratio = contraste(tokens['--fg-dim'], tokens['--bg'])
        assert ratio >= 4.5, (
            f'El separador en tema {tema} da {ratio:.2f}:1 sobre el fondo del modal'
        )

    def test_el_separador_usa_el_token_de_texto_secundario(self, css):
        cuerpo = regla(css, '.login-sep')
        assert 'var(--fg-dim)' in cuerpo
        assert 'var(--border-mid)' not in cuerpo, (
            '--border-mid sobre blanco es un borde, no un glifo: 1.5:1'
        )

    def test_el_separador_no_depende_de_un_estilo_inline(self, html, css):
        assert 'class="login-sep"' in html
        assert 'color: var(--border-mid); margin: 0 8px;' not in html, (
            'El color inline le gana a la hoja de estilos y vuelve a 1.36:1'
        )
        assert 'margin: 0 8px' in regla(css, '.login-sep'), (
            'El espaciado del separador se mueve con el color, no queda en la plantilla'
        )

    def test_el_tema_claro_tambien_tiene_piso_en_movil(self, css):
        # El hero claro es blanco sobre la foto natural, sin el brightness(0.65)
        # del oscuro, así que necesita su propia regla: --scrim-rgb invertido a
        # blanco borraría el texto en vez de sostenerlo.
        movil = bloque_movil(css)
        assert '[data-theme="light"] .hero-overlay {' in movil
        bloque = movil[movil.index('[data-theme="light"] .hero-overlay {'):]
        bloque = bloque[:bloque.index('}')]
        alfas = [float(a) for a in re.findall(r'rgba\(0, 0, 0, ([\d.]+)\)', bloque)]
        assert alfas, 'El velo claro es negro explícito: el texto del hero es blanco'
        assert min(alfas) >= 0.75, (
            f'El piso del velo claro en móvil ({min(alfas)}) deja el párrafo por '
            f'debajo de 4.5:1; medido, el de escritorio daba 1.35:1'
        )


class TestEnlacesDelNavSobreElHero:
    """SCRUM-427: arriba el nav es transparente y los enlaces se apoyan en la foto
    del reel. --fg-dim (#a0a0a0) a 0.75rem daba 1.69:1 en 1024x768."""

    def test_el_estado_sobre_el_hero_sube_el_tono(self, css):
        bloque = regla(css, '.nav-tech:not(.scrolled) .nav-links a')
        alfas = [float(a) for a in re.findall(r'rgba\(var\(--ink-rgb\),\s*([\d.]+)\)', bloque)]
        assert alfas, 'Sobre el hero el enlace tiene que fijar su propio tono'
        assert min(alfas) >= 0.85, (
            'Con menos de 0.85 de tinta el peor glifo cae por debajo de 4.5:1; '
            'medido, --fg-dim daba 1.69:1 a 1024x768'
        )

    def test_con_fondo_el_enlace_conserva_el_tono_secundario(self, css):
        # En .scrolled el nav ya tiene un velo casi opaco: ahí --fg-dim alcanza y
        # subir el tono rompería la jerarquía del nav cerrado.
        assert '.nav-tech:not(.scrolled) .nav-links a' in css
        assert '.nav-tech.scrolled .nav-links a { color' not in css

    def test_el_tema_claro_conserva_su_propia_regla(self, css):
        # Su selector lleva el prefijo del tema, así que gana por especificidad
        # sin importar el orden. Si cae a un selector de clase, la regla de
        # oscuro le gana y el nav claro cambia sin que nadie lo pida.
        assert '[data-theme="light"] .nav-tech:not(.scrolled) .nav-links a' in css


class TestEnlacesDelModal:
    """En tema oscuro los enlaces del modal usaban --muted (#555555), que sobre el
    fondo casi negro da 2.73:1: el separador quedaba más visible que los enlaces
    que separa."""

    def test_usan_el_tono_de_texto_secundario(self, css):
        bloque = regla(css, '.login-link')
        assert 'var(--fg-dim)' in bloque
        assert 'var(--muted)' not in bloque

    @pytest.mark.parametrize('tema', ['oscuro', 'claro'])
    def test_el_tono_del_enlace_pasa_aa(self, css, tema):
        tokens = tokens_tema(css, tema)
        ratio = contraste(tokens['--fg-dim'], tokens['--bg'])
        assert ratio >= 4.5, f'Los enlaces del modal dan {ratio:.2f}:1 en tema {tema}'

    @pytest.mark.parametrize('tema,valor', [('oscuro', '#555555'), ('claro', '#5f6673')])
    def test_el_token_muted_no_se_toca(self, css, tema, valor):
        # Lo comparten otros componentes y los tests de tema fijan su valor.
        assert tokens_tema(css, tema)['--muted'] == valor

    def test_el_hover_vuelve_al_texto_principal(self, css):
        assert 'var(--fg)' in regla(css, '.login-link:hover')

    def test_la_barra_lleva_velo_propio_sobre_el_hero(self, css):
        # El color del enlace solo no alcanza: el peor píxel de la caja llega a
        # luminancia 0.23 y ahí ni el blanco puro da 4.5:1 (3.8:1). El velo de la
        # barra es lo que baja ese fondo.
        bloque = regla(css, ':root:not([data-theme="light"]) .nav-tech:not(.scrolled)')
        assert 'linear-gradient' in bloque
        alfas = [float(a) for a in re.findall(r'rgba\(var\(--scrim-rgb\),\s*([\d.]+)\)', bloque)]
        assert alfas, 'El velo de la barra sale de --scrim-rgb para seguir al tema'
        assert max(alfas) >= 0.5, (
            'Sin un piso de 0.5 el velo no baja el fondo lo suficiente; el peor '
            'glifo quedaba en 5.12:1 y con otra tipografía cruzaba AA'
        )

    def test_el_velo_no_toca_el_tema_claro(self, css):
        # En claro el velo del hero ya cubre la zona del nav (medía 15:1) y el
        # header tiene que seguir transparente.
        assert '[data-theme="light"] .nav-tech:not(.scrolled) {' not in css
        bloque = regla(css, ':root:not([data-theme="light"]) .nav-tech:not(.scrolled)')
        assert bloque.startswith(':root:not([data-theme="light"])')
