import json
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from .models import Contratacion, ContratoDigital, SolicitudCancelacion
from . import services
from postulaciones.models import Postulacion
from notificaciones.models import Notificacion
from proyectos.models import Proyecto, Equipo
from logs.models import LogAuditoria


def _destino_cancelaciones(usuario):
    """Empresa vive en la pestaña de su panel; dev y admin, en la página propia."""
    if getattr(usuario, 'rol', None) == 'empresa':
        return f"{reverse('dashboard_empresa')}?section=cancelaciones"
    return reverse('solicitudes_cancelacion')


@login_required
def listar_contrataciones_empresa(request):
    """Listado de todos los desarrolladores contratados por la empresa"""
    if request.user.rol != 'empresa':
        return redirect('inicio')
    
    contrataciones = Contratacion.objects.filter(empresa=request.user).select_related('proyecto', 'desarrollador').order_by('-fecha_inicio')
    return render(request, 'contrataciones/lista_empresa.html', {'contrataciones': contrataciones})

@login_required
def ver_detalle_contrato(request, contratacion_id):
    """Ver detalles técnicos de un contrato específico"""
    contrato = get_object_or_404(Contratacion, id=contratacion_id)
    
    # Seguridad
    if request.user != contrato.empresa and request.user != contrato.desarrollador and request.user.rol != 'administrador':
        return redirect('inicio')
        
    return render(request, 'contrataciones/detalle.html', {'contrato': contrato})

def _contexto_solicitudes_cancelacion(usuario):
    """Construye el contexto compartido para la página de solicitudes de dev/admin."""
    rol = usuario.rol
    solicitudes = SolicitudCancelacion.objects.select_related(
        'contratacion__proyecto', 'contratacion__empresa',
        'contratacion__desarrollador', 'solicitante', 'resuelto_por',
    )
    contratos = Contratacion.objects.none()
    if rol == 'desarrollador':
        solicitudes = solicitudes.filter(contratacion__desarrollador=usuario)
        contratos = Contratacion.objects.filter(
            desarrollador=usuario, estado='activa',
        ).exclude(
            proyecto__estado='en_disputa',
        ).exclude(
            solicitudes_cancelacion__estado__in=['pendiente_acuerdo', 'pendiente_revision'],
        ).select_related('proyecto', 'empresa', 'desarrollador')
    else:
        solicitudes = solicitudes.exclude(causal='acuerdo_mutuo').exclude(estado='pendiente_acuerdo')

    return {
        'solicitudes': solicitudes.order_by('-fecha_creacion'),
        'contratos': contratos,
        'causales': SolicitudCancelacion.CAUSALES,
        'rol': rol,
    }


def _render_cancelaciones_htmx(request, *, toast=None):
    """Devuelve el partial/panel actualizado de cancelaciones + HX-Trigger toast."""
    if request.user.rol == 'empresa':
        response = render(
            request,
            'empresa/partials/_tab_cancelaciones.html',
            services.datos_dashboard_cancelaciones(request.user),
        )
    else:
        response = render(
            request,
            'contrataciones/solicitudes_cancelacion.html',
            _contexto_solicitudes_cancelacion(request.user),
        )
    if toast:
        tipo, mensaje = toast
        response['HX-Trigger'] = json.dumps({
            'jobdevs:toast': {'tipo': tipo, 'mensaje': mensaje},
        })
    return response


@login_required
@require_POST
def cancelar_contratacion(request, contratacion_id):
    """Ruta histórica: inicia una solicitud; nunca cancela inmediatamente."""
    if request.user.rol not in ('empresa', 'desarrollador'):
        raise PermissionDenied

    titular = 'empresa' if request.user.rol == 'empresa' else 'desarrollador'
    contrato = get_object_or_404(Contratacion, id=contratacion_id, **{titular: request.user})
    motivo = request.POST.get('motivo_cancelacion') or request.POST.get('motivo') or ''
    causal = request.POST.get('causal', '')
    evidencia = request.POST.get('evidencia', '')
    if causal in ('incumplimiento', 'inactividad'):
        messages.info(request, 'Para un conflicto grave completa el formulario formal de disputa; esta solicitud no se guardó.')
        return redirect(
            f"{reverse('disputas:abrir_disputa', args=[contrato.proyecto_id])}"
            f"?contratacion_id={contrato.pk}"
        )

    try:
        services.solicitar_cancelacion(
            contratacion_id, request.user, causal=causal, motivo=motivo, evidencia=evidencia,
        )
        toast_tipo = 'success'
        msg = 'Solicitud registrada. El contrato sigue activo hasta su aprobación.'
    except PermissionDenied as exc:
        toast_tipo = 'error'
        msg = str(exc)
    except ValidationError as exc:
        toast_tipo = 'error'
        msg = ' '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)

    if _es_htmx(request):
        return _render_cancelaciones_htmx(request, toast=(toast_tipo, msg))

    getattr(messages, toast_tipo)(request, msg)
    return redirect(_destino_cancelaciones(request.user))


