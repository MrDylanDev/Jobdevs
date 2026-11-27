import json
import os
import zipfile
from PIL import Image
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from .models import Avance
from proyectos.models import Proyecto, Entregable
from contrataciones.models import Contratacion
from notificaciones.models import Notificacion

EXTENSIONES_PERMITIDAS = {'.pdf', '.zip', '.png', '.jpg', '.jpeg'}
MAX_AVANCE_BYTES = 10 * 1024 * 1024  # 10 MB

# SCRUM-220: solo se revisan avances mientras el proyecto siga activo
ESTADOS_PROYECTO_REVISABLES = ('en_desarrollo', 'en_revision')


def _es_ajax(request):
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in (request.headers.get('Accept') or '')
        or request.GET.get('format') == 'json'
    )


def _es_htmx(request):
    return request.headers.get('HX-Request') == 'true' and not _es_ajax(request)


def _json_error(msg, status=400):
    return JsonResponse({'ok': False, 'error': msg, 'mensaje': msg}, status=status)


def _htmx_error(msg, status=400):
    return HttpResponse(
        f'<div class="jdm-error"><i data-lucide="alert-triangle"></i><span>{escape(msg)}</span></div>',
        status=status,
    )


def _validar_archivo_adjunto(archivo):
    """Valida tamaño, extensión, cabecera mágica y consistencia estructural (SCRUM-168)."""
    if not archivo:
        return None
    if archivo.size > MAX_AVANCE_BYTES:
        return "El archivo adjunto no puede superar los 10 MB."

    _, ext = os.path.splitext(archivo.name.lower())
    if ext not in EXTENSIONES_PERMITIDAS:
        return f"Tipo de archivo no permitido ({ext}). Solo se admiten archivos PDF, ZIP, PNG y JPG."

    cabecera = archivo.read(16)
    archivo.seek(0)

    if ext == '.pdf':
        if not cabecera.startswith(b'%PDF-'):
            return "El archivo no es un documento PDF válido."
    elif ext == '.zip':
        if not (cabecera.startswith(b'PK\x03\x04') or cabecera.startswith(b'PK\x05\x06')):
            return "El archivo no es un archivo ZIP válido."
        if not zipfile.is_zipfile(archivo):
            return "El archivo no es un archivo ZIP válido o está dañado."
        archivo.seek(0)
    elif ext in ('.png', '.jpg', '.jpeg'):
        if ext == '.png' and not cabecera.startswith(b'\x89PNG\r\n\x1a\n'):
            return "El archivo no es una imagen PNG válida."
        if ext in ('.jpg', '.jpeg') and not cabecera.startswith(b'\xff\xd8\xff'):
            return "El archivo no es una imagen JPG válida."
        try:
            with Image.open(archivo) as img:
                img.verify()
        except Exception:
            return f"El archivo no es una imagen {ext[1:].upper()} válida o está dañada."
        finally:
            archivo.seek(0)

    return None

