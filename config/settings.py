

import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.management.utils import get_random_secret_key

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = get_random_secret_key()
    else:
        raise ValueError("DJANGO_SECRET_KEY es obligatorio en producción. Verifica tu archivo .env")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'tailwind',
    'theme',
    'usuarios',
    'proyectos',
    'postulaciones',
    'contrataciones',
    'avances',
    'mensajes',
    'notificaciones',
    'favoritos',
    'logs',
    'disputas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'usuarios.middleware.UsuarioActivoMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Django Tailwind: app que contiene los estilos (ver theme/static_src/src/styles.css)
TAILWIND_APP_NAME = 'theme'

# Recarga automática del navegador solo en desarrollo si está instalado
if DEBUG:
    try:
        import django_browser_reload
        INSTALLED_APPS += ['django_browser_reload']
        MIDDLEWARE += ['django_browser_reload.middleware.BrowserReloadMiddleware']
    except ImportError:
        pass

ROOT_URLCONF = 'config.urls'
ASGI_APPLICATION = 'config.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

_db_engine = os.environ.get('DB_ENGINE', 'django.db.backends.postgresql')
if _db_engine in ('postgresql', 'postgres'):
    _db_engine = 'django.db.backends.postgresql'
elif _db_engine == 'mysql':
    _db_engine = 'django.db.backends.mysql'
elif _db_engine in ('sqlite', 'sqlite3'):
    _db_engine = 'django.db.backends.sqlite3'

DATABASES = {
    'default': {
        'ENGINE': _db_engine,
        'NAME': os.environ.get('DB_NAME', 'teir_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        # RNF-10: reutilización de conexiones (pooling a nivel de Django)
        # mantiene conexiones vivas entre requests y verifica su salud.
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
        'CONN_HEALTH_CHECKS': True,
    }
}

# ---------------------------------------------------------------------------
# RNF-14 (Disponibilidad): respaldos y recuperación de la base de datos
# ---------------------------------------------------------------------------
# Directorio donde se escriben los respaldos (fuera de control de versiones).
BACKUP_DIR = Path(os.environ.get('DJANGO_BACKUP_DIR', BASE_DIR / 'backups'))
# Política de retención: capa diaria (se conservan todos), capa semanal
# (el más reciente de cada semana) y purga de lo más antiguo que el total.
BACKUP_RETENTION_DAILY_DAYS = int(os.environ.get('BACKUP_RETENTION_DAILY_DAYS', '7'))
BACKUP_RETENTION_TOTAL_DAYS = int(os.environ.get('BACKUP_RETENTION_TOTAL_DAYS', '30'))
# Objetivo del RNF-14: reconstruir el esquema en un servidor nuevo en < 5 minutos.
DB_RECOVERY_TARGET_SECONDS = int(os.environ.get('DB_RECOVERY_TARGET_SECONDS', '300'))

AUTHENTICATION_BACKENDS = [
    'usuarios.backends.UsuarioAuthBackend',
]

REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
_cache_backend = os.environ.get('DJANGO_CACHE_BACKEND', 'redis' if _db_engine == 'django.db.backends.postgresql' else 'locmem')

if _cache_backend == 'redis':
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'IGNORE_EXCEPTIONS': True,
            }
        }
    }
elif _cache_backend == 'db':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'teir_cache_table',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Django Channels - Channel Layer
if os.environ.get('USE_REDIS_CHANNEL_LAYER', '1' if _cache_backend == 'redis' else '0') == '1':
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'usuarios.validators.ComplexPasswordValidator',
    },
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media Files Settings
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ==============================================================================
# Observabilidad: logs técnicos del servidor (SCRUM-317 / HU-A18)
# ==============================================================================
# Los logs rotativos viven fuera de control de versiones (var/ está en .gitignore).
LOGS_DIR = BASE_DIR / 'var' / 'log'
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE_APP = Path(os.environ.get('DJANGO_LOG_FILE', LOGS_DIR / 'jobdevs.log'))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_FILE_APP),
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'usuarios': {
            'handlers': ['file', 'console'],
            'level': os.environ.get('USUARIOS_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'usuarios.Usuario'

SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Expira al cerrar navegador
_csrf_origins = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS')
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]
elif DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost',
        'http://127.0.0.1',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]
else:
    CSRF_TRUSTED_ORIGINS = []

# Configuraciones de transporte seguro y cookies (activadas vía env en producción)
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'False') == 'True'
SESSION_COOKIE_SECURE = os.environ.get('DJANGO_SESSION_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_SECURE = os.environ.get('DJANGO_CSRF_COOKIE_SECURE', 'False') == 'True'
if os.environ.get('DJANGO_SECURE_HSTS_SECONDS'):
    SECURE_HSTS_SECONDS = int(os.environ['DJANGO_SECURE_HSTS_SECONDS'])
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
if os.environ.get('DJANGO_SECURE_PROXY_SSL_HEADER', 'False') == 'True':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# Configuración de redirección de login
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'login'

# Configuración de Email
# En desarrollo: los emails se imprimen en la consola del servidor
# En producción: configurar EMAIL_HOST, EMAIL_PORT, etc. en .env
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'JobDevs <noreply@jobdevs.edu.co>')

# ==============================================================================
# Reglas de negocio del panel administrador
# ==============================================================================
# SCRUM-315 (HU-A07): días sin avances tras los cuales un proyecto en desarrollo
# se marca como inactivo en las alertas del panel de administración.
PROYECTO_DIAS_ALERTA_RETRASO = int(os.environ.get('PROYECTO_DIAS_ALERTA_RETRASO', '15'))

# ==============================================================================
# Celery Configuration (SCRUM-196 / SCRUM-197)
# ==============================================================================
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Celery Beat Periodic Tasks (SCRUM-200)
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'purgar-notificaciones-medianoche': {
        'task': 'notificaciones.purgar_notificaciones_antiguas',
        'schedule': crontab(hour=0, minute=0),
        'kwargs': {'dias': 30, 'incluir_no_leidas': False},
    },
    'expirar-negociaciones-vencidas': {
        'task': 'postulaciones.expirar_negociaciones_vencidas',
        'schedule': crontab(minute='*/30'),
    },
}