@login_required
def solicitudes_cancelacion(request):
    """Consulta privada de solicitudes y contratos que aún admiten una solicitud."""
    rol = request.user.rol
    if rol not in ('empresa', 'desarrollador', 'administrador'):
        raise PermissionDenied
    if rol == 'empresa':
        # La empresa gestiona el flujo dentro de su panel; la URL histórica
        # sobrevive como atajo para no romper enlaces ni marcadores.
        return redirect(_destino_cancelaciones(request.user))
    return render(
        request,
        'contrataciones/solicitudes_cancelacion.html',
        _contexto_solicitudes_cancelacion(request.user),
    )


@login_required
@require_POST
def resolver_solicitud_cancelacion(request, solicitud_id):
    decision = request.POST.get('decision')
    if decision not in ('aprobar', 'rechazar'):
        msg = 'Selecciona una decisión válida.'
        if _es_htmx(request):
            return _render_cancelaciones_htmx(request, toast=('error', msg))
        messages.error(request, msg)
        return redirect(_destino_cancelaciones(request.user))
    try:
        services.resolver_solicitud_cancelacion(
            solicitud_id, request.user, aprobar=(decision == 'aprobar'),
            dictamen=request.POST.get('dictamen', ''),
        )
        toast_tipo = 'success'
        msg = 'Decisión registrada y notificada a ambas partes.'
    except ValidationError as exc:
        toast_tipo = 'error'
        msg = ' '.join(exc.messages)

    if _es_htmx(request):
        return _render_cancelaciones_htmx(request, toast=(toast_tipo, msg))

    getattr(messages, toast_tipo)(request, msg)
    return redirect(_destino_cancelaciones(request.user))


# ---------------------------------------------------------------------------
# Contrato digital (Módulo 8)
# ---------------------------------------------------------------------------

def _rol_en_contrato(user, contrato):
    """Devuelve 'empresa', 'desarrollador', 'administrador' o None según la relación con el contrato."""
    postulacion = contrato.postulacion
    if user.id == postulacion.proyecto.empresa_id:
        return 'empresa'
    if user.id == postulacion.desarrollador_id:
        return 'desarrollador'
    if user.rol == 'administrador':
        return 'administrador'
    return None


def _es_xhr(request):
    """True cuando la petición proviene del modal in-situ (Fetch con Accept application/json o XHR)."""
    accept = request.headers.get('Accept', '')
    return (
        'application/json' in accept
        or request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.POST.get('origen') == 'dashboard'
    )


def _peticion_ajax(request):
    """True cuando el cliente espera JSON (Fetch con Accept application/json o ?format=json)."""
    return _es_xhr(request) or request.GET.get('format') == 'json'


def _es_htmx(request):
    """True cuando la petición proviene de HTMX y no solicita JSON explícitamente."""
    return request.headers.get('HX-Request') == 'true' and not _peticion_ajax(request)


def _es_modal_jdm(request):
    """True cuando el destino es el modal compartido #jdmModal del panel desarrollador."""
    return (
        request.GET.get('jdm') == '1'
        or request.POST.get('jdm') == '1'
        or request.headers.get('HX-Target') == 'jdmBody'
    )


def _es_url_http_segura(url):
    return bool(re.match(r'^https?://\S+$', str(url or '').strip(), re.I))


def _parsear_clausulas(clausulas_raw):
    items = []
    for raw in re.split(r'(?=\d+\.\s)', clausulas_raw or ''):
        texto = raw.strip()
        if not texto:
            continue
        match = re.match(r'^(\d+\.\s*[A-ZÁÉÍÓÚÑ0-9 _/-]+:)\s*(.*)$', texto, re.S)
        limpia = re.sub(r'^\d+[\.\)]\s*', '', texto)
        limpia = re.sub(r'^CLÁUSULA\s*\d+[\.\:]\s*', '', limpia, flags=re.I)
        items.append({
            'texto': texto,
            'titulo': match.group(1) if match else '',
            'cuerpo': match.group(2) if match else texto,
            'limpia': limpia,
        })
    return items


