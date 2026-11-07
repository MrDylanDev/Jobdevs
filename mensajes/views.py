import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.html import format_html, format_html_join
from django.views.decorators.http import require_POST
from logs.models import LogAuditoria
from .models import Mensaje
from usuarios.models import Usuario
from usuarios.utils import get_admin_ids
from proyectos.models import Proyecto
from contrataciones.models import Contratacion
from notificaciones.models import Notificacion
from . import services
from .policies import (
    obtener_destinatarios_disponibles,
    puede_comunicarse,
    puede_participar_en_chat_grupal,
    puede_ver_mensaje,
)

logger = logging.getLogger(__name__)


@login_required
def sala_chat_grupal(request, proyecto_id):
    """Espacio de Trabajo: Chat grupal para todos los involucrados en un proyecto"""
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    
    # Verificar acceso: Empresa dueña o Desarrollador vinculado (activo o finalizado)
    if not puede_participar_en_chat_grupal(request.user, proyecto):
        messages.error(request, "No tienes acceso a este espacio de trabajo.")
        return redirect('inicio')

    # Mensajes grupales: receptor es NULL y están ligados a este proyecto
    mensajes_chat = Mensaje.objects.filter(proyecto=proyecto, receptor__isnull=True).order_by('fecha_envio')

    if request.method == 'POST':
        contenido = request.POST.get('cuerpo') or request.POST.get('contenido') or ''
        try:
            services.enviar_mensaje_grupal(request.user, proyecto, contenido)
            return redirect('sala_chat_grupal', proyecto_id=proyecto_id)
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
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

    # Aislamiento estricto por proyecto (SCRUM-221 / RF 6.1.3)
    if proyecto:
        mensajes_chat = mensajes_chat.filter(proyecto=proyecto)
    else:
        # En chat general, solo mostramos los que no tienen proyecto asignado
        mensajes_chat = mensajes_chat.filter(proyecto__isnull=True)

    mensajes_chat = mensajes_chat.select_related('remitente', 'receptor').order_by('fecha_envio')
    
    # Marcar leídos solo de este contexto
    mensajes_chat.filter(receptor=request.user, leido=False).update(leido=True)

    if request.method == 'POST':
        try:
            services.enviar_mensaje(
                remitente=request.user,
                receptor=receptor,
                contenido=request.POST.get('contenido'),
                proyecto=proyecto,
                titulo=f"Chat: {proyecto.titulo if proyecto else 'General'}",
            )
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
        except Exception as e:
            messages.error(request, f"Error al enviar: {e}")

        return redirect('sala_chat', receptor_id=receptor_id, proyecto_id=proyecto_id if proyecto_id else 0)
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
    """Bandeja de entrada: mensajes directos recibidos (con receptor != None) con paginación"""
    mensajes_recibidos = Mensaje.objects.filter(
        receptor=request.user
    ).select_related('remitente', 'proyecto').order_by('-fecha_envio')
    
    paginator = Paginator(mensajes_recibidos, 20)
    page_number = request.GET.get('page')
    mensajes = paginator.get_page(page_number)
    
    return render(request, 'mensajes/inbox.html', {
        'mensajes': mensajes
    })


