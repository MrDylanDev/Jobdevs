import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from logs.models import LogAuditoria
from notificaciones.models import Notificacion

from ..decorators import requiere_usuario_activo
from ..models import PerfilDesarrollador, PerfilEmpresa, Usuario
from ..services_sena import (
    admin_resolver_verificacion_desarrollador as resolver_desarrollador_sena_service,
    solicitar_verificacion_manual_desarrollador,
    verificar_desarrollador_automatico,
)
from ..utils_dian import calcular_dv_dian, limpiar_documento

MAX_SOPORTE_BYTES = 5 * 1024 * 1024  # 5 MB


def _validar_solicitud(request, perfil):
    """Valida el POST; retorna (datos_limpios, errores)."""
    errores = {}
    tipos_persona = [c[0] for c in PerfilEmpresa.TIPO_PERSONA_CHOICES]
    tipos_documento = [c[0] for c in PerfilEmpresa.TIPO_DOCUMENTO_CHOICES]

    tipo_persona = request.POST.get('tipo_persona', '').strip()
    if tipo_persona not in tipos_persona:
        errores['tipo_persona'] = 'Selecciona un tipo de persona válido.'

    tipo_documento = request.POST.get('tipo_documento', '').strip()
    if tipo_documento not in tipos_documento:
        errores['tipo_documento'] = 'Selecciona un tipo de documento válido.'

    if tipo_persona == 'juridica' and tipo_documento != 'NIT' and 'tipo_documento' not in errores:
        errores['tipo_documento'] = 'Las personas jurídicas deben identificarse con NIT.'

    numero = limpiar_documento(request.POST.get('numero_documento', ''))
    dv = None
    if not numero:
        errores['numero_documento'] = 'El número de documento es obligatorio.'
    else:
        try:
            # El DV DIAN solo aplica a NIT; para CC/CE solo se valida el formato.
            calculado = calcular_dv_dian(numero)
            if tipo_documento == 'NIT':
                dv = calculado
        except ValueError as exc:
            mensaje = str(exc)
            if 'dígitos' in mensaje and 'más de' not in mensaje:
                mensaje = 'El número de documento solo puede contener dígitos.'
            errores['numero_documento'] = mensaje

    razon_social = request.POST.get('razon_social', '').strip()
    if not razon_social:
        errores['razon_social'] = 'La razón social es obligatoria.'
    elif len(razon_social) > 255:
        errores['razon_social'] = 'La razón social no puede superar 255 caracteres.'

    archivo = request.FILES.get('documento_soporte')
    if archivo is None:
        if not perfil.documento_soporte or perfil.estado_verificacion == 'sin_verificar':
            errores['documento_soporte'] = (
                'Adjunta el documento de soporte (Cámara de Comercio o RUT) en formato PDF.'
            )
    elif os.path.splitext(archivo.name)[1].lower() != '.pdf':
        errores['documento_soporte'] = 'El documento de soporte debe ser un archivo PDF.'
    elif archivo.size > MAX_SOPORTE_BYTES:
        errores['documento_soporte'] = 'El documento de soporte no puede superar los 5 MB.'
    else:
        cabecera = archivo.read(1024)
        archivo.seek(0)
        if not cabecera.startswith(b'%PDF-'):
            errores['documento_soporte'] = 'El archivo debe ser un documento PDF válido.'

    datos = {
        'tipo_persona': tipo_persona,
        'tipo_documento': tipo_documento,
        'numero_documento': numero,
        'digito_verificacion': dv,
        'razon_social': razon_social,
        'documento_soporte': archivo,
    }
    return datos, errores


