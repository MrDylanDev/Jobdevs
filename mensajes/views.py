from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.utils.dateparse import parse_date
from django.utils.html import format_html, format_html_join
from logs.models import LogAuditoria
from .models import Mensaje
from usuarios.models import Usuario
from usuarios.utils import get_admin_ids
from proyectos.models import Proyecto
from contrataciones.models import Contratacion
from notificaciones.models import Notificacion
from .services import puede_comunicarse, obtener_destinatarios_disponibles

@login_required
def sala_chat_grupal(request, proyecto_id):
    """Espacio de Trabajo: Chat grupal para todos los involucrados en un proyecto"""
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    
    # Verificar acceso: Empresa dueña o Desarrollador vinculado (activo o finalizado)
    es_empresa = (request.user.rol == 'empresa' and proyecto.empresa == request.user)
    es_desarrollador = Contratacion.objects.filter(
        proyecto=proyecto, desarrollador=request.user, estado__in=['activa', 'finalizada']
    ).exists()
    
    if not (es_empresa or es_desarrollador or request.user.rol == 'administrador'):
        messages.error(request, "No tienes acceso a este espacio de trabajo.")
        return redirect('inicio')

    # Mensajes grupales: receptor es NULL y están ligados a este proyecto
    mensajes_chat = Mensaje.objects.filter(proyecto=proyecto, receptor__isnull=True).order_by('fecha_envio')

    if request.method == 'POST':
        # Bloquear envío si el proyecto está finalizado
        if proyecto and proyecto.estado == 'finalizado':
            messages.error(request, "No se pueden enviar mensajes a proyectos finalizados.")
            return redirect('sala_chat_grupal', proyecto_id=proyecto.id)

        contenido = request.POST.get('cuerpo') or request.POST.get('contenido')
        if contenido:
            try:
                Mensaje.objects.create(
                    remitente=request.user,
                    receptor=None, # Mensaje grupal
                    titulo=f"Espacio de Trabajo: {proyecto.titulo}",
                    contenido=contenido,
                    proyecto=proyecto
                )

                # Notificar a todos los participantes del proyecto excepto el remitente
                destinatarios_ids = set(
                    Contratacion.objects.filter(
                        proyecto=proyecto, estado__in=['activa', 'finalizada']
                    ).values_list('desarrollador_id', flat=True)
                )
                destinatarios_ids.add(proyecto.empresa_id)
                destinatarios_ids.discard(request.user.id)

                notificaciones = [
                    Notificacion(
                        usuario_id=dest_id,
                        proyecto=proyecto,
                        tipo='mensaje',
                        mensaje=f"{request.user.nombre or request.user.username} envió un mensaje en '{proyecto.titulo}'"
                    ) for dest_id in destinatarios_ids
                ]
                if notificaciones:
                    Notificacion.objects.bulk_create(notificaciones)

                return redirect('sala_chat_grupal', proyecto_id=proyecto_id)
            except Exception as e:
                messages.error(request, f"Error al enviar: {e}")

    # Lista de compañeros (Optimizado con JOIN inverso)
    companeros = Usuario.objects.filter(
        contrataciones_dev__proyecto=proyecto,
        contrataciones_dev__estado__in=['activa', 'finalizada']
    ).distinct()

    return render(request, 'mensajes/sala_chat.html', {
        'proyecto': proyecto,
        'mensajes_chat': mensajes_chat,
        'es_grupal': True,
        'companeros': companeros
    })

