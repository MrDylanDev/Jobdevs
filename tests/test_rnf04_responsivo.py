"""
RNF-04 — Usabilidad: Interfaz adaptable a diferentes resoluciones de pantalla (responsiva).

Verifica que las plantillas clave del sistema definen viewport móvil estándar
y utilizan clases de rejilla responsiva (Bootstrap 5 y media queries).
"""

from pathlib import Path
import pytest
from django.conf import settings


class TestRNF04InterfazResponsiva:
    """Verifica que las plantillas incluyan viewport móvil y reglas responsivas."""

    def test_meta_viewport_en_plantilla_base(self):
        """La plantilla base debe definir la metaetiqueta viewport para móviles."""
        base_html_path = Path(settings.BASE_DIR) / 'templates' / 'base.html'
        assert base_html_path.exists()
        content = base_html_path.read_text(encoding='utf-8')
        assert 'name="viewport"' in content
        assert 'width=device-width' in content

    def test_meta_viewport_en_plantillas_autonomas(self):
        """Las plantillas de dashboards y vistas públicas deben ser responsivas."""
        plantillas = [
            'templates/Desarrollador/Desarrollador.html',
            'templates/empresa/empresa.html',
            'templates/administrador/Administrador.html',
            'templates/publico/index.html',
        ]
        for rel_path in plantillas:
            path = Path(settings.BASE_DIR) / rel_path
            assert path.exists(), f"Plantilla {rel_path} debe existir"
            content = path.read_text(encoding='utf-8')
            assert ('viewport' in content or 'base.html' in content), (
                f"Plantilla {rel_path} debe incluir viewport o heredar de base.html"
            )

    def test_hoja_estilos_dashboard_incluye_media_queries(self):
        """El CSS principal del dashboard debe definir puntos de quiebre (media queries) responsivos."""
        css_path = Path(settings.BASE_DIR) / 'static' / 'dashboard' / 'css' / 'dashboard.css'
        if not css_path.exists():
            css_path = Path(settings.BASE_DIR) / 'static' / 'css' / 'dashboard.css'
        
        assert css_path.exists(), f"Archivo CSS {css_path} debe existir"
        content = css_path.read_text(encoding='utf-8')
        assert '@media' in content
        assert ('max-width' in content or 'min-width' in content)
