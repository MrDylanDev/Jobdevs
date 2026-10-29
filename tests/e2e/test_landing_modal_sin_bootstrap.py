"""
Landing — el modal de login sin Bootstrap (SCRUM-421).

Bootstrap aportaba ESC, clic en el fondo, bloqueo del scroll, aria y foco. Estos
tests recorren ese checklist con teclado y mouse reales sobre el controlador
propio, abriendo el modal desde los tres puntos de apertura.
"""

import pytest


def abrir_desde_navbar(page, live_server, tema='dark'):
    page.set_viewport_size({'width': 1440, 'height': 900})
    page.goto(live_server.url, wait_until='load')
    page.evaluate(f"localStorage.setItem('jobdevs-theme', '{tema}')")
    page.reload(wait_until='load')
    page.wait_for_timeout(600)
    # El primer [data-abrir-login] del DOM es el ítem del menú móvil, que en
    # escritorio está oculto: se abre desde el CTA del navbar.
    abridor = page.locator('.nav-cta[data-abrir-login]')
    abridor.click()
    page.wait_for_timeout(400)
    return abridor


def estado(page):
    return page.evaluate(
        """() => {
            const m = document.getElementById('loginModal');
            return {
                abierto: m.classList.contains('show'),
                ariaHidden: m.getAttribute('aria-hidden'),
                bodyBloqueado: document.body.classList.contains('modal-open'),
                overflow: getComputedStyle(document.body).overflow,
                activo: document.activeElement ? document.activeElement.id || document.activeElement.tagName : null,
                dentroDelModal: m.contains(document.activeElement)
            };
        }"""
    )


@pytest.mark.e2e
class TestChecklistSinBootstrap:
    def test_abre_desde_el_navbar_y_bloquea_el_scroll(self, page, live_server):
        abrir_desde_navbar(page, live_server)
        e = estado(page)
        assert e['abierto'] is True
        assert e['ariaHidden'] == 'false'
        assert e['bodyBloqueado'] is True
        assert e['overflow'] == 'hidden', 'El scroll del body tiene que quedar bloqueado'

    def test_el_foco_entra_al_primer_campo(self, page, live_server):
        abrir_desde_navbar(page, live_server)
        e = estado(page)
        assert e['activo'] == 'username', f'El foco quedó en {e["activo"]}'
        assert e['dentroDelModal'] is True

    def test_escape_cierra_y_devuelve_el_foco(self, page, live_server):
        abridor = abrir_desde_navbar(page, live_server)
        page.keyboard.press('Escape')
        page.wait_for_timeout(300)
        e = estado(page)
        assert e['abierto'] is False
        assert e['ariaHidden'] == 'true'
        assert e['bodyBloqueado'] is False
        assert e['overflow'] != 'hidden', 'El scroll del body tiene que volver'
        assert not e['dentroDelModal'], 'El foco no puede quedar dentro del modal cerrado'
        assert abridor.evaluate('(el) => el === document.activeElement'), (
            'El foco tiene que volver al botón que abrió el modal'
        )

    def test_el_boton_de_cerrar_cierra(self, page, live_server):
        abrir_desde_navbar(page, live_server)
        page.locator('[data-cerrar-login]').click()
        page.wait_for_timeout(300)
        assert estado(page)['abierto'] is False

    def test_clic_en_el_fondo_cierra(self, page, live_server):
        abrir_desde_navbar(page, live_server)
        page.mouse.click(20, 20)
        page.wait_for_timeout(300)
        e = estado(page)
        assert e['abierto'] is False
        assert e['bodyBloqueado'] is False

    def test_clic_dentro_no_cierra(self, page, live_server):
        abrir_desde_navbar(page, live_server)
        page.locator('#loginModal .modal-title').click()
        page.wait_for_timeout(300)
        assert estado(page)['abierto'] is True

    def test_la_tabulacion_queda_contenida(self, page, live_server):
        abrir_desde_navbar(page, live_server)
        for _ in range(25):
            page.keyboard.press('Tab')
            assert estado(page)['dentroDelModal'], (
                'Tab se escapó del modal: falta la trampa de tabulación'
            )
        for _ in range(25):
            page.keyboard.press('Shift+Tab')
            assert estado(page)['dentroDelModal'], (
                'Shift+Tab se escapó del modal'
            )

    @pytest.mark.parametrize('tema', ['dark', 'light'])
    def test_abre_con_el_parametro_login(self, page, live_server, tema):
        page.set_viewport_size({'width': 1440, 'height': 900})
        page.goto(live_server.url, wait_until='load')
        page.evaluate(f"localStorage.setItem('jobdevs-theme', '{tema}')")
        page.goto(f'{live_server.url}/?login=1', wait_until='load')
        page.wait_for_timeout(700)
        e = estado(page)
        assert e['abierto'] is True, '?login=1 tiene que abrir el modal solo'
        assert e['bodyBloqueado'] is True

    def test_el_aspa_se_pinta_sin_cdn(self, page, live_server):
        abrir_desde_navbar(page, live_server)
        info = page.locator('[data-cerrar-login]').evaluate(
            """el => {
                const s = getComputedStyle(el);
                return {
                    ancho: el.getBoundingClientRect().width,
                    alto: el.getBoundingClientRect().height,
                    fondo: s.backgroundImage
                };
            }"""
        )
        assert info['ancho'] > 0 and info['alto'] > 0
        assert 'data:image/svg+xml' in info['fondo'], (
            'El aspa tiene que ser un SVG en línea: Bootstrap la traía como imagen'
        )


