"""Regresiones de UX-02: toasts unificados para SSE y WebSocket."""

from pathlib import Path

from django.conf import settings

BASE = Path(settings.BASE_DIR)
SSE_JS = BASE / 'static' / 'dashboard' / 'script' / 'notificaciones_sse.js'
POPOVER_JS = BASE / 'static' / 'dashboard' / 'script' / 'notificaciones_popover.js'
CHAT_JS = BASE / 'static' / 'mensajes' / 'script' / 'chat_inline.js'
DASHBOARD_CSS = BASE / 'static' / 'dashboard' / 'css' / 'dashboard.css'
TEMPLATES = {
    'admin': BASE / 'templates' / 'administrador' / 'Administrador.html',
    'dev': BASE / 'templates' / 'Desarrollador' / 'Desarrollador.html',
    'empresa': BASE / 'templates' / 'empresa' / 'empresa.html',
}


def _leer(path):
    return path.read_text(encoding='utf-8')


class TestToastCSS:
    def test_define_contenedor_y_cuatro_tipos(self):
        css = _leer(DASHBOARD_CSS)
        assert '.jobdevs-toast-container' in css
        for tipo in ('success', 'info', 'warning', 'error'):
            assert f'.jobdevs-toast--{tipo}' in css

    def test_esquina_superior_derecha_y_movil(self):
        css = _leer(DASHBOARD_CSS)
        bloque = css[css.index('.jobdevs-toast-container'):]
        assert 'top: 20px;' in bloque
        assert 'right: 20px;' in bloque
        assert '@media (max-width: 640px)' in bloque
        assert 'left: 12px;' in bloque

    def test_boton_cierre_progreso_y_tema_claro(self):
        css = _leer(DASHBOARD_CSS)
        assert '.jobdevs-toast__close' in css
        assert '@keyframes jobdevs-toast-progress' in css
        assert '[data-theme="light"] .jobdevs-toast' in css
        assert 'prefers-reduced-motion' in css


class TestToastJS:
    def test_autocierre_cinco_segundos_y_pausa(self):
        js = _leer(SSE_JS)
        assert 'TOAST_DURACION_MS = 5000' in js
        assert 'const pausar' in js
        assert 'const reanudar' in js
        assert 'TOAST_MAX_VISIBLES = 4' in js
        assert 'enHover' in js
        assert 'enFoco' in js
        assert 'hasOwnProperty.call(TOAST_ALIAS' in js
        assert '_jdLimpiar' in js

    def test_expone_api_unificada(self):
        js = _leer(SSE_JS)
        assert 'window.JobDevsToast' in js
        assert 'window.JobDevsSSE' in js
        assert "tipo: 'success'" in js
        assert "tipo: 'error'" in js

    def test_mapea_tipos_de_dominio_a_tipos_visuales(self):
        js = _leer(SSE_JS)
        assert "aprobacion: 'success'" in js
        assert "mensaje: 'info'" in js
        assert "alerta: 'warning'" in js
        assert "error: 'error'" in js

    def test_no_inyecta_mensajes_con_innerhtml(self):
        js = _leer(SSE_JS)
        assert 'innerHTML' not in js
        assert 'textContent = titulo' in js
        assert 'textContent = mensaje' in js

    def test_conserva_integracion_con_popover(self):
        js = _leer(SSE_JS)
        assert 'notifPopover' in js
        assert 'JobDevsNotificaciones' in js


class TestIntegracionWebSocket:
    def test_chat_notifica_mensajes_entrantes_con_el_toast_unificado(self):
        js = _leer(CHAT_JS)
        assert 'notificarMensajeEntrante' in js
        assert 'window.JobDevsToast' in js
        assert "tipo: 'mensaje'" in js
        assert 'duracion: 5000' in js
        assert "origen: 'ws'" in js

    def test_sin_toasts_legados_en_modales_ni_desarrollador(self):
        modals_dir = BASE / 'static' / 'dashboard' / 'script'
        modals_files = [modals_dir / 'dashboard_modals.js', *sorted((modals_dir / 'modules').glob('*.js'))]
        modals_js = '\n'.join(_leer(p) for p in modals_files if p.exists())
        dev_dir = BASE / 'static' / 'Desarrollador' / 'script'
        dev_files = [dev_dir / 'desarrollador.js', *sorted((dev_dir / 'modules').glob('*.js'))]
        dev_js = '\n'.join(_leer(p) for p in dev_files if p.exists())
        assert 'jdm-toast' not in modals_js
        assert 'jd-toast' not in dev_js
        assert 'window.JobDevsToast' in modals_js
        assert 'window.JobDevsToast' in dev_js

    def test_popover_reporta_errores_como_error(self):
        js = _leer(POPOVER_JS)
        assert "mostrarToast('No se pudieron actualizar las notificaciones.', 'error')" in js
        assert "mostrarToast('No se pudieron cargar las notificaciones.', 'error')" in js


class TestCacheBusting:
    # Versión compartida de cada asset: evita caché obsoleta entre roles.
    VERSIONES_COMUNES = {
        'dashboard/css/dashboard.css': '20261126_v35',
        'dashboard/css/dashboard_modals.css': '20261126_v33',
        'dashboard/script/dashboard_modals.js': '20261126_mod1',
        'dashboard/script/notificaciones_sse.js': '2',
        'mensajes/script/chat_inline.js': '20261121_v10',
    }

    def test_los_tres_roles_cargan_el_css_y_sse_actualizados(self):
        for rol, path in TEMPLATES.items():
            html = _leer(path)
            for asset, version in self.VERSIONES_COMUNES.items():
                esperado = f"static '{asset}' %}}?v={version}"
                assert esperado in html, f'{rol}: {asset} no sirve la versión {version}'
        assert "static 'dashboard/script/notificaciones_popover.js' %}?v=3" in _leer(TEMPLATES['admin'])
        assert "static 'dashboard/script/notificaciones_popover.js' %}?v=3" in _leer(TEMPLATES['dev'])
        assert "static 'Desarrollador/css/desarrollador.css' %}?v=20261126_v34" in _leer(TEMPLATES['dev'])
        assert "static 'Desarrollador/script/desarrollador.js' %}?v=20261126_mod1" in _leer(TEMPLATES['dev'])
