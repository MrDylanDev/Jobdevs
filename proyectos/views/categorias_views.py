import json

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify

from logs.models import LogAuditoria
from usuarios.decorators import api_ratelimit

from ..models import CategoriaSolucion

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
        return JsonResponse(
            {'error': 'El nombre no puede superar 100 caracteres.'}, status=400
        )

    slug = slugify(str(data.get('slug') or '').strip() or nombre)[:50]
    if not slug:
        return JsonResponse({'error': 'No se pudo generar un slug válido.'}, status=400)

    descripcion = str(data.get('descripcion') or '').strip()
    activo = data.get('activo', True)
    if not isinstance(activo, bool):
        return JsonResponse(
            {'error': 'El campo activo debe ser booleano.'}, status=400
        )

    if CategoriaSolucion.objects.filter(nombre__iexact=nombre).exists():
        return JsonResponse(
            {'error': 'Ya existe una categoría con ese nombre.'}, status=409
        )
    if CategoriaSolucion.objects.filter(slug=slug).exists():
        return JsonResponse(
            {'error': 'Ya existe una categoría con ese slug.'}, status=409
        )

    try:
        with transaction.atomic():
            categoria = CategoriaSolucion.objects.create(
                nombre=nombre,
                slug=slug,
                descripcion=descripcion,
                activo=activo,
            )
            _log_categoria(
                request,
                categoria,
                f"Creó categoría de solución {categoria.nombre} ({categoria.slug})",
            )
    except IntegrityError:
        return JsonResponse(
            {'error': 'Ya existe una categoría con ese nombre o slug.'}, status=409
        )

    return JsonResponse(_categoria_to_dict(categoria, 0), status=201)


@login_required
@api_ratelimit(max_requests=30, window_seconds=60)
def api_categoria_actualizar(request, categoria_id):
    if request.user.rol != 'administrador':
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)
    if request.method not in ('PUT', 'POST'):
        return JsonResponse(
            {'error': 'Método no permitido. Use PUT o POST.'}, status=405
        )

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
            return JsonResponse(
                {'error': 'El nombre no puede superar 100 caracteres.'}, status=400
            )
        if (
            CategoriaSolucion.objects.filter(nombre__iexact=nombre)
            .exclude(pk=categoria.pk)
            .exists()
        ):
            return JsonResponse(
                {'error': 'Ya existe una categoría con ese nombre.'}, status=409
            )
        categoria.nombre = nombre
        campos.append('nombre')
    if 'descripcion' in data:
        categoria.descripcion = str(data.get('descripcion') or '').strip()
        campos.append('descripcion')
    if 'activo' in data:
        if not isinstance(data['activo'], bool):
            return JsonResponse(
                {'error': 'El campo activo debe ser booleano.'}, status=400
            )
        categoria.activo = data['activo']
        campos.append('activo')

    try:
        with transaction.atomic():
            categoria.save()
            _log_categoria(
                request,
                categoria,
                f"Actualizó categoría de solución {categoria.slug}: {', '.join(campos) or 'sin cambios'}",
            )
    except IntegrityError:
        return JsonResponse(
            {'error': 'Ya existe una categoría con ese nombre.'}, status=409
        )

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
            request,
            categoria,
            f"{'Activó' if categoria.activo else 'Desactivó'} categoría de solución {categoria.slug}",
        )
    return JsonResponse(_categoria_to_dict(categoria), status=200)