@login_required
def registrar_avance(request, proyecto_id):
    is_ajax = _es_ajax(request)
    is_htmx = _es_htmx(request)

    if request.user.rol != 'desarrollador':
        msg = "Solo los desarrolladores pueden registrar avances."
        if is_ajax:
            return _json_error(msg, status=403)
        if is_htmx:
            return _htmx_error(msg, status=403)
        messages.error(request, msg)
        return redirect('inicio')

    if is_ajax or is_htmx:
        proyecto = Proyecto.objects.filter(id=proyecto_id).first()
        if not proyecto:
            msg = "El proyecto no existe."
            return _json_error(msg, status=404) if is_ajax else _htmx_error(msg, status=404)
    else:
        proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    # 1. Verificar que el desarrollador está contratado para este proyecto (SCRUM-459 / AUD-001)
    contratado = Contratacion.objects.filter(proyecto=proyecto, desarrollador=request.user, estado='activa').exists()
    if not contratado:
        msg = "No tienes un contrato activo para este proyecto."
        if is_ajax:
            return _json_error(msg, status=403)
        if is_htmx:
            return _htmx_error(msg, status=403)
        messages.error(request, msg)
        return redirect(reverse('dashboard_desarrollador') + '?section=activos')

    # 2. Verificar el estado del proyecto: 
    # Solo se permiten avances en proyectos 'en_desarrollo' o 'en_revision' (si hay hitos pendientes).
    # IMPORTANTE: No mutar estado en GET. La transición a 'en_desarrollo' se efectúa atómicamente en POST.
    hitos_pendientes_count = Entregable.objects.filter(proyecto=proyecto, estado='pendiente').count()
    if proyecto.estado not in ('en_desarrollo', 'en_revision') or (proyecto.estado == 'en_revision' and hitos_pendientes_count == 0):
        msg = f"Ya no puedes subir más avances para el proyecto '{proyecto.titulo}', pues ya no se encuentra en estado de desarrollo."
        if is_ajax:
            return _json_error(msg, status=400)
        if is_htmx:
            return _htmx_error(msg, status=400)
        messages.warning(request, msg)
        return redirect(reverse('dashboard_desarrollador') + '?section=activos')

    # 3. SCRUM-205 / SCRUM-309: Verificar si hay hitos pendientes disponibles para el desarrollador
    #    - Hitos asignados individualmente a él (desarrollador=request.user)
    #    - Hitos sin desarrollador asignado que sean de su equipo o generales
    hitos_pendientes = Entregable.objects.filter(
        Q(proyecto=proyecto) &
        Q(estado='pendiente') &
        (
            Q(desarrollador=request.user)
            | (Q(desarrollador__isnull=True) & (Q(equipo__miembros=request.user) | Q(equipo__isnull=True)))
        )
    ).distinct()

    if not hitos_pendientes.exists():
        total_hitos = Entregable.objects.filter(proyecto=proyecto).count()
        if total_hitos == 0:
            msg = f"El proyecto '{proyecto.titulo}' aún no tiene hitos definidos por la empresa."
            if is_ajax:
                return _json_error(msg, status=400)
            if is_htmx:
                return _htmx_error(msg, status=400)
            messages.warning(request, msg)
        else:
            msg = f"Todos los hitos del proyecto '{proyecto.titulo}' ya han sido entregados o están en revisión."
            if is_ajax:
                return _json_error(msg, status=400)
            if is_htmx:
                return _htmx_error(msg, status=400)
            messages.info(request, msg)
        return redirect(reverse('dashboard_desarrollador') + '?section=activos')

    url_registrar = reverse('registrar_avance', args=[proyecto.id])

    if request.method == 'GET' and is_ajax:
        return JsonResponse({
            'ok': True,
            'proyecto': {
                'id': proyecto.id,
                'titulo': proyecto.titulo,
            },
            'hitos_pendientes': [
                {'id': h.id, 'titulo': h.titulo, 'descripcion': h.descripcion or ''}
                for h in hitos_pendientes
            ],
            'url_registrar': url_registrar,
        })

    form_data = {
        'entregable_id': '',
        'descripcion': '',
        'archivo_url': '',
    }

    if request.method == 'GET' and is_htmx:
        return render(request, 'avances/partials/_modal_registrar_avance.html', {
            'proyecto': proyecto,
            'hitos_pendientes': hitos_pendientes,
            'form_data': form_data,
            'url_registrar': url_registrar,
            'error': None,
        })

    def _responder_error(msg_error):
        if is_ajax:
            return JsonResponse({'status': 'error', 'error': msg_error}, status=400)
        if is_htmx:
            return render(request, 'avances/partials/_modal_registrar_avance.html', {
                'proyecto': proyecto,
                'hitos_pendientes': hitos_pendientes,
                'form_data': form_data,
                'url_registrar': url_registrar,
                'error': msg_error,
            }, status=200)
        messages.error(request, msg_error)
        return render(request, 'avances/registrar.html', {
            'proyecto': proyecto,
            'hitos_pendientes': hitos_pendientes,
            'form_data': form_data,
        })

    if request.method == 'POST':
        try:
            descripcion = (request.POST.get('descripcion') or '').strip()
            archivo_url = (request.POST.get('archivo_url') or '').strip()
            archivo_adjunto = request.FILES.get('archivo_adjunto')
            entregable_id = (request.POST.get('entregable_id') or '').strip()

            form_data = {
                'entregable_id': entregable_id,
                'descripcion': descripcion,
                'archivo_url': archivo_url,
            }

            if not entregable_id:
                return _responder_error("Debes seleccionar un hito para registrar el avance.")

            if not descripcion:
                return _responder_error("Debes ingresar una descripción detallada del progreso realizado.")
            
            if archivo_url:
                from django.core.validators import URLValidator
                from django.core.exceptions import ValidationError
                url_val = URLValidator(schemes=['http', 'https'])
                try:
                    url_val(archivo_url)
                except ValidationError:
                    return _responder_error("La URL de evidencia debe ser una dirección web válida (iniciando con http:// o https://).")

            if archivo_adjunto:
                error_adjunto = _validar_archivo_adjunto(archivo_adjunto)
                if error_adjunto:
                    return _responder_error(error_adjunto)

            entregable = get_object_or_404(Entregable, id=entregable_id, proyecto=proyecto)

            if entregable.estado != 'pendiente':
                return _responder_error(f"El hito '{entregable.titulo}' ya no se encuentra pendiente y no admite nuevos avances.")

            # SCRUM-309 (HU-E13): guardas de asignación individual y de equipo
            if entregable.desarrollador_id and entregable.desarrollador_id != request.user.id:
                return _responder_error(
                    f"El hito '{entregable.titulo}' está asignado a otro desarrollador y no puedes registrar avances sobre él."
                )

            if entregable.equipo_id and not entregable.equipo.miembros.filter(id=request.user.id).exists():
                return _responder_error(
                    f"No eres miembro del equipo '{entregable.equipo.nombre}' asignado al hito '{entregable.titulo}', por lo que no puedes registrar avances sobre él."
                )

            with transaction.atomic():
                # Bloquear el proyecto para evitar condiciones de carrera
                proyecto = Proyecto.objects.select_for_update().get(id=proyecto_id)

                # Re-verificar estado dentro de la transacción
                hitos_pendientes_count = Entregable.objects.filter(proyecto=proyecto, estado='pendiente').count()

                if proyecto.estado == 'en_revision' and hitos_pendientes_count > 0:
                    estado_anterior = proyecto.estado
                    proyecto.estado = 'en_desarrollo'
                    proyecto.save()
                    proyecto.registrar_cambio_estado('en_desarrollo', request.user, estado_anterior=estado_anterior)
                elif proyecto.estado != 'en_desarrollo':
                    raise Exception(f"El proyecto '{proyecto.titulo}' ya no se encuentra en estado de desarrollo.")

                # 1. Crear el Avance
                avance = Avance.objects.create(
                    proyecto=proyecto,
                    desarrollador=request.user,
                    entregable=entregable,
                    descripcion=descripcion,
                    archivo_url=archivo_url or None,
                    archivo_adjunto=archivo_adjunto,
                    estado='pendiente'
                )

                # 2. Actualizar el Hito
                entregable.estado = 'en_revision'
                entregable.save()

                # 3. Notificar a la Empresa
                Notificacion.objects.create(
                    usuario=proyecto.empresa,
                    proyecto=proyecto,
                    tipo='avance',
                    mensaje=f"{request.user.nombre or request.user.username} completó el hito '{entregable.titulo}' en el proyecto: {proyecto.titulo}"
                )

                # 4. Verificar si quedan hitos pendientes para cierre automático del proyecto
                hitos_restantes = Entregable.objects.filter(proyecto=proyecto, estado='pendiente').count()
                
                if hitos_restantes == 0:
                    estado_anterior = proyecto.estado
                    proyecto.estado = 'en_revision'
                    proyecto.save()
                    # Auditoría de estado
                    proyecto.registrar_cambio_estado('en_revision', request.user, estado_anterior=estado_anterior)
                    messages.info(request, "¡Felicidades! Has enviado el último hito. El proyecto ha pasado a Revisión Final.")

            redirect_target = reverse('dashboard_desarrollador') + '?section=activos'
            msg_exito = '¡Hito completado y avance registrado exitosamente!'
            if is_htmx:
                response = HttpResponse('')
                response['HX-Trigger'] = json.dumps({
                    'jobdevs:toast': {'tipo': 'success', 'mensaje': msg_exito},
                    'jobdevs:avance-registrado': {'proyecto_id': proyecto.id},
                })
                return response
            messages.success(request, msg_exito)
            if is_ajax:
                return JsonResponse({
                    'status': 'ok',
                    'mensaje': msg_exito,
                    'redirect_url': redirect_target,
                })
            return redirect(redirect_target)
        except Exception as e:
            return _responder_error(f"Error al registrar avance: {str(e)}")

    return render(request, 'avances/registrar.html', {
        'proyecto': proyecto,
        'hitos_pendientes': hitos_pendientes,
        'form_data': form_data,
    })