@login_required
def mensajeria_sent(request):
    """Mensajes enviados directamente (con receptor != None) con paginación"""
    mensajes_enviados = Mensaje.objects.filter(
        remitente=request.user,
        receptor__isnull=False
    ).select_related('receptor', 'proyecto').order_by('-fecha_envio')
    
    paginator = Paginator(mensajes_enviados, 20)
    page_number = request.GET.get('page')
    mensajes = paginator.get_page(page_number)
    
    return render(request, 'mensajes/sent.html', {
        'mensajes': mensajes
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
        elif len(contenido) > 2000:
            messages.error(request, 'El contenido del mensaje no puede superar los 2000 caracteres.')
        elif len(titulo) > 200:
            messages.error(request, 'El título del mensaje no puede superar los 200 caracteres.')
        else:
            try:
                receptor = get_object_or_404(Usuario, id=receptor_id)
                proyecto = Proyecto.objects.filter(id=proyecto_id).first() if proyecto_id else None

                if not puede_comunicarse(request.user, receptor, proyecto):
                    messages.error(request, 'No tienes autorización para comunicarte con este usuario o proyecto.')
                    return redirect('mensajeria_redactar')

                services.enviar_mensaje(
                    remitente=request.user,
                    receptor=receptor,
                    contenido=contenido,
                    proyecto=proyecto,
                    titulo=titulo or f'Mensaje de {request.user.nombre or request.user.username}',
                )

                messages.success(request, f'Mensaje enviado a {receptor.nombre or receptor.username}.')
                return redirect('mensajeria_sent')
            except PermissionDenied as exc:
                messages.error(request, str(exc))
            except ValidationError as exc:
                messages.error(request, ' '.join(exc.messages))
            except Exception as e:
                messages.error(request, f'Error al enviar el mensaje: {e}')

    def _safe_int(val, default=0):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    return render(request, 'mensajes/redactar.html', {
        'usuarios': usuarios_disponibles,
        'proyectos': proyectos_disponibles,
        'para_id': _safe_int(request.GET.get('para', 0)),
        'proyecto_pre': _safe_int(request.GET.get('proyecto', 0)),
    })


@login_required
def ver_mensaje(request, mensaje_id):
    """Ver el detalle de un mensaje. Solo el remitente o receptor pueden verlo."""
    mensaje = get_object_or_404(
        Mensaje,
        id=mensaje_id
    )
    # Control de acceso: solo emisor o receptor pueden ver el mensaje
    if not puede_ver_mensaje(request.user, mensaje):
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


# =============================================
#  API JSON PARA EL CHAT EMBEBIDO (panel tipo WhatsApp)
# =============================================

def _nombre_usuario(usuario):
    """Nombre visible de un usuario, con fallback al username."""
    if usuario is None:
        return 'Usuario eliminado'
    return usuario.nombre or usuario.username


def _serializar_mensaje(mensaje, usuario):
    """Representación JSON mínima de un mensaje para el chat embebido."""
    fecha_local = timezone.localtime(mensaje.fecha_envio)
    return {
        'id': mensaje.id,
        'contenido': mensaje.contenido,
        'hora': fecha_local.strftime('%H:%M'),
        'fecha': fecha_local.strftime('%d/%m/%Y'),
        'iso': mensaje.fecha_envio.isoformat(),
        'es_propio': mensaje.remitente_id == usuario.id,
        'remitente_id': mensaje.remitente_id,
        'remitente_nombre': _nombre_usuario(mensaje.remitente),
    }


def _grupo_chat_directo(usuario_id, receptor_id, proyecto):
    """Mismo nombre de grupo que usa ChatDirectoConsumer."""
    ids = sorted([int(usuario_id), int(receptor_id)])
    sufijo = f'_proy_{proyecto.id}' if proyecto is not None else '_general'
    return f'chat_directo_{ids[0]}_{ids[1]}{sufijo}'


def _payload_mensaje_directo(mensaje, proyecto):
    """Payload neutro para el broadcast: el cliente calcula es_propio."""
    fecha_local = timezone.localtime(mensaje.fecha_envio)
    return {
        'id': mensaje.id,
        'remitente_id': mensaje.remitente_id,
        'remitente_nombre': _nombre_usuario(mensaje.remitente),
        'remitente_rol': mensaje.remitente.rol,
        'receptor_id': mensaje.receptor_id,
        'proyecto_id': proyecto.id if proyecto is not None else None,
        'contenido': mensaje.contenido,
        'fecha_envio': fecha_local.strftime('%H:%M'),
        'fecha': fecha_local.strftime('%d/%m/%Y'),
        'es_grupal': False,
    }


def _emitir_mensaje_directo(mensaje, proyecto):
    """Emite por Channels un mensaje guardado por el fallback HTTP.

    El mensaje ya está persistido; si el channel layer falla, la petición
    HTTP no debe fallar. Solo se registra el problema para diagnóstico.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning(
            'Channel layer no configurado; no se emitió el mensaje %s.',
            mensaje.id,
        )
        return

    try:
        async_to_sync(channel_layer.group_send)(
            _grupo_chat_directo(
                mensaje.remitente_id, mensaje.receptor_id, proyecto
            ),
            {
                'type': 'chat.message',
                'mensaje': _payload_mensaje_directo(mensaje, proyecto),
            },
        )
    except Exception:
        logger.exception(
            'No se pudo emitir el mensaje %s por Channels.', mensaje.id
        )


def _mensajes_de_conversacion(usuario, receptor, proyecto):
    """Mensajes 1:1 entre dos usuarios, aislados por proyecto (RF 6.1.3)."""
    qs = Mensaje.objects.filter(
        Q(remitente=usuario, receptor=receptor)
        | Q(remitente=receptor, receptor=usuario)
    )
    if proyecto is not None:
        return qs.filter(proyecto=proyecto)
    return qs.filter(proyecto__isnull=True)


def _json_error(mensaje, status):
    return JsonResponse({'error': mensaje}, status=status)


@login_required
def api_conversacion(request, receptor_id, proyecto_id=0):
    """Historial de una conversación 1:1 en JSON para el panel embebido."""
    receptor = Usuario.objects.filter(id=receptor_id).first()
    if receptor is None:
        return _json_error('El destinatario no existe.', 404)

    proyecto = None
    if proyecto_id:
        proyecto = Proyecto.objects.filter(id=proyecto_id).first()
        if proyecto is None:
            return _json_error('El proyecto no existe.', 404)

    if receptor.id == request.user.id:
        return _json_error('No puedes abrir una conversación contigo mismo.', 400)

    if not puede_comunicarse(request.user, receptor, proyecto):
        return _json_error('No tienes autorización para esta conversación.', 403)

    mensajes_qs = _mensajes_de_conversacion(
        request.user, receptor, proyecto
    ).select_related('remitente').order_by('fecha_envio')

    # Marcar como leídos solo los mensajes de este contexto
    mensajes_qs.filter(receptor=request.user, leido=False).update(leido=True)

    return JsonResponse({
        'yo_id': request.user.id,
        'receptor': {
            'id': receptor.id,
            'nombre': _nombre_usuario(receptor),
            'username': receptor.username,
            'rol': receptor.get_rol_display(),
            'inicial': _nombre_usuario(receptor)[:1].upper(),
        },
        'proyecto': {
            'id': proyecto.id,
            'titulo': proyecto.titulo,
            'estado': proyecto.estado,
        } if proyecto else None,
        'puede_escribir': not (proyecto is not None and proyecto.estado == 'finalizado'),
        'mensajes': [_serializar_mensaje(m, request.user) for m in mensajes_qs],
    })


@login_required
@require_POST
def api_enviar(request):
    """Envía un mensaje 1:1 desde el panel embebido y devuelve el mensaje creado."""
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return _json_error('JSON inválido.', 400)

    if not isinstance(payload, dict):
        return _json_error('JSON inválido.', 400)

    receptor_id = payload.get('receptor_id')
    proyecto_id = payload.get('proyecto_id') or 0
    contenido = payload.get('contenido', '')

    if not receptor_id:
        return _json_error('Falta el destinatario.', 400)

    receptor = Usuario.objects.filter(id=receptor_id).first()
    if receptor is None:
        return _json_error('El destinatario no existe.', 404)

    proyecto = None
    if proyecto_id:
        proyecto = Proyecto.objects.filter(id=proyecto_id).first()
        if proyecto is None:
            return _json_error('El proyecto no existe.', 404)

    try:
        mensaje = services.enviar_mensaje(
            remitente=request.user,
            receptor=receptor,
            contenido=contenido,
            proyecto=proyecto,
            titulo=f"Chat: {proyecto.titulo if proyecto else 'General'}",
        )
    except PermissionDenied as exc:
        return _json_error(str(exc), 403)
    except ValidationError as exc:
        return _json_error(' '.join(exc.messages), 400)

    _emitir_mensaje_directo(mensaje, proyecto)

    return JsonResponse(
        {'mensaje': _serializar_mensaje(mensaje, request.user)}, status=201
    )
