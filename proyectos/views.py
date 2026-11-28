from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import (
    Avg, Q, Count, Prefetch, Value, FloatField, F, IntegerField, OuterRef, Subquery,
)
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta
import json
from urllib.parse import urlencode
from django.core.paginator import Paginator
from .models import Proyecto, Valoracion, Entregable, Equipo, CategoriaSolucion
from . import services
from logs.models import LogAuditoria


def _espera_json(request):
    """Detecta peticiones asíncronas modernas vía Fetch (Accept: application/json) o XHR."""
    return (
        'application/json' in request.headers.get('Accept', '')
        or request.headers.get('x-requested-with') == 'XMLHttpRequest'
    )


def _es_htmx(request):
    return request.headers.get('HX-Request') == 'true' and not _espera_json(request)
from usuarios.decorators import api_ratelimit
from usuarios.models import Usuario, PerfilDesarrollador
from contrataciones.models import Contratacion
from favoritos.models import Favorito
from postulaciones.models import Postulacion
from notificaciones.models import Notificacion
from avances.models import Avance

@login_required
def listar_proyectos(request):
    tipo = request.GET.get('tipo')
    prioridad = request.GET.get('prioridad')
    modalidad = request.GET.get('modalidad')
    ciudad = request.GET.get('ciudad', '').strip()
    q = request.GET.get('q', '').strip()
    
    # Subconsultas para el cupo real: evitan joins extra que inflarían el Avg
    # de reputación y permiten filtrar por cupo antes de paginar.
    contratos_activos_sq = (
        Contratacion.objects.filter(proyecto=OuterRef('pk'), estado='activa')
        .values('proyecto').annotate(total=Count('*')).values('total')
    )
    negociaciones_sq = (
        Postulacion.objects.filter(proyecto=OuterRef('pk'), estado='en_negociacion')
        .values('proyecto').annotate(total=Count('*')).values('total')
    )

    proyectos_qs = Proyecto.objects.select_related(
        'empresa__perfil_empresa'
    ).annotate(
        # Hallazgo 10: distinct=True para evitar conteos inflados por joins adicionales
        num_postulaciones=Count('postulaciones', distinct=True),
        empresa_reputacion=Coalesce(Avg('empresa__valoraciones_como_empresa__puntuacion',
            filter=Q(empresa__valoraciones_como_empresa__rol_evaluador='desarrollador')),
            Value(0.0), output_field=FloatField()),
        contratos_activos=Coalesce(
            Subquery(contratos_activos_sq, output_field=IntegerField()), Value(0)
        ),
        negociaciones_abiertas=Coalesce(
            Subquery(negociaciones_sq, output_field=IntegerField()), Value(0)
        ),
    ).annotate(
        disponibles_anotadas=F('vacantes') - F('contratos_activos') - F('negociaciones_abiertas'),
    ).filter(
        # Excepción de producto: también en desarrollo, pero nunca sin cupo libre.
        Q(estado__in=('publicado', 'en_desarrollo')),
        Q(disponibles_anotadas__gt=0),
        (Q(fecha_limite__isnull=True) | Q(fecha_limite__gte=timezone.now().date())),
    )
    
    if tipo:
        proyectos_qs = proyectos_qs.filter(tipo_solucion=tipo)
    if prioridad:
        proyectos_qs = proyectos_qs.filter(prioridad=prioridad)
    if modalidad:
        proyectos_qs = proyectos_qs.filter(modalidad=modalidad)
    if ciudad:
        proyectos_qs = proyectos_qs.filter(ciudad__icontains=ciudad)
    if q:
        proyectos_qs = proyectos_qs.filter(
            Q(titulo__icontains=q) | Q(descripcion__icontains=q)
        )

    favoritos_ids = []
    if request.user.rol == 'desarrollador':
        # Excluir a nivel SQL los proyectos donde el desarrollador ya tiene postulación
        postulaciones_ids = Postulacion.objects.filter(desarrollador=request.user).values_list('proyecto_id', flat=True)
        proyectos_qs = proyectos_qs.exclude(id__in=postulaciones_ids)
        favoritos_ids = list(Favorito.objects.filter(desarrollador=request.user).values_list('proyecto_id', flat=True))

    paginator = Paginator(proyectos_qs.order_by('-fecha_publicacion'), 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    proyectos = []
    for p in page_obj:
        logo = p.empresa.perfil_empresa.logo.url if (
            hasattr(p.empresa, 'perfil_empresa') and p.empresa.perfil_empresa.logo
        ) else None
        perfil = getattr(p.empresa, 'perfil_empresa', None)
        proyectos.append({
            'id': p.id,
            'empresa_id': p.empresa_id,
            'titulo': p.titulo,
            'descripcion': p.descripcion,
            'tipo_solucion': p.tipo_solucion,
            'prioridad': p.prioridad,
            'fecha_publicacion': p.fecha_publicacion,
            'empresa_nombre': p.empresa.nombre,
            'num_postulaciones': p.num_postulaciones,
            'empresa_reputacion': p.empresa_reputacion,
            'empresa_logo': logo,
            'empresa_verificada': perfil.es_verificada if perfil else False,
            'empresa_badge': perfil.badge_info if perfil else None,
            'empresa_estado_verificacion': perfil.estado_verificacion if perfil else 'sin_verificar',
            'vacantes': p.vacantes,
            'vacantes_disponibles': p.vacantes_disponibles,
            'modalidad': p.modalidad,
            'ciudad': p.ciudad,
            'ubicacion_display': p.ubicacion_display,
        })

    wants_json = (
        'application/json' in (request.headers.get('Accept') or '')
        or request.GET.get('format') == 'json'
    )
    is_htmx = request.headers.get('HX-Request') == 'true' and not wants_json
    is_ajax = (
        wants_json
        or (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and not is_htmx)
    )
    if is_ajax:
        proyectos_json = []
        for p in proyectos:
            item = dict(p)
            if item.get('fecha_publicacion'):
                item['fecha_publicacion'] = item['fecha_publicacion'].strftime('%d/%m/%Y')
            item['empresa_url'] = reverse('detalle_empresa', args=[p['empresa_id']])
            item['postular_url'] = reverse('postularse_a_proyecto', args=[p['id']])
            proyectos_json.append(item)

        return JsonResponse({
            'status': 'ok',
            'proyectos': proyectos_json,
            'favoritos_ids': favoritos_ids,
            'total_proyectos': paginator.count,
            'total_paginas': paginator.num_pages,
            'pagina_actual': page_obj.number,
            'tiene_siguiente': page_obj.has_next(),
            'tiene_anterior': page_obj.has_previous(),
        })

    context = {
        'proyectos': proyectos,
        'page_obj': page_obj,
        'favoritos_ids': favoritos_ids,
    }
    if is_htmx:
        clean_params = []
        if q:
            clean_params.append(('q', q))
        if tipo:
            clean_params.append(('tipo', tipo))
        if prioridad:
            clean_params.append(('prioridad', prioridad))
        if modalidad:
            clean_params.append(('modalidad', modalidad))
        if ciudad:
            clean_params.append(('ciudad', ciudad))
        if page_obj.number > 1:
            clean_params.append(('page', str(page_obj.number)))
        base_url = reverse('listar_proyectos')
        clean_url = f"{base_url}?{urlencode(clean_params)}" if clean_params else base_url
        response = render(request, 'proyectos/partials/_catalogo_resultados.html', context)
        response['HX-Replace-Url'] = clean_url
        return response

    context['categorias_solucion'] = CategoriaSolucion.objects.filter(activo=True)
    return render(request, 'proyectos/listar.html', context)

@login_required
def crear_proyecto(request):
    wants_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in (request.headers.get('Accept') or '')
        or request.GET.get('format') == 'json'
    )
    es_htmx = request.headers.get('HX-Request') == 'true' and not wants_json
    es_ajax = wants_json

    def responder_error(msg):
        if es_ajax:
            return JsonResponse({'ok': False, 'mensaje': msg}, status=400)
        if es_htmx:
            response = HttpResponse(status=200)
            response['HX-Trigger'] = json.dumps({
                'jobdevs:toast': {'tipo': 'error', 'mensaje': msg},
            })
            return response
        messages.error(request, msg)
        return redirect(reverse('dashboard_empresa') + '#ofertas')

    if request.user.rol != 'empresa':
        return responder_error("Solo las empresas pueden publicar proyectos.")

    categorias_solucion = CategoriaSolucion.objects.filter(activo=True)

    if request.method == 'POST':
        try:
            try:
                vacantes = int(request.POST.get('vacantes', 1))
            except (ValueError, TypeError):
                vacantes = 0

            if vacantes < 1:
                return responder_error("Las vacantes deben ser un número mayor o igual a 1.")

            tipo_solucion = request.POST.get('tipo_solucion')
            categoria = categorias_solucion.filter(slug=tipo_solucion).first()
            if categoria is None and tipo_solucion not in dict(Proyecto.TIPO_SOLUCION):
                return responder_error("Error: el tipo de solución seleccionado no es válido.")

            # Hallazgo 9: Validar que fecha_limite no sea en el pasado
            fecha_limite = request.POST.get('fecha_limite') or None
            if fecha_limite:
                try:
                    fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%d').date()
                    if fecha_limite_dt < timezone.now().date():
                        return responder_error("La fecha límite no puede ser anterior a la fecha actual.")
                except ValueError:
                    return responder_error("Formato de fecha límite inválido.")

            fecha_cumplimiento = (request.POST.get('fecha_cumplimiento') or '').strip()
            if not fecha_cumplimiento:
                return responder_error("La fecha de cumplimiento es obligatoria.")
            try:
                fecha_cumplimiento_dt = datetime.strptime(fecha_cumplimiento, '%Y-%m-%d').date()
                if fecha_cumplimiento_dt < timezone.localdate():
                    return responder_error("La fecha de cumplimiento no puede estar en el pasado.")
            except ValueError:
                return responder_error("Formato de fecha de cumplimiento inválido.")

            prioridad = request.POST.get('prioridad', 'media')
            if prioridad not in dict(Proyecto.PRIORIDAD):
                prioridad = 'media'

            modalidad = request.POST.get('modalidad', 'remoto')
            if modalidad not in dict(Proyecto.MODALIDAD):
                modalidad = 'remoto'
            ciudad = (request.POST.get('ciudad') or '').strip()
            if modalidad == 'remoto':
                ciudad = ''

            proyecto = Proyecto(
                empresa=request.user,
                titulo=request.POST.get('titulo'),
                descripcion=request.POST.get('descripcion'),
                categoria=categoria,
                tipo_solucion=categoria.slug if categoria else tipo_solucion,
                prioridad=prioridad,
                modalidad=modalidad,
                ciudad=ciudad,
                vacantes=vacantes,
                fecha_limite=fecha_limite,
                fecha_cumplimiento=fecha_cumplimiento,
                estado='publicado'
            )
            # Hallazgo 18: full_clean() para capturar validaciones de modelo de forma limpia.
            # tipo_solucion se excluye porque admite slugs dinamicos de CategoriaSolucion
            # (ya validado contra TIPO_SOLUCION por la vista cuando no hay categoria).
            proyecto.full_clean(exclude=['tipo_solucion'])
            proyecto.save()
            proyecto.registrar_cambio_estado('publicado', request.user, estado_anterior=None)

            msg_exito = f"¡Proyecto '{proyecto.titulo}' publicado exitosamente!"
            if es_ajax:
                return JsonResponse({
                    'ok': True,
                    'mensaje': msg_exito,
                    'proyecto_id': proyecto.id,
                    'redirect_url': reverse('dashboard_empresa') + '#ofertas',
                })
            if es_htmx:
                response = HttpResponse(status=204)
                response['HX-Trigger'] = json.dumps({
                    'jobdevs:toast': {'tipo': 'success', 'mensaje': msg_exito},
                    'jobdevs:proyecto-creado': {
                        'proyecto_id': proyecto.id,
                        'reload_hash': 'ofertas',
                    },
                })
                return response

            messages.success(request, msg_exito)
            return redirect(reverse('dashboard_empresa') + '#ofertas')
        except ValidationError as ve:
            return responder_error(f"Error de validación: {', '.join(ve.messages)}")
        except Exception as e:
            return responder_error(f"Error: {e}")

    return redirect(reverse('dashboard_empresa') + '#ofertas')

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
            if es_htmx else 'proyectos/finalizar.html'
        )
        return render(request, template, {
            'proyecto': proyecto,
            'desarrollador': None,
            'restantes': 0,
            'action_url': action_url,
        })

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

        msg = (
            f"Calificación registrada para {desarrollador.username}. "
            + (f"Quedan {restantes} por calificar." if restantes > 0 else "Era el último colaborador.")
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
        if es_htmx else 'proyectos/finalizar.html'
    )
    return render(request, template, {
        'proyecto': proyecto,
        'desarrollador': desarrollador,
        'restantes': restantes,
        'action_url': action_url,
    })


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
    es_obligatorio = (
        request.GET.get('obligatorio') in ('1', 'true')
        or request.POST.get('obligatorio') in ('1', 'true')
    )
    partial_tpl = 'proyectos/partials/_modal_calificar_empresa.html'

    if request.user.rol != 'desarrollador':
        if es_ajax:
            return JsonResponse(
                {'ok': False, 'error': 'Acceso denegado.', 'mensaje': 'Acceso denegado.'},
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
                return JsonResponse({'ok': False, 'error': msg, 'mensaje': msg}, status=404)
            return render(request, partial_tpl, {'solo_mensaje': True, 'error': msg}, status=404)
        contratacion = Contratacion.objects.filter(proyecto=proyecto, desarrollador=request.user).first()
        if not contratacion:
            msg = 'No tienes una contratación asociada a este proyecto.'
            if es_ajax:
                return JsonResponse({'ok': False, 'error': msg, 'mensaje': msg}, status=404)
            return render(request, partial_tpl, {'solo_mensaje': True, 'error': msg}, status=404)
    else:
        proyecto = get_object_or_404(Proyecto, id=proyecto_id, estado='finalizado')
        contratacion = get_object_or_404(Contratacion, proyecto=proyecto, desarrollador=request.user)

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
                        return render(request, partial_tpl, _htmx_ctx(ya_califico=True), status=200)
                    messages.error(request, msg)
                    return redirect('dashboard_desarrollador')

                Valoracion.objects.create(
                    proyecto=proyecto,
                    empresa=proyecto.empresa,
                    desarrollador=request.user,
                    puntuacion=puntuacion,
                    comentario=comentario,
                    rol_evaluador='desarrollador'
                )

                # RF 5.3.1: reflejar la nueva valoración en la reputación pública.
                services.recalcular_reputacion_empresa(proyecto.empresa_id)
        except IntegrityError:
            # Dos POST simultáneos: la unicidad del modelo gana la carrera.
            msg = "Ya has calificado a esta empresa para este proyecto."
            if es_ajax:
                return JsonResponse({'ok': False, 'mensaje': msg}, status=409)
            if es_htmx:
                return render(request, partial_tpl, _htmx_ctx(ya_califico=True), status=200)
            messages.error(request, msg)
            return redirect('dashboard_desarrollador')

        ok_msg = "¡Gracias! Tu calificación ha sido registrada."
        if es_ajax:
            return JsonResponse({'ok': True, 'mensaje': ok_msg, 'puntuacion': puntuacion})
        if es_htmx:
            response = render(
                request,
                partial_tpl,
                _htmx_ctx(calificacion_guardada=True, puntuacion=puntuacion, puntuacion_num=puntuacion),
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

def _contexto_equipos_panel(proyecto):
    desarrolladores = Contratacion.objects.desarrolladores_activos(proyecto)
    equipos = proyecto.equipos.all().prefetch_related('miembros')
    return {
        'proyecto': proyecto,
        'desarrolladores': desarrolladores,
        'equipos': equipos,
    }


def _render_equipos_panel_htmx(request, proyecto, mensaje, tipo='success'):
    response = render(request, 'proyectos/partials/_equipos_panel.html', _contexto_equipos_panel(proyecto))
    response['HX-Trigger'] = json.dumps({
        'jobdevs:toast': {'tipo': tipo, 'mensaje': mensaje},
    })
    return response


def _contexto_hitos_panel(proyecto):
    hitos = Entregable.objects.filter(proyecto=proyecto).select_related('desarrollador', 'equipo').order_by('fecha_creacion')
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
    response = render(request, 'proyectos/partials/_hitos_panel.html', _contexto_hitos_panel(proyecto))
    response['HX-Trigger'] = json.dumps({
        'jobdevs:toast': {'tipo': tipo, 'mensaje': mensaje},
    })
    return response


@login_required
def gestionar_equipos(request, proyecto_id):
    if request.user.rol != 'empresa': return redirect('inicio')
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
                    return _render_equipos_panel_htmx(request, proyecto, msg, tipo='error')
                messages.error(request, msg)
                return redirect('gestionar_equipos', proyecto_id=proyecto.id)

            # Hallazgo 8: Validar que todos los miembros pertenezcan a los desarrolladores activos contratados
            dev_ids_activos = set(str(uid) for uid in desarrolladores.values_list('id', flat=True))
            if not all(str(m) in dev_ids_activos for m in miembros_ids):
                msg = "Error: Solo puedes asignar desarrolladores contratados y activos en este proyecto."
                if es_htmx:
                    return _render_equipos_panel_htmx(request, proyecto, msg, tipo='error')
                messages.error(request, msg)
                return redirect('gestionar_equipos', proyecto_id=proyecto.id)

            equipo = Equipo.objects.create(nombre=nombre, proyecto=proyecto)
            equipo.miembros.set(miembros_ids)

            # Notificación: Avisar a cada miembro usando equipo.nombre consistente
            for miembro_id in miembros_ids:
                Notificacion.objects.create(
                    usuario_id=miembro_id,
                    tipo='mensaje',
                    mensaje=f"Has sido asignado al equipo '{equipo.nombre}' en el proyecto: {proyecto.titulo}"
                )

            msg = f"Equipo '{equipo.nombre}' creado y miembros notificados."
            if es_htmx:
                return _render_equipos_panel_htmx(request, proyecto, msg, tipo='success')
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

    return render(request, 'proyectos/gestionar_equipos.html', {
        'proyecto': proyecto,
        'desarrolladores': desarrolladores,
        'equipos': equipos
    })

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
                        return _render_hitos_panel_htmx(request, proyecto, msg, tipo='error')
                    messages.error(request, msg)
                    return redirect('gestionar_hitos', proyecto_id=proyecto.id)

            # SCRUM-309 (HU-E13): el desarrollador asignado debe tener contratación activa
            desarrollador = None
            if desarrollador_id:
                contratacion = Contratacion.objects.filter(
                    proyecto=proyecto,
                    desarrollador_id=desarrollador_id,
                    estado='activa',
                ).select_related('desarrollador').first()
                if not contratacion:
                    msg = "Error: El desarrollador seleccionado no tiene una contratación activa en este proyecto."
                    if es_htmx:
                        return _render_hitos_panel_htmx(request, proyecto, msg, tipo='error')
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
                    mensaje=f"Nueva tarea asignada de forma individual en '{proyecto.titulo}': {titulo}"
                )
            elif equipo:
                # Avisar solo a los miembros del equipo
                for miembro in equipo.miembros.all():
                    Notificacion.objects.create(
                        usuario=miembro,
                        tipo='avance',
                        mensaje=f"Nueva tarea asignada a tu equipo '{equipo.nombre}': {titulo}"
                    )
            else:
                # Avisar a todos los contratados en el proyecto (Hito General)
                # Hallazgo 19: Usar helper del manager Contratacion
                desarrolladores = Contratacion.objects.desarrolladores_activos(proyecto)
                for dev in desarrolladores:
                    Notificacion.objects.create(
                        usuario=dev,
                        tipo='avance',
                        mensaje=f"Nueva tarea general en '{proyecto.titulo}': {titulo}"
                    )

            msg = f"Hito '{titulo}' creado y desarrolladores notificados."
            if es_htmx:
                return _render_hitos_panel_htmx(request, proyecto, msg, tipo='success')
            messages.success(request, msg)
            next_url = request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return HttpResponseRedirect(next_url)
            return redirect('gestionar_hitos', proyecto_id=proyecto.id)
        elif es_htmx:
            return _render_hitos_panel_htmx(
                request, proyecto, "El nombre del hito es obligatorio.", tipo='error'
            )

    equipos = proyecto.equipos.all()
    tiene_multiples_contratos = Contratacion.objects.filter(proyecto=proyecto, estado='activa').count() >= 2
    # SCRUM-309 (HU-E13): candidatos válidos para asignación individual de hitos
    desarrolladores_activos = Contratacion.objects.filter(
        proyecto=proyecto, estado='activa'
    ).select_related('desarrollador')

    # Sub-tab "Línea de Tiempo de Avances" sin recargar la página
    avances = Avance.objects.filter(proyecto=proyecto).select_related(
        'desarrollador__perfil_desarrollador', 'entregable'
    ).order_by('-fecha_hora')
    progreso = hitos.aggregate(
        hitos_completados=Count('id', filter=Q(estado='completado')),
        hitos_totales=Count('id'),
    )

    return render(request, 'proyectos/gestionar_hitos.html', {
        'proyecto': proyecto, 
        'hitos': hitos,
        'avances': avances,
        'hitos_completados': progreso['hitos_completados'] or 0,
        'hitos_totales': progreso['hitos_totales'] or 0,
        'equipos': equipos,
        'tiene_multiples_contratos': tiene_multiples_contratos,
        'desarrolladores_activos': desarrolladores_activos,
    })

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

def _render_ofertas_htmx(request, *, toast=None):
    """Renderiza el partial _tab_ofertas.html actualizado para respuestas HTMX."""
    hoy = timezone.localdate()
    limite_48h = hoy + timedelta(days=2)
    mis_ofertas = list(
        Proyecto.objects.filter(empresa=request.user, estado='publicado')
        .select_related('categoria')
        .annotate(
            num_candidatos=Count(
                'postulaciones',
                filter=Q(postulaciones__estado__in=['pendiente', 'en_negociacion']),
                distinct=True,
            ),
            num_pendientes=Count(
                'postulaciones',
                filter=Q(postulaciones__estado='pendiente'),
                distinct=True,
            ),
            num_contratos=Count('contrataciones', distinct=True),
            num_contratos_cancelados=Count(
                'contrataciones',
                filter=Q(contrataciones__estado='cancelada'),
                distinct=True,
            ),
            num_contratos_activos=Count(
                'contrataciones',
                filter=Q(contrataciones__estado='activa'),
                distinct=True,
            ),
            num_negociaciones=Count(
                'postulaciones',
                filter=Q(postulaciones__estado='en_negociacion'),
                distinct=True,
            ),
        )
        .order_by('-fecha_publicacion')
    )
    for proyecto in mis_ofertas:
        proyecto.cierra_pronto = bool(
            proyecto.fecha_limite and hoy <= proyecto.fecha_limite <= limite_48h
        )
        proyecto.puede_reabrir = bool(
            proyecto.fecha_limite
            and proyecto.fecha_limite < hoy
            and proyecto.num_contratos_cancelados
            and proyecto.vacantes > proyecto.num_contratos_activos + proyecto.num_negociaciones
        )

    total_vacantes_ofertas = sum(p.vacantes for p in mis_ofertas)
    total_postulaciones = Postulacion.objects.filter(
        proyecto__empresa=request.user,
        estado='pendiente',
        proyecto__estado__in=['publicado', 'en_desarrollo'],
    ).count()

    response = render(
        request,
        'empresa/partials/_tab_ofertas.html',
        {
            'mis_ofertas': mis_ofertas,
            'total_vacantes_ofertas': total_vacantes_ofertas,
            'total_postulaciones': total_postulaciones,
            'fecha_minima_reapertura': (hoy + timedelta(days=1)).isoformat(),
            'htmx_ofertas_activa': True,
        },
    )
    if toast:
        tipo, mensaje = toast
        response['HX-Trigger'] = json.dumps({
            'jobdevs:toast': {'tipo': tipo, 'mensaje': mensaje},
        })
    return response


@login_required
@require_POST
def reabrir_postulaciones(request, proyecto_id):
    """Amplía explícitamente solo el plazo de postulación tras una cancelación."""
    if request.user.rol != 'empresa':
        raise PermissionDenied

    error_msg = None
    with transaction.atomic():
        proyecto = get_object_or_404(
            Proyecto.objects.select_for_update(), id=proyecto_id, empresa=request.user,
        )
        hoy = timezone.localdate()
        if not (
            proyecto.estado == 'publicado'
            and proyecto.fecha_limite is not None
            and proyecto.fecha_limite < hoy
            and Contratacion.objects.filter(proyecto=proyecto, estado='cancelada').exists()
            and proyecto.vacantes_disponibles > 0
        ):
            error_msg = "Este proyecto no admite reabrir postulaciones."
        else:
            try:
                nueva_fecha = datetime.strptime(request.POST.get('fecha_limite', ''), '%Y-%m-%d').date()
            except (TypeError, ValueError):
                error_msg = "Indica una fecha válida de cierre de postulaciones."
                nueva_fecha = None

            if error_msg is None and nueva_fecha <= hoy:
                error_msg = "El nuevo cierre debe ser posterior a hoy."

            if error_msg is None:
                anterior = proyecto.fecha_limite
                proyecto.fecha_limite = nueva_fecha
                proyecto.save(update_fields=['fecha_limite'])
                LogAuditoria.objects.create(
                    usuario=request.user, tabla_afectada='proyectos', registro_id=proyecto.pk,
                    accion=f"Amplió cierre de postulaciones de {proyecto.titulo}"[:300],
                    valor_anterior=anterior.isoformat(), valor_nuevo=nueva_fecha.isoformat(),
                )

    if error_msg:
        if _es_htmx(request):
            return _render_ofertas_htmx(request, toast=('error', error_msg))
        messages.error(request, error_msg)
        return redirect('dashboard_empresa')

    msg_ok = "Convocatoria reabierta con el nuevo plazo de postulación."
    if _es_htmx(request):
        return _render_ofertas_htmx(request, toast=('success', msg_ok))
    messages.success(request, msg_ok)
    return redirect(f"{reverse('dashboard_empresa')}#ofertas")


@login_required
@require_http_methods(["GET", "POST"])
def editar_proyecto(request, proyecto_id):
    if request.user.rol != 'empresa':
        messages.error(request, "Solo las empresas pueden editar proyectos.")
        return redirect('dashboard_empresa')

    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)

    if proyecto.estado not in ('publicado', 'en_desarrollo', 'en_revision'):
        messages.error(request, "No puedes editar un proyecto retirado, finalizado o en disputa.")
        return redirect('dashboard_empresa')

    if Contratacion.objects.filter(proyecto=proyecto, estado='activa').exists():
        messages.error(request, "No puedes modificar un proyecto con contratos activos. Finalízalo o retíralo primero.")
        return redirect('gestionar_hitos', proyecto_id=proyecto.id)

    permite_edicion_tecnica = (
        proyecto.estado == 'publicado'
        and not Contratacion.objects.filter(proyecto=proyecto).exists()
        and not proyecto.postulaciones.filter(estado='en_negociacion').exists()
    )
    if request.method == 'POST' and not permite_edicion_tecnica:
        titulo = (request.POST.get('titulo') or '').strip()
        prioridad = request.POST.get('prioridad')
        if not titulo or len(titulo) > 200 or prioridad not in dict(Proyecto.PRIORIDAD):
            messages.error(request, "Título o prioridad inválidos.")
            return redirect('editar_proyecto', proyecto_id=proyecto.id)
        proyecto.titulo = titulo
        proyecto.prioridad = prioridad
        proyecto.save(update_fields=['titulo', 'prioridad'])
        messages.success(request, "Datos básicos del proyecto actualizados.")
        if _espera_json(request):
            return JsonResponse({'status': 'ok', 'message': 'Datos básicos del proyecto actualizados.'})
        return redirect(f"{reverse('dashboard_empresa')}#desarrollo")

    categorias_solucion = CategoriaSolucion.objects.filter(activo=True)
    if proyecto.categoria_id:
        # Conserva visible la categoría actual aunque haya sido desactivada.
        categorias_solucion = CategoriaSolucion.objects.filter(
            Q(activo=True) | Q(pk=proyecto.categoria_id)
        )

    if request.method == 'POST':
        try:
            vacantes = int(request.POST.get('vacantes', 1))
        except (ValueError, TypeError):
            vacantes = 0

        if vacantes < 1:
            messages.error(request, "Las vacantes deben ser un número mayor o igual a 1.")
            return redirect('editar_proyecto', proyecto_id=proyecto.id)

        contratos_activos = Contratacion.objects.filter(proyecto=proyecto, estado='activa').count()
        negociaciones_activas = proyecto.postulaciones.filter(estado='en_negociacion').count()
        comprometidas = contratos_activos + negociaciones_activas
        if vacantes < comprometidas:
            messages.error(
                request,
                f"No puedes reducir las vacantes a {vacantes} porque ya hay {comprometidas} "
                f"vacante(s) comprometida(s) ({contratos_activos} contratos activos y {negociaciones_activas} en negociación)."
            )
            return redirect('editar_proyecto', proyecto_id=proyecto.id)

        # Hallazgo 9: Validar que fecha_limite no sea en el pasado
        fecha_limite = request.POST.get('fecha_limite') or None
        if fecha_limite:
            try:
                fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%d').date()
                if fecha_limite_dt < timezone.now().date():
                    messages.error(request, "La fecha límite no puede ser anterior a la fecha actual.")
                    return redirect('editar_proyecto', proyecto_id=proyecto.id)
            except ValueError:
                messages.error(request, "Formato de fecha límite inválido.")
                return redirect('editar_proyecto', proyecto_id=proyecto.id)

        fecha_cumplimiento = (
            request.POST.get('fecha_cumplimiento') or None
            if 'fecha_cumplimiento' in request.POST else proyecto.fecha_cumplimiento
        )
        if 'fecha_cumplimiento' in request.POST and fecha_cumplimiento:
            try:
                fecha_cumplimiento_dt = datetime.strptime(fecha_cumplimiento, '%Y-%m-%d').date()
                if fecha_cumplimiento_dt < timezone.localdate():
                    messages.error(request, "La fecha de cumplimiento no puede estar en el pasado.")
                    return redirect('editar_proyecto', proyecto_id=proyecto.id)
            except ValueError:
                messages.error(request, "Formato de fecha de cumplimiento inválido.")
                return redirect('editar_proyecto', proyecto_id=proyecto.id)

        try:
            proyecto.titulo = request.POST.get('titulo')
            proyecto.descripcion = request.POST.get('descripcion')
            tipo_solucion = request.POST.get('tipo_solucion')
            categoria = categorias_solucion.filter(slug=tipo_solucion).first()
            if categoria is None and tipo_solucion not in dict(Proyecto.TIPO_SOLUCION):
                messages.error(request, "Error: el tipo de solución seleccionado no es válido.")
                return redirect('editar_proyecto', proyecto_id=proyecto.id)
            proyecto.categoria = categoria
            proyecto.tipo_solucion = categoria.slug if categoria else tipo_solucion
            proyecto.prioridad = request.POST.get('prioridad', 'media')
            modalidad = request.POST.get('modalidad', 'remoto')
            if modalidad not in dict(Proyecto.MODALIDAD):
                modalidad = 'remoto'
            ciudad = (request.POST.get('ciudad') or '').strip()
            if modalidad == 'remoto':
                ciudad = ''
            proyecto.modalidad = modalidad
            proyecto.ciudad = ciudad
            proyecto.vacantes = vacantes
            proyecto.fecha_limite = fecha_limite
            proyecto.fecha_cumplimiento = fecha_cumplimiento
            # Hallazgo 18: full_clean() para capturar validaciones de modelo de forma limpia.
            # tipo_solucion se excluye porque admite slugs dinamicos de CategoriaSolucion
            # (ya validado contra TIPO_SOLUCION por la vista cuando no hay categoria).
            proyecto.full_clean(exclude=['tipo_solucion'])
            proyecto.save()

            messages.success(request, f"Proyecto '{proyecto.titulo}' actualizado exitosamente.")
            if _espera_json(request):
                return JsonResponse({'status': 'ok', 'message': f"Proyecto '{proyecto.titulo}' actualizado exitosamente."})
            return redirect(f"{reverse('dashboard_empresa')}#ofertas")
        except ValidationError as ve:
            msg = f"Error de validación: {', '.join(ve.messages)}"
            messages.error(request, msg)
            if _espera_json(request):
                return JsonResponse({'status': 'error', 'message': msg}, status=400)
            return redirect('editar_proyecto', proyecto_id=proyecto.id)
        except Exception as e:
            msg = f"Error: {e}"
            messages.error(request, msg)
            if _espera_json(request):
                return JsonResponse({'status': 'error', 'message': msg}, status=500)
            return redirect('editar_proyecto', proyecto_id=proyecto.id)

    return render(request, 'proyectos/editar_proyecto.html', {
        'proyecto': proyecto,
        'categorias_solucion': categorias_solucion,
        'permite_edicion_tecnica': permite_edicion_tecnica,
    })

