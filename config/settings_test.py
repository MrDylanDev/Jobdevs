import os
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'True')
os.environ.setdefault('DJANGO_SECRET_KEY', 'django-insecure-test-key-teir-postgresql-migration')
os.environ.setdefault('DJANGO_DEBUG', 'True')

from .settings import *

# Env-driven DB selection: use PostgreSQL when explicitly requested via
# DB_ENGINE=postgresql or USE_POSTGRES=1 (or DB_HOST defined with engine postgresql),
# otherwise fall back to fast SQLite in-memory.
_DB_ENGINE = os.environ.get("DB_ENGINE", "").lower()
_USE_POSTGRES = os.environ.get("USE_POSTGRES", "") == "1" or os.environ.get("USE_POSTGRESQL", "") == "1"
_DB_HOST = os.environ.get("DB_HOST")

if _USE_POSTGRES or "postgres" in _DB_ENGINE or (_DB_HOST is not None and "postgres" in _DB_ENGINE):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'teir_db_test'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    # Use SQLite in-memory for fast, isolated tests (default for test-sqlite)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
            'TEST': {
                'NAME': ':memory:',
            },
        }
    }

# Disable password validators during tests (speed)
AUTH_PASSWORD_VALIDATORS = []

# Use fast password hasher
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable CSRF for API-like test client calls
TESTING = True

# Disable email sending during tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Use console cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


# Migration 0005 uses SeparateDatabaseAndState with empty database_operations
# (column renamed manually in MySQL). SQLite needs the rename applied.
# We monkey-patch the migration class at import time.
import importlib
from django.db.migrations.state import ProjectState
from django.db.migrations.executor import MigrationExecutor

_original_apply = MigrationExecutor._migrate_all_forwards


def _patched_migrate_all_forwards(executor, *args, **kwargs):
    """After all migrations, rename cedula→identificacion if on SQLite."""
    result = _original_apply(executor, *args, **kwargs)
    from django.db import connection
    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    "ALTER TABLE usuarios RENAME COLUMN cedula TO identificacion"
                )
            except Exception:
                pass
    return result


MigrationExecutor._migrate_all_forwards = _patched_migrate_all_forwards
