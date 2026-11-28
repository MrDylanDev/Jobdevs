import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from contrataciones.models import Contratacion
from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from postulaciones.models import Postulacion

from ..models import CategoriaSolucion, Proyecto
from ._helpers import _es_htmx, _espera_json


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
                return responder_error(
                    "Las vacantes deben ser un número mayor o igual a 1."
                )

            tipo_solucion = request.POST.get('tipo_solucion')
            categoria = categorias_solucion.filter(slug=tipo_solucion).first()
            if categoria is None and tipo_solucion not in dict(Proyecto.TIPO_SOLUCION):
                return responder_error(
                    "Error: el tipo de solución seleccionado no es válido."
                )

            # Hallazgo 9: Validar que fecha_limite no sea en el pasado
            fecha_limite = request.POST.get('fecha_limite') or None
            if fecha_limite:
                try:
                    fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%d').date()
                    if fecha_limite_dt < timezone.now().date():
                        return responder_error(
                            "La fecha límite no puede ser anterior a la fecha actual."
                        )
                except ValueError:
                    return responder_error("Formato de fecha límite inválido.")

            fecha_cumplimiento = (request.POST.get('fecha_cumplimiento') or '').strip()
            if not fecha_cumplimiento:
                return responder_error("La fecha de cumplimiento es obligatoria.")
            try:
                fecha_cumplimiento_dt = datetime.strptime(
                    fecha_cumplimiento, '%Y-%m-%d'
                ).date()
                if fecha_cumplimiento_dt < timezone.localdate():
                    return responder_error(
                        "La fecha de cumplimiento no puede estar en el pasado."
                    )
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
                estado='publicado',
            )
            # Hallazgo 18: full_clean() para capturar validaciones de modelo de forma limpia.
            # tipo_solucion se excluye porque admite slugs dinamicos de CategoriaSolucion
            # (ya validado contra TIPO_SOLUCION por la vista cuando no hay categoria).
            proyecto.full_clean(exclude=['tipo_solucion'])
            proyecto.save()
            proyecto.registrar_cambio_estado(
                'publicado', request.user, estado_anterior=None
            )

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
            and proyecto.vacantes
            > proyecto.num_contratos_activos + proyecto.num_negociaciones
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
            Proyecto.objects.select_for_update(),
            id=proyecto_id,
            empresa=request.user,
        )
        hoy = timezone.localdate()
        if not (
            proyecto.estado == 'publicado'
            and proyecto.fecha_limite is not None
            and proyecto.fecha_limite < hoy
            and Contratacion.objects.filter(
                proyecto=proyecto, estado='cancelada'
            ).exists()
            and proyecto.vacantes_disponibles > 0
        ):
            error_msg = "Este proyecto no admite reabrir postulaciones."
        else:
            try:
                nueva_fecha = datetime.strptime(
                    request.POST.get('fecha_limite', ''), '%Y-%m-%d'
                ).date()
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
                    usuario=request.user,
                    tabla_afectada='proyectos',
                    registro_id=proyecto.pk,
                    accion=f"Amplió cierre de postulaciones de {proyecto.titulo}"[:300],
                    valor_anterior=anterior.isoformat(),
                    valor_nuevo=nueva_fecha.isoformat(),
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
        messages.error(
            request, "No puedes editar un proyecto retirado, finalizado o en disputa."
        )
        return redirect('dashboard_empresa')

    if Contratacion.objects.filter(proyecto=proyecto, estado='activa').exists():
        messages.error(
            request,
            "No puedes modificar un proyecto con contratos activos. Finalízalo o retíralo primero.",
        )
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
            return JsonResponse({
                'status': 'ok',
                'message': 'Datos básicos del proyecto actualizados.',
            })
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
            messages.error(
                request, "Las vacantes deben ser un número mayor o igual a 1."
            )
            return redirect('editar_proyecto', proyecto_id=proyecto.id)

        contratos_activos = Contratacion.objects.filter(
            proyecto=proyecto, estado='activa'
        ).count()
        negociaciones_activas = proyecto.postulaciones.filter(
            estado='en_negociacion'
        ).count()
        comprometidas = contratos_activos + negociaciones_activas
        if vacantes < comprometidas:
            messages.error(
                request,
                f"No puedes reducir las vacantes a {vacantes} porque ya hay {comprometidas} "
                f"vacante(s) comprometida(s) ({contratos_activos} contratos activos y {negociaciones_activas} en negociación).",
            )
            return redirect('editar_proyecto', proyecto_id=proyecto.id)

        # Hallazgo 9: Validar que fecha_limite no sea en el pasado
        fecha_limite = request.POST.get('fecha_limite') or None
        if fecha_limite:
            try:
                fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%d').date()
                if fecha_limite_dt < timezone.now().date():
                    messages.error(
                        request,
                        "La fecha límite no puede ser anterior a la fecha actual.",
                    )
                    return redirect('editar_proyecto', proyecto_id=proyecto.id)
            except ValueError:
                messages.error(request, "Formato de fecha límite inválido.")
                return redirect('editar_proyecto', proyecto_id=proyecto.id)

        fecha_cumplimiento = (
            request.POST.get('fecha_cumplimiento') or None
            if 'fecha_cumplimiento' in request.POST
            else proyecto.fecha_cumplimiento
        )
        if 'fecha_cumplimiento' in request.POST and fecha_cumplimiento:
            try:
                fecha_cumplimiento_dt = datetime.strptime(
                    fecha_cumplimiento, '%Y-%m-%d'
                ).date()
                if fecha_cumplimiento_dt < timezone.localdate():
                    messages.error(
                        request,
                        "La fecha de cumplimiento no puede estar en el pasado.",
                    )
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
                messages.error(
                    request, "Error: el tipo de solución seleccionado no es válido."
                )
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

            messages.success(
                request, f"Proyecto '{proyecto.titulo}' actualizado exitosamente."
            )
            if _espera_json(request):
                return JsonResponse({
                    'status': 'ok',
                    'message': f"Proyecto '{proyecto.titulo}' actualizado exitosamente.",
                })
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

    return render(
        request,
        'proyectos/editar_proyecto.html',
        {
            'proyecto': proyecto,
            'categorias_solucion': categorias_solucion,
            'permite_edicion_tecnica': permite_edicion_tecnica,
        },
    )


