from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from contrataciones.models import Contratacion
from proyectos.models import Proyecto

from .models import Disputa
from .services import abrir_disputa


@login_required
def abrir_disputa_view(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, pk=proyecto_id)
    user = request.user

    contratacion = Contratacion.objects.filter(proyecto=proyecto, estado='activa')
    if user.pk == proyecto.empresa_id:
        contratacion = contratacion.order_by('pk').first()
    else:
        contratacion = contratacion.filter(desarrollador=user).first()
        if contratacion is None:
            raise PermissionDenied('No participas en este proyecto.')

    context = {'proyecto': proyecto, 'contratacion': contratacion, 'motivo': ''}

    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()
        context['motivo'] = motivo
        if not motivo:
            messages.error(request, 'Debes indicar el motivo de la disputa.')
            return render(request, 'disputas/abrir_disputa.html', context)
        try:
            disputa = abrir_disputa(proyecto, user, motivo, contratacion)
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
            return render(request, 'disputas/abrir_disputa.html', context, status=400)
        messages.success(
            request, 'Disputa abierta. El proyecto fue congelado hasta su resolución.'
        )
        return redirect('disputas:detalle_disputa', disputa_id=disputa.id)

    return render(request, 'disputas/abrir_disputa.html', context)


@login_required
def detalle_disputa_view(request, disputa_id):
    """Placeholder de la sala de disputa (se implementa en tareas posteriores)."""
    disputa = get_object_or_404(Disputa.objects.select_related('proyecto'), pk=disputa_id)
    user = request.user
    participa = (
        user.pk in (disputa.proyecto.empresa_id, disputa.iniciado_por_id)
        or (disputa.contratacion_id and user.pk == disputa.contratacion.desarrollador_id)
        or user.rol == 'administrador'
    )
    if not participa:
        raise PermissionDenied
    return HttpResponse(f'Disputa #{disputa.pk} - {disputa.get_estado_display()}')
