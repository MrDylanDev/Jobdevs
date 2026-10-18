import os

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from playwright.sync_api import sync_playwright

User = get_user_model()

# RNF-12 (compatibilidad multi-navegador): navegadores soportados por los tests E2E.
#   clave -> (motor de Playwright, canal del navegador instalado en el sistema)
# Chromium es el navegador por defecto; Chrome y Edge usan los binarios del
# sistema (en CI los runners de GitHub ya los traen instalados).
BROWSERS = {
    'chromium': ('chromium', None),
    'chrome': ('chromium', 'chrome'),
    'firefox': ('firefox', None),
    'edge': ('chromium', 'msedge'),
}

DEFAULT_BROWSERS = 'chromium'


def _selected_browsers():
    """Navegadores a testear, desde la variable de entorno E2E_BROWSERS.

    Ejemplos: E2E_BROWSERS=chromium (por defecto), E2E_BROWSERS=chrome,firefox,edge
    """
    raw = os.environ.get('E2E_BROWSERS', DEFAULT_BROWSERS)
    names = [name.strip().lower() for name in raw.split(',') if name.strip()]
    unknown = sorted(set(names) - set(BROWSERS))
    if unknown:
        raise pytest.UsageError(
            f"E2E_BROWSERS contiene navegadores no soportados: {', '.join(unknown)}. "
            f"Valores válidos: {', '.join(BROWSERS)}"
        )
    return names


@pytest.fixture(scope='session', autouse=True)
def fix_sqlite_column_renames(django_db_setup, django_db_blocker):
    """
    Migration 0005 uses SeparateDatabaseAndState with empty database_operations.
    SQLite in-memory needs the column rename applied manually.
    """
    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    "ALTER TABLE usuarios RENAME COLUMN cedula TO identificacion"
                )
            except Exception:
                pass  # Already renamed or doesn't exist


@pytest.fixture(scope='session', params=_selected_browsers())
def browser(request):
    """Un navegador por cada valor de E2E_BROWSERS (RNF-12: Chrome, Firefox, Edge)."""
    engine, channel = BROWSERS[request.param]
    options = {'channel': channel} if channel else {}
    with sync_playwright() as p:
        browser = getattr(p, engine).launch(headless=True, **options)
        _report_browser_version(request.config, request.param, browser.version)
        yield browser
        browser.close()


def _report_browser_version(config, name, version):
    """Registra en el log la versión real del navegador (evidencia de RNF-12)."""
    message = f'[E2E] navegador {name}: versión {version}'
    reporter = config.pluginmanager.get_plugin('terminalreporter')
    if reporter is not None:
        reporter.write_line(message)
    else:  # pragma: no cover - solo si no hay reporter de terminal
        print(message)


@pytest.fixture
def page(browser, live_server):
    """Create a new page for each test, pointing at the live server."""
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = context.new_page()
    yield page
    context.close()


# Los fixtures de datos son de alcance 'function': los tests E2E usan
# django_db(transaction=True), que vacía la base de datos al terminar cada test.
# Un fixture de sesión quedaría obsoleto (el usuario ya no existiría en la BD) y
# el login fallaría. Esto también permite correr varios navegadores en una misma
# sesión de pytest (E2E_BROWSERS=chromium,firefox).
@pytest.fixture
def test_empresa(django_db_setup, django_db_blocker):
    """Create a test empresa user for E2E login tests."""
    with django_db_blocker.unblock():
        return User.objects.create_user(
            username='e2e_empresa',
            email='e2e_empresa@test.jobdevs',
            nombre='E2E Empresa',
            rol='empresa',
            estado='activo',
            password='E2ETest123!',
        )


@pytest.fixture
def test_dev(django_db_setup, django_db_blocker):
    """Create a test desarrollador user for E2E login tests."""
    with django_db_blocker.unblock():
        return User.objects.create_user(
            username='e2e_dev',
            email='e2e_dev@test.jobdevs',
            nombre='E2E Dev',
            rol='desarrollador',
            estado='activo',
            password='E2ETest123!',
        )


@pytest.fixture(autouse=True)
def ensure_admin_exists(django_db_setup, django_db_blocker):
    """Ensure admin exists for dashboard templates."""
    with django_db_blocker.unblock():
        if not User.objects.filter(rol='administrador').exists():
            User.objects.create_user(
                username='e2e_admin',
                email='e2e_admin@jobdevs.edu.co',
                nombre='E2E Admin',
                rol='administrador',
                estado='activo',
                password='AdminPass123!',
            )
