import re
import pytest
from django.template.loader import render_to_string


def test_base_template_does_not_reference_nonexistent_estilos_css():
    """base.html must not link to nonexistent publico/css/estilos.css (causing 404 on all pages)."""
    rendered = render_to_string('base.html')
    assert 'estilos.css' not in rendered


def test_base_template_external_assets_have_sri_integrity():
    """Each external CDN link and script tag in base.html must have integrity and crossorigin attributes."""
    rendered = render_to_string('base.html')

    external_links = re.findall(r'<link[^>]+href=["\']https?://[^>]+>', rendered)
    assert len(external_links) >= 2, "Deben existir enlaces CDN para Bootstrap y FontAwesome"
    for tag in external_links:
        assert 'integrity=' in tag, f"El enlace externo carece de atributo integrity: {tag}"
        assert 'crossorigin="anonymous"' in tag, f"El enlace externo carece de crossorigin: {tag}"

    external_scripts = re.findall(r'<script[^>]+src=["\']https?://[^>]+>', rendered)
    assert len(external_scripts) >= 1, "Debe existir al menos un script CDN para Bootstrap"
    for tag in external_scripts:
        assert 'integrity=' in tag, f"El script externo carece de atributo integrity: {tag}"
        assert 'crossorigin="anonymous"' in tag, f"El script externo carece de crossorigin: {tag}"
