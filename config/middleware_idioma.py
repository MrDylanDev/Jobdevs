"""Idioma determinista para las URLs sin prefijo.

Con `prefix_default_language=False` el español vive en `/` y el inglés en `/en/`,
pero `LocaleMiddleware` sigue resolviendo el idioma de una ruta sin prefijo con
la sesión, la cookie y el header `Accept-Language`. Eso hacía que `/` se sirviera
en inglés a un navegador en inglés, duplicando el contenido y dejando el español
sin URL canónica.

Este middleware corre después de `LocaleMiddleware` y, cuando la ruta no trae
prefijo de idioma, activa el idioma por defecto. El inglés queda donde
corresponde: en `/en/`.
"""

from django.conf import settings
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin


class IdiomaPorDefectoSinPrefijo(MiddlewareMixin):
    def process_request(self, request):
        if translation.get_language_from_path(request.path_info) is not None:
            return None
        translation.activate(settings.LANGUAGE_CODE)
        request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        return None
