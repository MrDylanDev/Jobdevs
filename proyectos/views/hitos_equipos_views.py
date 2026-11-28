import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from avances.models import Avance
from contrataciones.models import Contratacion
from notificaciones.models import Notificacion

from ..models import Entregable, Equipo, Proyecto
from ._helpers import _es_htmx


def _contexto_equipos_panel(proyecto):
    desarrolladores = Contratacion.objects.desarrolladores_activos(proyecto)
    equipos = proyecto.equipos.all().prefetch_related('miembros')
    return {
        'proyecto': proyecto,
        'desarrolladores': desarrolladores,
        'equipos': equipos,
    }


def _render_equipos_panel_htmx(request, proyecto, mensaje, tipo='success'):
    response = render(
        request,
        'proyectos/partials/_equipos_panel.html',
        _contexto_equipos_panel(proyecto),
    )
    response['HX-Trigger'] = json.dumps({
        'jobdevs:toast': {'tipo': tipo, 'mensaje': mensaje},
    })
    return response


def _contexto_hitos_panel(proyecto):
    hitos = (
        Entregable.objects.filter(proyecto=proyecto)
        .select_related('desarrollador', 'equipo')
        .order_by('fecha_creacion')
    )
    equipos = proyecto.equipos.all()
    contratos_activos = Contratacion.objects.filter(proyecto=proyecto, estado='activa')
    tiene_multiples_contratos = contratos_activos.count() >= 2
    desarrolladores_activos = contratos_activos.select_related('desarrollador')
    return {
        'proyecto': proyecto,
        'hitos': hitos,
        'equipos': equipos,
        'tiene_multiples_contratos': tiene_multiples_contratos,
        'desarrolladores_activos': desarrolladores_activos,
    }


def _render_hitos_panel_htmx(request, proyecto, mensaje, tipo='success'):
    response = render(
        request,
        'proyectos/partials/_hitos_panel.html',
        _contexto_hitos_panel(proyecto),
    )
    response['HX-Trigger'] = json.dumps({
        'jobdevs:toast': {'tipo': tipo, 'mensaje': mensaje},
    })
    return response


@login_required
def gestionar_equipos(request, proyecto_id):
    if request.user.rol != 'empresa':
        return redirect('inicio')
    es_htmx = _es_htmx(request)

    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)
    # Hallazgo 19: Usar helper del manager Contratacion
    desarrolladores = Contratacion.objects.desarrolladores_activos(proyecto)

    if desarrolladores.count() < 2:
        msg = "Para crear grupos o parejas se requieren al menos 2 desarrolladores contratados."
        if es_htmx:
            return _render_equipos_panel_htmx(request, proyecto, msg, tipo='warning')
        messages.warning(request, msg)
        return redirect('gestionar_hitos', proyecto_id=proyecto.id)

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        miembros_ids = request.POST.getlist('miembros')

        if nombre and miembros_ids:
            nombre = (request.POST.get('nombre') or '').strip()[:100]
            if not nombre:
                msg = "El nombre del equipo es obligatorio."
                if es_htmx:
                    return _render_equipos_panel_htmx(
                        request, proyecto, msg, tipo='error'
                    )
                messages.error(request, msg)
                return redirect('gestionar_equipos', proyecto_id=proyecto.id)

            # Hallazgo 8: Validar que todos los miembros pertenezcan a los desarrolladores activos contratados
            dev_ids_activos = {
                str(uid) for uid in desarrolladores.values_list('id', flat=True)
            }
            if not all(str(m) in dev_ids_activos for m in miembros_ids):
                msg = "Error: Solo puedes asignar desarrolladores contratados y activos en este proyecto."
                if es_htmx:
                    return _render_equipos_panel_htmx(
                        request, proyecto, msg, tipo='error'
                    )
                messages.error(request, msg)
                return redirect('gestionar_equipos', proyecto_id=proyecto.id)

            equipo = Equipo.objects.create(nombre=nombre, proyecto=proyecto)
            equipo.miembros.set(miembros_ids)

            # Notificación: Avisar a cada miembro usando equipo.nombre consistente
            for miembro_id in miembros_ids:
                Notificacion.objects.create(
                    usuario_id=miembro_id,
                    tipo='mensaje',
                    mensaje=f"Has sido asignado al equipo '{equipo.nombre}' en el proyecto: {proyecto.titulo}",
                )

            msg = f"Equipo '{equipo.nombre}' creado y miembros notificados."
            if es_htmx:
                return _render_equipos_panel_htmx(
                    request, proyecto, msg, tipo='success'
                )
            messages.success(request, msg)
            return redirect('gestionar_equipos', proyecto_id=proyecto.id)
        elif es_htmx:
            return _render_equipos_panel_htmx(
                request,
                proyecto,
                "Debes indicar un nombre y seleccionar al menos un miembro.",
                tipo='error',
            )

    equipos = proyecto.equipos.all().prefetch_related('miembros')

    return render(
        request,
        'proyectos/gestionar_equipos.html',
        {
            'proyecto': proyecto,
            'desarrolladores': desarrolladores,
            'equipos': equipos,
        },
    )


