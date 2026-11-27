import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from contrataciones.models import Contratacion
from notificaciones.models import Notificacion
from proyectos.models import Proyecto
from usuarios.models import Usuario

from .models import Disputa, MensajeDisputa
from .services import (
    abrir_disputa,
    auditar_mensaje_disputa,
    datos_dashboard_disputas,
    resolver_disputa,
)

ESTADOS_MENSAJERIA = ('abierta', 'en_mediacion')


@login_required
def lista_disputas_view(request):
    user = request.user
    if user.rol == 'empresa':
        return redirect(f"{reverse('dashboard_empresa')}?section=disputas")
    if user.rol == 'desarrollador':
        return redirect(f"{reverse('dashboard_desarrollador')}?section=disputas")
    estado = request.GET.get('estado')
    return render(request, 'disputas/lista_disputas.html', datos_dashboard_disputas(user, estado=estado))


@login_required
def abrir_disputa_view(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, pk=proyecto_id)
    user = request.user

    contrataciones_activas = Contratacion.objects.filter(proyecto=proyecto, estado='activa')
    contrato_id = request.GET.get('contratacion_id')
    if contrato_id and not contrato_id.isdigit():
        raise Http404('Contrato no válido.')
    if user.pk == proyecto.empresa_id:
        contratacion = (
            get_object_or_404(contrataciones_activas, pk=contrato_id)
            if contrato_id else contrataciones_activas.order_by('pk').first()
        )
        categorias = Disputa.CATEGORIAS_EMPRESA
        categoria_default = 'incumplimiento_contractual'
    else:
        contratacion = contrataciones_activas.filter(desarrollador=user).first()
        if contratacion is None:
            raise PermissionDenied('No participas en este proyecto.')
        if contrato_id and str(contratacion.pk) != contrato_id:
            raise PermissionDenied('No participas en este contrato.')
        categorias = Disputa.CATEGORIAS_DESARROLLADOR
        categoria_default = 'retencion_fondos'

    categoria_solicitada = request.GET.get('categoria', '')
    if categoria_solicitada in dict(categorias):
        categoria_default = categoria_solicitada

    es_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in (request.headers.get('Accept') or '')
        or request.GET.get('format') == 'json'
        or request.POST.get('origen') == 'dashboard'
    )
    es_htmx = request.headers.get('HX-Request') == 'true' and not es_ajax
    url_abrir = (
        f"{reverse('disputas:abrir_disputa', args=[proyecto.id])}?contratacion_id={contratacion.pk}"
        if contratacion else reverse('disputas:abrir_disputa', args=[proyecto.id])
    )

    if request.method == 'GET' and es_ajax:
        return JsonResponse({
            'ok': True,
            'proyecto': {
                'id': proyecto.id,
                'titulo': proyecto.titulo,
                'empresa': proyecto.empresa.nombre or proyecto.empresa.username,
            },
            'categorias': [{'codigo': c[0], 'label': str(c[1])} for c in categorias],
            'categoria': categoria_default,
            'url_abrir': url_abrir,
        })

    context = {
        'proyecto': proyecto,
        'contratacion': contratacion,
        'motivo': '',
        'categoria': categoria_default,
        'evidencia_url': '',
        'declara_evidencia_no_disponible': False,
        'categorias': categorias,
        'confirma_intento_previo': False,
        'confirma_gravedad': False,
        'acepta_sanciones': False,
        'url_abrir': url_abrir,
        'error': None,
    }

    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()
        categoria = request.POST.get('categoria', '').strip() or categoria_default
        evidencia_url = request.POST.get('evidencia_url', '').strip()
        evidencia_archivo = request.FILES.get('evidencia_archivo')
        declara_evidencia_no_disponible = bool(
            request.POST.get('declara_evidencia_no_disponible')
        )
        confirma_intento_previo = bool(request.POST.get('confirma_intento_previo'))
        confirma_gravedad = bool(request.POST.get('confirma_gravedad'))
        acepta_sanciones = bool(request.POST.get('acepta_sanciones'))

        context.update({
            'motivo': motivo,
            'categoria': categoria,
            'evidencia_url': evidencia_url,
            'declara_evidencia_no_disponible': declara_evidencia_no_disponible,
            'confirma_intento_previo': confirma_intento_previo,
            'confirma_gravedad': confirma_gravedad,
            'acepta_sanciones': acepta_sanciones,
        })

        if not motivo:
            error_msg = 'Debes indicar el motivo de la disputa.'
            if es_ajax:
                return JsonResponse({'ok': False, 'mensaje': error_msg}, status=400)
            if es_htmx:
                context['error'] = error_msg
                return render(request, 'disputas/partials/_modal_abrir_disputa.html', context, status=200)
            messages.error(request, error_msg)
            return render(request, 'disputas/abrir_disputa.html', context, status=200)

        if categoria not in dict(categorias):
            error_msg = 'Debes seleccionar una causal válida para tu rol.'
            if es_ajax:
                return JsonResponse({'ok': False, 'mensaje': error_msg}, status=400)
            if es_htmx:
                context['error'] = error_msg
                return render(request, 'disputas/partials/_modal_abrir_disputa.html', context, status=200)
            messages.error(request, error_msg)
            return render(request, 'disputas/abrir_disputa.html', context, status=400)

        try:
            disputa = abrir_disputa(
                proyecto=proyecto,
                usuario=user,
                motivo=motivo,
                contratacion=contratacion,
                categoria=categoria,
                evidencia_url=evidencia_url,
                evidencia_archivo=evidencia_archivo,
                declara_evidencia_no_disponible=declara_evidencia_no_disponible,
                confirma_intento_previo=confirma_intento_previo,
                confirma_gravedad=confirma_gravedad,
                acepta_sanciones=acepta_sanciones,
            )
        except ValidationError as exc:
            error_msg = ' '.join(exc.messages)
            if es_ajax:
                return JsonResponse({'ok': False, 'mensaje': error_msg}, status=400)
            if es_htmx:
                context['error'] = error_msg
                return render(request, 'disputas/partials/_modal_abrir_disputa.html', context, status=200)
            messages.error(request, error_msg)
            return render(request, 'disputas/abrir_disputa.html', context, status=400)

        msg_exito = 'Disputa abierta. El proyecto fue congelado hasta su resolución.'
        if es_ajax:
            return JsonResponse({
                'ok': True,
                'mensaje': msg_exito,
                'disputa_id': disputa.id,
            })
        if es_htmx:
            response = HttpResponse('')
            response['HX-Trigger'] = json.dumps({
                'jobdevs:toast': {'tipo': 'success', 'mensaje': msg_exito},
                'jobdevs:disputa-creada': {'disputa_id': disputa.id, 'reload_hash': 'desarrollo'},
            })
            return response
        messages.success(request, msg_exito)
        return redirect('disputas:detalle_disputa', disputa_id=disputa.id)

    if es_htmx:
        return render(request, 'disputas/partials/_modal_abrir_disputa.html', context)
    return render(request, 'disputas/abrir_disputa.html', context)