@login_required
def sala_chat(request, receptor_id, proyecto_id=None):
    """Vista de chat fluido unificada (Soporte Admin compartido y Chat Privado)"""
    # Si receptor_id es 0, redirigir al chat grupal si hay proyecto
    try:
        if int(receptor_id) == 0 and proyecto_id:
            return redirect('sala_chat_grupal', proyecto_id=proyecto_id)
    except (ValueError, TypeError):
        return redirect('inicio')

    receptor = get_object_or_404(Usuario, id=receptor_id)
    proyecto = get_object_or_404(Proyecto, id=proyecto_id) if proyecto_id else None

    # Control de acceso estricto a chats 1:1
    if receptor.id == request.user.id:
        return HttpResponseForbidden("No puedes iniciar una conversación contigo mismo.")

    if not puede_comunicarse(request.user, receptor, proyecto):
        return HttpResponseForbidden("No tienes autorización para comunicarte con este usuario.")

    # Filtro de participantes: Remitente -> Receptor O Receptor -> Remitente
    mensajes_chat = Mensaje.objects.filter(
        (Q(remitente=request.user, receptor=receptor) | Q(remitente=receptor, receptor=request.user))
    )

    # Aislamiento flexible por proyecto
    # Si hay proyecto, mostramos los de ese proyecto + los generales (sin proyecto)
    if proyecto:
        mensajes_chat = mensajes_chat.filter(Q(proyecto=proyecto) | Q(proyecto__isnull=True))
    else:
        # En chat general, solo mostramos los que no tienen proyecto asignado
        mensajes_chat = mensajes_chat.filter(proyecto__isnull=True)

    mensajes_chat = mensajes_chat.order_by('fecha_envio')
    
    # Marcar leídos solo de este contexto
    mensajes_chat.filter(receptor=request.user, leido=False).update(leido=True)

    if request.method == 'POST':
        # Bloquear envío si el proyecto está finalizado
        if proyecto and proyecto.estado == 'finalizado':
            messages.error(request, "No se pueden enviar mensajes a proyectos finalizados.")
            return redirect('sala_chat', receptor_id=receptor_id, proyecto_id=proyecto_id if proyecto_id else 0)

        contenido = request.POST.get('contenido')
        if contenido:
            try:
                Mensaje.objects.create(
                    remitente=request.user,
                    receptor=receptor,
                    titulo=f"Chat: {proyecto.titulo if proyecto else 'General'}",
                    contenido=contenido,
                    proyecto=proyecto
                )

                Notificacion.objects.create(
                    usuario=receptor,
                    proyecto=proyecto,
                    tipo='mensaje',
                    mensaje=f"{request.user.nombre or request.user.username} te envió un mensaje: {proyecto.titulo if proyecto else 'General'}"
                )

                return redirect('sala_chat', receptor_id=receptor_id, proyecto_id=proyecto_id if proyecto_id else 0)
            except Exception as e:
                messages.error(request, f"Error al enviar: {e}")
                
    return render(request, 'mensajes/sala_chat.html', {
        'receptor': receptor,
        'proyecto': proyecto,
        'mensajes_chat': mensajes_chat
    })


# =============================================
#  MENSAJERÍA DIRECTA (Inbox / Sent / Redactar)
# =============================================

@login_required
def mensajeria_inbox(request):
    """Bandeja de entrada: mensajes directos recibidos (con receptor != None)"""
    mensajes_recibidos = Mensaje.objects.filter(
        receptor=request.user
    ).select_related('remitente', 'proyecto').order_by('-fecha_envio')
    return render(request, 'mensajes/inbox.html', {
        'mensajes': mensajes_recibidos
    })


@login_required
def mensajeria_sent(request):
    """Mensajes enviados directamente (con receptor != None)"""
    mensajes_enviados = Mensaje.objects.filter(
        remitente=request.user,
        receptor__isnull=False
    ).select_related('receptor', 'proyecto').order_by('-fecha_envio')
    return render(request, 'mensajes/sent.html', {
        'mensajes': mensajes_enviados
    })


@login_required
def mensajeria_redactar(request):
    """Redactar y enviar un mensaje directo a otro usuario"""
    # Construir lista de usuarios disponibles autorizados según rol
    usuarios_disponibles = obtener_destinatarios_disponibles(request.user)

    # Proyectos visibles para el usuario actual
    if request.user.rol == 'empresa':
        proyectos_disponibles = Proyecto.objects.filter(empresa=request.user)
    elif request.user.rol == 'desarrollador':
        proyectos_disponibles = Proyecto.objects.filter(
            contrataciones__desarrollador=request.user
        ).distinct()
    else:
        proyectos_disponibles = Proyecto.objects.all()

    if request.method == 'POST':
        receptor_id = request.POST.get('receptor')
        proyecto_id = request.POST.get('proyecto')
        titulo = request.POST.get('titulo', '').strip()
        contenido = request.POST.get('contenido', '').strip()

        if not receptor_id or not contenido:
            messages.error(request, 'Debes seleccionar un destinatario y escribir un mensaje.')
        else:
            try:
                receptor = get_object_or_404(Usuario, id=receptor_id)
                proyecto = Proyecto.objects.filter(id=proyecto_id).first() if proyecto_id else None

                if not puede_comunicarse(request.user, receptor, proyecto):
                    messages.error(request, 'No tienes autorización para comunicarte con este usuario o proyecto.')
                    return redirect('mensajeria_redactar')

                Mensaje.objects.create(
                    remitente=request.user,
                    receptor=receptor,
                    titulo=titulo or f'Mensaje de {request.user.nombre or request.user.username}',
                    contenido=contenido,
                    proyecto=proyecto
                )

                Notificacion.objects.create(
                    usuario=receptor,
                    proyecto=proyecto,
                    tipo='mensaje',
                    mensaje=f"{request.user.nombre or request.user.username} te envió un mensaje: {titulo or 'General'}"
                )

                messages.success(request, f'Mensaje enviado a {receptor.nombre or receptor.username}.')
                return redirect('mensajeria_sent')
            except Exception as e:
                messages.error(request, f'Error al enviar el mensaje: {e}')

    return render(request, 'mensajes/redactar.html', {
        'usuarios': usuarios_disponibles,
        'proyectos': proyectos_disponibles,
        'para_id': int(request.GET.get('para', 0)),
        'proyecto_pre': int(request.GET.get('proyecto', 0)),
    })