@login_required
@require_POST
def revisar_avance(request, avance_id):
    if request.user.rol != 'empresa':
        messages.error(request, "Solo las empresas pueden revisar avances.")
        return redirect('inicio')
    
    avance = get_object_or_404(Avance, id=avance_id, proyecto__empresa=request.user)

    # SCRUM-220: bloquear la revisión si el proyecto ya no está activo
    if avance.proyecto.estado not in ESTADOS_PROYECTO_REVISABLES:
        messages.error(
            request,
            f"No se pueden revisar avances en un proyecto con estado '{avance.proyecto.get_estado_display()}'."
        )
        return redirect('ver_avances', proyecto_id=avance.proyecto.id)

    if avance.estado != 'pendiente':
        messages.error(
            request,
            f"Este avance ya fue {avance.get_estado_display().lower()} y no puede volver a revisarse."
        )
        return redirect('ver_avances', proyecto_id=avance.proyecto.id)

    accion = request.POST.get('accion') 
    comentario = request.POST.get('comentario', '') 
    
    if accion not in ['aceptar', 'rechazar']:
        messages.error(request, "Acción de revisión no válida.")
        return redirect('ver_avances', proyecto_id=avance.proyecto.id)

    if accion == 'rechazar' and not comentario.strip():
        messages.error(request, "Debes escribir un comentario explicando por qué rechazas el avance.")
        return redirect('ver_avances', proyecto_id=avance.proyecto.id)

    proyecto_recien_finalizado = False
    try:
        with transaction.atomic():
            avance = (
                Avance.objects.select_for_update()
                .select_related('proyecto', 'entregable', 'desarrollador')
                .get(id=avance_id, proyecto__empresa=request.user)
            )
            # SCRUM-220: bloquear también el proyecto para revalidar su estado dentro de la transacción
            proyecto = Proyecto.objects.select_for_update().get(id=avance.proyecto_id)
            if proyecto.estado not in ESTADOS_PROYECTO_REVISABLES:
                messages.error(
                    request,
                    f"No se pueden revisar avances en un proyecto con estado '{proyecto.get_estado_display()}'."
                )
                return redirect('ver_avances', proyecto_id=proyecto.id)

            if avance.estado != 'pendiente':
                messages.error(
                    request,
                    f"Este avance ya fue {avance.get_estado_display().lower()} y no puede volver a revisarse."
                )
                return redirect('ver_avances', proyecto_id=avance.proyecto.id)

            if accion == 'aceptar':
                avance.estado = 'aceptado'
                avance.comentario_revision = comentario
                avance.save()
                
                # Marcar hito como COMPLETADO
                avance.entregable.estado = 'completado'
                avance.entregable.save()

                # RF 5.1.1 oficial: aprobar el último hito finaliza el proyecto.
                if not avance.proyecto.entregables.exclude(estado='completado').exists():
                    from proyectos.services import finalizar_proyecto, desarrolladores_pendientes

                    finalizar_proyecto(avance.proyecto_id, request.user)
                    proyecto_recien_finalizado = desarrolladores_pendientes(avance.proyecto).exists()
                
                # Notificar al desarrollador
                Notificacion.objects.create(
                    usuario=avance.desarrollador,
                    proyecto=avance.proyecto,
                    tipo='aprobacion',
                    mensaje=f"Tu avance en el hito '{avance.entregable.titulo}' ha sido ACEPTADO."
                )
                messages.success(request, f"Hito '{avance.entregable.titulo}' aceptado.")
            else:
                avance.estado = 'rechazado'
                avance.comentario_revision = comentario
                avance.save()

                # Devolver hito a PENDIENTE
                # El método save() de Entregable se encargará de devolver el proyecto 
                # a 'en_desarrollo' si estaba 'en_revision' y registrar la auditoría.
                avance.entregable.estado = 'pendiente'
                avance.entregable.save(cambiado_por=request.user)

                messages.warning(request, f"Hito '{avance.entregable.titulo}' rechazado.")

                Notificacion.objects.create(
                    usuario=avance.desarrollador,
                    proyecto=avance.proyecto,
                    tipo='alerta',
                    mensaje=f"Tu avance en el hito '{avance.entregable.titulo}' ha sido RECHAZADO. Revisa los comentarios."
                )
                messages.warning(request, "Avance rechazado. Se ha notificado al desarrollador y el proyecto ha vuelto a 'En Desarrollo'.")

        if proyecto_recien_finalizado:
            return redirect(f"{reverse('dashboard_empresa')}?section=historial&calificar_proyecto={avance.proyecto.id}#historial")

        next_url = request.POST.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return HttpResponseRedirect(next_url)
        return redirect('ver_avances', proyecto_id=avance.proyecto.id)
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('ver_avances', proyecto_id=avance.proyecto.id)