def _get_disputa(disputa_id):
    return get_object_or_404(
        Disputa.objects.select_related(
            'proyecto__empresa', 'contratacion__desarrollador', 'iniciado_por', 'mediador',
        ),
        pk=disputa_id,
    )


def _es_participante(user, disputa):
    return (
        user.pk in (disputa.proyecto.empresa_id, disputa.iniciado_por_id)
        or (disputa.contratacion_id is not None and user.pk == disputa.contratacion.desarrollador_id)
        or user.rol == 'administrador'
    )


@login_required
def descargar_evidencia_view(request, disputa_id):
    disputa = _get_disputa(disputa_id)
    if not _es_participante(request.user, disputa):
        raise PermissionDenied('No tienes acceso a esta evidencia.')
    if not disputa.evidencia_archivo:
        raise Http404('La disputa no tiene un archivo de evidencia.')
    nombre = disputa.evidencia_archivo.name.rsplit('/', 1)[-1]
    return FileResponse(
        disputa.evidencia_archivo.open('rb'),
        as_attachment=True,
        filename=nombre,
    )


def _rol_emisor(user, disputa):
    if user.rol == 'administrador':
        return 'admin'
    if user.pk == disputa.proyecto.empresa_id:
        return 'empresa'
    return 'dev'


def _contexto_sala(disputa, error=None):
    mensajes = []
    for m in disputa.mensajes.select_related('emisor').order_by('fecha_envio', 'pk'):
        m.rol_emisor = _rol_emisor(m.emisor, disputa)
        mensajes.append(m)
    desarrollador = disputa.contratacion.desarrollador if disputa.contratacion_id else None
    return {
        'disputa': disputa,
        'proyecto': disputa.proyecto,
        'empresa': disputa.proyecto.empresa,
        'desarrollador': desarrollador,
        'mediador': disputa.mediador,
        'mensajes': mensajes,
        'puede_escribir': disputa.estado in ESTADOS_MENSAJERIA,
        'error': error,
    }


def _destinatarios_mensaje(disputa, emisor):
    ids = {disputa.proyecto.empresa_id}
    if disputa.contratacion_id:
        ids.add(disputa.contratacion.desarrollador_id)
    elif disputa.iniciado_por_id != disputa.proyecto.empresa_id:
        ids.add(disputa.iniciado_por_id)
    if disputa.mediador_id:
        ids.add(disputa.mediador_id)
    else:
        ids |= set(
            Usuario.objects.filter(rol='administrador', estado='activo')
            .values_list('pk', flat=True)
        )
    ids.discard(emisor.pk)
    return ids