@login_required
@require_POST
def desactivar_proyecto(request, proyecto_id):
    if request.user.rol != 'empresa':
        return redirect('inicio')
    
    with transaction.atomic():
        proyecto = get_object_or_404(
            Proyecto.objects.select_for_update(), id=proyecto_id, empresa=request.user
        )

        # El retiro de una oferta no termina contratos: eso requiere el flujo contractual.
        if proyecto.estado == 'publicado' and not Contratacion.objects.filter(proyecto=proyecto).exists():
            estado_anterior = proyecto.estado
            proyecto.estado = 'inactivo'
            proyecto.save()
            
            # 1. Registrar Historial
            proyecto.registrar_cambio_estado('inactivo', request.user, estado_anterior=estado_anterior)
            
            # 2. Gestionar Postulaciones y Notificaciones en bloque
            # Hallazgo 6: Filtrar solo postulaciones pendientes o en negociación
            postulaciones = Postulacion.objects.filter(
                proyecto=proyecto,
                estado__in=['pendiente', 'en_negociacion']
            ).select_related('desarrollador')
            
            if postulaciones.exists():
                # Notificaciones masivas para postulantes
                notificaciones_lista = [
                    Notificacion(
                        usuario=pos.desarrollador,
                        tipo='alerta',
                        mensaje=f"El proyecto '{proyecto.titulo}' ha sido retirado por la empresa. Tu postulación ya no está vigente."
                    ) for pos in postulaciones
                ]
                
                # Actualización masiva de estados
                postulaciones.update(estado='rechazada')
                # Creación masiva de notificaciones
                Notificacion.objects.bulk_create(notificaciones_lista)

            msg = f"El proyecto '{proyecto.titulo}' ha sido retirado y los desarrolladores han sido notificados."
            toast_tipo = 'info'
        else:
            msg = "Solo puedes retirar una oferta publicada sin contratos. Los proyectos en ejecución requieren el flujo de terminación o resolución contractual."
            toast_tipo = 'error'

    if _es_htmx(request):
        return _render_ofertas_htmx(request, toast=(toast_tipo, msg))
    getattr(messages, toast_tipo)(request, msg)
    return redirect('dashboard_empresa')


