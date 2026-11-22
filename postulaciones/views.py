import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, HttpResponseRedirect
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
    )

@login_required
def ver_postulaciones_empresa(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)

    estado_filtro = request.GET.get('estado', '').strip()
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

    programa = request.GET.get('programa', '').strip()
    ficha = request.GET.get('ficha', '').strip()
    habilidad = request.GET.get('habilidad', '').strip()

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
            
    return render(request, 'postulaciones/lista_recibidas.html', {
        'proyecto': proyecto,
        'postulaciones': postulaciones,
        'programas_disponibles': list(programas_disponibles),
        'filtros': {'programa': programa, 'ficha': ficha, 'habilidad': habilidad, 'estado': estado_filtro},
        'conteos_funnel': conteos_funnel,
    })

def _es_peticion_ajax(request):
    """El modal del dashboard envía X-Requested-With y origen=dashboard."""
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.POST.get('origen') == 'dashboard'
    )


@login_required
def postularse_a_proyecto(request, proyecto_id):
    ajax = _es_peticion_ajax(request)

    def fallo(mensaje, nivel='error', status=400, **extra):
        """Responde JSON para el modal o mantiene el flujo HTML clásico."""
        if ajax:
            return JsonResponse({'ok': False, 'mensaje': mensaje, **extra}, status=status)
        getattr(messages, nivel)(request, mensaje)
        return redirect('dashboard_desarrollador')

    if request.user.rol != 'desarrollador':
        if ajax:
            return JsonResponse(
                {'ok': False, 'mensaje': 'Solo los desarrolladores pueden postularse a proyectos.'},
                status=403,
            )
        return redirect('inicio')

    perfil_dev, _ = PerfilDesarrollador.objects.get_or_create(usuario=request.user)
    if not perfil_dev.es_verificado_sena:
        mensaje_verificacion = (
            "Debes verificar tu identidad como aprendiz SENA antes de postularte a proyectos."
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
        if ajax:
            return JsonResponse(
                {'ok': False, 'mensaje': 'El proyecto solicitado no existe.'}, status=404
            )
        messages.error(request, "El proyecto solicitado no existe.")
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

            if ajax:
                from django.utils.formats import date_format
                from django.urls import reverse
                perfil_emp = getattr(proyecto.empresa, 'perfil_empresa', None)
                empresa_logo = perfil_emp.logo.url if (perfil_emp and perfil_emp.logo) else None
                empresa_nombre = (perfil_emp.nombre_empresa if perfil_emp and perfil_emp.nombre_empresa else '') or proyecto.empresa.nombre or proyecto.empresa.username
                return JsonResponse({
                    'ok': True,
                    'mensaje': f"¡Te has postulado al proyecto '{proyecto.titulo}'!",
                    'proyecto_id': proyecto.id,
                    'postulacion': {
                        'id': postulacion.id,
                        'fecha': date_format(postulacion.fecha, 'd/m/Y'),
                        'estado': postulacion.estado,
                        'estado_display': postulacion.get_estado_display(),
                        'proyecto': {
                            'id': proyecto.id,
                            'titulo': proyecto.titulo,
                            'tipo_solucion': proyecto.get_tipo_solucion_display() or proyecto.tipo_solucion,
                            'modalidad': proyecto.get_modalidad_display() or proyecto.modalidad,
                            'empresa_id': proyecto.empresa_id,
                            'empresa_nombre': empresa_nombre,
                            'empresa_logo': empresa_logo,
                            'detalle_empresa_url': reverse('detalle_empresa', args=[proyecto.empresa_id]),
                            'detalle_proyecto_url': reverse('api_detalle_proyecto', args=[proyecto.id]),
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

    try:
        with transaction.atomic():
            # Serializar decisiones de cupo bloqueando el proyecto
            proyecto = Proyecto.objects.select_for_update().get(id=proyecto_id, empresa=request.user)
            postulacion = Postulacion.objects.select_for_update().get(
                id=postulacion_id, proyecto=proyecto)

            if postulacion.estado != 'pendiente':
                messages.error(request, "Solo se puede iniciar negociación con postulaciones pendientes.")
                return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

            if proyecto.estado not in ('publicado', 'en_desarrollo'):
                messages.error(
                    request,
                    f"No se puede negociar en un proyecto con estado '{proyecto.get_estado_display()}'."
                )
                return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

            contrataciones_activas = Contratacion.objects.filter(
                proyecto=proyecto, estado='activa').count()
            postulaciones_en_negociacion = Postulacion.objects.filter(
                proyecto=proyecto, estado='en_negociacion').count()
            if contrataciones_activas + postulaciones_en_negociacion >= proyecto.vacantes:
                messages.error(request, "El proyecto ya ha alcanzado el límite de vacantes disponibles.")
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
    messages.success(request, msg)
    if _espera_json(request):
        return JsonResponse({'status': 'ok', 'message': msg})
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
    proyecto_id = postulacion.proyecto_id
    motivo = request.POST.get('motivo', '')

    try:
        services.rechazar_postulacion(postulacion_id, request.user, motivo=motivo)
        msg = f"La postulación de {postulacion.desarrollador.nombre or postulacion.desarrollador.username} ha sido rechazada."
        messages.success(request, msg)
        if _espera_json(request):
            return JsonResponse({'status': 'ok', 'message': msg})
    except PermissionDenied as exc:
        messages.error(request, str(exc))
        if _espera_json(request):
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=403)
    except ValidationError as exc:
        msg = ' '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
        messages.error(request, msg)
        if _espera_json(request):
            return JsonResponse({'status': 'error', 'message': msg}, status=400)
    except Exception:
        logger.exception("Error inesperado al rechazar postulación %s por usuario %s", postulacion_id, request.user.id)
        mensaje_error = "Error inesperado al procesar la solicitud."
        messages.error(request, mensaje_error)
        if _espera_json(request):
            return JsonResponse({'status': 'error', 'message': mensaje_error}, status=500)

    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return HttpResponseRedirect(next_url)
    return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

