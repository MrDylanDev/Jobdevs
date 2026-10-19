from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Favorito
from proyectos.models import Proyecto

@login_required
@require_POST
def toggle_favorito(request, proyecto_id):
    """Añadir o quitar un proyecto de favoritos (permite remover favoritos de cualquier estado y soporta AJAX)."""
    is_ajax = (
        request.headers.get('Accept') == 'application/json'
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )

    if request.user.rol != 'desarrollador':
        if is_ajax:
            return JsonResponse({'error': 'Solo los desarrolladores pueden gestionar favoritos.'}, status=403)
        return redirect('inicio')
        
    favorito = Favorito.objects.filter(desarrollador=request.user, proyecto_id=proyecto_id).first()
    if favorito:
        favorito.delete()
        mensaje = "Proyecto eliminado de favoritos."
        agregado = False
    else:
        proyecto = get_object_or_404(Proyecto, id=proyecto_id, estado='publicado')
        Favorito.objects.create(desarrollador=request.user, proyecto=proyecto)
        mensaje = "Proyecto añadido a favoritos."
        agregado = True

    if is_ajax:
        return JsonResponse({
            'status': 'ok',
            'agregado': agregado,
            'mensaje': mensaje,
            'proyecto_id': proyecto_id,
        })
        
    messages.success(request, mensaje)
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect('listar_proyectos')

@login_required
def listar_favoritos(request):
    """Ver lista de proyectos favoritos del desarrollador con select_related y paginación"""
    if request.user.rol != 'desarrollador':
        return redirect('inicio')
        
    favoritos_qs = Favorito.objects.filter(
        desarrollador=request.user
    ).select_related('proyecto__empresa', 'proyecto__categoria').order_by('-id')
    
    paginator = Paginator(favoritos_qs, 20)
    page_number = request.GET.get('page')
    favoritos = paginator.get_page(page_number)
    
    return render(request, 'favoritos/lista.html', {'favoritos': favoritos})
