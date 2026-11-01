from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ..forms import PerfilEmpresaForm, PerfilDesarrolladorForm
from ..models import PerfilEmpresa, PerfilDesarrollador
from logs.models import LogAuditoria


@login_required
def editar_perfil(request):
    if request.user.rol == 'empresa':
        perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=request.user)
        form = PerfilEmpresaForm(request.POST or None, request.FILES or None, instance=perfil)
        redirect_to = f"{reverse('dashboard_empresa')}#perfil"
    elif request.user.rol == 'desarrollador':
        perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=request.user)
        form = PerfilDesarrolladorForm(request.POST or None, request.FILES or None, instance=perfil)
        redirect_to = 'dashboard_desarrollador'
    else: return redirect('inicio')

    if request.method == 'POST' and form.is_valid():
        form.save()
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f"Actualizó su perfil de {request.user.rol}",
            tabla_afectada=f"perfil_{request.user.rol}",
            registro_id=request.user.id,
        )
        messages.success(request, "Perfil actualizado")
        return redirect(redirect_to)
    return render(request, 'usuarios/editar_perfil.html', {'form': form})
