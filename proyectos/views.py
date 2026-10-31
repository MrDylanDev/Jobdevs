from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import (
    Avg, Q, Count, Prefetch, Value, FloatField, F, IntegerField, OuterRef, Subquery,
)
from django.db.models.functions import Coalesce
from datetime import datetime
import json
from django.core.paginator import Paginator
from .models import Proyecto, Valoracion, Entregable, Equipo, CategoriaSolucion
from . import services
from logs.models import LogAuditoria
from usuarios.decorators import api_ratelimit
from usuarios.models import Usuario, PerfilDesarrollador
from contrataciones.models import Contratacion
from favoritos.models import Favorito
from postulaciones.models import Postulacion
from notificaciones.models import Notificacion

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
        # RF 3.1.1: publicado, o en desarrollo mientras queden cupos libres y plazo vigente.
        (Q(estado='publicado') | Q(estado='en_desarrollo', disponibles_anotadas__gt=0)),
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

    is_ajax = (
        request.headers.get('Accept') == 'application/json'
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    if is_ajax:
        proyectos_json = []
        for p in proyectos:
            item = dict(p)
            if item.get('fecha_publicacion'):
                item['fecha_publicacion'] = item['fecha_publicacion'].strftime('%d/%m/%Y')
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

    return render(request, 'proyectos/listar.html', {
        'proyectos': proyectos,
        'page_obj': page_obj,
        'favoritos_ids': favoritos_ids,
        'categorias_solucion': CategoriaSolucion.objects.filter(activo=True),
    })

@login_required
def crear_proyecto(request):
    if request.user.rol != 'empresa':
        messages.error(request, "Solo las empresas pueden publicar proyectos.")
        return redirect('dashboard_empresa')

    categorias_solucion = CategoriaSolucion.objects.filter(activo=True)

    if request.method == 'POST':
        try:
            try:
                vacantes = int(request.POST.get('vacantes', 1))
            except (ValueError, TypeError):
                vacantes = 0

            if vacantes < 1:
                messages.error(request, "Las vacantes deben ser un número mayor o igual a 1.")
                return redirect('dashboard_empresa')

            tipo_solucion = request.POST.get('tipo_solucion')
            categoria = categorias_solucion.filter(slug=tipo_solucion).first()
            if categoria is None and tipo_solucion not in dict(Proyecto.TIPO_SOLUCION):
                messages.error(request, "Error: el tipo de solución seleccionado no es válido.")
                return redirect('dashboard_empresa')

            # Hallazgo 9: Validar que fecha_limite no sea en el pasado
            fecha_limite = request.POST.get('fecha_limite') or None
            if fecha_limite:
                try:
                    fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%d').date()
                    if fecha_limite_dt < timezone.now().date():
                        messages.error(request, "La fecha límite no puede ser anterior a la fecha actual.")
                        return redirect('dashboard_empresa')
                except ValueError:
                    messages.error(request, "Formato de fecha límite inválido.")
                    return redirect('dashboard_empresa')

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
                estado='publicado'
            )
            # Hallazgo 18: full_clean() para capturar validaciones de modelo de forma limpia.
            # tipo_solucion se excluye porque admite slugs dinamicos de CategoriaSolucion
            # (ya validado contra TIPO_SOLUCION por la vista cuando no hay categoria).
            proyecto.full_clean(exclude=['tipo_solucion'])
            proyecto.save()
            proyecto.registrar_cambio_estado('publicado', request.user, estado_anterior=None)
            messages.success(request, f"¡Proyecto '{proyecto.titulo}' publicado exitosamente!")
            return redirect('dashboard_empresa')
        except ValidationError as ve:
            messages.error(request, f"Error de validación: {', '.join(ve.messages)}")
        except Exception as e:
            messages.error(request, f"Error: {e}")
            
    return redirect('dashboard_empresa')

