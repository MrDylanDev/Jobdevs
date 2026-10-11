from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import Postulacion
from proyectos.models import Proyecto
from contrataciones.models import Contratacion, ContratoDigital
from notificaciones.models import Notificacion
from logs.models import LogAuditoria
from proyectos.models import Equipo

@login_required
def ver_postulaciones_empresa(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, empresa=request.user)
    
    postulaciones_orm = Postulacion.objects.filter(
        proyecto_id=proyecto_id,
        estado__in=['pendiente', 'en_negociacion']
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
        'filtros': {'programa': programa, 'ficha': ficha, 'habilidad': habilidad},
    })

@login_required
def postularse_a_proyecto(request, proyecto_id):
    if request.user.rol != 'desarrollador':
        return redirect('inicio')
    
    proyecto = Proyecto.objects.filter(id=proyecto_id).first()

    if not proyecto:
        messages.error(request, "El proyecto solicitado no existe.")
        return redirect('dashboard_desarrollador')

    if proyecto.estado != 'publicado':
        messages.warning(request, f"Lo sentimos, el proyecto '{proyecto.titulo}' ya no acepta postulaciones (Estado: {proyecto.get_estado_display()}).")
        return redirect('dashboard_desarrollador')
    
    if request.method == 'POST':
        carta = request.POST.get('carta', '')
        experiencia = request.POST.get('experiencia', '')
        link = request.POST.get('link', '')
        
        mensaje = f"CARTA DE PRESENTACIÓN:\n{carta}\n\nEXPERIENCIA:\n{experiencia}\n\nPORTAFOLIO/ENLACE:\n{link}"
        
        try:
            # Validar duplicado
            if Postulacion.objects.filter(proyecto=proyecto, desarrollador=request.user).exists():
                messages.warning(request, "Ya te habías postulado a este proyecto anteriormente.")
                return redirect('dashboard_desarrollador')
            
            # Validar límite de 3 postulaciones/proyectos activos
            active_count = (
                Postulacion.objects.filter(desarrollador=request.user, estado='pendiente').count() +
                Contratacion.objects.filter(desarrollador=request.user, estado='activa').count()
            )
            if active_count >= 3:
                messages.error(request, "Límite alcanzado: No puedes tener más de 3 postulaciones o proyectos activos.")
                return redirect('dashboard_desarrollador')
            
            Postulacion.objects.create(
                proyecto=proyecto,
                desarrollador=request.user,
                mensaje=mensaje,
                estado='pendiente'
            )
            
            messages.success(request, f"¡Te has postulado al proyecto '{proyecto.titulo}'!")
            return redirect('dashboard_desarrollador')
        except Exception as e:
            messages.error(request, f"Error del sistema: {str(e)}")
            return redirect('dashboard_desarrollador')
                
    return render(request, 'postulaciones/postularse.html', {'proyecto': proyecto})

@login_required
@require_POST
def aceptar_postulacion(request, postulacion_id):
    if request.user.rol != 'empresa':
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    postulacion = get_object_or_404(Postulacion, id=postulacion_id, proyecto__empresa=request.user)
    proyecto_id = postulacion.proyecto.id

    try:
        with transaction.atomic():
            # Serializar decisiones de contratación bloqueando la fila del proyecto
            proyecto = Proyecto.objects.select_for_update().get(id=proyecto_id, empresa=request.user)

            if proyecto.estado not in ('publicado', 'en_desarrollo'):
                messages.error(
                    request,
                    f"No se pueden aceptar postulaciones en un proyecto con estado '{proyecto.get_estado_display()}'."
                )
                return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

            # Bloquear la postulación específica
            postulacion = Postulacion.objects.select_for_update().get(
                id=postulacion_id, proyecto=proyecto, estado='pendiente')

            # Validar límite de vacantes según RF 3.3.2
            contrataciones_activas = Contratacion.objects.filter(
                proyecto=proyecto,
                estado='activa'
            ).count()

            postulaciones_en_negociacion = Postulacion.objects.filter(
                proyecto=proyecto,
                estado='en_negociacion'
            ).exclude(id=postulacion.id).count()

            if contrataciones_activas + postulaciones_en_negociacion >= proyecto.vacantes:
                messages.error(
                    request,
                    "El proyecto ya ha alcanzado el límite de vacantes disponibles."
                )
                return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

            Contratacion.objects.create(
                proyecto=proyecto,
                desarrollador=postulacion.desarrollador,
                empresa=request.user,
                estado='activa',
            )

            # Agregar al desarrollador al equipo del proyecto
            equipo, _ = Equipo.objects.get_or_create(
                proyecto=proyecto,
                nombre=f'Equipo {proyecto.titulo}',
                defaults={'nombre': f'Equipo {proyecto.titulo}'},
            )
            equipo.miembros.add(postulacion.desarrollador)

            postulacion.estado = 'aceptada'
            postulacion.save()

            if proyecto.estado == 'publicado':
                estado_anterior = proyecto.estado
                proyecto.estado = 'en_desarrollo'
                proyecto.save()
                proyecto.registrar_cambio_estado('en_desarrollo', request.user, estado_anterior=estado_anterior)

            LogAuditoria.objects.create(
                usuario=request.user,
                accion=f"Aceptó postulación de {postulacion.desarrollador.nombre} en {proyecto.titulo}",
                tabla_afectada='postulaciones',
                registro_id=postulacion.id,
            )

        messages.success(request, "¡Contratación exitosa! El desarrollador ha sido vinculado al proyecto.")
    except Postulacion.DoesNotExist:
        messages.error(request, "La postulación ya fue procesada o no existe.")
    except Proyecto.DoesNotExist:
        messages.error(request, "El proyecto no existe o no pertenece a tu empresa.")
    except Exception as e:
        messages.error(request, f"Error al procesar: {str(e)}")

    return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)


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
            postulacion.fecha_limite_negociacion = timezone.now() + timedelta(days=7)
            postulacion.save()

            ContratoDigital.objects.get_or_create(postulacion=postulacion)

            Notificacion.objects.create(
                usuario=postulacion.desarrollador,
                proyecto=proyecto,
                tipo='postulacion',
                mensaje=(
                    f"{request.user.nombre} inició una negociación contigo para el proyecto "
                    f"'{proyecto.titulo}'. Tienes 7 días para revisar y firmar el contrato digital."
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
        return redirect('ver_postulaciones_empresa', proyecto_id=proyecto_id)

    messages.success(request, "Negociación iniciada. Define los términos del contrato digital.")
    return redirect('sala_chat', receptor_id=postulacion.desarrollador_id, proyecto_id=postulacion.proyecto_id)
