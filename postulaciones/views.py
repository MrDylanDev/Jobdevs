import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.utils.formats import date_format
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Postulacion
from . import services
from proyectos.models import Proyecto
from contrataciones.models import Contratacion, ContratoDigital
from notificaciones.models import Notificacion
from logs.models import LogAuditoria
from proyectos.models import Equipo
from usuarios.models import Usuario, PerfilDesarrollador

logger = logging.getLogger(__name__)


def _espera_json(request):
    """Detecta peticiones asíncronas modernas vía Fetch (Accept: application/json) o XHR."""
    return (
        'application/json' in request.headers.get('Accept', '')
        or request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.GET.get('format') == 'json'
    )


def _es_htmx(request):
    """Detecta peticiones HTMX que esperan HTML parcial (sin pedir JSON explícito)."""
    return (
        request.headers.get('HX-Request') == 'true'
        and not _espera_json(request)
    )


def _build_postulaciones_empresa_context(proyecto, estado_filtro='', programa='', ficha='', habilidad=''):
    proyecto_id = proyecto.id
    estado_filtro = (estado_filtro or '').strip()
    if estado_filtro in ['pendiente', 'en_negociacion', 'aceptada', 'rechazada']:
        estados_consulta = [estado_filtro]
    else:
        estados_consulta = ['pendiente', 'en_negociacion']
        estado_filtro = ''

    conteos_funnel = {
        'total': Postulacion.objects.filter(proyecto_id=proyecto_id).count(),
        'pendientes': Postulacion.objects.filter(proyecto_id=proyecto_id, estado='pendiente').count(),
        'en_negociacion': Postulacion.objects.filter(proyecto_id=proyecto_id, estado='en_negociacion').count(),
        'aceptadas': Postulacion.objects.filter(proyecto_id=proyecto_id, estado='aceptada').count(),
        'rechazadas': Postulacion.objects.filter(proyecto_id=proyecto_id, estado='rechazada').count(),
    }

    postulaciones_orm = Postulacion.objects.filter(
        proyecto_id=proyecto_id,
        estado__in=estados_consulta
    ).select_related(
        'desarrollador__perfil_desarrollador', 'contrato_digital'
    ).order_by('-fecha')

    programa = (programa or '').strip()
    ficha = (ficha or '').strip()
    habilidad = (habilidad or '').strip()

    if programa:
        postulaciones_orm = postulaciones_orm.filter(
            desarrollador__perfil_desarrollador__programa_formacion__icontains=programa
        )
    if ficha:
        postulaciones_orm = postulaciones_orm.filter(
            desarrollador__perfil_desarrollador__ficha__icontains=ficha
        )
    if habilidad:
        for term in (t.strip() for t in habilidad.split(',')):
            if term:
                postulaciones_orm = postulaciones_orm.filter(
                    desarrollador__perfil_desarrollador__habilidades__icontains=term
                )

    programas_disponibles = (
        Postulacion.objects.filter(
            proyecto_id=proyecto_id, estado__in=['pendiente', 'en_negociacion'])
        .exclude(desarrollador__perfil_desarrollador__programa_formacion__isnull=True)
        .exclude(desarrollador__perfil_desarrollador__programa_formacion='')
        .values_list('desarrollador__perfil_desarrollador__programa_formacion', flat=True)
        .distinct()
        .order_by('desarrollador__perfil_desarrollador__programa_formacion')
    )

    postulaciones = []
    for p in postulaciones_orm:
        perfil = getattr(p.desarrollador, 'perfil_desarrollador', None)
        contrato = getattr(p, 'contrato_digital', None)
        postulaciones.append({
            'id': p.id,
            'estado': p.estado,
            'fecha_limite_negociacion': p.fecha_limite_negociacion,
            'contrato_id': contrato.id if contrato else None,
            'desarrollador': {
                'id': p.desarrollador_id,
                'nombre': p.desarrollador.nombre,
                'foto_perfil': perfil.foto_perfil.url if perfil and perfil.foto_perfil else None,
                'programa_formacion': perfil.programa_formacion if perfil else '',
                'ficha': perfil.ficha if perfil else '',
                'es_verificado_sena': perfil.es_verificado_sena if perfil else False,
                'fecha_verificacion': perfil.fecha_verificacion if perfil else None,
                'badge_info': perfil.badge_info if perfil else None,
            },
            'calificacion_promedio': perfil.calificacion_promedio if perfil else 0,
            'proyectos_completados': perfil.num_proyectos_completados if perfil else 0,
            'habilidades': perfil.habilidades if perfil else '',
            'portafolio_url': perfil.portafolio_url if perfil else '',
            'mensaje': p.mensaje,
            'fecha': p.fecha,
        })

    return {
        'proyecto': proyecto,
        'postulaciones': postulaciones,
        'programas_disponibles': list(programas_disponibles),
        'filtros': {'programa': programa, 'ficha': ficha, 'habilidad': habilidad, 'estado': estado_filtro},
        'conteos_funnel': conteos_funnel,
    }


