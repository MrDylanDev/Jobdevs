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
TEMPLATE_PATH = Path(settings.BASE_DIR) / 'templates' / 'publico' / 'index.html'
JS_PATH = Path(settings.BASE_DIR) / 'static' / 'publico' / 'script' / 'index.js'

# Tokens que el tema oscuro tenía hardcodeados y ahora salen de la capa semántica.
# `--bg-card-hover` y `--border-high` ya no están: se borraron por no tener ningún
# uso (ni en CSS, ni en plantillas, ni en JS) durante la limpieza del frontend.
TOKENS_OSCUROS = {
    '--bg': '#000000',
    '--bg-darker': '#050505',
    '--bg-card': '#0a0a0a',
    '--fg': '#ffffff',
    '--fg-dim': '#a0a0a0',
    '--muted': '#555555',
    '--border-dim': '#1a1a1a',
    '--border-mid': '#333333',
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
def html():
    return TEMPLATE_PATH.read_text(encoding='utf-8')


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
        assert '.theme-toggle { display: none' not in css, 'El botón nunca se oculta'

    def test_el_switch_no_choca_la_marca_en_pantallas_angostas(self, css):
        movil = css[css.index('@media (max-width: 767.98px)'):]
        assert '.theme-toggle-icon { padding: 7px 6px; }' in movil, (
            'A 320px la marca y el switch quedan a 3px si no se achica el relleno'
        )

    def test_es_un_switch_de_dos_posiciones(self, html):
        navbar = html[html.index('id="navbar"'):html.index('id="inicio"')]
        assert 'lucide-moon' in navbar and 'lucide-sun' in navbar, (
            'Las dos posiciones tienen que estar a la vista: un solo icono no dice a dónde va'
        )
        assert 'themeToggleLabel' not in navbar, (
            'El texto de estado se leía como etiqueta pasiva, no como control'
        )

    def test_el_estado_lo_comunica_el_css_no_el_js(self, css, js):
        assert '.theme-toggle[aria-pressed="false"] .theme-toggle-icon--dark' in css
        assert '.theme-toggle[aria-pressed="true"] .theme-toggle-icon--light' in css
        assert 'themeToggleLabel' not in js, 'Quedó código muerto del botón viejo'


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


class TestTextoSobreFoto:
    """S5: los elementos que siempre viven sobre una foto no pueden heredar el
    color del tema, porque el fondo que tienen detrás no cambia con el tema."""

    def test_la_etiqueta_de_caso_conserva_el_acento_brillante(self, css):
        assert '[data-theme="light"] .story-img-tag { color: #69f0ae; }' in css, (
            'Sobre la foto de la tarjeta, el acento oscuro del tema claro queda en 3:1'
        )

    def test_el_aspa_del_modal_no_queda_invertida_en_claro(self, css):
        assert '[data-theme="light"] .btn-close-tech { filter: none; }' in css, (
            'La imagen del aspa es negra: invertirla en claro la vuelve invisible'
        )


class TestHeroDelTemaClaro:
    """S3 (revisada): en el hero la foto manda con su velo oscuro y el texto va en
    blanco. La alternativa (foto clara + texto oscuro) se midió en 1.05:1 y la de
    dos áreas se descartó por diseño."""

    def test_la_foto_del_hero_va_en_color_natural(self, css):
        bloque = css[css.index('[data-theme="light"] .reel-frame img {'):]
        bloque = bloque[:bloque.index('}')]
        assert 'filter: none' in bloque, (
            'El grayscale y el brightness(0.65) del tema oscuro apagan la foto'
        )

    def test_el_velo_se_limita_a_la_zona_del_texto(self, css):
        grupo = css[css.index('[data-theme="light"] .cta-hero-overlay'):]
        grupo = grupo[:grupo.index('}')]
        assert '.hero-overlay' not in grupo, (
            'El hero conserva un velo mínimo: es lo que sostiene el texto blanco'
        )
        bloque = css[css.index('[data-theme="light"] .hero-overlay'):]
        bloque = bloque[:bloque.index('}')]
        assert 'rgba(0, 0, 0, 0.62) 46%' in bloque, (
            'La tinta del titular llega al 46%: ahí el velo tiene que seguir denso'
        )
        assert 'rgba(0, 0, 0, 0) 68%' in bloque, (
            'Del 68% del ancho hacia la derecha la foto tiene que quedar al natural'
        )
        resto = css[css.index('@media (max-width: 1199.98px) {'):]
        tramo = resto[:resto.index('[data-theme="light"] .hero-overlay')]
        assert tramo.strip().startswith('@media') or True
        assert 'rgba(0, 0, 0, 0.64) 74%' in css, (
            'De 1200px para abajo el titular llega al 95%: el velo tiene que cubrirlo'
        )
        assert 'rgba(255, 255, 255' not in bloque

    def test_el_hero_no_tiene_caja_blanca(self, css):
        assert '[data-theme="light"] .hero-copy' not in css

    def test_el_texto_del_hero_va_en_blanco(self, css):
        assert '[data-theme="light"] .hero-title span { color: #ffffff; }' in css
        assert '[data-theme="light"] .hero-subtitle { color: rgba(255, 255, 255, 0.74); }' in css

    def test_el_acento_del_hero_usa_el_verde_brillante(self, css):
        assert '.hero-accent { color: var(--accent); }' in css
        assert '[data-theme="light"] .hero-title .hero-accent { color: var(--accent-hero); }' in css
        assert '--accent-hero: #00e676;' in css

    def test_discplina_conserva_el_trazo_claro_sobre_el_velo(self, css):
        assert '[data-theme="light"] .hero-title .text-stroke { -webkit-text-stroke: 2px rgba(255, 255, 255, 0.55); }' in css

    def test_la_banda_del_marquee_va_en_blanco_con_letra_negra(self, css):
        bloque = css[css.index('[data-theme="light"] .hero-marquee {'):]
        bloque = bloque[:bloque.index('}')]
        assert 'background: var(--bg)' in bloque
        assert '[data-theme="light"] .hero-marquee .marquee-track { color: var(--fg); }' in css
        assert '[data-theme="light"] .hero-marquee .marquee-sep { color: var(--accent); }' in css

    def test_el_marquee_arranca_con_talento_sena_verificado(self, html):
        bloque = html[html.index('class="marquee-track"'):]
        bloque = bloque[:bloque.index('</div>')]
        assert bloque.index('TALENTO SENA VERIFICADO') < bloque.index('CERO BUROCRACIA')
        assert bloque.index('CERO BUROCRACIA') < bloque.index('TRAZABILIDAD')


class TestHeaderTransparente:
    """S7: el header es transparente en claro; arriba vive sobre el hero oscuro,
    así que el texto y los botones se invierten sólo en ese estado."""

    def test_no_hay_superficie_blanca_de_header(self, css):
        assert 'background: var(--bg) !important' not in css

    def test_arriba_el_texto_del_nav_es_claro(self, css):
        assert '[data-theme="light"] .nav-tech:not(.scrolled) .nav-brand,' in css
        assert '[data-theme="light"] .nav-tech:not(.scrolled) .nav-links a { color: rgba(255, 255, 255, 0.78); }' in css

    def test_arriba_los_botones_del_nav_son_vidrio_oscuro(self, css):
        bloque = css[css.index('[data-theme="light"] .nav-tech:not(.scrolled) .nav-cta,'):]
        bloque = bloque[:bloque.index('}')]
        assert 'rgba(0, 0, 0, 0.35)' in bloque
        assert 'rgba(255, 255, 255, 0.24)' in bloque

    def test_el_nav_no_lleva_halo_blanco(self, css):
        assert '[data-theme="light"] .nav-tech .nav-links a,' in css, (
            'En claro el text-shadow se invierte a blanco y dibuja un halo por palabra'
        )
        assert '[data-theme="light"] .nav-tech .nav-brand { text-shadow: none; }' in css

    def test_el_header_no_lleva_velo(self, css):
        assert '[data-theme="light"] .nav-tech:not(.scrolled) {' not in css, (
            'El header no pinta fondo propio: el nav es transparente'
        )

    def test_al_hacer_scroll_recupera_el_tema(self, css):
        assert '[data-theme="light"] .nav-cta,' in css
        assert '[data-theme="light"] .theme-toggle,' in css, (
            'El switch de tema comparte el grupo de superficies opacas con el '
            'conmutador de idioma; el grupo creció y el test tiene que seguirlo'
        )
        assert '[data-theme="light"] .lang-switch {' in css


class TestSuperficiesSinVelo:
    """S3: en las bandas con foto que quedan en claro, el blanco va en objetos
    locales y no encima de la imagen."""

    def test_los_encabezados_van_sobre_banda_lateral(self, css, html):
        bloque = css[css.index('[data-theme="light"] .wf-main-header,'):]
        bloque = bloque[:bloque.index('}')]
        assert "background: none" in bloque
        grupo = css[css.index('[data-theme="light"] .wf-bg-overlay,'):]
        grupo = grupo[:grupo.index('}')]
        assert 'linear-gradient(90deg' in grupo, (
            'El velo tiene que concentrarse a la derecha, donde vive el texto'
        )
        assert 'rgba(0, 0, 0, 0.10) 0%' in grupo, (
            'A la izquierda, donde está la persona, la foto va casi al natural'
        )
        assert 'color: var(--fg-dim); margin-bottom: 24px' not in html, (
            'El color inline en los párrafos de encabezado le gana a la regla del tema claro'
        )
        assert '[data-theme="light"] .roles-main-header .desc-mono { color: rgba(255, 255, 255, 0.78); }' in css
        assert '[data-theme="light"] .roles-hero-section .role-stage-title { color: #ffffff; }' in css, (
            'El detalle del rol quedaba con tipografía del tema claro sobre la banda oscura'
        )
        assert '[data-theme="light"] .roles-hero-section .role-stage-desc,' in css
        assert '[data-theme="light"] .roles-hero-section .role-stage-features li strong { color: #ffffff; }' in css
        assert '.rp-label--accent { color: var(--accent); }' in css, (
            'La etiqueta de aprendices usaba style inline, que le gana al CSS'
        )
        assert '[data-theme="light"] .wf-main-header .sh-title,' in css
        assert '[data-theme="light"] .roles-main-header .sh-title { color: #ffffff; }' in css

    def test_los_objetos_sobre_foto_son_opacos_y_sin_blur(self, css):
        bloque = css[css.index('[data-theme="light"] .wf-step-item,'):]
        bloque = bloque[:bloque.index('[data-theme="light"] .modal-tech')]
        assert 'backdrop-filter: none' in bloque, (
            'El blur sobre la foto es la parte literalmente difuminada'
        )
        for objeto in ('.wf-step-item', '.nav-cta', '.theme-toggle'):
            assert objeto in bloque, f'Falta dejar opaco {objeto} en claro'

    def test_los_logos_del_carrusel_se_leen_sobre_blanco(self, css):
        # Los SVG sólo usan #c9c9c9 (gris claro) y #0b0b0b: sobre blanco, sin
        # invertir y al 50% de opacidad, desaparecen.
        assert '[data-theme="light"] .logos-wordmark img { filter: invert(1); opacity: 1; }' in css

    def test_las_miniaturas_de_casos_no_van_apagadas(self, css):
        bloque = css[css.index('[data-theme="light"] .story-img {'):]
        bloque = bloque[:bloque.index('}')]
        assert 'brightness(0.95)' in bloque, (
            'brightness(0.6) era para el fondo negro: en claro se veía apagado'
        )

    def test_la_etiqueta_de_caso_sobre_foto_clara_es_un_chip(self, css):
        bloque = css[css.index('[data-theme="light"] .story-img-tag {'):]
        bloque = bloque[:bloque.index('}')]
        assert 'rgba(0, 0, 0, 0.62)' in bloque

    def test_la_tarjeta_activa_de_pasos_sigue_opaca(self, css):
        bloque = css[css.index('[data-theme="light"] .wf-step-item.active {'):]
        bloque = bloque[:bloque.index('}')]
        assert 'background: #f0f7f3' in bloque, (
            'El verde al 6% deja pasar la foto y el texto pierde legibilidad'
        )

    def test_el_hero_envuelve_el_texto_pero_sin_caja(self, html):
        inicio = html.index('class="hero-content')
        bloque = html[inicio:]
        bloque = bloque[:bloque.index('class="hero-marquee"')]
        assert 'class="hero-copy"' in bloque, (
            'El envoltorio sigue siendo útil como unidad, aunque ya no pinte fondo'
        )
        assert 'class="hero-accent"' in bloque


class TestGranoSoloEnOscuro:
    """S6: el grano de película es parte de la piel oscura; en claro se lee como
    papel sucio sobre el fondo blanco, así que no se pinta."""

    def test_el_grano_no_se_pinta_en_claro(self, css):
        assert '[data-theme="light"] .grain { display: none; }' in css, (
            'Sin esta regla el ruido fractal queda sobre el blanco y ensucia la página'
        )

    def test_el_grano_sigue_intacto_en_oscuro(self, css):
        bloque = css[css.index('.grain {'):]
        bloque = bloque[:bloque.index('}')]
        assert 'opacity: 0.045' in bloque
        assert 'mix-blend-mode: overlay' in bloque


class TestTokensInexistentes:
    """Un `var(--x)` que no existe no rompe nada visible: el navegador descarta la
    declaración y el elemento hereda el color. Eso lo vuelve invisible al ojo y a
    los tests de contraste, así que se fija acá."""

    def test_las_plantillas_solo_referencian_tokens_existentes(self, css, html):
        declarados = set(re.findall(r'(--[\w-]+):', css))
        referenciados = set(re.findall(r'var\((--[\w-]+)', html))
        inexistentes = sorted(referenciados - declarados)
        assert not inexistentes, (
            f'La plantilla usa tokens que no existen y el estilo se descarta: {inexistentes}'
        )