@pytest.mark.e2e
class TestIconosSinCdn:
    """SCRUM-426: el modal no puede depender de un CDN externo para sus iconos. El
    ojo de la contraseña y los avisos venian de Font Awesome."""

    def test_no_queda_ningun_enlace_a_font_awesome(self, page, live_server):
        abrir_desde_navbar(page, live_server)
        externos = page.evaluate(
            """() => Array.from(document.querySelectorAll('link[rel="stylesheet"], script[src]'))
                .map(el => el.getAttribute('href') || el.getAttribute('src'))
                .filter(u => u && /font-?awesome|bootstrap/i.test(u))"""
        )
        assert externos == [], f'La landing sigue cargando CDN de terceros: {externos}'

    def test_el_ojo_cambia_de_icono_y_de_tipo(self, page, live_server):
        abrir_desde_navbar(page, live_server)
        ojo = page.locator('#togglePassTech')
        campo = page.locator('#password')

        funcion = """(sel) => {
            const el = document.querySelector(sel);
            return el ? getComputedStyle(el).display !== 'none' : false;
        }"""
        assert campo.get_attribute('type') == 'password'
        assert ojo.get_attribute('aria-pressed') == 'false'
        assert page.evaluate(funcion, '#togglePassTech .lucide-eye') is True
        assert page.evaluate(funcion, '#togglePassTech .lucide-eye-off') is False

        ojo.click()
        page.wait_for_timeout(150)
        assert campo.get_attribute('type') == 'text'
        assert ojo.get_attribute('aria-pressed') == 'true'
        assert page.evaluate(funcion, '#togglePassTech .lucide-eye') is False
        assert page.evaluate(funcion, '#togglePassTech .lucide-eye-off') is True

        ojo.click()
        page.wait_for_timeout(150)
        assert campo.get_attribute('type') == 'password'

    def test_los_iconos_visibles_se_pintan_con_tamano(self, page, live_server):
        # Los iconos de los paneles ocultos miden cero a propósito: sólo se
        # revisan los que el usuario ve.
        page.goto(live_server.url, wait_until='load')
        page.wait_for_timeout(600)
        chicos = page.evaluate(
            """() => Array.from(document.querySelectorAll('svg.lucide'))
                .filter(s => s.checkVisibility && s.checkVisibility())
                .map(s => s.getBoundingClientRect())
                .filter(r => r.width < 4 || r.height < 4).length"""
        )
        assert chicos == 0, f'{chicos} iconos visibles de Lucide se pintaron sin tamaño'
