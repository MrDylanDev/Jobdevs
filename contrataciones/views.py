from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from .models import Contratacion, ContratoDigital
from . import services
from postulaciones.models import Postulacion
from notificaciones.models import Notificacion
from proyectos.models import Proyecto, Equipo
from logs.models import LogAuditoria

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

@login_required
@require_POST
def cancelar_contratacion(request, contratacion_id):
    """Delega la cancelación del contrato en contrataciones/services.py"""
    if request.user.rol != 'empresa':
        return redirect('inicio')

    get_object_or_404(Contratacion, id=contratacion_id, empresa=request.user)
    motivo = request.POST.get('motivo_cancelacion') or request.POST.get('motivo') or ''

    try:
        services.cancelar_contratacion(contratacion_id, request.user, motivo=motivo)
        messages.warning(request, "Contrato cancelado exitosamente.")
    except PermissionDenied as exc:
        messages.error(request, str(exc))
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages) if hasattr(exc, 'messages') else str(exc))
    except Exception as e:
        messages.error(request, f"Error al cancelar contrato: {str(e)}")

    return redirect('dashboard_empresa')


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
        Postulacion.objects.filter(proyecto=proyecto, estado='pendiente').update(estado='rechazada')

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

    if request.method == 'POST':
        if rol_contrato != 'empresa':
            raise PermissionDenied
        if not _contrato_editable(contrato):
            messages.error(request, "El contrato ya no puede editarse porque tiene firmas o no está en negociación.")
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

        if errores:
            for e in errores:
                messages.error(request, e)
            return redirect('ver_contrato_digital', contrato_id=contrato.id)

        with transaction.atomic():
            contrato.monto = monto
            contrato.moneda = moneda
            contrato.forma_pago = forma_pago
            contrato.comentarios_adicionales = request.POST.get('comentarios_adicionales', '').strip()
            contrato.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                accion=f"Actualizó los términos del contrato digital #{contrato.id}",
                tabla_afectada='contratos_digitales',
                registro_id=contrato.id,
            )
        messages.success(request, "Términos del contrato actualizados.")
        return redirect('ver_contrato_digital', contrato_id=contrato.id)

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
    return render(request, 'contrataciones/contrato_digital.html', {
        'contrato': contrato,
        'postulacion': postulacion,
        'proyecto': postulacion.proyecto,
        'empresa': postulacion.proyecto.empresa,
        'desarrollador': postulacion.desarrollador,
        'rol_contrato': rol_contrato,
        'puede_editar': rol_contrato == 'empresa' and _contrato_editable(contrato),
        'puede_firmar': puede_firmar,
        'ya_firmo': ya_firmo,
        'monedas': ContratoDigital.MONEDAS,
        'formas_pago': ContratoDigital.FORMAS_PAGO,
    })


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
        messages.error(request, "Debes aceptar los términos del contrato para firmarlo.")
        return redirect('ver_contrato_digital', contrato_id=contrato.id)

    try:
        with transaction.atomic():
            contrato = ContratoDigital.objects.select_for_update().select_related(
                'postulacion__proyecto__empresa', 'postulacion__desarrollador').get(id=contrato_id)
            postulacion = contrato.postulacion

            if contrato.estado not in ('borrador', 'pendiente_firma') or postulacion.estado != 'en_negociacion':
                messages.error(request, "Este contrato ya no está disponible para firma.")
                return redirect('ver_contrato_digital', contrato_id=contrato.id)

            if postulacion.fecha_limite_negociacion and postulacion.fecha_limite_negociacion < timezone.now():
                from postulaciones.services import expirar_negociacion
                expirar_negociacion(postulacion.id)
                messages.error(request, "El plazo para formalizar este contrato ha expirado.")
                return redirect('ver_contrato_digital', contrato_id=contrato.id)

            ya_firmo = contrato.firmado_empresa if rol_contrato == 'empresa' else contrato.firmado_desarrollador
            if ya_firmo:
                messages.warning(request, "Ya firmaste este contrato.")
                return redirect('ver_contrato_digital', contrato_id=contrato.id)

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
        messages.error(request, f"No es posible formalizar la contratación: {mensaje_error}")
        return redirect('ver_contrato_digital', contrato_id=contrato_id)
    except Exception as e:
        messages.error(request, f"Error al firmar el contrato: {str(e)}")
        return redirect('ver_contrato_digital', contrato_id=contrato_id)

    messages.success(request, mensaje)
    return redirect('ver_contrato_digital', contrato_id=contrato.id)