@login_required
def detalle_disputa_view(request, disputa_id):
    disputa = _get_disputa(disputa_id)
    if not _es_participante(request.user, disputa):
        raise PermissionDenied

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
        ctx = _contexto_sala(disputa)
        mensajes_data = [
            {
                'id': m.id,
                'emisor': m.emisor.nombre or m.emisor.username,
                'rol': m.rol_emisor,
                'contenido': m.contenido,
                'fecha': m.fecha_envio.strftime('%d/%m/%Y %H:%M'),
                'es_propio': m.emisor_id == request.user.id,
            }
            for m in ctx['mensajes']
        ]
        return JsonResponse({
            'ok': True,
            'disputa': {
                'id': disputa.id,
                'proyecto_id': disputa.proyecto_id,
                'proyecto_titulo': disputa.proyecto.titulo,
                'categoria': disputa.get_categoria_display(),
                'motivo': disputa.motivo,
                'evidencia_url': disputa.evidencia_url or '',
                'estado': disputa.estado,
                'estado_label': disputa.get_estado_display(),
                'iniciado_por': disputa.iniciado_por.nombre or disputa.iniciado_por.username,
                'empresa': disputa.proyecto.empresa.nombre or disputa.proyecto.empresa.username,
                'desarrollador': disputa.contratacion.desarrollador.nombre or disputa.contratacion.desarrollador.username if disputa.contratacion else 'N/A',
                'mediador': disputa.mediador.nombre or disputa.mediador.username if disputa.mediador else 'Pendiente de asignación',
                'resolucion': disputa.get_resolucion_display() if disputa.resolucion else None,
                'dictamen': disputa.notas_resolucion or '',
                'puede_escribir': ctx['puede_escribir'],
                'es_admin': request.user.rol == 'administrador',
                'resoluciones': (
                    [{'codigo': r[0], 'label': str(r[1])} for r in Disputa.RESOLUCION]
                    if request.user.rol == 'administrador' else []
                ),
                'enviar_url': reverse('disputas:enviar_mensaje_disputa', args=[disputa.id]),
                'resolver_url': reverse('disputas:resolver_disputa', args=[disputa.id]) if request.user.rol == 'administrador' else None,
            },
            'mensajes': mensajes_data,
        })

    return render(request, 'disputas/sala_mediacion.html', _contexto_sala(disputa))


@login_required
@require_POST
def enviar_mensaje_disputa_view(request, disputa_id):
    user = request.user
    contenido = request.POST.get('contenido', '').strip()
    error = None

    with transaction.atomic():
        disputa = _get_disputa(disputa_id)
        if not _es_participante(user, disputa):
            raise PermissionDenied
        # Releer bloqueando para evitar carreras con la resolución.
        estado_actual = (
            Disputa.objects.select_for_update().values_list('estado', flat=True).get(pk=disputa.pk)
        )
        disputa.estado = estado_actual

        if estado_actual not in ESTADOS_MENSAJERIA:
            error = 'La disputa está cerrada: no se pueden enviar nuevos mensajes.'
        elif not contenido:
            error = 'El mensaje no puede estar vacío.'
        else:
            if user.rol == 'administrador' and disputa.estado == 'abierta':
                disputa.estado = 'en_mediacion'
                if not disputa.mediador_id:
                    disputa.mediador = user
                disputa.save(update_fields=['estado', 'mediador'])

            MensajeDisputa.objects.create(disputa=disputa, emisor=user, contenido=contenido)
            auditar_mensaje_disputa(disputa, user, 'HTTP')
            Notificacion.objects.bulk_create([
                Notificacion(
                    usuario_id=uid, proyecto=disputa.proyecto, tipo='mensaje',
                    mensaje=(
                        f"Nuevo mensaje de {user.nombre or user.username} en la disputa "
                        f"#{disputa.pk} del proyecto '{disputa.proyecto.titulo}'."
                    ),
                )
                for uid in _destinatarios_mensaje(disputa, user)
            ])

    if error:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': error}, status=400)
        return render(
            request, 'disputas/sala_mediacion.html', _contexto_sala(disputa, error), status=400,
        )
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('disputas:detalle_disputa', disputa_id=disputa.id)


@login_required
@require_POST
def resolver_disputa_view(request, disputa_id):
    if request.user.rol != 'administrador':
        raise PermissionDenied('Solo un administrador puede resolver disputas.')

    disputa = _get_disputa(disputa_id)
    resolucion = request.POST.get('resolucion', '').strip()
    dictamen = request.POST.get('dictamen', '').strip()

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.POST.get('origen') == 'dashboard'
    )

    try:
        resolver_disputa(disputa, request.user, resolucion, dictamen)
    except ValidationError as exc:
        disputa.refresh_from_db()
        if is_ajax:
            return JsonResponse({'ok': False, 'mensaje': ' '.join(exc.messages)}, status=400)
        return render(
            request, 'disputas/sala_mediacion.html',
            _contexto_sala(disputa, ' '.join(exc.messages)), status=400,
        )
    if is_ajax:
        return JsonResponse({'ok': True, 'mensaje': 'Resolución emitida y acciones ejecutadas correctamente.'})
    messages.success(request, 'Resolución emitida y acciones ejecutadas correctamente.')
    return redirect('disputas:detalle_disputa', disputa_id=disputa_id)