@login_required
def ver_mensaje(request, mensaje_id):
    """Ver el detalle de un mensaje. Solo el remitente o receptor pueden verlo."""
    mensaje = get_object_or_404(
        Mensaje,
        id=mensaje_id
    )
    # Control de acceso: solo emisor o receptor pueden ver el mensaje
    if request.user != mensaje.remitente and request.user != mensaje.receptor:
        messages.error(request, 'No tienes permiso para ver este mensaje.')
        return redirect('mensajeria_inbox')

    # Marcar como leído si el usuario actual es el receptor
    if request.user == mensaje.receptor and not mensaje.leido:
        mensaje.leido = True
        mensaje.save(update_fields=['leido'])

    return render(request, 'mensajes/detalle.html', {
        'mensaje': mensaje
    })


AUDITORIA_MENSAJES_POR_PAGINA = 25


@login_required
def admin_auditar_mensajes(request):
    """Auditoría de chats (HU-A20): solo administradores. Toda consulta queda en LogAuditoria."""
    quiere_json = (
        'application/json' in request.headers.get('accept', '')
        or request.GET.get('format') == 'json'
    )
    if request.user.rol != 'administrador':
        if quiere_json:
            return JsonResponse({'error': 'Acceso denegado.'}, status=403)
        return HttpResponseForbidden('Acceso denegado.')

    filtros = {
        k: request.GET.get(k, '').strip()
        for k in ('remitente', 'receptor', 'proyecto', 'q', 'fecha_desde', 'fecha_hasta')
    }

    mensajes_qs = Mensaje.objects.select_related('remitente', 'receptor', 'proyecto')
    if filtros['remitente']:
        mensajes_qs = mensajes_qs.filter(
            Q(remitente__username__icontains=filtros['remitente'])
            | Q(remitente__nombre__icontains=filtros['remitente'])
        )
    if filtros['receptor']:
        mensajes_qs = mensajes_qs.filter(
            Q(receptor__username__icontains=filtros['receptor'])
            | Q(receptor__nombre__icontains=filtros['receptor'])
        )
    if filtros['proyecto']:
        q_proyecto = Q(proyecto__titulo__icontains=filtros['proyecto'])
        if filtros['proyecto'].isdigit():
            q_proyecto |= Q(proyecto__id=int(filtros['proyecto']))
        mensajes_qs = mensajes_qs.filter(q_proyecto)
    if filtros['q']:
        mensajes_qs = mensajes_qs.filter(
            Q(contenido__icontains=filtros['q']) | Q(titulo__icontains=filtros['q'])
        )
    fecha_desde = parse_date(filtros['fecha_desde']) if filtros['fecha_desde'] else None
    fecha_hasta = parse_date(filtros['fecha_hasta']) if filtros['fecha_hasta'] else None
    if fecha_desde:
        mensajes_qs = mensajes_qs.filter(fecha_envio__date__gte=fecha_desde)
    if fecha_hasta:
        mensajes_qs = mensajes_qs.filter(fecha_envio__date__lte=fecha_hasta)
    mensajes_qs = mensajes_qs.order_by('-fecha_envio', '-id')

    paginator = Paginator(mensajes_qs, AUDITORIA_MENSAJES_POR_PAGINA)
    page_obj = paginator.get_page(request.GET.get('page'))

    detalle_filtros = ', '.join(f'{k}={v}' for k, v in filtros.items() if v) or 'sin filtros'
    accion = f"Auditoría de mensajes: consultó conversaciones con filtros [{detalle_filtros}]"
    LogAuditoria.objects.create(
        usuario=request.user,
        accion=accion[:300],
        tabla_afectada='mensajes',
    )

    if quiere_json:
        return JsonResponse({
            'mensajes': [{
                'id': m.id,
                'remitente_username': m.remitente.username,
                'remitente_nombre': m.remitente.nombre,
                'receptor_username': m.receptor.username if m.receptor else None,
                'receptor_nombre': m.receptor.nombre if m.receptor else None,
                'proyecto_titulo': m.proyecto.titulo if m.proyecto else None,
                'titulo': m.titulo or '',
                'contenido': m.contenido,
                'fecha_envio': m.fecha_envio.isoformat(),
                'es_grupal': m.receptor_id is None,
            } for m in page_obj],
            'pagina': page_obj.number,
            'total_paginas': paginator.num_pages,
            'total': paginator.count,
        })

    filas = format_html_join(
        '',
        '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>',
        (
            (
                m.fecha_envio.strftime('%d/%m/%Y %H:%M'),
                m.remitente.nombre or m.remitente.username,
                'Grupal de Proyecto' if m.receptor_id is None else f'Privado: {m.receptor.username}',
                m.proyecto.titulo if m.proyecto else '—',
                m.contenido[:120],
            )
            for m in page_obj
        ),
    )
    return HttpResponse(format_html(
        '<table class="data-table"><tbody>{}</tbody></table>', filas
    ))
