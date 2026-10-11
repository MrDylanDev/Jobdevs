import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from logs.models import LogAuditoria
from notificaciones.models import Notificacion

from ..decorators import requiere_usuario_activo
from ..models import PerfilEmpresa, Usuario
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

    numero = limpiar_documento(request.POST.get('numero_documento', ''))
    dv = None
    if not numero:
        errores['numero_documento'] = 'El número de documento es obligatorio.'
    else:
        try:
            dv = calcular_dv_dian(numero)
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

        datos, errores = _validar_solicitud(request, perfil)
        if not errores:
            with transaction.atomic():
                perfil.tipo_persona = datos['tipo_persona']
                perfil.tipo_documento = datos['tipo_documento']
                perfil.numero_documento = datos['numero_documento']
                perfil.digito_verificacion = str(datos['digito_verificacion'])
                perfil.razon_social = datos['razon_social']
                if datos['documento_soporte'] is not None:
                    perfil.documento_soporte = datos['documento_soporte']
                perfil.estado_verificacion = 'en_revision'
                perfil.fecha_solicitud_verificacion = timezone.now()
                perfil.save()

                LogAuditoria.objects.create(
                    usuario=request.user,
                    accion=f'Solicitud de verificación de empresa ({perfil.documento_completo})',
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
            accion=accion_log,
            tabla_afectada='perfil_empresa',
            registro_id=perfil.id,
        )
        Notificacion.objects.create(
            usuario=perfil.usuario,
            tipo='aprobacion' if accion == 'aprobar' else 'alerta',
            mensaje=mensaje,
        )

    return destino
