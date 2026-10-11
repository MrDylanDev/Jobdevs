import pytest
from django.template.loader import render_to_string


def test_base_template_does_not_reference_nonexistent_estilos_css():
    """base.html must not link to nonexistent publico/css/estilos.css (causing 404 on all pages)."""
    rendered = render_to_string('base.html')
    assert 'estilos.css' not in rendered


def test_base_template_external_scripts_have_sri_integrity():
    """External CDN scripts and styles in base.html must have Subresource Integrity (SRI) attributes."""
    rendered = render_to_string('base.html')
    assert 'integrity=' in rendered
    assert 'crossorigin="anonymous"' in rendered
