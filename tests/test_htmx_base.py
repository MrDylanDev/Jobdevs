"""Pruebas base de infraestructura HTMX local (Fase 0 / S1)."""

import re
from pathlib import Path

import pytest
from django.conf import settings

BASE = Path(settings.BASE_DIR)
HTMX_VENDOR_JS = BASE / 'static' / 'vendor' / 'htmx' / 'htmx.min.js'
HTMX_BRIDGE_JS = BASE / 'static' / 'dashboard' / 'script' / 'htmx_bridge.js'

TEMPLATES = {
    'base': BASE / 'templates' / 'base.html',
    'administrador': BASE / 'templates' / 'administrador' / 'Administrador.html',
    'desarrollador': BASE / 'templates' / 'Desarrollador' / 'Desarrollador.html',
    'empresa': BASE / 'templates' / 'empresa' / 'empresa.html',
}

HTMX_CDN_PATTERN = re.compile(
    r'https?://[^\s"\'<>]*htmx',
    re.IGNORECASE,
)


def _leer(path: Path) -> str:
    return path.read_text(encoding='utf-8')


class TestHtmxVendorYBridgeExisten:
    def test_htmx_min_js_vendored_existe_y_no_esta_vacio(self):
        assert HTMX_VENDOR_JS.exists(), f'Falta {HTMX_VENDOR_JS}'
        size = HTMX_VENDOR_JS.stat().st_size
        assert size > 30_000, f'htmx.min.js demasiado pequeño ({size} bytes)'

    def test_htmx_bridge_js_existe_y_no_esta_vacio(self):
        assert HTMX_BRIDGE_JS.exists(), f'Falta {HTMX_BRIDGE_JS}'
        contenido = _leer(HTMX_BRIDGE_JS).strip()
        assert len(contenido) > 100


class TestHtmxTemplatesIntegracion:
    @pytest.mark.parametrize('nombre,ruta', TEMPLATES.items())
    def test_template_carga_htmx_local_y_bridge_con_defer(self, nombre, ruta):
        html = _leer(ruta)
        assert "vendor/htmx/htmx.min.js" in html, f'{nombre} no carga vendor/htmx/htmx.min.js'
        assert "dashboard/script/htmx_bridge.js" in html, f'{nombre} no carga dashboard/script/htmx_bridge.js'

        htmx_tag = re.search(
            r'<script[^>]*vendor/htmx/htmx\.min\.js[^>]*></script>',
            html,
        )
        bridge_tag = re.search(
            r'<script[^>]*dashboard/script/htmx_bridge\.js[^>]*></script>',
            html,
        )
        assert htmx_tag is not None, f'{nombre} no tiene <script> válido para htmx.min.js'
        assert bridge_tag is not None, f'{nombre} no tiene <script> válido para htmx_bridge.js'
        assert 'defer' in htmx_tag.group(0), f'{nombre} debe cargar htmx.min.js con defer'
        assert 'defer' in bridge_tag.group(0), f'{nombre} debe cargar htmx_bridge.js con defer'

    @pytest.mark.parametrize('nombre,ruta', TEMPLATES.items())
    def test_template_sin_cdn_externo_de_htmx(self, nombre, ruta):
        html = _leer(ruta)
        assert not HTMX_CDN_PATTERN.search(html), f'{nombre} contiene referencia CDN externa a HTMX'


class TestHtmxBridgeContrato:
    def test_guard_doble_inicializacion(self):
        js = _leer(HTMX_BRIDGE_JS)
        assert '__jobdevsHtmxBridgeInit' in js

    def test_config_request_adjunta_csrf_token(self):
        js = _leer(HTMX_BRIDGE_JS)
        assert 'htmx:configRequest' in js
        assert 'X-CSRFToken' in js
        assert 'csrftoken' in js
        assert 'csrfmiddlewaretoken' in js

    def test_after_swap_reinicializa_lucide(self):
        js = _leer(HTMX_BRIDGE_JS)
        assert 'htmx:afterSwap' in js
        assert 'lucide.createIcons' in js

    def test_jobdevs_toast_bridge_a_toasts_unificados(self):
        js = _leer(HTMX_BRIDGE_JS)
        assert 'jobdevs:toast' in js
        assert 'JobDevsToast' in js
        assert 'JobDevsSSE' in js
        assert 'mostrarToast' in js