@login_required
def ver_avances(request, proyecto_id):
    es_ajax = _es_ajax(request)
    es_htmx = _es_htmx(request)

    if es_ajax or es_htmx:
        proyecto = Proyecto.objects.filter(id=proyecto_id).first()
        if not proyecto:
            msg = "El proyecto no existe."
            return _json_error(msg, status=404) if es_ajax else _htmx_error(msg, status=404)
    else:
        proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    # Verificar si el usuario tiene relación con el proyecto (Desarrollador, Empresa, Admin)
    es_admin = request.user.rol == 'administrador'
    es_empresa_duena = (request.user.rol == 'empresa' and proyecto.empresa == request.user)
    es_desarrollador_relacionado = Contratacion.objects.filter(
        proyecto=proyecto, 
        desarrollador=request.user
    ).exists()

    if not (es_admin or es_empresa_duena or es_desarrollador_relacionado):
        msg = "No tienes permisos para ver los avances de este proyecto."
        if es_ajax:
            return _json_error(msg, status=403)
        if es_htmx:
            return _htmx_error(msg, status=403)
        messages.error(request, msg)
        if request.user.rol == 'desarrollador':
            return redirect('dashboard_desarrollador')
        elif request.user.rol == 'empresa':
            return redirect('dashboard_empresa')
        return redirect('inicio')
        
    # Consulta de avances optimizada con select_related
    avances = Avance.objects.filter(proyecto=proyecto).select_related('desarrollador__perfil_desarrollador', 'entregable').order_by('-fecha_hora')
    
    # Obtener el progreso total desde ORM
    progreso = Entregable.objects.filter(proyecto=proyecto).aggregate(
        hitos_completados=Count('id', filter=Q(estado='completado')),
        hitos_totales=Count('id'),
    )
    hitos_completados = progreso['hitos_completados'] or 0
    hitos_totales = progreso['hitos_totales'] or 0

    if es_ajax or es_htmx:
        avances_data = []
        for a in avances:
            avances_data.append({
                'id': a.id,
                'entregable_id': a.entregable_id,
                'entregable_titulo': a.entregable.titulo if a.entregable else 'Avance general',
                'desarrollador': a.desarrollador.nombre or a.desarrollador.username,
                'descripcion': a.descripcion,
                'archivo_url': a.archivo_url or '',
                'archivo_adjunto_url': a.archivo_adjunto.url if a.archivo_adjunto else '',
                'archivo_adjunto_nombre': os.path.basename(a.archivo_adjunto.name) if a.archivo_adjunto else '',
                'fecha': a.fecha_hora.strftime('%d/%m/%Y %H:%M'),
                'estado': a.estado,
                'estado_label': a.get_estado_display(),
                'observaciones': getattr(a, 'comentario_revision', None) or '',
            })

        hitos_qs = proyecto.entregables.all().order_by('fecha_creacion')
        progreso_pct = round((hitos_completados / hitos_totales) * 100) if hitos_totales else 0
        puede_registrar = (request.user.rol == 'desarrollador' and proyecto.estado == 'en_desarrollo')
        registrar_url = reverse('registrar_avance', args=[proyecto.id])
        empresa_nombre = proyecto.empresa.nombre or proyecto.empresa.username

        if es_htmx:
            return render(request, 'avances/partials/_modal_ver_avances.html', {
                'proyecto': proyecto,
                'empresa_nombre': empresa_nombre,
                'estado_label': proyecto.get_estado_display(),
                'progreso_pct': progreso_pct,
                'hitos_completados': hitos_completados,
                'hitos_totales': hitos_totales,
                'hitos': hitos_qs,
                'avances_items': avances_data,
                'puede_registrar': puede_registrar,
                'registrar_url': registrar_url,
            })

        hitos_data = [
            {
                'id': h.id,
                'titulo': h.titulo,
                'descripcion': h.descripcion or '',
                'estado': h.estado,
                'estado_label': h.get_estado_display(),
            }
            for h in hitos_qs
        ]

        return JsonResponse({
            'ok': True,
            'proyecto': {
                'id': proyecto.id,
                'titulo': proyecto.titulo,
                'estado': proyecto.estado,
                'estado_label': proyecto.get_estado_display(),
                'progreso': progreso_pct,
                'hitos_completados': hitos_completados,
                'hitos_totales': hitos_totales,
                'empresa': empresa_nombre,
            },
            'hitos': hitos_data,
            'avances': avances_data,
            'puede_registrar': puede_registrar,
            'registrar_url': registrar_url,
        })

    # Datos del sub-tab "Hitos del Proyecto" para alternar sin recargar la página (solo empresa)
    hitos = []
    equipos = []
    tiene_multiples_contratos = False
    desarrolladores_activos = []

    if request.user.rol == 'empresa' and proyecto.empresa_id == request.user.id:
        hitos = Entregable.objects.filter(proyecto=proyecto).select_related('desarrollador', 'equipo').order_by('fecha_creacion')
        equipos = proyecto.equipos.all()
        contratos_activos = Contratacion.objects.filter(proyecto=proyecto, estado='activa')
        tiene_multiples_contratos = contratos_activos.count() >= 2
        desarrolladores_activos = contratos_activos.select_related('desarrollador')

    return render(request, 'avances/ver_lista.html', {
        'proyecto': proyecto, 
        'avances': avances,
        'hitos': hitos,
        'equipos': equipos,
        'tiene_multiples_contratos': tiene_multiples_contratos,
        'desarrolladores_activos': desarrolladores_activos,
        'hitos_completados': hitos_completados,
        'hitos_totales': hitos_totales
    })
