import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from contrataciones.models import Contratacion

from .. import services
from ..models import Proyecto, Valoracion


@login_required
def finalizar_proyecto(request, proyecto_id):
    """Muestra la confirmación o delega finalización/valoración en los servicios.

    La vista se queda con permisos, parseo del input y mensajes; las reglas de
    negocio (estado, hitos, cupos, transiciones) viven en proyectos/services.py.
    """
    wants_json = (
        'application/json' in (request.headers.get('Accept') or '')
        or request.GET.get('format') == 'json'
        or request.headers.get('x-requested-with') == 'XMLHttpRequest'
    )
    es_htmx = request.headers.get('HX-Request') == 'true' and not wants_json

    if request.user.rol != 'empresa':
        if es_htmx:
            return render(
                request,
                'proyectos/partials/_modal_finalizar_proyecto.html',
                {'error': 'Acceso denegado.', 'solo_mensaje': True},
                status=403,
            )
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)
    action_url = reverse('finalizar_proyecto', args=[proyecto.id])

    if proyecto.estado == 'finalizado':
        try:
            services.validar_plazo_valoracion(proyecto)
        except ValidationError as exc:
            err_msg = ' '.join(exc.messages)
            if es_htmx:
                return render(
                    request,
                    'proyectos/partials/_modal_finalizar_proyecto.html',
                    {'proyecto': proyecto, 'error': err_msg, 'solo_mensaje': True},
                    status=200,
                )
            messages.error(request, err_msg)
            return redirect('dashboard_empresa')
    else:
        # Prevalidación de UX para el cierre manual de compatibilidad.
        try:
            services.validar_finalizacion(proyecto)
        except ValidationError as exc:
            motivo = ' '.join(exc.messages)
            if es_htmx:
                return render(
                    request,
                    'proyectos/partials/_modal_finalizar_proyecto.html',
                    {'proyecto': proyecto, 'error': motivo, 'solo_mensaje': True},
                    status=200,
                )
            messages.error(request, motivo)
            if 'hitos definidos' in motivo:
                return redirect('gestionar_hitos', proyecto_id=proyecto.id)
            if 'hitos sin completar' in motivo:
                return redirect('ver_avances', proyecto_id=proyecto.id)
            return redirect('dashboard_empresa')

        # Compatibilidad para proyectos antiguos con todos sus hitos aprobados:
        # se confirma el cierre primero y las valoraciones se recogen después.
        if request.method == 'POST':
            try:
                services.finalizar_proyecto(proyecto.id, request.user)
                msg = f"El proyecto '{proyecto.titulo}' fue finalizado. Ya puedes calificar al equipo."
                if es_htmx:
                    pendientes_post = services.desarrolladores_pendientes(proyecto)
                    if pendientes_post.exists():
                        response = render(
                            request,
                            'proyectos/partials/_modal_finalizar_proyecto.html',
                            {
                                'proyecto': proyecto,
                                'desarrollador': pendientes_post.first(),
                                'restantes': pendientes_post.count() - 1,
                                'action_url': action_url,
                            },
                        )
                        response['HX-Trigger'] = json.dumps({
                            'jobdevs:toast': {'tipo': 'success', 'mensaje': msg},
                        })
                        return response
                    response = HttpResponse('')
                    response['HX-Trigger'] = json.dumps({
                        'jobdevs:toast': {'tipo': 'success', 'mensaje': msg},
                        'jobdevs:calificacion-guardada': {
                            'proyecto_id': proyecto.id,
                            'reload_hash': 'historial',
                        },
                    })
                    return response
                messages.success(request, msg)
            except (PermissionDenied, ValidationError) as exc:
                err_msg = ' '.join(getattr(exc, 'messages', [str(exc)]))
                if es_htmx:
                    return render(
                        request,
                        'proyectos/partials/_modal_finalizar_proyecto.html',
                        {
                            'proyecto': proyecto,
                            'desarrollador': None,
                            'restantes': 0,
                            'action_url': action_url,
                            'error': err_msg,
                        },
                        status=200,
                    )
                messages.error(request, err_msg)
            return redirect('finalizar_proyecto', proyecto_id=proyecto.id)

        template = (
            'proyectos/partials/_modal_finalizar_proyecto.html'
            if es_htmx
            else 'proyectos/finalizar.html'
        )
        return render(
            request,
            template,
            {
                'proyecto': proyecto,
                'desarrollador': None,
                'restantes': 0,
                'action_url': action_url,
            },
        )

    pendientes = services.desarrolladores_pendientes(proyecto)

    # Proyecto ya cerrado: las valoraciones no gobiernan la transición de estado.
    if not pendientes.exists():
        if es_htmx:
            return render(
                request,
                'proyectos/partials/_modal_finalizar_proyecto.html',
                {'proyecto': proyecto, 'todos_calificados': True},
                status=200,
            )
        messages.info(request, "Todos los colaboradores ya fueron calificados.")
        return redirect('dashboard_empresa')

    # ── Caso B: quedan colaboradores por calificar ──
    desarrollador = pendientes.first()
    restantes = pendientes.count() - 1

    if request.method == 'POST':
        puntuacion = request.POST.get('puntuacion')
        comentario = request.POST.get('comentario', '')
        err_msg = None
        try:
            finalizado, restantes = services.valorar_y_finalizar_si_ultima(
                proyecto_id=proyecto.id,
                desarrollador_id=desarrollador.id,
                puntuacion=puntuacion,
                comentario=comentario,
                ejecutado_por=request.user,
            )
        except PermissionDenied as exc:
            err_msg = str(exc)
        except ValidationError as exc:
            err_msg = ' '.join(exc.messages)
        except Exception as e:
            err_msg = f"Error: {str(e)}"

        if err_msg is not None:
            if es_htmx:
                return render(
                    request,
                    'proyectos/partials/_modal_finalizar_proyecto.html',
                    {
                        'proyecto': proyecto,
                        'desarrollador': desarrollador,
                        'restantes': restantes,
                        'action_url': action_url,
                        'puntuacion': puntuacion or '',
                        'comentario': comentario,
                        'error': err_msg,
                    },
                    status=200,
                )
            messages.error(request, err_msg)
            return redirect('finalizar_proyecto', proyecto_id=proyecto.id)

        if finalizado:
            msg = (
                f"¡Excelente! Has calificado a todo el equipo y el proyecto "
                f"'{proyecto.titulo}' ha finalizado."
            )
            if es_htmx:
                response = HttpResponse('')
                response['HX-Trigger'] = json.dumps({
                    'jobdevs:toast': {'tipo': 'success', 'mensaje': msg},
                    'jobdevs:calificacion-guardada': {
                        'proyecto_id': proyecto.id,
                        'reload_hash': 'historial',
                    },
                })
                return response
            messages.success(request, msg)
            return redirect('dashboard_empresa')

        msg = f"Calificación registrada para {desarrollador.username}. " + (
            f"Quedan {restantes} por calificar."
            if restantes > 0
            else "Era el último colaborador."
        )
        if es_htmx:
            pendientes_post = services.desarrolladores_pendientes(proyecto)
            if pendientes_post.exists():
                response = render(
                    request,
                    'proyectos/partials/_modal_finalizar_proyecto.html',
                    {
                        'proyecto': proyecto,
                        'desarrollador': pendientes_post.first(),
                        'restantes': pendientes_post.count() - 1,
                        'action_url': action_url,
                    },
                )
                response['HX-Trigger'] = json.dumps({
                    'jobdevs:toast': {'tipo': 'success', 'mensaje': msg},
                })
                return response
            response = HttpResponse('')
            response['HX-Trigger'] = json.dumps({
                'jobdevs:toast': {'tipo': 'success', 'mensaje': msg},
                'jobdevs:calificacion-guardada': {
                    'proyecto_id': proyecto.id,
                    'reload_hash': 'historial',
                },
            })
            return response

        messages.success(request, msg)
        # Recargamos la misma vista para el siguiente desarrollador
        return redirect('finalizar_proyecto', proyecto_id=proyecto.id)

    template = (
        'proyectos/partials/_modal_finalizar_proyecto.html'
        if es_htmx
        else 'proyectos/finalizar.html'
    )
    return render(
        request,
        template,
        {
            'proyecto': proyecto,
            'desarrollador': desarrollador,
            'restantes': restantes,
            'action_url': action_url,
        },
    )