def _parsear_mensaje_postulacion(mensaje):
    texto = str(mensaje or '').strip()
    if not texto:
        return []
    patron = r'(CARTA DE PRESENTACIÓN|EXPERIENCIA|PORTAFOLIO/ENLACE):\s*'
    if not re.search(patron, texto, re.I):
        return []
    partes = re.split(patron, texto, flags=re.I)
    bloques = []
    for i in range(1, len(partes), 2):
        titulo = (partes[i] or '').strip()
        contenido = (partes[i + 1] if i + 1 < len(partes) else '').strip()
        if not contenido:
            continue
        bloques.append({
            'titulo': titulo,
            'contenido': contenido,
            'es_enlace': bool(re.search(r'PORTAFOLIO', titulo, re.I) and _es_url_http_segura(contenido)),
        })
    return bloques


def _render_contrato_htmx(
    request,
    contrato,
    rol_contrato,
    *,
    error_terminos=None,
    error_firma=None,
    aviso_firma=None,
    form_values=None,
    toast=None,
    actualizado=False,
    recien_firmado=False,
):
    postulacion = contrato.postulacion
    proyecto = postulacion.proyecto
    perfil = contrato.obtener_perfil_profesional()
    ya_firmo, puede_firmar = _permisos_firma(contrato, rol_contrato)
    habilidades_raw = str((perfil or {}).get('habilidades') or '').strip()
    habilidades_lista = [s.strip() for s in habilidades_raw.split(',') if s.strip()] if habilidades_raw else []
    portafolio_url = (perfil or {}).get('portafolio_url') or ''
    valores_form = form_values if form_values is not None else {
        'monto': f"{contrato.monto:.2f}" if contrato.monto is not None else '',
        'moneda': contrato.moneda,
        'forma_pago': contrato.forma_pago,
        'medio_pago': contrato.medio_pago or 'transferencia',
        'comentarios_adicionales': contrato.comentarios_adicionales or '',
    }
    contexto = {
        'contrato': contrato,
        'codigo': f"CTR-{contrato.id:04d}",
        'postulacion': postulacion,
        'proyecto': proyecto,
        'empresa': proyecto.empresa,
        'desarrollador': postulacion.desarrollador,
        'perfil_profesional': perfil,
        'habilidades_lista': habilidades_lista,
        'portafolio_url_segura': _es_url_http_segura(portafolio_url),
        'mensaje_postulacion_bloques': _parsear_mensaje_postulacion((perfil or {}).get('mensaje_postulacion')),
        'clausulas_items': _parsear_clausulas(contrato.clausulas or ''),
        'rol_contrato': rol_contrato,
        'puede_editar': rol_contrato == 'empresa' and _contrato_editable(contrato),
        'puede_firmar': puede_firmar,
        'ya_firmo': ya_firmo,
        'monedas': ContratoDigital.MONEDAS,
        'formas_pago': ContratoDigital.FORMAS_PAGO,
        'medios_pago': ContratoDigital.MEDIOS_PAGO,
        'medio_pago_display': (
            contrato.get_medio_pago_display()
            if (contrato.medio_pago and hasattr(contrato, 'get_medio_pago_display'))
            else 'Transferencia bancaria'
        ),
        'fecha_creacion_fmt': timezone.localtime(contrato.fecha_creacion).strftime('%d/%m/%Y %H:%M') if contrato.fecha_creacion else '',
        'fecha_firma_empresa_fmt': timezone.localtime(contrato.fecha_firma_empresa).strftime('%d/%m/%Y %H:%M') if contrato.fecha_firma_empresa else None,
        'fecha_firma_desarrollador_fmt': timezone.localtime(contrato.fecha_firma_desarrollador).strftime('%d/%m/%Y %H:%M') if contrato.fecha_firma_desarrollador else None,
        'url_editar': reverse('ver_contrato_digital', args=[contrato.id]),
        'url_firmar': reverse('firmar_contrato_digital', args=[contrato.id]),
        'error_terminos': error_terminos,
        'error_firma': error_firma,
        'aviso_firma': aviso_firma,
        'form_values': valores_form,
    }
    template = (
        'contrataciones/partials/_modal_contrato_jdm.html'
        if _es_modal_jdm(request)
        else 'contrataciones/partials/_modal_contrato_empresa.html'
    )
    response = render(request, template, contexto, status=200)
    triggers = {}
    if toast:
        tipo, mensaje = toast
        triggers['jobdevs:toast'] = {'tipo': tipo, 'mensaje': mensaje}
    if actualizado:
        triggers['jobdevs:contrato-actualizado'] = {
            'id': contrato.id,
            'estado': contrato.estado,
            'estado_display': contrato.get_estado_display(),
            'firmado_empresa': contrato.firmado_empresa,
            'firmado_desarrollador': contrato.firmado_desarrollador,
            'esta_firmado': contrato.esta_firmado,
            'monto_formateado': contrato.monto_formateado,
            'hash_contrato': contrato.hash_contrato or '',
            'recien_firmado': recien_firmado,
        }
    if triggers:
        response['HX-Trigger'] = json.dumps(triggers)
    return response