@login_required
def finalizar_proyecto(request, proyecto_id):
    """Muestra la confirmación o delega finalización/valoración en los servicios.

    La vista se queda con permisos, parseo del input y mensajes; las reglas de
    negocio (estado, hitos, cupos, transiciones) viven en proyectos/services.py.
    """
    if request.user.rol != 'empresa':
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)

    # Prevalidación de UX: conserva los destinos de redirección específicos
    # (hitos sin definir -> gestión de hitos; hitos pendientes -> avances).
    try:
        services.validar_finalizacion(proyecto)
    except ValidationError as exc:
        motivo = ' '.join(exc.messages)
        messages.error(request, motivo)
        if 'hitos definidos' in motivo:
            return redirect('gestionar_hitos', proyecto_id=proyecto.id)
        if 'hitos sin completar' in motivo:
            return redirect('ver_avances', proyecto_id=proyecto.id)
        return redirect('dashboard_empresa')

    pendientes = services.desarrolladores_pendientes(proyecto)

    # ── Caso A: ya todos valorados → solo falta confirmar el cierre ──
    if not pendientes.exists():
        if request.method == 'POST':
            try:
                services.finalizar_proyecto(proyecto.id, request.user)
                messages.success(
                    request,
                    f"¡Excelente! El proyecto '{proyecto.titulo}' ha sido finalizado exitosamente."
                )
            except PermissionDenied as exc:
                messages.error(request, str(exc))
            except ValidationError as exc:
                messages.error(request, ' '.join(exc.messages))
            except Exception as e:
                messages.error(request, f"Error crítico al finalizar: {str(e)}")
            return redirect('dashboard_empresa')

        return render(request, 'proyectos/finalizar.html', {
            'proyecto': proyecto,
            'desarrollador': None,
            'restantes': 0
        })

    # ── Caso B: quedan colaboradores por calificar ──
    desarrollador = pendientes.first()
    restantes = pendientes.count() - 1

    if request.method == 'POST':
        try:
            finalizado, restantes = services.valorar_y_finalizar_si_ultima(
                proyecto_id=proyecto.id,
                desarrollador_id=desarrollador.id,
                puntuacion=request.POST.get('puntuacion'),
                comentario=request.POST.get('comentario', ''),
                ejecutado_por=request.user,
            )
        except PermissionDenied as exc:
            messages.error(request, str(exc))
            return redirect('finalizar_proyecto', proyecto_id=proyecto.id)
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
            return redirect('finalizar_proyecto', proyecto_id=proyecto.id)
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('finalizar_proyecto', proyecto_id=proyecto.id)

        if finalizado:
            messages.success(
                request,
                f"¡Excelente! Has calificado a todo el equipo y el proyecto "
                f"'{proyecto.titulo}' ha finalizado."
            )
            return redirect('dashboard_empresa')

        messages.success(
            request,
            f"Calificación registrada para {desarrollador.username}. "
            + (f"Quedan {restantes} por calificar." if restantes > 0 else "Era el último colaborador.")
        )
        # Recargamos la misma vista para el siguiente desarrollador
        return redirect('finalizar_proyecto', proyecto_id=proyecto.id)

    return render(request, 'proyectos/finalizar.html', {
        'proyecto': proyecto,
        'desarrollador': desarrollador,
        'restantes': restantes
    })


