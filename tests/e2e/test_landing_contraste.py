"""
Landing — contraste medido bajo los glifos (SCRUM-424/425/427).

El hero y el nav son texto sobre píxeles que no controlamos: la foto del reel. El
contraste real no se puede deducir de los tokens, así que se mide: se captura el
bloque dos veces, una con el texto visible y otra con `color: transparent`, y se
compara el color del texto contra el fondo que quedó debajo de cada glifo. Es la
única forma de ver el peor caso, que no está en la mediana sino en los píxeles
claros de la foto justo debajo de una letra.
"""

import io
import re

import pytest
from PIL import Image

UMBRAL_NORMAL = 4.5
UMBRAL_NO_TEXTO = 3.0
FRAME_ESTABLE = 2  # una de las siete fotos del reel
FOTOS = 7


def _luminancia(color):
    def canal(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(v) for v in color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    la, lb = _luminancia(a), _luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def rgb_de(valor_css):
    return tuple(int(v) for v in re.findall(r'\d+', valor_css)[:3])


def _alfa(valor_css):
    coincidencia = re.findall(r'rgba\([^)]*?,\s*([\d.]+)\)', valor_css)
    return float(coincidencia[0]) if coincidencia else 1.0


def congelar(page):
    """Sin esto, el dot parpadeante del logo y el crossfade del reel aparecen en
    una captura sí y en la otra no, y el peor caso medido es ruido."""
    page.add_style_tag(
        content='* { animation: none !important; transition: none !important; }'
    )
    forzar_foto(page, FRAME_ESTABLE)


def forzar_foto(page, indice):
    page.evaluate(
        "i => document.querySelectorAll('.reel-frame').forEach((f, j) => f.classList.toggle('active', j === i))",
        indice,
    )
    page.wait_for_timeout(150)


def peor_contraste_bajo_glifos(page, locator, cobertura_minima=0.85):
    """Mínimo y mediana del contraste del texto contra el fondo bajo sus glifos.

    El interior del glifo se detecta por cobertura y no por un umbral fijo de
    diferencia: con un umbral, el texto de bajo contraste —justo el que hay que
    medir— se queda fuera de la máscara y la medición devuelve cero píxeles.

    `cobertura_minima` baja para glifos de un solo píxel de trazo (el separador
    "|"): ahí no existe un píxel completamente cubierto, sólo antialias.
    """
    estilo = locator.evaluate("el => getComputedStyle(el).color")
    color = rgb_de(estilo)
    alfa = _alfa(estilo)

    con_texto = list(Image.open(io.BytesIO(locator.screenshot())).convert('RGB').getdata())
    locator.evaluate("el => { el.dataset.colorOriginal = el.style.color; el.style.color = 'transparent'; }")
    sin_texto = list(Image.open(io.BytesIO(locator.screenshot())).convert('RGB').getdata())
    locator.evaluate("el => { el.style.color = el.dataset.colorOriginal || ''; }")

    ratios = []
    for pintado, fondo in zip(con_texto, sin_texto):
        texto = tuple(alfa * color[i] + (1 - alfa) * fondo[i] for i in range(3))
        coberturas = [
            (pintado[i] - fondo[i]) / (texto[i] - fondo[i])
            for i in range(3) if abs(texto[i] - fondo[i]) > 15
        ]
        if coberturas and min(coberturas) >= cobertura_minima:
            ratios.append(contraste(texto, fondo))

    assert ratios, 'No se detectaron glifos sólidos: la medición no es válida'
    ratios.sort()
    return ratios[0], ratios[len(ratios) // 2]


def abrir_landing(page, live_server, tema, ancho=1440, alto=900):
    page.set_viewport_size({'width': ancho, 'height': alto})
    page.goto(live_server.url, wait_until='load')
    page.evaluate(f"localStorage.setItem('jobdevs-theme', '{tema}')")
    page.reload(wait_until='load')
    page.wait_for_timeout(1000)
    congelar(page)


@pytest.mark.e2e
class TestContrasteBajoGlifos:
    """SCRUM-424: el hero del tema oscuro es texto claro sobre una foto con velo.
    A 390px el párrafo cruzaba el centro del ancho, donde el velo horizontal cae a
    0.02: el peor glifo medido era 3.12:1."""

    @pytest.mark.parametrize('tema', ['dark', 'light'])
    def test_el_parrafo_del_hero_se_lee_en_movil(self, page, live_server, tema):
        abrir_landing(page, live_server, tema, ancho=390, alto=844)

        parrafo = page.locator('.hero-subtitle')
        peor, mediana = peor_contraste_bajo_glifos(page, parrafo)
        assert peor >= UMBRAL_NORMAL, (
            f'El peor píxel bajo un glifo en tema {tema} da {peor:.2f}:1 '
            f'(mediana {mediana:.2f}:1). El velo del hero en móvil tiene que cubrir '
            f'la foto al menos hasta AA'
        )

    def test_la_marca_del_nav_se_lee_sobre_la_foto(self, page, live_server):
        # El 1.67:1 que reportaba el ticket era el verde del dot parpadeante, no
        # la marca. Con las animaciones congeladas la marca pasa con margen; este
        # test fija ese piso para que no se degrade sin que nadie lo note.
        abrir_landing(page, live_server, 'dark', ancho=1920, alto=1080)

        marca = page.locator('.nav-brand')
        peor, mediana = peor_contraste_bajo_glifos(page, marca)
        assert peor >= UMBRAL_NORMAL, (
            f'La marca del nav da {peor:.2f}:1 en el peor píxel (mediana {mediana:.2f}:1)'
        )

    @pytest.mark.parametrize('tema', ['light', 'dark'])
    def test_el_separador_del_modal_se_percibe(self, page, live_server, tema):
        # SCRUM-425: es un divisor decorativo, no texto: no le aplica 4.5:1, pero
        # con --border-mid quedaba en 1.4-1.5:1, es decir invisible.
        page.set_viewport_size({'width': 1440, 'height': 900})
        page.goto(live_server.url, wait_until='load')
        page.evaluate(f"localStorage.setItem('jobdevs-theme', '{tema}')")
        page.reload(wait_until='load')
        page.locator('.nav-cta').first.click()
        page.wait_for_timeout(800)
        congelar(page)

        separador = page.locator('.login-sep')
        assert separador.is_visible()
        peor, mediana = peor_contraste_bajo_glifos(page, separador, cobertura_minima=0.55)
        assert peor >= UMBRAL_NO_TEXTO, (
            f'El separador en tema {tema} da {peor:.2f}:1 (mediana {mediana:.2f}:1): '
            f'un divisor no necesita 4.5:1, pero sí tiene que percibirse'
        )