def _permisos_firma(contrato, rol_contrato):
    """Calcula ya_firmo / puede_firmar para la parte que consulta el contrato."""
    postulacion = contrato.postulacion
    ya_firmo = (
        (rol_contrato == 'empresa' and contrato.firmado_empresa)
        or (rol_contrato == 'desarrollador' and contrato.firmado_desarrollador)
    )
    puede_firmar = (
        rol_contrato in ('empresa', 'desarrollador')
        and not ya_firmo
        and contrato.estado in ('borrador', 'pendiente_firma')
        and postulacion.estado == 'en_negociacion'
    )
    return ya_firmo, puede_firmar


def _serializar_contrato_digital(contrato, rol_contrato):
    """Payload JSON del contrato digital para el modal in-situ del dashboard."""
    postulacion = contrato.postulacion
    proyecto = postulacion.proyecto
    desarrollador = postulacion.desarrollador
    empresa = proyecto.empresa
    ya_firmo, puede_firmar = _permisos_firma(contrato, rol_contrato)
    return {
        'id': contrato.id,
        'codigo': f"CTR-{contrato.id:04d}",
        'proyecto_titulo': proyecto.titulo,
        'proyecto_id': proyecto.id,
        'desarrollador_nombre': desarrollador.nombre or desarrollador.username,
        'desarrollador_id': desarrollador.id,
        'perfil_profesional': contrato.obtener_perfil_profesional(),
        'empresa_nombre': empresa.nombre or empresa.username,
        'monto_formateado': contrato.monto_formateado,
        'monto': contrato.monto,
        'moneda': contrato.moneda,
        'forma_pago': contrato.forma_pago,
        'forma_pago_display': contrato.get_forma_pago_display(),
        'medio_pago': contrato.medio_pago or 'transferencia',
        'medio_pago_display': contrato.get_medio_pago_display() if (contrato.medio_pago and hasattr(contrato, 'get_medio_pago_display')) else 'Transferencia bancaria',
        'medios_pago': [{'valor': k, 'label': v} for k, v in ContratoDigital.MEDIOS_PAGO],
        'formas_pago': [{'valor': k, 'label': v} for k, v in ContratoDigital.FORMAS_PAGO],
        'monedas': [{'valor': k, 'label': v} for k, v in ContratoDigital.MONEDAS],
        'clausulas': contrato.clausulas,
        'comentarios_adicionales': contrato.comentarios_adicionales,
        'disclaimer': contrato.disclaimer,
        'estado': contrato.estado,
        'estado_display': contrato.get_estado_display(),
        'firmado_empresa': contrato.firmado_empresa,
        'fecha_firma_empresa': contrato.fecha_firma_empresa,
        'firmado_desarrollador': contrato.firmado_desarrollador,
        'fecha_firma_desarrollador': contrato.fecha_firma_desarrollador,
        'hash_documento': contrato.hash_documento,
        'hash_contrato': contrato.hash_contrato,
        'esta_firmado': contrato.esta_firmado,
        'puede_editar': rol_contrato == 'empresa' and _contrato_editable(contrato),
        'puede_firmar': puede_firmar,
        'ya_firmo': ya_firmo,
        'url_firmar': reverse('firmar_contrato_digital', args=[contrato.id]),
        'firma_url': reverse('firmar_contrato_digital', args=[contrato.id]),
        'url_editar': reverse('ver_contrato_digital', args=[contrato.id]),
    }


def _contrato_editable(contrato):
    """Los términos solo se editan mientras no exista ninguna firma ni formalización."""
    return (
        contrato.estado in ('borrador', 'pendiente_firma')
        and not contrato.firmado_empresa
        and not contrato.firmado_desarrollador
        and contrato.postulacion.estado == 'en_negociacion'
    )


