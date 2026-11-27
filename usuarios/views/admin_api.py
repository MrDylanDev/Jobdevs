import csv
import json
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.core.cache import cache
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from ..models import Usuario
from ..decorators import api_ratelimit
from ..utils import invalidar_sesiones_activas_usuario
from logs.models import LogAuditoria


def invalidar_cache_administradores():
    """RNF-21: mantiene coherente la caché de administradores ante cualquier alta, baja o cambio de rol.

    Un solo punto para las tres rutas (crear, actualizar, eliminar) evita que se
    repita el defecto de SCRUM-397: crear y actualizar invalidaban, eliminar no.
    """
    cache.delete('admin_id')
    cache.delete('admin_ids_list')


@login_required
@api_ratelimit(max_requests=60, window_seconds=60)
def api_usuarios(request):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado. Solo administradores pueden listar usuarios.'}, status=403)

    q = request.GET.get('q', '').strip()
    rol = request.GET.get('rol', '').strip()
    estado = request.GET.get('estado', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

    qs = Usuario.objects.all()
    if q:
        qs = qs.filter(
            Q(username__icontains=q) |
            Q(nombre__icontains=q) |
            Q(email__icontains=q) |
            Q(identificacion__icontains=q)
        )
    if rol:
        qs = qs.filter(rol=rol)
    if estado:
        qs = qs.filter(estado=estado)

    # SCRUM-226 (RF 1.3.3): filtro por rango de fecha de registro.
    fecha_desde_parsed = parse_date(fecha_desde) if fecha_desde else None
    fecha_hasta_parsed = parse_date(fecha_hasta) if fecha_hasta else None
    if fecha_desde_parsed:
        qs = qs.filter(date_joined__date__gte=fecha_desde_parsed)
    if fecha_hasta_parsed:
        qs = qs.filter(date_joined__date__lte=fecha_hasta_parsed)

    limit = request.GET.get('limit')
    page = request.GET.get('page')
    if limit or page:
        try:
            limit_val = int(limit) if limit else 25
            page_val = int(page) if page else 1
            if limit_val <= 0 or page_val <= 0:
                return JsonResponse({'error': 'Los parámetros limit y page deben ser enteros positivos.'}, status=400)
            limit_val = min(limit_val, 200)
            paginator = Paginator(qs.order_by('-date_joined', '-id'), limit_val)
            page_obj = paginator.get_page(page_val)
            return JsonResponse({
                'total': paginator.count,
                'total_pages': paginator.num_pages,
                'page': page_obj.number,
                'usuarios': list(page_obj.object_list.values('id', 'username', 'nombre', 'email', 'rol', 'identificacion', 'estado', 'date_joined'))
            })
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Parámetros de paginación inválidos.'}, status=400)

    usuarios = list(qs.order_by('-date_joined', '-id').values('id', 'username', 'nombre', 'email', 'rol', 'identificacion', 'estado', 'date_joined'))
    return JsonResponse(usuarios, safe=False)


@login_required
@api_ratelimit(max_requests=60, window_seconds=60)
def api_usuario_detalle(request, usuario_id):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)
    
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    user = get_object_or_404(Usuario, id=usuario_id)
    return JsonResponse({
        'id': user.id, 
        'username': user.username, 
        'nombre': user.nombre,
        'email': user.email, 
        'rol': user.rol,
        'identificacion': user.identificacion,
        'estado': user.estado
    })


@login_required
@api_ratelimit(max_requests=30, window_seconds=60)
def api_crear_usuario(request):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido. Use POST.'}, status=405)

    try:
        data = json.loads(request.body)
        required = ['username', 'email', 'password', 'rol']
        if not all(k in data for k in required):
            return JsonResponse({'error': f'Faltan campos requeridos: {required}'}, status=400)

        nombre = (data.get('nombre') or '').strip()
        identificacion = (data.get('identificacion') or '').strip()
        tipo_doc = (data.get('tipo_documento') or '').strip().lower()

        if identificacion:
            from ..utils_dian import validar_documento_identidad
            if tipo_doc:
                doc_type = tipo_doc
            elif data['rol'] == 'empresa' and '-' in identificacion:
                doc_type = 'nit'
            else:
                doc_type = 'cedula'
            try:
                identificacion = validar_documento_identidad(identificacion, doc_type)
            except ValueError as exc:
                return JsonResponse({'error': str(exc)}, status=400)

        with transaction.atomic():
            extra = {}
            if nombre:
                extra['nombre'] = nombre
            if identificacion:
                extra['identificacion'] = identificacion

            user = Usuario.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                rol=data['rol'],
                **extra,
            )

            if user.rol == 'desarrollador':
                from ..models import PerfilDesarrollador
                PerfilDesarrollador.objects.get_or_create(usuario=user)
            elif user.rol == 'empresa':
                from ..models import PerfilEmpresa
                PerfilEmpresa.objects.get_or_create(
                    usuario=user,
                    defaults={'nombre_empresa': nombre or user.username},
                )
        
        if user.rol == 'administrador':
            invalidar_cache_administradores()
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f'Creó el usuario {user.username}',
            tabla_afectada='usuarios',
            registro_id=user.id,
            valor_nuevo=f'email={user.email}; rol={user.rol}; estado={user.estado}',
        )
            
        return JsonResponse({'id': user.id, 'status': 'created'}, status=201)
    except IntegrityError:
        return JsonResponse({'error': 'El nombre de usuario o email ya existe.'}, status=409)
    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': f'Datos JSON inválidos: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)