# ---------------------------------------------------------------------------
# API administrativa: categorías de solución
# ---------------------------------------------------------------------------

def _categoria_to_dict(categoria, proyectos_count=None):
    if proyectos_count is None:
        proyectos_count = categoria.proyectos.count()
    return {
        'id': categoria.id,
        'nombre': categoria.nombre,
        'slug': categoria.slug,
        'descripcion': categoria.descripcion,
        'activo': categoria.activo,
        'proyectos_count': proyectos_count,
    }


def _parse_json_body(request):
    """Devuelve (dict, None) o (None, JsonResponse) si el cuerpo no es un objeto JSON válido."""
    try:
        data = json.loads(request.body or b'')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({'error': 'Formato JSON inválido.'}, status=400)
    if not isinstance(data, dict):
        return None, JsonResponse({'error': 'Formato JSON inválido.'}, status=400)
    return data, None


def _log_categoria(request, categoria, accion):
    LogAuditoria.objects.create(
        usuario=request.user,
        accion=accion,
        tabla_afectada='categorias_solucion',
        registro_id=categoria.id,
    )


@login_required
@api_ratelimit(max_requests=60, window_seconds=60)
def api_categorias_listar(request):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido. Use GET.'}, status=405)

    categorias = CategoriaSolucion.objects.annotate(
        proyectos_count=Count('proyectos')
    ).order_by('nombre')
    return JsonResponse(
        [_categoria_to_dict(c, c.proyectos_count) for c in categorias],
        safe=False,
    )