def _render_drawer_htmx(request, proyecto, estado_filtro='', toast_msg=None, toast_tipo='success', status=200):
    context = _build_postulaciones_empresa_context(proyecto, estado_filtro=estado_filtro)
    response = render(request, 'postulaciones/partials/_drawer_candidatos.html', context, status=status)
    if toast_msg:
        response['HX-Trigger'] = json.dumps({
            'jobdevs:toast': {'tipo': toast_tipo, 'mensaje': toast_msg}
        })
    return response


@login_required
def ver_postulaciones_empresa(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)
    context = _build_postulaciones_empresa_context(
        proyecto,
        estado_filtro=request.GET.get('estado', ''),
        programa=request.GET.get('programa', ''),
        ficha=request.GET.get('ficha', ''),
        habilidad=request.GET.get('habilidad', ''),
    )
    if _es_htmx(request):
        return render(request, 'postulaciones/partials/_drawer_candidatos.html', context)
    return render(request, 'postulaciones/lista_recibidas.html', context)

def _es_peticion_ajax(request):
    """El modal del dashboard envía X-Requested-With y origen=dashboard."""
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.POST.get('origen') == 'dashboard'
    )


def _respuesta_error_postulacion_htmx(mensaje, nivel='error', status=400, requiere_verificacion=False):
    tipo_toast = 'warning' if nivel == 'warning' else 'error'
    response = HttpResponse(
        f'<div class="jd-inline-feedback is-error">{escape(mensaje)}</div>',
        status=status,
    )
    response['HX-Trigger'] = json.dumps({
        'jobdevs:toast': {'tipo': tipo_toast, 'mensaje': mensaje},
        'jobdevs:postulacion-error': {
            'mensaje': mensaje,
            'requiere_verificacion': bool(requiere_verificacion),
        },
    })
    response['HX-Reswap'] = 'none'
    return response


