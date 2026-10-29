"""URLs de estáticos con versión.

nginx sirve `/static/` con `Cache-Control: public, immutable, max-age=30d`, y la
URL no cambia cuando cambia el archivo: el navegador se queda con la copia vieja
aunque se recargue. Esta etiqueta agrega la fecha de modificación como query, así
un archivo nuevo estrena URL y el cache deja de mentir.
"""

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(ruta):
    url = static(ruta)
    ruta_absoluta = finders.find(ruta)
    if not ruta_absoluta:
        return url
    try:
        from pathlib import Path

        version = int(Path(ruta_absoluta).stat().st_mtime)
    except OSError:
        return url
    return f'{url}?v={version}'