@login_required
@api_ratelimit(max_requests=30, window_seconds=60)
def api_categoria_crear(request):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido. Use POST.'}, status=405)

    data, error = _parse_json_body(request)
    if error:
        return error

    nombre = str(data.get('nombre') or '').strip()
    if not nombre:
        return JsonResponse({'error': 'El campo nombre es requerido.'}, status=400)
    if len(nombre) > 100:
        return JsonResponse({'error': 'El nombre no puede superar 100 caracteres.'}, status=400)

    slug = slugify(str(data.get('slug') or '').strip() or nombre)[:50]
    if not slug:
        return JsonResponse({'error': 'No se pudo generar un slug válido.'}, status=400)

    descripcion = str(data.get('descripcion') or '').strip()
    activo = data.get('activo', True)
    if not isinstance(activo, bool):
        return JsonResponse({'error': 'El campo activo debe ser booleano.'}, status=400)

    if CategoriaSolucion.objects.filter(nombre__iexact=nombre).exists():
        return JsonResponse({'error': 'Ya existe una categoría con ese nombre.'}, status=409)
    if CategoriaSolucion.objects.filter(slug=slug).exists():
        return JsonResponse({'error': 'Ya existe una categoría con ese slug.'}, status=409)

    try:
        with transaction.atomic():
            categoria = CategoriaSolucion.objects.create(
                nombre=nombre, slug=slug, descripcion=descripcion, activo=activo,
            )
            _log_categoria(request, categoria, f"Creó categoría de solución {categoria.nombre} ({categoria.slug})")
    except IntegrityError:
        return JsonResponse({'error': 'Ya existe una categoría con ese nombre o slug.'}, status=409)

    return JsonResponse(_categoria_to_dict(categoria, 0), status=201)


