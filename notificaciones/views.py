from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Notificacion
from django.contrib import messages

@login_required
def lista_notificaciones(request):
    """Lista todas las notificaciones del usuario actual con select_related y paginación."""
    notificaciones_qs = Notificacion.objects.filter(
        usuario=request.user
    ).select_related('proyecto').order_by('-fecha')
    
    paginator = Paginator(notificaciones_qs, 20)
    page_number = request.GET.get('page')
    notificaciones = paginator.get_page(page_number)
    
    return render(request, 'notificaciones/lista.html', {
        'notificaciones': notificaciones,
    })

@login_required
@require_POST
def marcar_leida(request, notificacion_id):
    """Marca una notificación específica como leída."""
    notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
    notificacion.leida = True
    notificacion.save()
    return redirect('notificaciones_lista')

@login_required
@require_POST
def marcar_todas_leidas(request):
    """Marca todas las notificaciones pendientes del usuario como leídas (SCRUM-173)."""
    Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
    messages.success(request, "Todas las notificaciones han sido marcadas como leídas.")
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect('notificaciones_lista')
