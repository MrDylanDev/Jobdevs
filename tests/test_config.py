import os
import importlib
import pytest


def test_allowed_hosts_strips_whitespace(monkeypatch):
    """DJANGO_ALLOWED_HOSTS with spaces around commas must parse into stripped hostnames without empty entries."""
    monkeypatch.setenv('DJANGO_ALLOWED_HOSTS', ' localhost, 127.0.0.1 , web , ')
    import config.settings
    importlib.reload(config.settings)
    assert config.settings.ALLOWED_HOSTS == ['localhost', '127.0.0.1', 'web']


def test_auth_password_validators_includes_django_standard_and_complex():
    """AUTH_PASSWORD_VALIDATORS in production settings must include standard validators plus complex."""
    import config.settings
    validator_names = [v['NAME'] for v in config.settings.AUTH_PASSWORD_VALIDATORS]
    assert 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator' in validator_names
    assert 'django.contrib.auth.password_validation.MinimumLengthValidator' in validator_names
    assert 'django.contrib.auth.password_validation.CommonPasswordValidator' in validator_names
    assert 'django.contrib.auth.password_validation.NumericPasswordValidator' in validator_names
    assert 'usuarios.validators.ComplexPasswordValidator' in validator_names


def test_csrf_trusted_origins_not_hardcoding_zero_ip_and_loads_from_env(monkeypatch):
    """CSRF_TRUSTED_ORIGINS must not include 0.0.0.0 and must load cleanly from environment."""
    import config.settings
    importlib.reload(config.settings)
    assert not any('0.0.0.0' in origin for origin in config.settings.CSRF_TRUSTED_ORIGINS)

    monkeypatch.setenv('DJANGO_CSRF_TRUSTED_ORIGINS', 'https://jobdevs.sena.edu.co, https://app.jobdevs.co ')
    importlib.reload(config.settings)
    assert config.settings.CSRF_TRUSTED_ORIGINS == ['https://jobdevs.sena.edu.co', 'https://app.jobdevs.co']


def test_settings_test_fails_loudly_outside_pytest():
    """Importing settings_test outside pytest must raise RuntimeError."""
    import sys
    import subprocess
    cmd = [
        sys.executable,
        "-c",
        "import config.settings_test"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert "RuntimeError" in res.stderr
    assert "config.settings_test solo debe ser importado en entornos de prueba con pytest" in res.stderr