@login_required
@api_ratelimit(max_requests=30, window_seconds=60)
def api_categoria_actualizar(request, categoria_id):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)
    if request.method not in ('PUT', 'POST'):
        return JsonResponse({'error': 'Método no permitido. Use PUT o POST.'}, status=405)

    categoria = get_object_or_404(CategoriaSolucion, id=categoria_id)
    data, error = _parse_json_body(request)
    if error:
        return error

    campos = []
    if 'nombre' in data:
        nombre = str(data.get('nombre') or '').strip()
        if not nombre:
            return JsonResponse({'error': 'El campo nombre es requerido.'}, status=400)
        if len(nombre) > 100:
            return JsonResponse({'error': 'El nombre no puede superar 100 caracteres.'}, status=400)
        if CategoriaSolucion.objects.filter(nombre__iexact=nombre).exclude(pk=categoria.pk).exists():
            return JsonResponse({'error': 'Ya existe una categoría con ese nombre.'}, status=409)
        categoria.nombre = nombre
        campos.append('nombre')
    if 'descripcion' in data:
        categoria.descripcion = str(data.get('descripcion') or '').strip()
        campos.append('descripcion')
    if 'activo' in data:
        if not isinstance(data['activo'], bool):
            return JsonResponse({'error': 'El campo activo debe ser booleano.'}, status=400)
        categoria.activo = data['activo']
        campos.append('activo')

    try:
        with transaction.atomic():
            categoria.save()
            _log_categoria(
                request, categoria,
                f"Actualizó categoría de solución {categoria.slug}: {', '.join(campos) or 'sin cambios'}",
            )
    except IntegrityError:
        return JsonResponse({'error': 'Ya existe una categoría con ese nombre.'}, status=409)

    return JsonResponse(_categoria_to_dict(categoria), status=200)