@login_required
def postularse_a_proyecto(request, proyecto_id):
    htmx = _es_htmx(request)
    ajax = (not htmx) and _es_peticion_ajax(request)

    def fallo(mensaje, nivel='error', status=400, **extra):
        """Responde HTMX, JSON para el modal o mantiene el flujo HTML clásico."""
        if htmx:
            return _respuesta_error_postulacion_htmx(
                mensaje,
                nivel=nivel,
                status=status,
                requiere_verificacion=extra.get('requiere_verificacion', False),
            )
        if ajax:
            return JsonResponse({'ok': False, 'mensaje': mensaje, **extra}, status=status)
        getattr(messages, nivel)(request, mensaje)
        return redirect('dashboard_desarrollador')

    if request.user.rol != 'desarrollador':
        mensaje_rol = 'Solo los desarrolladores pueden postularse a proyectos.'
        if htmx:
            return _respuesta_error_postulacion_htmx(mensaje_rol, status=403)
        if ajax:
            return JsonResponse({'ok': False, 'mensaje': mensaje_rol}, status=403)
        return redirect('inicio')

    perfil_dev, _ = PerfilDesarrollador.objects.get_or_create(usuario=request.user)
    if not perfil_dev.es_verificado_sena:
        mensaje_verificacion = (
            "Debes verificar tu identidad como aprendiz SENA antes de postularte a proyectos."
        )
        if htmx:
            return _respuesta_error_postulacion_htmx(
                mensaje_verificacion, status=403, requiere_verificacion=True
            )
        if ajax:
            return JsonResponse(
                {'ok': False, 'mensaje': mensaje_verificacion, 'requiere_verificacion': True},
                status=403,
            )
        messages.error(request, mensaje_verificacion)
        return redirect('solicitar_verificacion_desarrollador')

    proyecto = Proyecto.objects.filter(id=proyecto_id).first()

    if not proyecto:
        mensaje_no_existe = 'El proyecto solicitado no existe.'
        if htmx:
            return _respuesta_error_postulacion_htmx(mensaje_no_existe, status=404)
        if ajax:
            return JsonResponse({'ok': False, 'mensaje': mensaje_no_existe}, status=404)
        messages.error(request, mensaje_no_existe)
        return redirect('dashboard_desarrollador')

    # Hallazgo 17: Evitar auto-postulación
    if proyecto.empresa_id == request.user.id:
        return fallo(
            "No puedes postularte a un proyecto publicado por tu propia cuenta.",
            status=403,
        )

    if not proyecto.acepta_postulaciones:
        return fallo(
            f"Lo sentimos, el proyecto '{proyecto.titulo}' ya no acepta postulaciones "
            f"(Estado: {proyecto.get_estado_display()}).",
            nivel='warning',
            status=409,
        )

    # RF 3.3.2: no aceptar postulaciones sin cupo, aunque el proyecto siga abierto.
    if proyecto.vacantes_disponibles <= 0:
        return fallo(
            f"El proyecto '{proyecto.titulo}' ya no tiene vacantes disponibles.",
            nivel='warning',
            status=409,
        )

    # Hallazgo 9: Validar si la fecha límite de postulación ya venció
    if proyecto.fecha_limite and proyecto.fecha_limite < timezone.localdate():
        return fallo(
            f"El plazo de postulación para '{proyecto.titulo}' venció el {proyecto.fecha_limite}.",
            nivel='warning',
            status=409,
        )

    if request.method == 'POST':
        perfil = getattr(request.user, 'perfil_desarrollador', None)
        carta = (request.POST.get('carta') or '').strip()
        experiencia = (request.POST.get('experiencia') or '').strip()
        link = (request.POST.get('link') or '').strip()
        if not link and perfil and perfil.portafolio_url:
            link = perfil.portafolio_url

        if not carta:
            return fallo("La carta de presentación es obligatoria.", status=400)

        mensaje = f"CARTA DE PRESENTACIÓN:\n{carta}\n\nEXPERIENCIA:\n{experiencia}\n\nPORTAFOLIO/ENLACE:\n{link}"

        try:
            with transaction.atomic():
                # Hallazgo 12: Bloquear el registro del usuario para prevenir race condition en el límite de postulaciones
                Usuario.objects.select_for_update().get(id=request.user.id)

                # Validar duplicado
                if Postulacion.objects.filter(proyecto=proyecto, desarrollador=request.user).exists():
                    return fallo(
                        "Ya te habías postulado a este proyecto anteriormente.",
                        nivel='warning',
                        status=409,
                    )

                # Validar límite de 3 postulaciones/proyectos activos
                active_count = (
                    Postulacion.objects.filter(desarrollador=request.user, estado__in=['pendiente', 'en_negociacion']).count() +
                    Contratacion.objects.filter(desarrollador=request.user, estado='activa').count()
                )
                if active_count >= 3:
                    return fallo(
                        "Límite alcanzado: No puedes tener más de 3 postulaciones o proyectos activos.",
                        status=409,
                    )

                postulacion = Postulacion.objects.create(
                    proyecto=proyecto,
                    desarrollador=request.user,
                    mensaje=mensaje,
                    estado='pendiente'
                )

                # RF 6.2.2: la empresa debe enterarse de inmediato de la postulación.
                Notificacion.objects.create(
                    usuario=proyecto.empresa,
                    proyecto=proyecto,
                    tipo='postulacion',
                    mensaje=(
                        f"{request.user.nombre} se postuló a tu proyecto "
                        f"'{proyecto.titulo}'."
                    ),
                )

            if htmx or ajax:
                perfil_emp = getattr(proyecto.empresa, 'perfil_empresa', None)
                empresa_logo = perfil_emp.logo.url if (perfil_emp and perfil_emp.logo) else None
                empresa_nombre = (
                    (perfil_emp.nombre_empresa if perfil_emp and perfil_emp.nombre_empresa else '')
                    or proyecto.empresa.nombre
                    or proyecto.empresa.username
                )
                fecha_fmt = date_format(timezone.localtime(postulacion.fecha), 'd/m/Y')
                estado_display = postulacion.get_estado_display()
                tipo_solucion = proyecto.get_tipo_solucion_display() or proyecto.tipo_solucion
                modalidad = proyecto.get_modalidad_display() or proyecto.modalidad
                detalle_empresa_url = reverse('detalle_empresa', args=[proyecto.empresa_id])
                detalle_proyecto_url = reverse('api_detalle_proyecto', args=[proyecto.id])
                mensaje_exito = f"¡Te has postulado al proyecto '{proyecto.titulo}'!"

                if htmx:
                    response = render(
                        request,
                        'postulaciones/partials/_postulacion_activa_card.html',
                        {
                            'postulacion': postulacion,
                            'proyecto': proyecto,
                            'empresa_nombre': empresa_nombre,
                            'empresa_logo': empresa_logo,
                            'fecha': fecha_fmt,
                            'estado_display': estado_display,
                            'tipo_solucion': tipo_solucion,
                            'modalidad': modalidad,
                            'detalle_empresa_url': detalle_empresa_url,
                            'detalle_proyecto_url': detalle_proyecto_url,
                        },
                    )
                    response['HX-Trigger'] = json.dumps({
                        'jobdevs:toast': {'tipo': 'success', 'mensaje': mensaje_exito},
                        'jobdevs:postulacion-creada': {
                            'proyecto_id': proyecto.id,
                            'requiere_verificacion': False,
                        },
                    })
                    return response

                return JsonResponse({
                    'ok': True,
                    'mensaje': mensaje_exito,
                    'proyecto_id': proyecto.id,
                    'postulacion': {
                        'id': postulacion.id,
                        'fecha': fecha_fmt,
                        'estado': postulacion.estado,
                        'estado_display': estado_display,
                        'proyecto': {
                            'id': proyecto.id,
                            'titulo': proyecto.titulo,
                            'tipo_solucion': tipo_solucion,
                            'modalidad': modalidad,
                            'empresa_id': proyecto.empresa_id,
                            'empresa_nombre': empresa_nombre,
                            'empresa_logo': empresa_logo,
                            'detalle_empresa_url': detalle_empresa_url,
                            'detalle_proyecto_url': detalle_proyecto_url,
                        }
                    }
                })

            messages.success(request, f"¡Te has postulado al proyecto '{proyecto.titulo}'!")
            return redirect('dashboard_desarrollador')
        except Exception:
            logger.exception(
                "Error inesperado al procesar postulación al proyecto %s por usuario %s",
                proyecto_id,
                request.user.id,
            )
            mensaje_error = "Ocurrió un error inesperado al procesar tu postulación. Por favor intenta más tarde."
            if htmx:
                return _respuesta_error_postulacion_htmx(mensaje_error, status=500)
            if ajax:
                return JsonResponse(
                    {'ok': False, 'mensaje': mensaje_error}, status=500
                )
            messages.error(request, mensaje_error)
            return redirect('dashboard_desarrollador')

    return render(request, 'postulaciones/postularse.html', {'proyecto': proyecto})