@login_required
@require_POST
def eliminar_equipo(request, equipo_id):
    es_htmx = _es_htmx(request)
    equipo = get_object_or_404(Equipo, id=equipo_id, proyecto__empresa=request.user)
    proyecto = equipo.proyecto
    equipo.delete()
    msg = "Equipo eliminado."
    if es_htmx:
        return _render_equipos_panel_htmx(request, proyecto, msg, tipo='info')
    messages.info(request, msg)
    return redirect('gestionar_equipos', proyecto_id=proyecto.id)


@login_required
def gestionar_hitos(request, proyecto_id):
    es_htmx = _es_htmx(request)
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)
    hitos = Entregable.objects.filter(proyecto=proyecto).order_by('fecha_creacion')

    if request.method == 'POST':
        # Hallazgo 16: No permitir crear hitos en proyectos finalizados, inactivos o rechazados
        if proyecto.estado in ('finalizado', 'inactivo', 'rechazado'):
            msg = f"No se pueden agregar hitos a un proyecto {proyecto.get_estado_display().lower()}."
            if es_htmx:
                return _render_hitos_panel_htmx(request, proyecto, msg, tipo='error')
            messages.error(request, msg)
            return redirect('gestionar_hitos', proyecto_id=proyecto.id)

        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        equipo_id = request.POST.get('equipo_id')
        desarrollador_id = request.POST.get('desarrollador_id')

        if titulo:
            # Validacion de integridad: El equipo debe pertenecer al proyecto
            equipo = None
            if equipo_id:
                equipo = Equipo.objects.filter(id=equipo_id, proyecto=proyecto).first()
                if not equipo:
                    msg = "Error: El equipo seleccionado no pertenece a este proyecto."
                    if es_htmx:
                        return _render_hitos_panel_htmx(
                            request, proyecto, msg, tipo='error'
                        )
                    messages.error(request, msg)
                    return redirect('gestionar_hitos', proyecto_id=proyecto.id)

            # SCRUM-309 (HU-E13): el desarrollador asignado debe tener contratación activa
            desarrollador = None
            if desarrollador_id:
                contratacion = (
                    Contratacion.objects.filter(
                        proyecto=proyecto,
                        desarrollador_id=desarrollador_id,
                        estado='activa',
                    )
                    .select_related('desarrollador')
                    .first()
                )
                if not contratacion:
                    msg = "Error: El desarrollador seleccionado no tiene una contratación activa en este proyecto."
                    if es_htmx:
                        return _render_hitos_panel_htmx(
                            request, proyecto, msg, tipo='error'
                        )
                    messages.error(request, msg)
                    return redirect('gestionar_hitos', proyecto_id=proyecto.id)
                desarrollador = contratacion.desarrollador

            Entregable.objects.create(
                proyecto=proyecto,
                titulo=titulo,
                descripcion=descripcion,
                equipo=equipo,
                desarrollador=desarrollador,
            )

            # Notificacion
            if desarrollador:
                # SCRUM-309: avisar únicamente al desarrollador asignado
                Notificacion.objects.create(
                    usuario=desarrollador,
                    tipo='avance',
                    mensaje=f"Nueva tarea asignada de forma individual en '{proyecto.titulo}': {titulo}",
                )
            elif equipo:
                # Avisar solo a los miembros del equipo
                for miembro in equipo.miembros.all():
                    Notificacion.objects.create(
                        usuario=miembro,
                        tipo='avance',
                        mensaje=f"Nueva tarea asignada a tu equipo '{equipo.nombre}': {titulo}",
                    )
            else:
                # Avisar a todos los contratados en el proyecto (Hito General)
                # Hallazgo 19: Usar helper del manager Contratacion
                desarrolladores = Contratacion.objects.desarrolladores_activos(proyecto)
                for dev in desarrolladores:
                    Notificacion.objects.create(
                        usuario=dev,
                        tipo='avance',
                        mensaje=f"Nueva tarea general en '{proyecto.titulo}': {titulo}",
                    )

            msg = f"Hito '{titulo}' creado y desarrolladores notificados."
            if es_htmx:
                return _render_hitos_panel_htmx(request, proyecto, msg, tipo='success')
            messages.success(request, msg)
            next_url = request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return HttpResponseRedirect(next_url)
            return redirect('gestionar_hitos', proyecto_id=proyecto.id)
        elif es_htmx:
            return _render_hitos_panel_htmx(
                request,
                proyecto,
                "El nombre del hito es obligatorio.",
                tipo='error',
            )

    equipos = proyecto.equipos.all()
    tiene_multiples_contratos = (
        Contratacion.objects.filter(proyecto=proyecto, estado='activa').count() >= 2
    )
    # SCRUM-309 (HU-E13): candidatos válidos para asignación individual de hitos
    desarrolladores_activos = Contratacion.objects.filter(
        proyecto=proyecto, estado='activa'
    ).select_related('desarrollador')

    # Sub-tab "Línea de Tiempo de Avances" sin recargar la página
    avances = (
        Avance.objects.filter(proyecto=proyecto)
        .select_related('desarrollador__perfil_desarrollador', 'entregable')
        .order_by('-fecha_hora')
    )
    progreso = hitos.aggregate(
        hitos_completados=Count('id', filter=Q(estado='completado')),
        hitos_totales=Count('id'),
    )

    return render(
        request,
        'proyectos/gestionar_hitos.html',
        {
            'proyecto': proyecto,
            'hitos': hitos,
            'avances': avances,
            'hitos_completados': progreso['hitos_completados'] or 0,
            'hitos_totales': progreso['hitos_totales'] or 0,
            'equipos': equipos,
            'tiene_multiples_contratos': tiene_multiples_contratos,
            'desarrolladores_activos': desarrolladores_activos,
        },
    )


@login_required
@require_POST
def eliminar_hito(request, hito_id):
    es_htmx = _es_htmx(request)
    hito = get_object_or_404(Entregable, id=hito_id, proyecto__empresa=request.user)
    proyecto = hito.proyecto
    if hito.estado == 'pendiente':
        hito.delete()
        msg = "Hito eliminado."
        if es_htmx:
            return _render_hitos_panel_htmx(request, proyecto, msg, tipo='success')
        messages.success(request, msg)
    else:
        msg = "No se puede eliminar un hito que ya ha sido completado."
        if es_htmx:
            return _render_hitos_panel_htmx(request, proyecto, msg, tipo='error')
        messages.error(request, msg)
    return redirect('gestionar_hitos', proyecto_id=proyecto.id)