@login_required
@requiere_usuario_activo
def solicitar_verificacion_empresa(request):
    if request.user.rol != 'empresa':
        raise PermissionDenied

    perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        if perfil.estado_verificacion == 'verificada':
            messages.info(request, 'Tu empresa ya está verificada.')
            return redirect('solicitar_verificacion_empresa')
        if perfil.estado_verificacion == 'en_revision':
            messages.warning(
                request,
                'Tu solicitud ya se encuentra en revisión por el equipo del SENA. '
                'No es posible modificarla hasta obtener una respuesta.',
            )
            return redirect('solicitar_verificacion_empresa')

        datos, errores = _validar_solicitud(request, perfil)
        if not errores:
            with transaction.atomic():
                perfil.tipo_persona = datos['tipo_persona']
                perfil.tipo_documento = datos['tipo_documento']
                perfil.numero_documento = datos['numero_documento']
                dv = datos['digito_verificacion']
                perfil.digito_verificacion = str(dv) if datos['tipo_documento'] == 'NIT' and dv is not None else None
                perfil.razon_social = datos['razon_social']
                if datos['documento_soporte'] is not None:
                    perfil.documento_soporte = datos['documento_soporte']
                perfil.estado_verificacion = 'en_revision'
                perfil.fecha_solicitud_verificacion = timezone.now()
                perfil.save()

                LogAuditoria.objects.create(
                    usuario=request.user,
                    accion=f'Solicitud de verificación de empresa ({perfil.documento_completo})'[:300],
                    tabla_afectada='perfil_empresa',
                    registro_id=perfil.id,
                )
                Notificacion.objects.bulk_create([
                    Notificacion(
                        usuario=admin,
                        tipo='alerta',
                        mensaje=(
                            f'La empresa {perfil.razon_social} ({request.user.nombre}) '
                            'solicitó verificación de identidad.'
                        ),
                    )
                    for admin in Usuario.objects.filter(rol='administrador')
                ])
            messages.success(
                request,
                'Tu solicitud fue enviada y está en revisión. Te notificaremos el resultado.',
            )
            return redirect('solicitar_verificacion_empresa')

        valores = {
            'tipo_persona': datos['tipo_persona'],
            'tipo_documento': datos['tipo_documento'],
            'numero_documento': request.POST.get('numero_documento', ''),
            'razon_social': datos['razon_social'],
        }
        return render(request, 'empresa/verificacion.html', {
            'perfil': perfil, 'errores': errores, 'valores': valores,
            'tipos_persona': PerfilEmpresa.TIPO_PERSONA_CHOICES,
            'tipos_documento': PerfilEmpresa.TIPO_DOCUMENTO_CHOICES,
        })

    valores = {
        'tipo_persona': perfil.tipo_persona,
        'tipo_documento': perfil.tipo_documento,
        'numero_documento': perfil.numero_documento or '',
        'razon_social': perfil.razon_social or '',
    }
    return render(request, 'empresa/verificacion.html', {
        'perfil': perfil, 'errores': {}, 'valores': valores,
        'tipos_persona': PerfilEmpresa.TIPO_PERSONA_CHOICES,
        'tipos_documento': PerfilEmpresa.TIPO_DOCUMENTO_CHOICES,
    })


@login_required
@require_POST
def admin_resolver_verificacion_empresa(request, perfil_id):
    """Aprueba o rechaza una solicitud de verificación de empresa (solo administrador)."""
    if request.user.rol != 'administrador':
        raise PermissionDenied

    destino = redirect(reverse('dashboard_admin') + '?section=verificacionEmpresasSection')
    accion = request.POST.get('accion', '').strip()
    notas = request.POST.get('notas', '').strip()

    if accion not in ('aprobar', 'rechazar'):
        messages.error(request, 'Acción de verificación no válida.')
        return destino
    if accion == 'rechazar' and not notas:
        messages.error(request, 'Debes indicar el motivo del rechazo.')
        return destino

    with transaction.atomic():
        perfil = get_object_or_404(
            PerfilEmpresa.objects.select_for_update().select_related('usuario'),
            id=perfil_id,
        )
        if perfil.estado_verificacion != 'en_revision':
            messages.warning(request, 'Esta solicitud ya no está en revisión.')
            return destino

        nombre = perfil.razon_social or perfil.usuario.nombre
        perfil.fecha_verificacion = timezone.now()
        perfil.verificado_por = request.user
        perfil.notas_auditoria = notas or None

        if accion == 'aprobar':
            perfil.estado_verificacion = 'verificada'
            accion_log = f'Aprobó la verificación de la empresa {nombre} ({perfil.documento_completo})'
            mensaje = (
                f'Tu empresa {nombre} fue verificada. '
                'Ya cuentas con la insignia de empresa verificada.'
            )
            if notas:
                mensaje += f' Observaciones: {notas}'
            messages.success(request, f'Empresa {nombre} verificada correctamente.')
        else:
            perfil.estado_verificacion = 'rechazada'
            accion_log = f'Rechazó la verificación de la empresa {nombre} ({perfil.documento_completo})'
            mensaje = (
                f'Tu solicitud de verificación para {nombre} fue rechazada. '
                f'Motivo: {notas}. Puedes corregir tus datos y enviarla nuevamente.'
            )
            messages.info(request, f'Solicitud de {nombre} rechazada.')
        perfil.save()

        LogAuditoria.objects.create(
            usuario=request.user,
            accion=accion_log[:300],
            tabla_afectada='perfil_empresa',
            registro_id=perfil.id,
        )
        Notificacion.objects.create(
            usuario=perfil.usuario,
            tipo='aprobacion' if accion == 'aprobar' else 'alerta',
            mensaje=mensaje,
        )

    return destino


