import os
import sys

# Seguridad: impedir importaciones accidentales fuera de suites de pruebas con pytest
if 'pytest' not in sys.modules and not any('pytest' in arg for arg in sys.argv):
    raise RuntimeError("config.settings_test solo debe ser importado en entornos de prueba con pytest.")

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'True')
os.environ.setdefault('DJANGO_SECRET_KEY', 'django-insecure-test-key-jobdevs-postgresql-migration')
os.environ.setdefault('DJANGO_DEBUG', 'True')

from .settings import *

# Env-driven DB selection: use PostgreSQL ONLY when explicitly requested via
# USE_POSTGRES=1 / USE_POSTGRESQL=1 or TEST_DB=postgres / TEST_DB=postgresql.
# In all other cases (including local dev where .env has DB_ENGINE=postgresql/DB_HOST=db
# for Docker), default to fast SQLite in-memory so test suites run isolated and zero-config.
_USE_POSTGRES = (
    os.environ.get("USE_POSTGRES", "") == "1"
    or os.environ.get("USE_POSTGRESQL", "") == "1"
    or os.environ.get("TEST_DB", "").lower() in ("postgres", "postgresql")
)

if _USE_POSTGRES:
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
    # Use SQLite in-memory for fast, isolated tests (default for local & CI test-sqlite)
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


