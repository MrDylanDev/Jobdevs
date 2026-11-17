import importlib
import os
import subprocess
import sys

import pytest
from django.test import override_settings

from usuarios.models import Usuario


@pytest.mark.django_db
def test_http_security_headers_present_on_response(client):
    """Verify all required HTTP security headers are present on responses."""
    response = client.get('/')
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-Frame-Options') == 'DENY'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert response.headers.get('Cross-Origin-Opener-Policy') == 'same-origin'


@pytest.mark.django_db
@override_settings(
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    CSRF_COOKIE_SAMESITE='Lax',
)
def test_session_and_csrf_cookies_flags_on_https(client):
    """Verify sessionid and csrftoken cookies unconditionally include Secure, HttpOnly, and SameSite=Lax on HTTPS."""
    Usuario.objects.create_user(
        username='sec_user_test',
        email='sec_user_test@example.com',
        password='StrongPassword123!',
        rol='desarrollador',
        estado='activo',
    )

    # GET /login/ (following redirect to landing login modal) renders a CSRF-protected form, so csrftoken cookie MUST be set.
    login_page = client.get('/login/', secure=True, follow=True)
    assert 'csrftoken' in login_page.cookies
    csrf_cookie = login_page.cookies['csrftoken']
    assert csrf_cookie['secure'] is True
    assert csrf_cookie['samesite'] == 'Lax'

    # POST /login/ creates an authenticated session, so sessionid cookie MUST be set.
    login_resp = client.post(
        '/login/',
        data={'username': 'sec_user_test', 'password': 'StrongPassword123!'},
        secure=True,
    )
    assert login_resp.status_code in (200, 302)
    assert 'sessionid' in login_resp.cookies
    session_cookie = login_resp.cookies['sessionid']
    assert session_cookie['secure'] is True
    assert session_cookie['httponly'] is True
    assert session_cookie['samesite'] == 'Lax'


def test_production_settings_hardening_with_tls_env(monkeypatch):
    """When DJANGO_DEBUG=False with a valid cryptographic SECRET_KEY and TLS env vars, all 7 layers are active."""
    strong_key = 'xK9#mP2$vL7@nQ4!wR8&zT1*yB6^cF3+dG5_hJ0-kN2=pS4_qW9#mZ3!aX7'
    monkeypatch.setenv('DJANGO_DEBUG', 'False')
    monkeypatch.setenv('DJANGO_SECRET_KEY', strong_key)
    monkeypatch.setenv('DJANGO_SECURE_SSL_REDIRECT', 'True')
    monkeypatch.setenv('DJANGO_SESSION_COOKIE_SECURE', 'True')
    monkeypatch.setenv('DJANGO_CSRF_COOKIE_SECURE', 'True')
    monkeypatch.setenv('DJANGO_SECURE_HSTS_SECONDS', '31536000')
    monkeypatch.setenv('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True')
    monkeypatch.setenv('DJANGO_SECURE_HSTS_PRELOAD', 'True')
    monkeypatch.setenv('DJANGO_SECURE_PROXY_SSL_HEADER', 'True')

    import config.settings as settings_mod
    importlib.reload(settings_mod)

    assert settings_mod.DEBUG is False
    assert settings_mod.SECURE_SSL_REDIRECT is True
    assert settings_mod.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')
    assert settings_mod.SECURE_HSTS_SECONDS == 31536000
    assert settings_mod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert settings_mod.SECURE_HSTS_PRELOAD is True

    assert settings_mod.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert settings_mod.X_FRAME_OPTIONS == 'DENY'
    assert settings_mod.SECURE_REFERRER_POLICY == 'strict-origin-when-cross-origin'
    assert settings_mod.SECURE_CROSS_ORIGIN_OPENER_POLICY == 'same-origin'

    assert settings_mod.SESSION_COOKIE_SECURE is True
    assert settings_mod.CSRF_COOKIE_SECURE is True
    assert settings_mod.SESSION_COOKIE_HTTPONLY is True
    assert settings_mod.SESSION_COOKIE_SAMESITE == 'Lax'
    assert settings_mod.CSRF_COOKIE_SAMESITE == 'Lax'
    assert settings_mod.SESSION_EXPIRE_AT_BROWSER_CLOSE is True
    assert settings_mod.SESSION_COOKIE_AGE == 3600

    assert settings_mod.DATA_UPLOAD_MAX_MEMORY_SIZE == 10 * 1024 * 1024
    assert settings_mod.FILE_UPLOAD_MAX_MEMORY_SIZE == 2621440
    assert settings_mod.FILE_UPLOAD_PERMISSIONS == 0o644
    assert settings_mod.FILE_UPLOAD_DIRECTORY_PERMISSIONS == 0o755


def test_production_rejects_weak_or_insecure_secret_key(monkeypatch):
    """Production mode (DEBUG=False) must reject short, repeated-char, or django-insecure- SECRET_KEYs."""
    import config.settings as settings_mod

    monkeypatch.setenv('DJANGO_DEBUG', 'False')
    for bad_key in ('short-key', 'A' * 64, 'django-insecure-' + 'x' * 60):
        monkeypatch.setenv('DJANGO_SECRET_KEY', bad_key)
        with pytest.raises(ValueError):
            importlib.reload(settings_mod)

    # Restore valid test environment before returning
    monkeypatch.setenv('DJANGO_DEBUG', 'True')
    monkeypatch.setenv('DJANGO_SECRET_KEY', 'django-insecure-test-key-jobdevs-postgresql-migration')
    importlib.reload(settings_mod)


def test_manage_py_check_deploy_zero_warnings():
    """python manage.py check --deploy with DEBUG=False and TLS env passes with 0 warnings."""
    env = os.environ.copy()
    env.pop('DJANGO_ALLOW_ASYNC_UNSAFE', None)
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    env['DJANGO_DEBUG'] = 'False'
    env['DJANGO_SECRET_KEY'] = 'xK9#mP2$vL7@nQ4!wR8&zT1*yB6^cF3+dG5_hJ0-kN2=pS4_qW9#mZ3!aX7'
    env['DB_ENGINE'] = 'sqlite3'
    env['DB_NAME'] = ':memory:'
    env['DJANGO_ALLOWED_HOSTS'] = 'localhost,127.0.0.1'
    env['DJANGO_SECURE_SSL_REDIRECT'] = 'True'
    env['DJANGO_SESSION_COOKIE_SECURE'] = 'True'
    env['DJANGO_CSRF_COOKIE_SECURE'] = 'True'
    env['DJANGO_SECURE_HSTS_SECONDS'] = '31536000'
    env['DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS'] = 'True'
    env['DJANGO_SECURE_HSTS_PRELOAD'] = 'True'
    env['DJANGO_SECURE_PROXY_SSL_HEADER'] = 'True'

    res = subprocess.run(
        [sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"check --deploy failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert 'System check identified no issues' in res.stdout