def activar_contratacion_formal(contrato, empresa):
    """Formaliza la contratación cuando ambas partes firmaron. Debe llamarse dentro de una transacción."""
    if not contrato.esta_firmado:
        raise ValidationError('La contratación requiere ambas firmas.')
    postulacion = contrato.postulacion
    proyecto = Proyecto.objects.select_for_update().get(id=postulacion.proyecto_id)
    desarrollador = postulacion.desarrollador

    contrataciones_activas = Contratacion.objects.filter(proyecto=proyecto, estado='activa').count()
    if contrataciones_activas >= proyecto.vacantes:
        raise ValidationError(
            f"El proyecto '{proyecto.titulo}' ya ha alcanzado el límite de vacantes disponibles ({proyecto.vacantes})."
        )

    contrato.estado = 'firmado'

    postulacion.estado = 'aceptada'
    postulacion.save()

    contratacion = Contratacion.objects.create(
        proyecto=proyecto, empresa=empresa, desarrollador=desarrollador, estado='activa')
    contrato.contratacion = contratacion

    nombre_equipo = f'Equipo {proyecto.titulo}'[:100]
    equipo, _ = Equipo.objects.get_or_create(
        proyecto=proyecto,
        nombre=nombre_equipo,
        defaults={'nombre': nombre_equipo},
    )
    equipo.miembros.add(desarrollador)

    if proyecto.estado == 'publicado':
        estado_anterior = proyecto.estado
        proyecto.estado = 'en_desarrollo'
        proyecto.save()
        proyecto.registrar_cambio_estado('en_desarrollo', empresa, estado_anterior=estado_anterior)

    contrataciones_activas = Contratacion.objects.filter(proyecto=proyecto, estado='activa').count()
    if contrataciones_activas >= proyecto.vacantes:
        pendientes_rechazadas = list(
            Postulacion.objects.filter(proyecto=proyecto, estado='pendiente')
            .select_related('desarrollador')
        )
        Postulacion.objects.filter(
            id__in=[postulacion.id for postulacion in pendientes_rechazadas]
        ).update(estado='rechazada')
        Notificacion.objects.bulk_create([
            Notificacion(
                usuario=postulacion.desarrollador,
                proyecto=proyecto,
                tipo='postulacion',
                mensaje=(
                    f"Tu postulación al proyecto '{proyecto.titulo}' fue rechazada "
                    "porque se completaron las vacantes disponibles."
                ),
            )
            for postulacion in pendientes_rechazadas
        ])

    for destinatario in (empresa, desarrollador):
        Notificacion.objects.create(
            usuario=destinatario,
            proyecto=proyecto,
            tipo='aprobacion',
            mensaje=(
                f"El contrato digital del proyecto '{proyecto.titulo}' fue firmado por ambas partes "
                f"y la contratación quedó formalizada."
            ),
        )

    LogAuditoria.objects.create(
        usuario=empresa,
        accion=(
            f"Contrato digital #{contrato.id} firmado por ambas partes; contratación formalizada de "
            f"{desarrollador.nombre} en {proyecto.titulo}"
        )[:300],
        tabla_afectada='contratos_digitales',
        registro_id=contrato.id,
    )
    return contratacion