@login_required
@require_POST
def iniciar_negociacion(request, postulacion_id):
    """La empresa pasa una postulación pendiente a negociación y abre el contrato digital."""
    if request.user.rol != 'empresa':
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    postulacion = get_object_or_404(Postulacion, id=postulacion_id, proyecto__empresa=request.user)
    proyecto_id = postulacion.proyecto_id
    estado_actual = request.POST.get('estado_filtro', '').strip()

    try:
        with transaction.atomic():
            # Serializar decisiones de cupo bloqueando el proyecto
            proyecto = Proyecto.objects.select_for_update().get(id=proyecto_id, empresa=request.user)
            postulacion = Postulacion.objects.select_for_update().get(
                id=postulacion_id, proyecto=proyecto)

            if postulacion.estado != 'pendiente':
                err_msg = "Solo se puede iniciar negociación con postulaciones pendientes."
                if _es_htmx(request):
                    return _render_drawer_htmx(request, proyecto, estado_filtro=estado_actual, toast_msg=err_msg, toast_tipo='error')
                messages.error(request, err_msg)
                return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

            if proyecto.estado not in ('publicado', 'en_desarrollo'):
                err_msg = f"No se puede negociar en un proyecto con estado '{proyecto.get_estado_display()}'."
                if _es_htmx(request):
                    return _render_drawer_htmx(request, proyecto, estado_filtro=estado_actual, toast_msg=err_msg, toast_tipo='error')
                messages.error(request, err_msg)
                return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

            contrataciones_activas = Contratacion.objects.filter(
                proyecto=proyecto, estado='activa').count()
            postulaciones_en_negociacion = Postulacion.objects.filter(
                proyecto=proyecto, estado='en_negociacion').count()
            if contrataciones_activas + postulaciones_en_negociacion >= proyecto.vacantes:
                err_msg = "El proyecto ya ha alcanzado el límite de vacantes disponibles."
                if _es_htmx(request):
                    return _render_drawer_htmx(request, proyecto, estado_filtro=estado_actual, toast_msg=err_msg, toast_tipo='error')
                messages.error(request, err_msg)
                return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

            postulacion.estado = 'en_negociacion'
            plazo_dias = services.obtener_plazo_negociacion_dias()
            postulacion.fecha_limite_negociacion = timezone.now() + timezone.timedelta(
                days=plazo_dias
            )
            postulacion.save()

            ContratoDigital.objects.get_or_create(postulacion=postulacion)

            Notificacion.objects.create(
                usuario=postulacion.desarrollador,
                proyecto=proyecto,
                tipo='postulacion',
                mensaje=(
                    f"{request.user.nombre} inició una negociación contigo para el proyecto "
                    f"'{proyecto.titulo}'. Tienes {plazo_dias} días para revisar y firmar el contrato digital."
                ),
            )

            # El aviso de firma pendiente vive en la campana, no en el cuerpo del panel.
            Notificacion.objects.create(
                usuario=request.user,
                proyecto=proyecto,
                tipo='alerta',
                mensaje=(
                    f"Tu contrato digital del proyecto '{proyecto.titulo}' espera tu firma. "
                    f"Completá los términos y firmá para que "
                    f"{postulacion.desarrollador.nombre} pueda iniciar labores."
                ),
            )

            LogAuditoria.objects.create(
                usuario=request.user,
                accion=f"Inició negociación con {postulacion.desarrollador.nombre} en {proyecto.titulo}",
                tabla_afectada='postulaciones',
                registro_id=postulacion.id,
            )
    except (Postulacion.DoesNotExist, Proyecto.DoesNotExist):
        messages.error(request, "La postulación o el proyecto no existe.")
        if _espera_json(request):
            return JsonResponse({'status': 'error', 'message': 'La postulación o el proyecto no existe.'}, status=404)
        return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

    msg = "Negociación iniciada. Define los términos del contrato digital."
    if _espera_json(request):
        messages.success(request, msg)
        return JsonResponse({'status': 'ok', 'message': msg})
    if _es_htmx(request):
        return _render_drawer_htmx(request, proyecto, estado_filtro=estado_actual, toast_msg=msg, toast_tipo='success')
    messages.success(request, msg)
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return HttpResponseRedirect(next_url)
    return redirect('sala_chat', receptor_id=postulacion.desarrollador_id, proyecto_id=postulacion.proyecto_id)


