def _espera_json(request):
    """Detecta peticiones asíncronas modernas vía Fetch (Accept: application/json) o XHR."""
    return (
        'application/json' in request.headers.get('Accept', '')
        or request.headers.get('x-requested-with') == 'XMLHttpRequest'
    )


def _es_htmx(request):
    return request.headers.get('HX-Request') == 'true' and not _espera_json(request)