@login_required
def ver_contrato_digital(request, contrato_id):
    """Muestra el contrato digital; la empresa puede editar los términos mientras no haya firmas."""
    contrato = get_object_or_404(
        ContratoDigital.objects.select_related(
            'postulacion__proyecto__empresa', 'postulacion__desarrollador'),
        id=contrato_id,
    )
    rol_contrato = _rol_en_contrato(request.user, contrato)
    if rol_contrato is None:
        raise PermissionDenied

    postulacion = contrato.postulacion
    if (
        contrato.estado in ('borrador', 'pendiente_firma')
        and postulacion.estado == 'en_negociacion'
        and postulacion.fecha_limite_negociacion
        and postulacion.fecha_limite_negociacion < timezone.now()
    ):
        from postulaciones.services import expirar_negociacion
        expirar_negociacion(postulacion.id)
        contrato.refresh_from_db()
        postulacion.refresh_from_db()
        messages.warning(request, "El plazo para formalizar este contrato ha expirado.")

    if request.method == 'GET' and _peticion_ajax(request):
        clausulas_raw = contrato.clausulas or ''
        import re
        clausulas_list = [c.strip() for c in re.split(r'(?=\d+\.\s)', clausulas_raw) if c.strip()]
        c_dict = _serializar_contrato_digital(contrato, rol_contrato)
        c_dict['clausulas'] = clausulas_list
        c_dict['estado_label'] = contrato.get_estado_display()
        c_dict['fecha_creacion'] = timezone.localtime(contrato.fecha_creacion).strftime('%d/%m/%Y %H:%M') if contrato.fecha_creacion else ''
        c_dict['fecha_firma_empresa'] = timezone.localtime(contrato.fecha_firma_empresa).strftime('%d/%m/%Y %H:%M') if contrato.fecha_firma_empresa else None
        c_dict['fecha_firma_desarrollador'] = timezone.localtime(contrato.fecha_firma_desarrollador).strftime('%d/%m/%Y %H:%M') if contrato.fecha_firma_desarrollador else None
        return JsonResponse({
            'ok': True,
            'status': 'ok',
            'contrato': c_dict,
            **c_dict,
        })

    if request.method == 'GET' and _es_htmx(request):
        return _render_contrato_htmx(request, contrato, rol_contrato)

    if request.method == 'POST':
        if rol_contrato != 'empresa':
            raise PermissionDenied
        if not _contrato_editable(contrato):
            msg = "El contrato ya no puede editarse porque tiene firmas o no está en negociación."
            if _es_xhr(request):
                return JsonResponse({'status': 'error', 'message': msg}, status=400)
            if _es_htmx(request):
                return _render_contrato_htmx(
                    request, contrato, rol_contrato,
                    error_terminos=msg,
                    toast=('error', msg),
                )
            messages.error(request, msg)
            return redirect('ver_contrato_digital', contrato_id=contrato.id)

        errores = []
        try:
            monto = Decimal(request.POST.get('monto', '').strip().replace(',', '.'))
            if not monto.is_finite() or monto < 0 or monto >= Decimal('10000000000'):
                raise InvalidOperation
            monto = monto.quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError):
            errores.append("El monto debe ser un número válido mayor o igual a cero.")
            monto = None

        moneda = request.POST.get('moneda', '')
        if moneda not in dict(ContratoDigital.MONEDAS):
            errores.append("Moneda no válida.")
        forma_pago = request.POST.get('forma_pago', '')
        if forma_pago not in dict(ContratoDigital.FORMAS_PAGO):
            errores.append("Forma de pago no válida.")
        medio_pago = request.POST.get('medio_pago', '').strip() or contrato.medio_pago or 'transferencia'
        if medio_pago not in dict(ContratoDigital.MEDIOS_PAGO):
            errores.append("Medio de pago no válido.")

        if errores:
            if _es_xhr(request):
                return JsonResponse({'status': 'error', 'message': ' '.join(errores)}, status=400)
            if _es_htmx(request):
                msg_err = ' '.join(errores)
                return _render_contrato_htmx(
                    request, contrato, rol_contrato,
                    error_terminos=msg_err,
                    form_values={
                        'monto': request.POST.get('monto', '').strip(),
                        'moneda': moneda or contrato.moneda,
                        'forma_pago': forma_pago or contrato.forma_pago,
                        'medio_pago': medio_pago,
                        'comentarios_adicionales': request.POST.get('comentarios_adicionales', '').strip(),
                    },
                    toast=('error', msg_err),
                )
            for e in errores:
                messages.error(request, e)
            return redirect('ver_contrato_digital', contrato_id=contrato.id)

        with transaction.atomic():
            contrato.monto = monto
            contrato.moneda = moneda
            contrato.forma_pago = forma_pago
            contrato.medio_pago = medio_pago
            contrato.comentarios_adicionales = request.POST.get('comentarios_adicionales', '').strip()
            contrato.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                accion=f"Actualizó los términos del contrato digital #{contrato.id}",
                tabla_afectada='contratos_digitales',
                registro_id=contrato.id,
            )
        if _es_xhr(request):
            return JsonResponse({
                'status': 'ok',
                'message': 'Términos del contrato actualizados exitosamente.',
                'contrato': _serializar_contrato_digital(contrato, rol_contrato),
            })
        if _es_htmx(request):
            return _render_contrato_htmx(
                request, contrato, rol_contrato,
                toast=('success', 'Términos del contrato actualizados exitosamente.'),
                actualizado=True,
            )
        messages.success(request, "Términos del contrato actualizados.")
        return redirect('ver_contrato_digital', contrato_id=contrato.id)

    postulacion = contrato.postulacion
    ya_firmo, puede_firmar = _permisos_firma(contrato, rol_contrato)

    if _es_xhr(request) or request.headers.get('Accept') == 'application/json':
        clausulas_raw = contrato.clausulas or ''
        import re
        # Split numbered clauses like "1. FOO: ... 2. BAR: ..." into a list
        clausulas_list = [c.strip() for c in re.split(r'(?=\d+\.\s)', clausulas_raw) if c.strip()]
        return JsonResponse({
            'ok': True,
            'status': 'ok',
            'contrato': {
                'id': contrato.id,
                'codigo': f"CTR-{contrato.id:04d}",
                'proyecto_id': postulacion.proyecto_id,
                'proyecto_titulo': postulacion.proyecto.titulo,
                'empresa_id': postulacion.proyecto.empresa_id,
                'empresa_nombre': postulacion.proyecto.empresa.nombre or postulacion.proyecto.empresa.username,
                'desarrollador_id': postulacion.desarrollador_id,
                'desarrollador_nombre': postulacion.desarrollador.nombre or postulacion.desarrollador.username,
                'perfil_profesional': contrato.obtener_perfil_profesional(),
                'monto': f"{contrato.monto:,.2f}" if contrato.monto else 'A convenir',
                'monto_formateado': contrato.monto_formateado,
                'moneda': contrato.get_moneda_display(),
                'forma_pago': contrato.get_forma_pago_display(),
                'medio_pago': contrato.get_medio_pago_display() if hasattr(contrato, 'get_medio_pago_display') else '',
                'estado': contrato.estado,
                'estado_label': contrato.get_estado_display(),
                'firmado_empresa': contrato.firmado_empresa,
                'fecha_firma_empresa': contrato.fecha_firma_empresa.strftime('%d/%m/%Y %H:%M') if contrato.fecha_firma_empresa else None,
                'firmado_desarrollador': contrato.firmado_desarrollador,
                'fecha_firma_desarrollador': contrato.fecha_firma_desarrollador.strftime('%d/%m/%Y %H:%M') if contrato.fecha_firma_desarrollador else None,
                'puede_firmar': puede_firmar,
                'ya_firmo': ya_firmo,
                'clausulas': clausulas_list,
                'comentarios': contrato.comentarios_adicionales or '',
                'hash_documento': contrato.hash_documento or '',
                'hash_contrato': contrato.hash_contrato or '',
                'fecha_creacion': contrato.fecha_creacion.strftime('%d/%m/%Y %H:%M') if contrato.fecha_creacion else '',
                'firma_url': reverse('firmar_contrato_digital', args=[contrato.id]),
            }
        })

    return render(request, 'contrataciones/contrato_digital.html', {
        'contrato': contrato,
        'postulacion': postulacion,
        'proyecto': postulacion.proyecto,
        'empresa': postulacion.proyecto.empresa,
        'desarrollador': postulacion.desarrollador,
        'perfil_profesional': contrato.obtener_perfil_profesional(),
        'perfil_congelado': contrato.perfil_profesional is not None,
        'rol_contrato': rol_contrato,
        'puede_editar': rol_contrato == 'empresa' and _contrato_editable(contrato),
        'puede_firmar': puede_firmar,
        'ya_firmo': ya_firmo,
        'monedas': ContratoDigital.MONEDAS,
        'formas_pago': ContratoDigital.FORMAS_PAGO,
        'medios_pago': ContratoDigital.MEDIOS_PAGO,
    })


