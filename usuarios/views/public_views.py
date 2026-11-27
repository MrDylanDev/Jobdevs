from django.conf import settings
from django.shortcuts import render


def _legal_context(request, active_slug: str) -> dict:
    return {
        'allow_public_registration': getattr(settings, 'ALLOW_PUBLIC_REGISTRATION', True),
        'legal_active': active_slug,
        'IDIOMA': getattr(request, 'LANGUAGE_CODE', 'es-co'),
    }


def legal_condiciones_view(request):
    return render(request, 'publico/legal_condiciones.html', _legal_context(request, 'condiciones'))


def legal_privacidad_view(request):
    return render(request, 'publico/legal_privacidad.html', _legal_context(request, 'privacidad'))


def legal_cookies_view(request):
    return render(request, 'publico/legal_cookies.html', _legal_context(request, 'cookies'))