@login_required
def calificar_empresa(request, proyecto_id):
    """Permite al desarrollador calificar a la empresa tras finalizar un proyecto"""
    if request.user.rol != 'desarrollador':
        return redirect('inicio')
    
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, estado='finalizado')
    contratacion = get_object_or_404(Contratacion, proyecto=proyecto, desarrollador=request.user)
    
    if request.method == 'POST':
        try:
            puntuacion = int(request.POST.get('puntuacion'))
        except (TypeError, ValueError):
            messages.error(request, "Debes seleccionar una puntuación.")
            return redirect('calificar_empresa', proyecto_id=proyecto.id)

        if not 1 <= puntuacion <= 5:
            messages.error(request, "La puntuación debe estar entre 1 y 5.")
            return redirect('calificar_empresa', proyecto_id=proyecto.id)

        # RF 5.2.2: puntuación + comentario cualitativo obligatorio.
        comentario = (request.POST.get('comentario') or '').strip()
        if len(comentario) < services.MIN_COMENTARIO:
            messages.error(
                request,
                f"El comentario es obligatorio y debe tener al menos "
                f"{services.MIN_COMENTARIO} caracteres."
            )
            return redirect('calificar_empresa', proyecto_id=proyecto.id)

        try:
            with transaction.atomic():
                if Valoracion.objects.filter(
                    proyecto=proyecto,
                    empresa=proyecto.empresa,
                    desarrollador=request.user,
                    rol_evaluador='desarrollador',
                ).exists():
                    messages.error(request, "Ya has calificado a esta empresa para este proyecto.")
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
            messages.error(request, "Ya has calificado a esta empresa para este proyecto.")
            return redirect('dashboard_desarrollador')

        messages.success(request, "¡Gracias! Tu calificación ha sido registrada.")
        return redirect('dashboard_desarrollador')

    return render(request, 'proyectos/calificar_empresa.html', {'proyecto': proyecto})

@login_required
def gestionar_equipos(request, proyecto_id):
    if request.user.rol != 'empresa': return redirect('inicio')
    
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)
    # Hallazgo 19: Usar helper del manager Contratacion
    desarrolladores = Contratacion.objects.desarrolladores_activos(proyecto)

    if desarrolladores.count() < 2:
        messages.warning(request, "Para crear grupos o parejas se requieren al menos 2 desarrolladores contratados.")
        return redirect('gestionar_hitos', proyecto_id=proyecto.id)

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        miembros_ids = request.POST.getlist('miembros')
        
        if nombre and miembros_ids:
            nombre = (request.POST.get('nombre') or '').strip()[:100]
            if not nombre:
                messages.error(request, "El nombre del equipo es obligatorio.")
                return redirect('gestionar_equipos', proyecto_id=proyecto.id)

            # Hallazgo 8: Validar que todos los miembros pertenezcan a los desarrolladores activos contratados
            dev_ids_activos = set(str(uid) for uid in desarrolladores.values_list('id', flat=True))
            if not all(str(m) in dev_ids_activos for m in miembros_ids):
                messages.error(request, "Error: Solo puedes asignar desarrolladores contratados y activos en este proyecto.")
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
            
            messages.success(request, f"Equipo '{equipo.nombre}' creado y miembros notificados.")
            return redirect('gestionar_equipos', proyecto_id=proyecto.id)

    equipos = proyecto.equipos.all().prefetch_related('miembros')
    
    return render(request, 'proyectos/gestionar_equipos.html', {
        'proyecto': proyecto,
        'desarrolladores': desarrolladores,
        'equipos': equipos
    })

@login_required
@require_POST
def eliminar_equipo(request, equipo_id):
    equipo = get_object_or_404(Equipo, id=equipo_id, proyecto__empresa=request.user)
    proyecto_id = equipo.proyecto.id
    equipo.delete()
    messages.info(request, "Equipo eliminado.")
    return redirect('gestionar_equipos', proyecto_id=proyecto_id)

@login_required
def gestionar_hitos(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)
    hitos = Entregable.objects.filter(proyecto=proyecto).order_by('fecha_creacion')

    if request.method == 'POST':
        # Hallazgo 16: No permitir crear hitos en proyectos finalizados, inactivos o rechazados
        if proyecto.estado in ('finalizado', 'inactivo', 'rechazado'):
            messages.error(request, f"No se pueden agregar hitos a un proyecto {proyecto.get_estado_display().lower()}.")
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
                    messages.error(request, "Error: El equipo seleccionado no pertenece a este proyecto.")
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
                    messages.error(
                        request,
                        "Error: El desarrollador seleccionado no tiene una contratación activa en este proyecto.",
                    )
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

            messages.success(request, f"Hito '{titulo}' creado y desarrolladores notificados.")
            return redirect('gestionar_hitos', proyecto_id=proyecto.id)

    equipos = proyecto.equipos.all()
    tiene_multiples_contratos = Contratacion.objects.filter(proyecto=proyecto, estado='activa').count() >= 2
    # SCRUM-309 (HU-E13): candidatos válidos para asignación individual de hitos
    desarrolladores_activos = Contratacion.objects.filter(
        proyecto=proyecto, estado='activa'
    ).select_related('desarrollador')

    return render(request, 'proyectos/gestionar_hitos.html', {
        'proyecto': proyecto, 
        'hitos': hitos,
        'equipos': equipos,
        'tiene_multiples_contratos': tiene_multiples_contratos,
        'desarrolladores_activos': desarrolladores_activos,
    })

