import re


def _rol_en_contrato(user, contrato):
    """Devuelve 'empresa', 'desarrollador', 'administrador' o None según la relación con el contrato."""
    postulacion = contrato.postulacion
    if user.id == postulacion.proyecto.empresa_id:
        return 'empresa'
    if user.id == postulacion.desarrollador_id:
        return 'desarrollador'
    if user.rol == 'administrador':
        return 'administrador'
    return None


def _es_xhr(request):
    """True cuando la petición proviene del modal in-situ (Fetch con Accept application/json o XHR)."""
    accept = request.headers.get('Accept', '')
    return (
        'application/json' in accept
        or request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.POST.get('origen') == 'dashboard'
    )


def _peticion_ajax(request):
    """True cuando el cliente espera JSON (Fetch con Accept application/json o ?format=json)."""
    return _es_xhr(request) or request.GET.get('format') == 'json'


def _es_htmx(request):
    """True cuando la petición proviene de HTMX y no solicita JSON explícitamente."""
    return request.headers.get('HX-Request') == 'true' and not _peticion_ajax(request)


def _es_modal_jdm(request):
    """True cuando el destino es el modal compartido #jdmModal del panel desarrollador."""
    return (
        request.GET.get('jdm') == '1'
        or request.POST.get('jdm') == '1'
        or request.headers.get('HX-Target') == 'jdmBody'
    )


def _es_url_http_segura(url):
    return bool(re.match(r'^https?://\S+$', str(url or '').strip(), re.I))