@login_required
@require_POST
def desactivar_proyecto(request, proyecto_id):
    if request.user.rol != 'empresa':
        return redirect('inicio')

    with transaction.atomic():
        proyecto = get_object_or_404(
            Proyecto.objects.select_for_update(),
            id=proyecto_id,
            empresa=request.user,
        )

        # El retiro de una oferta no termina contratos: eso requiere el flujo contractual.
        if (
            proyecto.estado == 'publicado'
            and not Contratacion.objects.filter(proyecto=proyecto).exists()
        ):
            estado_anterior = proyecto.estado
            proyecto.estado = 'inactivo'
            proyecto.save()

            # 1. Registrar Historial
            proyecto.registrar_cambio_estado(
                'inactivo', request.user, estado_anterior=estado_anterior
            )

            # 2. Gestionar Postulaciones y Notificaciones en bloque
            # Hallazgo 6: Filtrar solo postulaciones pendientes o en negociación
            postulaciones = Postulacion.objects.filter(
                proyecto=proyecto, estado__in=['pendiente', 'en_negociacion']
            ).select_related('desarrollador')

            if postulaciones.exists():
                # Notificaciones masivas para postulantes
                notificaciones_lista = [
                    Notificacion(
                        usuario=pos.desarrollador,
                        tipo='alerta',
                        mensaje=f"El proyecto '{proyecto.titulo}' ha sido retirado por la empresa. Tu postulación ya no está vigente.",
                    )
                    for pos in postulaciones
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