@login_required
def calificar_empresa(request, proyecto_id):
    """Permite al desarrollador calificar a la empresa tras finalizar un proyecto"""
    wants_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in (request.headers.get('Accept') or '')
        or request.GET.get('format') == 'json'
        or request.POST.get('origen') == 'dashboard'
    )
    es_htmx = request.headers.get('HX-Request') == 'true' and not wants_json
    es_ajax = wants_json
    es_obligatorio = request.GET.get('obligatorio') in (
        '1',
        'true',
    ) or request.POST.get('obligatorio') in ('1', 'true')
    partial_tpl = 'proyectos/partials/_modal_calificar_empresa.html'

    if request.user.rol != 'desarrollador':
        if es_ajax:
            return JsonResponse(
                {
                    'ok': False,
                    'error': 'Acceso denegado.',
                    'mensaje': 'Acceso denegado.',
                },
                status=403,
            )
        if es_htmx:
            return render(
                request,
                partial_tpl,
                {'solo_mensaje': True, 'error': 'Acceso denegado.'},
                status=403,
            )
        return redirect('inicio')

    if es_ajax or es_htmx:
        proyecto = Proyecto.objects.filter(id=proyecto_id, estado='finalizado').first()
        if not proyecto:
            msg = 'El proyecto no existe o aún no ha finalizado.'
            if es_ajax:
                return JsonResponse(
                    {'ok': False, 'error': msg, 'mensaje': msg}, status=404
                )
            return render(
                request, partial_tpl, {'solo_mensaje': True, 'error': msg}, status=404
            )
        contratacion = Contratacion.objects.filter(
            proyecto=proyecto, desarrollador=request.user
        ).first()
        if not contratacion:
            msg = 'No tienes una contratación asociada a este proyecto.'
            if es_ajax:
                return JsonResponse(
                    {'ok': False, 'error': msg, 'mensaje': msg}, status=404
                )
            return render(
                request, partial_tpl, {'solo_mensaje': True, 'error': msg}, status=404
            )
    else:
        proyecto = get_object_or_404(Proyecto, id=proyecto_id, estado='finalizado')
        get_object_or_404(Contratacion, proyecto=proyecto, desarrollador=request.user)

    empresa_nombre = proyecto.empresa.nombre or proyecto.empresa.username
    action_url = reverse('calificar_empresa', args=[proyecto.id])

    def _htmx_ctx(**extra):
        ctx = {
            'proyecto': proyecto,
            'empresa_nombre': empresa_nombre,
            'action_url': action_url,
            'es_obligatorio': es_obligatorio,
            'min_comentario': services.MIN_COMENTARIO,
            'puntuacion': '',
            'puntuacion_num': 0,
            'comentario': '',
        }
        ctx.update(extra)
        return ctx

    try:
        services.validar_plazo_valoracion(proyecto)
    except ValidationError as exc:
        msg = ' '.join(exc.messages)
        if es_ajax:
            return JsonResponse({'ok': False, 'error': msg, 'mensaje': msg}, status=400)
        if es_htmx:
            return render(
                request,
                partial_tpl,
                _htmx_ctx(solo_mensaje=True, error=msg),
                status=400,
            )
        messages.error(request, msg)
        return redirect('dashboard_desarrollador')

    if request.method == 'GET' and (es_ajax or es_htmx):
        ya_califico = Valoracion.objects.filter(
            proyecto=proyecto,
            empresa=proyecto.empresa,
            desarrollador=request.user,
            rol_evaluador='desarrollador',
        ).exists()
        if es_htmx:
            return render(request, partial_tpl, _htmx_ctx(ya_califico=ya_califico))
        return JsonResponse({
            'ok': True,
            'proyecto': {
                'id': proyecto.id,
                'titulo': proyecto.titulo,
                'empresa': empresa_nombre,
            },
            'ya_califico': ya_califico,
            'url_calificar': action_url,
        })

    if request.method == 'POST':
        raw_puntuacion = (request.POST.get('puntuacion') or '').strip()
        raw_comentario = (request.POST.get('comentario') or '').strip()

        try:
            puntuacion = int(raw_puntuacion)
        except (TypeError, ValueError):
            msg = "Debes seleccionar una puntuación."
            if es_ajax:
                return JsonResponse({'ok': False, 'mensaje': msg}, status=400)
            if es_htmx:
                return render(
                    request,
                    partial_tpl,
                    _htmx_ctx(
                        error=msg,
                        puntuacion=raw_puntuacion,
                        puntuacion_num=0,
                        comentario=raw_comentario,
                    ),
                    status=200,
                )
            messages.error(request, msg)
            return redirect('calificar_empresa', proyecto_id=proyecto.id)

        if not 1 <= puntuacion <= 5:
            msg = "La puntuación debe estar entre 1 y 5."
            if es_ajax:
                return JsonResponse({'ok': False, 'mensaje': msg}, status=400)
            if es_htmx:
                return render(
                    request,
                    partial_tpl,
                    _htmx_ctx(
                        error=msg,
                        puntuacion=raw_puntuacion,
                        puntuacion_num=0,
                        comentario=raw_comentario,
                    ),
                    status=200,
                )
            messages.error(request, msg)
            return redirect('calificar_empresa', proyecto_id=proyecto.id)

        # RF 5.2.2: puntuación + comentario cualitativo obligatorio.
        comentario = raw_comentario
        if len(comentario) < services.MIN_COMENTARIO:
            msg = (
                f"El comentario es obligatorio y debe tener al menos "
                f"{services.MIN_COMENTARIO} caracteres."
            )
            if es_ajax:
                return JsonResponse({'ok': False, 'mensaje': msg}, status=400)
            if es_htmx:
                return render(
                    request,
                    partial_tpl,
                    _htmx_ctx(
                        error=msg,
                        puntuacion=str(puntuacion),
                        puntuacion_num=puntuacion,
                        comentario=comentario,
                    ),
                    status=200,
                )
            messages.error(request, msg)
            return redirect('calificar_empresa', proyecto_id=proyecto.id)

        try:
            with transaction.atomic():
                if Valoracion.objects.filter(
                    proyecto=proyecto,
                    empresa=proyecto.empresa,
                    desarrollador=request.user,
                    rol_evaluador='desarrollador',
                ).exists():
                    msg = "Ya has calificado a esta empresa para este proyecto."
                    if es_ajax:
                        return JsonResponse({'ok': False, 'mensaje': msg}, status=409)
                    if es_htmx:
                        return render(
                            request,
                            partial_tpl,
                            _htmx_ctx(ya_califico=True),
                            status=200,
                        )
                    messages.error(request, msg)
                    return redirect('dashboard_desarrollador')

                Valoracion.objects.create(
                    proyecto=proyecto,
                    empresa=proyecto.empresa,
                    desarrollador=request.user,
                    puntuacion=puntuacion,
                    comentario=comentario,
                    rol_evaluador='desarrollador',
                )

                # RF 5.3.1: reflejar la nueva valoración en la reputación pública.
                services.recalcular_reputacion_empresa(proyecto.empresa_id)
        except IntegrityError:
            # Dos POST simultáneos: la unicidad del modelo gana la carrera.
            msg = "Ya has calificado a esta empresa para este proyecto."
            if es_ajax:
                return JsonResponse({'ok': False, 'mensaje': msg}, status=409)
            if es_htmx:
                return render(
                    request, partial_tpl, _htmx_ctx(ya_califico=True), status=200
                )
            messages.error(request, msg)
            return redirect('dashboard_desarrollador')

        ok_msg = "¡Gracias! Tu calificación ha sido registrada."
        if es_ajax:
            return JsonResponse(
                {'ok': True, 'mensaje': ok_msg, 'puntuacion': puntuacion}
            )
        if es_htmx:
            response = render(
                request,
                partial_tpl,
                _htmx_ctx(
                    calificacion_guardada=True,
                    puntuacion=puntuacion,
                    puntuacion_num=puntuacion,
                ),
                status=200,
            )
            response['HX-Trigger'] = json.dumps({
                'jobdevs:toast': {'tipo': 'success', 'mensaje': ok_msg},
                'jobdevs:calificacion-empresa-guardada': {
                    'proyecto_id': proyecto.id,
                    'puntuacion': puntuacion,
                },
            })
            return response
        messages.success(request, ok_msg)
        return redirect('dashboard_desarrollador')

    return render(request, 'proyectos/calificar_empresa.html', {'proyecto': proyecto})