@login_required
@api_ratelimit(max_requests=30, window_seconds=60)
def api_actualizar_usuario(request, usuario_id):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)
    
    if request.method != 'PUT':
        return JsonResponse({'error': 'Método no permitido. Use PUT.'}, status=405)

    try:
        data = json.loads(request.body)
        user = get_object_or_404(Usuario, id=usuario_id)
        if user.id == request.user.id:
            return JsonResponse({'error': 'No puedes editar tu propia cuenta desde el directorio.'}, status=403)
        if user.rol == 'administrador':
            return JsonResponse({'error': 'No puedes editar la cuenta de otro administrador.'}, status=403)
        valores_anteriores = {
            campo: getattr(user, campo)
            for campo in ('email', 'nombre', 'rol', 'estado', 'identificacion')
        }
        
        rol_anterior = user.rol
        if 'email' in data: user.email = data['email']
        if 'nombre' in data: user.nombre = data['nombre']
        if 'rol' in data: user.rol = data['rol']
        if 'estado' in data:
            user.estado = data['estado']
            user.is_active = (user.estado == 'activo')
            if not user.is_active or user.estado in ('inactivo', 'suspendido'):
                user.bloqueado_por_intentos = False
                invalidar_sesiones_activas_usuario(user.id)
            elif user.is_active and user.estado == 'activo':
                user.intentos_fallidos = 0
                user.bloqueado_por_intentos = False

        identificacion = (data.get('identificacion') or '').strip()
        if identificacion:
            from ..utils_dian import validar_documento_identidad
            tipo_doc_raw = (data.get('tipo_documento') or '').strip().lower()
            if tipo_doc_raw:
                tipo_doc = tipo_doc_raw
            elif user.rol == 'empresa' and '-' in identificacion:
                tipo_doc = 'nit'
            else:
                tipo_doc = 'cedula'
            try:
                ident_limpia = validar_documento_identidad(identificacion, tipo_doc)
            except ValueError as e:
                return JsonResponse({'error': str(e)}, status=400)

            if Usuario.objects.filter(identificacion=ident_limpia).exclude(id=user.id).exists():
                return JsonResponse({'error': 'Ya existe otro usuario con esa identificación.'}, status=400)
            user.identificacion = ident_limpia
        
        user.save()

        campos_modificados = [k for k in data if k in ('email', 'nombre', 'rol', 'estado')]
        if identificacion:
            campos_modificados.append('identificacion')
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f"Actualizó usuario {user.username}: {', '.join(campos_modificados)}",
            tabla_afectada='usuarios',
            registro_id=user.id,
            valor_anterior='; '.join(
                f'{campo}={valores_anteriores[campo]}' for campo in campos_modificados
            ),
            valor_nuevo='; '.join(
                f'{campo}={getattr(user, campo)}' for campo in campos_modificados
            ),
        )

        if rol_anterior == 'administrador' or user.rol == 'administrador':
            invalidar_cache_administradores()

        return JsonResponse({'status': 'updated'})
    except IntegrityError:
        return JsonResponse({'error': 'El email ya está en uso por otro usuario.'}, status=409)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Formato JSON inválido.'}, status=400)


@login_required
@api_ratelimit(max_requests=30, window_seconds=60)
def api_eliminar_usuario(request, usuario_id):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)
    
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Método no permitido. Use DELETE.'}, status=405)

    user = get_object_or_404(Usuario, id=usuario_id)
    if user.id == request.user.id:
        return JsonResponse({'error': 'No puedes eliminarte a ti mismo.'}, status=400)
    if user.rol == 'administrador':
        return JsonResponse({'error': 'No puedes eliminar la cuenta de otro administrador.'}, status=403)

    era_administrador = user.rol == 'administrador'
    with transaction.atomic():
        LogAuditoria.objects.create(
            usuario=request.user,
            accion=f'Eliminó el usuario {user.username}',
            tabla_afectada='usuarios',
            registro_id=user.id,
            valor_anterior=f'email={user.email}; rol={user.rol}; estado={user.estado}',
            valor_nuevo='eliminado',
        )
        user.delete()
    if era_administrador:
        invalidar_cache_administradores()
    return JsonResponse({'status': 'deleted'})


