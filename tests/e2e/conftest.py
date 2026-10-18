import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from playwright.sync_api import sync_playwright

User = get_user_model()


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


@pytest.fixture(scope='session')
def browser():
    """Launch a single browser instance for the test session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser, live_server):
    """Create a new page for each test, pointing at the live server."""
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope='session')
def test_empresa(django_db_setup, django_db_blocker):
    """Create a test empresa user for E2E login tests (session-scoped)."""
    with django_db_blocker.unblock():
        return User.objects.create_user(
            username='e2e_empresa',
            email='e2e_empresa@test.jobdevs',
            nombre='E2E Empresa',
            rol='empresa',
            estado='activo',
            password='E2ETest123!',
        )


@pytest.fixture(scope='session')
def test_dev(django_db_setup, django_db_blocker):
    """Create a test desarrollador user for E2E login tests (session-scoped)."""
    with django_db_blocker.unblock():
        return User.objects.create_user(
            username='e2e_dev',
            email='e2e_dev@test.jobdevs',
            nombre='E2E Dev',
            rol='desarrollador',
            estado='activo',
            password='E2ETest123!',
        )


@pytest.fixture(scope='session', autouse=True)
def ensure_admin_exists(django_db_setup, django_db_blocker):
    """Ensure admin exists for dashboard templates (session-scoped)."""
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
