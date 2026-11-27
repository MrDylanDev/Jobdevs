import re
import pytest
from django.template.loader import render_to_string


def test_base_template_does_not_reference_nonexistent_estilos_css():
    """base.html must not link to nonexistent publico/css/estilos.css (causing 404 on all pages)."""
    rendered = render_to_string('base.html')
    assert 'estilos.css' not in rendered


def test_base_template_has_no_bootstrap_cdn_and_uses_local_css():
    """base.html must not load Bootstrap CDN and any external asset must include SRI integrity."""
    rendered = render_to_string('base.html')

    assert 'bootstrap' not in rendered.lower(), "base.html no debe cargar Bootstrap por CDN"
    assert 'base_views.css' in rendered, "base.html debe cargar el CSS local base_views.css"

    external_links = re.findall(r'<link[^>]+href=["\']https?://[^>]+>', rendered)
    for tag in external_links:
        assert 'integrity=' in tag, f"El enlace externo carece de atributo integrity: {tag}"
        assert 'crossorigin="anonymous"' in tag, f"El enlace externo carece de crossorigin: {tag}"

    # Los iconos son Lucide vendido localmente; cualquier CDN de Font
    # Awesome en base.html es un residuo de la migración SCRUM-422.
    assert 'cdnjs' not in rendered, "base.html no debe cargar CDNs residuales (Font Awesome / cdnjs)"

    external_scripts = re.findall(r'<script[^>]+src=["\']https?://[^>]+>', rendered)
    for tag in external_scripts:
        assert 'integrity=' in tag, f"El script externo carece de atributo integrity: {tag}"
        assert 'crossorigin="anonymous"' in tag, f"El script externo carece de crossorigin: {tag}"