@login_required
@require_POST
def eliminar_hito(request, hito_id):
    hito = get_object_or_404(Entregable, id=hito_id, proyecto__empresa=request.user)
    proyecto_id = hito.proyecto.id
    if hito.estado == 'pendiente':
        hito.delete()
        messages.success(request, "Hito eliminado.")
    else:
        messages.error(request, "No se puede eliminar un hito que ya ha sido completado.")
    return redirect('gestionar_hitos', proyecto_id=proyecto_id)

@login_required
@require_http_methods(["GET", "POST"])
def editar_proyecto(request, proyecto_id):
    if request.user.rol != 'empresa':
        messages.error(request, "Solo las empresas pueden editar proyectos.")
        return redirect('dashboard_empresa')

    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)

    if proyecto.estado != 'publicado':
        messages.error(request, "Solo puedes editar un proyecto en estado publicado.")
        return redirect('dashboard_empresa')

    if Contratacion.objects.filter(proyecto=proyecto, estado='activa').exists():
        messages.error(request, "No puedes modificar un proyecto con contratos activos. Finalízalo o retíralo primero.")
        return redirect('gestionar_hitos', proyecto_id=proyecto.id)

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
            # Hallazgo 18: full_clean() para capturar validaciones de modelo de forma limpia.
            # tipo_solucion se excluye porque admite slugs dinamicos de CategoriaSolucion
            # (ya validado contra TIPO_SOLUCION por la vista cuando no hay categoria).
            proyecto.full_clean(exclude=['tipo_solucion'])
            proyecto.save()

            messages.success(request, f"Proyecto '{proyecto.titulo}' actualizado exitosamente.")
            return redirect('dashboard_empresa')
        except ValidationError as ve:
            messages.error(request, f"Error de validación: {', '.join(ve.messages)}")
            return redirect('editar_proyecto', proyecto_id=proyecto.id)
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect('editar_proyecto', proyecto_id=proyecto.id)

    return render(request, 'proyectos/editar_proyecto.html', {
        'proyecto': proyecto,
        'categorias_solucion': categorias_solucion,
    })

@login_required
@require_POST
def desactivar_proyecto(request, proyecto_id):
    if request.user.rol != 'empresa':
        return redirect('inicio')
    
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)
    
    # Hallazgo 7: Permitir retirar proyectos en_revision además de publicado y en_desarrollo
    if proyecto.estado in ('publicado', 'en_desarrollo', 'en_revision'):
        with transaction.atomic():
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

            # 3. Gestionar contrataciones en bloque
            contratos = Contratacion.objects.filter(proyecto=proyecto, estado='activa').select_related('desarrollador')
            
            if contratos.exists():
                # Notificaciones masivas para contratados
                notificaciones_contratos = [
                    Notificacion(
                        usuario=c.desarrollador,
                        tipo='alerta',
                        mensaje=f"Importante: El proyecto '{proyecto.titulo}' en el que trabajabas ha sido CANCELADO por la empresa."
                    ) for c in contratos
                ]
                
                # Actualización masiva de contratos
                contratos.update(estado='cancelada')
                # Creación masiva de notificaciones
                Notificacion.objects.bulk_create(notificaciones_contratos)

        messages.info(request, f"El proyecto '{proyecto.titulo}' ha sido retirado y los desarrolladores han sido notificados.")
    else:
        messages.error(request, "No se puede retirar un proyecto que ya está finalizado o inactivo.")
        
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