@login_required
@require_POST
def admin_resolver_verificacion_desarrollador(request, perfil_id):
    """Aprueba o rechaza una solicitud de verificación manual de aprendiz SENA (solo administrador)."""
    if request.user.rol != 'administrador':
        raise PermissionDenied

    destino = redirect(reverse('dashboard_admin') + '?section=verificacionDevsSection')
    accion = request.POST.get('accion', '').strip()
    notas = request.POST.get('notas', '').strip()

    ok, msg = resolver_desarrollador_sena_service(
        perfil_id=perfil_id,
        admin_user=request.user,
        accion=accion,
        notas=notas,
    )
    if ok:
        if accion == 'aprobar':
            messages.success(request, msg)
        else:
            messages.info(request, msg)
    else:
        messages.error(request, msg)

    return destino



@login_required
def descargar_documento_soporte_empresa(request, perfil_id):
    """Sirve el documento de soporte (privado) al administrador o a la empresa dueña."""
    perfil = get_object_or_404(PerfilEmpresa, id=perfil_id)
    if request.user.rol != 'administrador' and request.user.pk != perfil.usuario_id:
        raise PermissionDenied
    if not perfil.documento_soporte:
        raise Http404('Documento no disponible.')
    try:
        archivo = perfil.documento_soporte.open('rb')
    except FileNotFoundError:
        raise Http404('Documento no disponible.')
    return FileResponse(archivo, content_type='application/pdf')


@login_required
@requiere_usuario_activo
def solicitar_verificacion_desarrollador(request):
    """Permite al desarrollador verificar su identidad SENA de forma automática o manual."""
    if request.user.rol != 'desarrollador':
        raise PermissionDenied

    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        if perfil.estado_verificacion == 'verificado':
            messages.info(request, 'Tu perfil ya se encuentra verificado como aprendiz SENA.')
            return redirect('solicitar_verificacion_desarrollador')
        if perfil.estado_verificacion == 'en_revision':
            messages.warning(
                request,
                'Tu solicitud ya se encuentra en revisión administrativa. '
                'No es posible modificarla hasta obtener una respuesta.',
            )
            return redirect('solicitar_verificacion_desarrollador')

        metodo = request.POST.get('metodo', 'automatica').strip()
        condicion = request.POST.get('condicion_sena', 'aprendiz').strip()
        ficha = request.POST.get('ficha', '').strip()
        programa = request.POST.get('programa_formacion', '').strip()

        if metodo == 'automatica':
            ok, msg = verificar_desarrollador_automatico(
                perfil=perfil,
                numero_ficha=ficha,
                programa_formacion=programa,
                usuario_solicitante=request.user,
            )
            if ok:
                messages.success(request, msg)
                return redirect('solicitar_verificacion_desarrollador')
            errores = {'ficha': msg}
            valores = {'ficha': ficha, 'programa_formacion': programa, 'metodo': metodo, 'condicion_sena': condicion}
            return render(request, 'desarrollador/verificacion.html', {
                'perfil': perfil, 'errores': errores, 'valores': valores,
            })

        elif metodo == 'manual':
            archivo = request.FILES.get('documento_soporte')
            ok, msg, errores = solicitar_verificacion_manual_desarrollador(
                perfil=perfil,
                numero_ficha=ficha,
                programa_formacion=programa,
                documento_soporte=archivo,
                usuario_solicitante=request.user,
                condicion_sena=condicion,
            )
            if ok:
                messages.success(request, msg)
                return redirect('solicitar_verificacion_desarrollador')
            valores = {'ficha': ficha, 'programa_formacion': programa, 'metodo': metodo, 'condicion_sena': condicion}
            return render(request, 'desarrollador/verificacion.html', {
                'perfil': perfil, 'errores': errores, 'valores': valores,
            })
        else:
            messages.error(request, 'Método de verificación no válido.')
            return redirect('solicitar_verificacion_desarrollador')

    valores = {
        'ficha': perfil.ficha or '',
        'programa_formacion': perfil.programa_formacion or '',
        'condicion_sena': perfil.condicion_sena or 'aprendiz',
        'metodo': 'automatica',
    }
    return render(request, 'desarrollador/verificacion.html', {
        'perfil': perfil,
        'errores': {},
        'valores': valores,
    })


@login_required
def descargar_documento_soporte_desarrollador(request, perfil_id):
    """Sirve de forma privada el documento soporte SENA al administrador o al aprendiz titular."""
    perfil = get_object_or_404(PerfilDesarrollador, id=perfil_id)
    if request.user.rol != 'administrador' and request.user.pk != perfil.usuario_id:
        raise PermissionDenied
    if not perfil.documento_soporte:
        raise Http404('Documento no disponible.')
    try:
        archivo = perfil.documento_soporte.open('rb')
    except FileNotFoundError:
        raise Http404('Documento no disponible.')
    return FileResponse(archivo, content_type='application/pdf')