def _respuesta_firma_error(request, contrato, mensaje, nivel='error', status=400):
    """Devuelve 400/409 JSON para el modal in-situ, partial HTMX o el redirect con mensaje tradicional."""
    if _es_xhr(request):
        return JsonResponse({
            'ok': (nivel == 'warning'),
            'status': 'warning' if nivel == 'warning' else 'error',
            'message': mensaje,
            'mensaje': mensaje,
        }, status=200 if nivel == 'warning' else status)
    if _es_htmx(request):
        contrato.refresh_from_db()
        rol_contrato = _rol_en_contrato(request.user, contrato)
        return _render_contrato_htmx(
            request, contrato, rol_contrato,
            error_firma=mensaje if nivel != 'warning' else None,
            aviso_firma=mensaje if nivel == 'warning' else None,
            toast=(nivel, mensaje),
        )
    getattr(messages, nivel)(request, mensaje)
    return redirect('ver_contrato_digital', contrato_id=contrato.id)


@login_required
@require_POST
def firmar_contrato_digital(request, contrato_id):
    """Firma digital de una de las partes; con ambas firmas se formaliza la contratación."""
    contrato = get_object_or_404(
        ContratoDigital.objects.select_related('postulacion__proyecto'), id=contrato_id)
    rol_contrato = _rol_en_contrato(request.user, contrato)
    if rol_contrato not in ('empresa', 'desarrollador'):
        raise PermissionDenied

    if not request.POST.get('acepta_terminos'):
        return _respuesta_firma_error(
            request, contrato, "Debes aceptar los términos del contrato para firmarlo.")

    try:
        with transaction.atomic():
            contrato = ContratoDigital.objects.select_for_update().select_related(
                'postulacion__proyecto__empresa', 'postulacion__desarrollador').get(id=contrato_id)
            postulacion = contrato.postulacion

            if contrato.estado not in ('borrador', 'pendiente_firma') or postulacion.estado != 'en_negociacion':
                return _respuesta_firma_error(
                    request, contrato, "Este contrato ya no está disponible para firma.", status=409)

            if postulacion.fecha_limite_negociacion and postulacion.fecha_limite_negociacion < timezone.now():
                from postulaciones.services import expirar_negociacion
                expirar_negociacion(postulacion.id)
                return _respuesta_firma_error(
                    request, contrato, "El plazo para formalizar este contrato ha expirado.", status=409)

            ya_firmo = contrato.firmado_empresa if rol_contrato == 'empresa' else contrato.firmado_desarrollador
            if ya_firmo:
                return _respuesta_firma_error(
                    request, contrato, "Ya firmaste este contrato.", nivel='warning')

            if contrato.hash_documento:
                if contrato.hash_documento != contrato.calcular_hash_documento():
                    return _respuesta_firma_error(
                        request, contrato, "El contenido firmado fue alterado; no se puede continuar.",
                        status=409)
            if not contrato.hash_documento:
                contrato.perfil_profesional = contrato.obtener_perfil_profesional()

            ahora = timezone.now()
            if rol_contrato == 'empresa':
                contrato.firmado_empresa = True
                contrato.fecha_firma_empresa = ahora
                otra_parte = postulacion.desarrollador
            else:
                contrato.firmado_desarrollador = True
                contrato.fecha_firma_desarrollador = ahora
                otra_parte = postulacion.proyecto.empresa
            contrato.hash_documento = contrato.hash_documento or contrato.calcular_hash_documento()
            contrato.hash_contrato = contrato.calcular_hash()

            if contrato.esta_firmado:
                activar_contratacion_formal(contrato, postulacion.proyecto.empresa)
                mensaje = "Contrato firmado por ambas partes. ¡La contratación quedó formalizada!"
                valor_anterior = contrato.hash_documento
                valor_nuevo = contrato.hash_contrato
            else:
                contrato.estado = 'pendiente_firma'
                Notificacion.objects.create(
                    usuario=otra_parte,
                    proyecto=postulacion.proyecto,
                    tipo='alerta',
                    mensaje=(
                        f"{request.user.nombre} firmó el contrato digital del proyecto "
                        f"'{postulacion.proyecto.titulo}'. El contrato espera tu firma."
                    ),
                )
                mensaje = "Has firmado el contrato. Queda pendiente la firma de la otra parte."
                valor_anterior = None
                valor_nuevo = contrato.hash_documento

            LogAuditoria.objects.create(
                usuario=request.user,
                accion=f"Firmó el contrato digital #{contrato.id} ({rol_contrato})",
                tabla_afectada='contratos_digitales',
                registro_id=contrato.id,
                valor_anterior=valor_anterior,
                valor_nuevo=valor_nuevo,
            )

            contrato.save()
    except ValidationError as ve:
        mensaje_error = ve.messages[0] if hasattr(ve, 'messages') and ve.messages else str(ve)
        return _respuesta_firma_error(
            request, contrato, f"No es posible formalizar la contratación: {mensaje_error}")
    except Exception as e:
        return _respuesta_firma_error(
            request, contrato, f"Error al firmar el contrato: {str(e)}")

    if _es_xhr(request):
        return JsonResponse({
            'ok': True,
            'status': 'ok',
            'message': mensaje,
            'mensaje': mensaje,
            'esta_firmado': contrato.esta_firmado,
        })
    if _es_htmx(request):
        return _render_contrato_htmx(
            request, contrato, rol_contrato,
            toast=('success', mensaje),
            actualizado=True,
            recien_firmado=True,
        )
    messages.success(request, mensaje)
    return redirect('ver_contrato_digital', contrato_id=contrato.id)
