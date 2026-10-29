"""Etiquetas del conmutador de idioma de la landing.

`django.urls.translate_url` sabe convertir una ruta en su equivalente para otro
idioma, pero no está expuesta como etiqueta de plantilla, así que la envolvemos
acá. Con `prefix_default_language=False` el español vive en `/` y el inglés en
`/en/`, y esta etiqueta respeta ese esquema.
"""

from django import template
from django.urls import translate_url

register = template.Library()


@register.simple_tag(takes_context=True)
def url_idioma(context, codigo):
    """Devuelve la URL de la página actual en `codigo`.

    Si la ruta actual no se puede traducir (por ejemplo, una vista que no está
    dentro de i18n_patterns), devuelve la raíz en ese idioma.
    """
    peticion = context.get('request')
    if peticion is None:
        return '/' if codigo == 'es-co' else '/en/'
    try:
        return translate_url(peticion.get_full_path(), codigo)
    except Exception:
        return '/' if codigo == 'es-co' else '/en/'