@login_required
@api_ratelimit(max_requests=30, window_seconds=60)
def api_bulk_toggle(request):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        action = data.get('action')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    if not ids or action not in ('activate', 'suspend'):
        return JsonResponse({'error': 'Parámetros inválidos.'}, status=400)

    qs_objetivo = Usuario.objects.filter(id__in=ids).exclude(id=request.user.id).exclude(rol='administrador')
    usuarios_objetivo = list(qs_objetivo)
    if action == 'activate':
        Usuario.objects.filter(id__in=[u.id for u in usuarios_objetivo]).update(
            estado='activo', is_active=True, intentos_fallidos=0,
            bloqueado_por_intentos=False,
        )
        nuevo_estado = 'activo'
    else:
        afectados = [u.id for u in usuarios_objetivo]
        Usuario.objects.filter(id__in=afectados).update(estado='suspendido', is_active=False, bloqueado_por_intentos=False)
        invalidar_sesiones_activas_usuario(afectados)
        nuevo_estado = 'suspendido'

    LogAuditoria.objects.bulk_create([
        LogAuditoria(
            usuario=request.user,
            accion=f'Cambio masivo de estado para {usuario.username}',
            tabla_afectada='usuarios',
            registro_id=usuario.id,
            valor_anterior=f'estado={usuario.estado}',
            valor_nuevo=f'estado={nuevo_estado}',
        )
        for usuario in usuarios_objetivo
    ])

    return JsonResponse({'status': 'ok', 'count': len(usuarios_objetivo)})


def _csv_safe(value):
    text = '' if value is None else str(value)
    if text and text[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + text
    return text


@login_required
@api_ratelimit(max_requests=60, window_seconds=60)
def api_auditoria(request):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado. Solo administradores pueden consultar auditoría.'}, status=403)

    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    usuario = request.GET.get('usuario', '').strip()
    tabla = request.GET.get('tabla', '').strip()
    q = request.GET.get('q', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

    qs = LogAuditoria.objects.select_related('usuario').order_by('-fecha_hora', '-id')
    if usuario:
        usuario_q = Q(usuario__username__icontains=usuario) | Q(usuario__nombre__icontains=usuario)
        if usuario.lower() in 'sistema':
            usuario_q |= Q(usuario__isnull=True)
        qs = qs.filter(usuario_q)
    if tabla:
        qs = qs.filter(tabla_afectada__icontains=tabla)
    if q:
        qs = qs.filter(
            Q(accion__icontains=q)
            | Q(valor_anterior__icontains=q)
            | Q(valor_nuevo__icontains=q)
        )

    fecha_desde_parsed = parse_date(fecha_desde) if fecha_desde else None
    fecha_hasta_parsed = parse_date(fecha_hasta) if fecha_hasta else None
    if fecha_desde_parsed:
        qs = qs.filter(fecha_hora__date__gte=fecha_desde_parsed)
    if fecha_hasta_parsed:
        qs = qs.filter(fecha_hora__date__lte=fecha_hasta_parsed)

    if request.GET.get('export', '').strip().lower() == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="auditoria.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['ID', 'Usuario', 'Acción', 'Tabla', 'Registro ID', 'Valor Anterior', 'Valor Nuevo', 'Fecha y Hora'])
        for log in qs[:5000]:
            writer.writerow([
                log.id,
                _csv_safe(log.usuario.username if log.usuario else 'Sistema'),
                _csv_safe(log.accion),
                _csv_safe(log.tabla_afectada or ''),
                '' if log.registro_id is None else log.registro_id,
                _csv_safe(log.valor_anterior or ''),
                _csv_safe(log.valor_nuevo or ''),
                log.fecha_hora.strftime('%Y-%m-%d %H:%M:%S') if log.fecha_hora else '',
            ])
        return response

    try:
        limit_val = int(request.GET.get('limit', 25))
        page_val = int(request.GET.get('page', 1))
        if limit_val <= 0 or page_val <= 0:
            return JsonResponse({'error': 'Los parámetros limit y page deben ser enteros positivos.'}, status=400)
        limit_val = min(limit_val, 100)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Parámetros de paginación inválidos.'}, status=400)

    paginator = Paginator(qs, limit_val)
    page_obj = paginator.get_page(page_val)
    tablas = list(
        LogAuditoria.objects.exclude(tabla_afectada__isnull=True)
        .exclude(tabla_afectada='')
        .values_list('tabla_afectada', flat=True)
        .distinct()
        .order_by('tabla_afectada')
    )

    es_htmx = (
        request.headers.get('HX-Request') == 'true'
        and request.GET.get('format') != 'json'
        and 'application/json' not in request.headers.get('Accept', '')
    )
    if es_htmx:
        return render(request, 'administrador/partials/_tabla_auditoria_logs.html', {
            'logs': page_obj,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total': paginator.count,
            'tablas': tablas,
        })

    logs = [
        {
            'id': log.id,
            'usuario': log.usuario.username if log.usuario else 'Sistema',
            'accion': log.accion,
            'tabla_afectada': log.tabla_afectada or '',
            'registro_id': log.registro_id,
            'valor_anterior': log.valor_anterior or '',
            'valor_nuevo': log.valor_nuevo or '',
            'fecha_hora': log.fecha_hora.isoformat() if log.fecha_hora else '',
        }
        for log in page_obj.object_list
    ]

    return JsonResponse({
        'total': paginator.count,
        'total_pages': paginator.num_pages,
        'page': page_obj.number,
        'tablas': tablas,
        'logs': logs,
    })
