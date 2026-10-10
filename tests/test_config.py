import os
import importlib
import pytest


def test_allowed_hosts_strips_whitespace(monkeypatch):
    """DJANGO_ALLOWED_HOSTS with spaces around commas must parse into stripped hostnames without empty entries."""
    monkeypatch.setenv('DJANGO_ALLOWED_HOSTS', ' localhost, 127.0.0.1 , web , ')
    import config.settings
    importlib.reload(config.settings)
    assert config.settings.ALLOWED_HOSTS == ['localhost', '127.0.0.1', 'web']