@login_required
@api_ratelimit(max_requests=30, window_seconds=60)
def api_categoria_toggle(request, categoria_id):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido. Use POST.'}, status=405)

    categoria = get_object_or_404(CategoriaSolucion, id=categoria_id)
    with transaction.atomic():
        categoria.activo = not categoria.activo
        categoria.save(update_fields=['activo'])
        _log_categoria(
            request, categoria,
            f"{'Activó' if categoria.activo else 'Desactivó'} categoría de solución {categoria.slug}",
        )
    return JsonResponse(_categoria_to_dict(categoria), status=200)


# ─────────────────────────────────────────────────────────────────────────────
# Detalle de proyecto en modal (dashboards de admin, empresa y desarrollador)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def api_detalle_proyecto(request, proyecto_id):
    """Ficha completa de un proyecto para el modal compartido de los dashboards.

    Mantiene los mismos permisos que ``avances.views.ver_avances``: admin,
    empresa dueña y desarrollador vinculado por contrato o postulación. El
    frontend solo pinta la respuesta; las acciones se resuelven aquí para no
    duplicar reglas de negocio en JavaScript.
    """
    from django.urls import reverse
    from django.utils.formats import date_format

    proyecto = get_object_or_404(
        Proyecto.objects.select_related('empresa__perfil_empresa', 'categoria'),
        id=proyecto_id,
    )
    user = request.user
    es_admin = user.rol == 'administrador'
    es_empresa = user.rol == 'empresa' and proyecto.empresa_id == user.id
    esta_contratado = Contratacion.objects.filter(proyecto=proyecto, desarrollador=user).exists()
    tiene_postulacion = Postulacion.objects.filter(proyecto=proyecto, desarrollador=user).exists()
    es_publicado = proyecto.estado == 'publicado'

    wants_htmx = (
        request.headers.get('HX-Request') == 'true'
        and 'application/json' not in request.headers.get('Accept', '')
        and request.GET.get('format') != 'json'
    )

    es_dev = user.rol == 'desarrollador' and (esta_contratado or tiene_postulacion or es_publicado)
    if not (es_admin or es_empresa or es_dev):
        if wants_htmx:
            return render(
                request,
                'proyectos/partials/_modal_detalle_proyecto.html',
                {'error_mensaje': 'No tienes permisos para ver este proyecto.'},
                status=403,
            )
        return JsonResponse(
            {'ok': False, 'mensaje': 'No tienes permisos para ver este proyecto.'},
            status=403,
        )

    hitos_qs = proyecto.entregables.order_by('fecha_creacion')
    hitos = [
        {
            'id': h.id,
            'titulo': h.titulo,
            'descripcion': h.descripcion or '',
            'estado': h.estado,
            'estado_label': h.get_estado_display(),
        }
        for h in hitos_qs
    ]
    total_hitos = len(hitos)
    completados = sum(1 for h in hitos if h['estado'] == 'completado')
    progreso = round((completados / total_hitos) * 100) if total_hitos else 0

    contrataciones_qs = proyecto.contrataciones.select_related('desarrollador').order_by('fecha_inicio')
    if es_admin or es_empresa or esta_contratado:
        contrataciones = [
            {
                'id': c.id,
                'desarrollador': c.desarrollador.nombre or c.desarrollador.username,
                'username': c.desarrollador.username,
                'estado': c.estado,
                'estado_label': c.get_estado_display(),
            }
            for c in contrataciones_qs
        ]
    else:
        contrataciones = []
    num_desarrolladores = contrataciones_qs.count()

    perfil_empresa = getattr(proyecto.empresa, 'perfil_empresa', None)
    badge = perfil_empresa.badge_info if perfil_empresa else None
    empresa_nombre = (
        (perfil_empresa.nombre_empresa if perfil_empresa else '')
        or proyecto.empresa.nombre
        or proyecto.empresa.username
    )

    acciones = []
    if es_admin:
        acciones.append({
            'label': 'Gestionar avances', 'url': reverse('ver_avances', args=[proyecto.id]),
            'icono': 'git-branch', 'estilo': 'primary',
        })
        acciones.append({
            'label': 'Gestionar hitos', 'url': reverse('gestionar_hitos', args=[proyecto.id]),
            'icono': 'list-checks', 'estilo': 'secondary',
        })
        acciones.append({
            'label': 'Ver empresa', 'url': reverse('detalle_empresa', args=[proyecto.empresa_id]),
            'icono': 'building', 'estilo': 'secondary',
        })
    elif es_empresa:
        acciones.append({
            'label': 'Ver avances', 'url': reverse('ver_avances', args=[proyecto.id]),
            'icono': 'git-branch', 'estilo': 'primary',
        })
        acciones.append({
            'label': 'Gestionar hitos', 'url': reverse('gestionar_hitos', args=[proyecto.id]),
            'icono': 'list-checks', 'estilo': 'secondary',
        })
        if proyecto.vacantes_disponibles > 0 and proyecto.acepta_postulaciones:
            acciones.append({
                'label': 'Ver candidatos',
                'url': reverse('ver_postulaciones_empresa', args=[proyecto.id]),
                'icono': 'user-plus', 'estilo': 'secondary',
            })
    else:
        # Desarrollador
        if esta_contratado:
            acciones.append({
                'label': 'Ver historial completo', 'url': reverse('ver_avances', args=[proyecto.id]),
                'icono': 'git-branch', 'estilo': 'primary',
            })
            if proyecto.estado == 'en_desarrollo':
                acciones.append({
                    'label': 'Registrar avance', 'url': reverse('registrar_avance', args=[proyecto.id]),
                    'icono': 'pen', 'estilo': 'secondary',
                })
        elif tiene_postulacion:
            acciones.append({
                'label': 'Ver mi postulación',
                'url': reverse('dashboard_desarrollador') + '#postulaciones',
                'icono': 'send',
                'estilo': 'secondary',
            })
        elif es_publicado and proyecto.acepta_postulaciones and proyecto.vacantes_disponibles > 0:
            acciones.append({
                'label': 'Postularme',
                'url': reverse('postularse_a_proyecto', args=[proyecto.id]),
                'icono': 'send',
                'estilo': 'primary',
            })

    if num_desarrolladores >= 2 and (es_admin or es_empresa or esta_contratado):
        acciones.append({
            'label': 'Chat grupal', 'url': reverse('sala_chat_grupal', args=[proyecto.id]),
            'icono': 'users', 'estilo': 'secondary',
        })

    payload = {
        'ok': True,
        'proyecto': {
            'id': proyecto.id,
            'titulo': proyecto.titulo,
            'descripcion': proyecto.descripcion,
            'estado': proyecto.estado,
            'estado_label': proyecto.get_estado_display(),
            'tipo': proyecto.get_tipo_solucion_display(),
            'prioridad': proyecto.prioridad,
            'prioridad_label': proyecto.get_prioridad_display(),
            'modalidad': proyecto.modalidad,
            'modalidad_label': proyecto.get_modalidad_display(),
            'ciudad': proyecto.ciudad or '',
            'ubicacion_display': proyecto.ubicacion_display,
            'vacantes': proyecto.vacantes,
            'vacantes_disponibles': proyecto.vacantes_disponibles,
            'fecha_publicacion': date_format(proyecto.fecha_publicacion, 'd M Y'),
            'fecha_limite': (
                date_format(proyecto.fecha_limite, 'd M Y')
                if proyecto.fecha_limite else 'Sin límite'
            ),
            'categoria': proyecto.categoria.nombre if proyecto.categoria_id else '',
            'empresa': {
                'id': proyecto.empresa_id,
                'nombre': empresa_nombre,
                'verificada': bool(perfil_empresa and perfil_empresa.es_verificada),
                'badge': badge['label'] if badge else '',
                'calificacion': float(perfil_empresa.calificacion_promedio or 0) if perfil_empresa else 0,
            },
            'hitos': hitos,
            'hitos_completados': completados,
            'hitos_totales': total_hitos,
            'progreso': progreso,
            'contrataciones': contrataciones,
            'num_desarrolladores': num_desarrolladores,
            'acepta_postulaciones': proyecto.acepta_postulaciones,
        },
        'acciones': acciones,
    }
    if wants_htmx:
        return render(request, 'proyectos/partials/_modal_detalle_proyecto.html', payload)
    return JsonResponse(payload)