@login_required
@require_POST
def rechazar_postulacion(request, postulacion_id):
    """La empresa rechaza formalmente una postulación recibida (SCRUM-310)."""
    if request.user.rol != 'empresa':
        messages.error(request, "Acceso denegado. Solo las empresas pueden rechazar postulaciones.")
        return redirect('inicio')

    postulacion = get_object_or_404(Postulacion, id=postulacion_id, proyecto__empresa=request.user)
    proyecto = postulacion.proyecto
    proyecto_id = postulacion.proyecto_id
    motivo = request.POST.get('motivo', '')
    estado_actual = request.POST.get('estado_filtro', '').strip()

    try:
        services.rechazar_postulacion(postulacion_id, request.user, motivo=motivo)
        msg = f"La postulación de {postulacion.desarrollador.nombre or postulacion.desarrollador.username} ha sido rechazada."
        if _espera_json(request):
            messages.success(request, msg)
            return JsonResponse({'status': 'ok', 'message': msg})
        if _es_htmx(request):
            return _render_drawer_htmx(request, proyecto, estado_filtro=estado_actual, toast_msg=msg, toast_tipo='success')
        messages.success(request, msg)
    except PermissionDenied as exc:
        if _espera_json(request):
            messages.error(request, str(exc))
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=403)
        if _es_htmx(request):
            return _render_drawer_htmx(request, proyecto, estado_filtro=estado_actual, toast_msg=str(exc), toast_tipo='error')
        messages.error(request, str(exc))
    except ValidationError as exc:
        msg = ' '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
        if _espera_json(request):
            messages.error(request, msg)
            return JsonResponse({'status': 'error', 'message': msg}, status=400)
        if _es_htmx(request):
            return _render_drawer_htmx(request, proyecto, estado_filtro=estado_actual, toast_msg=msg, toast_tipo='error')
        messages.error(request, msg)
    except Exception:
        logger.exception("Error inesperado al rechazar postulación %s por usuario %s", postulacion_id, request.user.id)
        mensaje_error = "Error inesperado al procesar la solicitud."
        if _espera_json(request):
            messages.error(request, mensaje_error)
            return JsonResponse({'status': 'error', 'message': mensaje_error}, status=500)
        if _es_htmx(request):
            return _render_drawer_htmx(request, proyecto, estado_filtro=estado_actual, toast_msg=mensaje_error, toast_tipo='error')
        messages.error(request, mensaje_error)

    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return HttpResponseRedirect(next_url)
    return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

