import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection

User = get_user_model()


@pytest.fixture(autouse=True, scope='session')
def fix_sqlite_column_renames(django_db_setup, django_db_blocker):
    """
    Migration 0005 uses SeparateDatabaseAndState with empty database_operations
    (column was renamed manually in MySQL). SQLite needs the rename applied.
    """
    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            # Rename cedula → identificacion (migration 0005)
            try:
                cursor.execute(
                    "ALTER TABLE usuarios RENAME COLUMN cedula TO identificacion"
                )
            except Exception:
                pass  # Already renamed or doesn't exist

            # Migration 0008 removes first_name/last_name columns
            # These are set to None on the model but the columns still exist
            # in SQLite from 0001. Django's RemoveField in 0008 only affects state.


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Give every test access to the database automatically.
    Using 'db' fixture ensures the test database is set up.
    """
    pass


@pytest.fixture(autouse=True)
def ensure_admin_exists(db):
    """
    Ensure at least one admin exists so dashboard templates
    that reference admin_id don't crash with None.
    """
    if not User.objects.filter(rol='administrador').exists():
        User.objects.create_user(
            username='system_admin',
            email='system@teir.edu.co',
            nombre='System Admin',
            rol='administrador',
            estado='activo',
            password='AdminPass123!',
        )


@pytest.fixture
def client():
    """Django test client (unauthenticated)."""
    return Client()


@pytest.fixture
def admin_user(db):
    """Create an active admin user."""
    user = User.objects.create_user(
        username='admin_test',
        email='admin@test.teir',
        nombre='Admin Test',
        rol='administrador',
        estado='activo',
        password='TestPass123!',
    )
    return user


@pytest.fixture
def empresa_user(db):
    """Create an active empresa user."""
    user = User.objects.create_user(
        username='empresa_test',
        email='empresa@test.teir',
        nombre='Empresa Test',
        rol='empresa',
        estado='activo',
        password='TestPass123!',
    )
    return user


@pytest.fixture
def desarrollador_user(db):
    """Create an active desarrollador user."""
    user = User.objects.create_user(
        username='dev_test',
        email='dev@test.teir',
        nombre='Dev Test',
        rol='desarrollador',
        estado='activo',
        password='TestPass123!',
    )
    from usuarios.models import PerfilDesarrollador
    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=user)
    perfil.estado_verificacion = 'verificado'
    perfil.save()
    return user


@pytest.fixture
def auth_client(client, empresa_user):
    """Authenticated test client logged in as empresa_user."""
    client.login(username='empresa_test', password='TestPass123!')
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Authenticated test client logged in as admin_user."""
    client.login(username='admin_test', password='TestPass123!')
    return client


@pytest.fixture
def dev_client(client, desarrollador_user):
    """Authenticated test client logged in as desarrollador_user."""
    client.login(username='dev_test', password='TestPass123!')
    return client


@pytest.fixture
def suspended_user(db):
    """Create a suspended user."""
    return User.objects.create_user(
        username='suspended_test',
        email='suspended@test.teir',
        nombre='Suspended Test',
        rol='desarrollador',
        estado='suspendido',
        password='TestPass123!',
    )
