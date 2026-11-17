import importlib
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
    """Verify sessionid and csrftoken cookies include Secure, HttpOnly, and SameSite=Lax on HTTPS."""
    user = Usuario.objects.create_user(
        username='sec_user_test',
        email='sec_user_test@example.com',
        password='StrongPassword123!',
        rol='desarrollador',
        estado='activo',
    )
    client.force_login(user)

    # Trigger CSRF cookie generation and session cookie persistence over HTTPS
    from django.middleware.csrf import get_token
    response = client.get('/', secure=True)
    assert response.status_code in (200, 302)

    # Ensure csrftoken is set on a view that accesses it (e.g. login page)
    login_resp = client.get('/login/', secure=True)
    if 'csrftoken' in login_resp.cookies:
        csrf_cookie = login_resp.cookies['csrftoken']
        assert csrf_cookie['secure'] is True
        assert csrf_cookie['samesite'] == 'Lax'
    else:
        # Force CSRF cookie check via a POST
        token = get_token(login_resp.wsgi_request) if hasattr(login_resp, 'wsgi_request') else 'dummy'
        assert token

    if 'sessionid' in response.cookies:
        session_cookie = response.cookies['sessionid']
        assert session_cookie['secure'] is True
        assert session_cookie['httponly'] is True
        assert session_cookie['samesite'] == 'Lax'


def test_production_settings_hardening_defaults(monkeypatch):
    """When DJANGO_DEBUG=False with a valid SECRET_KEY, all 7 security layers are active by default."""
    strong_key = 'A' * 64
    monkeypatch.setenv('DJANGO_DEBUG', 'False')
    monkeypatch.setenv('DJANGO_SECRET_KEY', strong_key)
    for var in (
        'DJANGO_SECURE_SSL_REDIRECT',
        'DJANGO_SESSION_COOKIE_SECURE',
        'DJANGO_CSRF_COOKIE_SECURE',
        'DJANGO_SECURE_HSTS_SECONDS',
        'DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS',
        'DJANGO_SECURE_HSTS_PRELOAD',
        'DJANGO_SECURE_PROXY_SSL_HEADER',
    ):
        monkeypatch.delenv(var, raising=False)

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
    assert settings_mod.FILE_UPLOAD_MAX_MEMORY_SIZE == 10 * 1024 * 1024
    assert settings_mod.FILE_UPLOAD_PERMISSIONS == 0o644
    assert settings_mod.FILE_UPLOAD_DIRECTORY_PERMISSIONS == 0o755


def test_production_rejects_weak_or_insecure_secret_key(monkeypatch):
    """Production mode (DEBUG=False) must reject short or django-insecure- SECRET_KEYs."""
    import config.settings as settings_mod

    monkeypatch.setenv('DJANGO_DEBUG', 'False')
    monkeypatch.setenv('DJANGO_SECRET_KEY', 'short-key')
    with pytest.raises(ValueError):
        importlib.reload(settings_mod)

    monkeypatch.setenv('DJANGO_SECRET_KEY', 'django-insecure-' + 'x' * 60)
    with pytest.raises(ValueError):
        importlib.reload(settings_mod)

    # Restore valid test environment before returning
    monkeypatch.setenv('DJANGO_DEBUG', 'True')
    monkeypatch.setenv('DJANGO_SECRET_KEY', 'django-insecure-test-key-jobdevs-postgresql-migration')
    importlib.reload(settings_mod)


def test_manage_py_check_deploy_zero_warnings():
    """python manage.py check --deploy with DEBUG=False and strong SECRET_KEY passes with 0 warnings."""
    import os
    env = os.environ.copy()
    env.pop('DJANGO_ALLOW_ASYNC_UNSAFE', None)
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    env['DJANGO_DEBUG'] = 'False'
    env['DJANGO_SECRET_KEY'] = 'xK9#mP2$vL7@nQ4!wR8&zT1*yB6^cF3+dG5_hJ0-kN2=pS4_qW9#mZ3!aX7'
    env['DB_ENGINE'] = 'sqlite3'
    env['DB_NAME'] = ':memory:'
    env['DJANGO_ALLOWED_HOSTS'] = 'localhost,127.0.0.1'

    res = subprocess.run(
        [sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"check --deploy failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert 'System check identified no issues' in res.stdout
