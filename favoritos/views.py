from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Favorito
from proyectos.models import Proyecto

@login_required
@require_POST
def toggle_favorito(request, proyecto_id):
    """Añadir o quitar un proyecto de favoritos (solo proyectos en estado publicado)"""
    if request.user.rol != 'desarrollador':
        return redirect('inicio')
        
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, estado='publicado')
    
    try:
        favorito, created = Favorito.objects.get_or_create(
            desarrollador=request.user,
            proyecto=proyecto
        )
        if not created:
            favorito.delete()
            messages.success(request, "Proyecto eliminado de favoritos.")
        else:
            messages.success(request, "Proyecto añadido a favoritos.")
    except Exception as e:
        messages.error(request, f"Error al procesar favorito: {e}")
        
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
