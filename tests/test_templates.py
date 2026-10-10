import pytest
from django.template.loader import render_to_string


def test_base_template_does_not_reference_nonexistent_estilos_css():
    """base.html must not link to nonexistent publico/css/estilos.css (causing 404 on all pages)."""
    rendered = render_to_string('base.html')
    assert 'estilos.css' not in rendered
