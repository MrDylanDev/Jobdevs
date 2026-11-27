"""Regresión de SCRUM-454: selector de tema claro/oscuro en el panel Desarrollador."""

from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

DASHBOARD_CSS_PATH = Path(settings.BASE_DIR) / "static" / "dashboard" / "css" / "dashboard.css"
CSS_PATH = Path(settings.BASE_DIR) / "static" / "Desarrollador" / "css" / "desarrollador.css"
JS_DIR = Path(settings.BASE_DIR) / "static" / "Desarrollador" / "script"
JS_PATH = JS_DIR / "desarrollador.js"


def _leer_js_desarrollador() -> str:
    rutas = [JS_PATH, *sorted((JS_DIR / "modules").glob("*.js"))]
    return "\n".join(p.read_text(encoding="utf-8") for p in rutas if p.exists())


@pytest.mark.django_db
def test_dashboard_desarrollador_incluye_toggle_de_tema(dev_client):
    response = dev_client.get(reverse("dashboard_desarrollador"))
    assert response.status_code == 200

    html = response.content.decode()
    assert 'id="devThemeToggle"' in html
    assert 'class="theme-toggle"' in html
    assert "toggleDevTheme()" in html
    assert 'aria-pressed="false"' in html


@pytest.mark.django_db
def test_dashboard_desarrollador_inicializa_tema_antes_del_render(dev_client):
    response = dev_client.get(reverse("dashboard_desarrollador"))
    html = response.content.decode()

    assert '<html lang="es" data-theme="dark">' in html
    # El script de inicialización debe ir en <head>, antes de las hojas de estilo.
    assert html.index("jobdevs-theme") < html.index("Desarrollador/css/desarrollador.css")


def test_css_define_tema_claro_y_estilos_del_switch():
    dashboard_css = DASHBOARD_CSS_PATH.read_text(encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")

    assert '[data-theme="light"]' in dashboard_css
    assert '[data-theme="light"]' in css
    assert ".theme-toggle" in css
    assert ".theme-toggle-icon--dark" in css
    assert ".theme-toggle-icon--light" in css
    # Verde accesible para texto sobre blanco (WCAG AA) centralizado en dashboard.css.
    assert "--accent:         #00713f" in dashboard_css
    # Componentes compartidos con color duro necesitan override explícito en modo claro
    # y están centralizados en dashboard.css.
    for selector in (
        '[data-theme="light"] .sidebar-brand-text',
        '[data-theme="light"] .top-header-title',
        '[data-theme="light"] .data-table td',
        '[data-theme="light"] .notif-item',
        '[data-theme="light"] .btn-secondary',
    ):
        assert selector in dashboard_css
    # Overrides propios del rol Desarrollador en modo claro.
    assert '[data-theme="light"] .btn-primary' in css


def test_js_persiste_la_preferencia_en_localstorage():
    js = _leer_js_desarrollador()

    assert "function toggleDevTheme()" in js
    assert "jobdevs-theme" in js
    assert "localStorage.setItem(DEV_THEME_STORAGE_KEY, nuevoTema)" in js
    assert "actualizarBotonTemaDev" in js
