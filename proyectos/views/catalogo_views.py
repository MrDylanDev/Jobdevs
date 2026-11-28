from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import (
    Avg,
    Count,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views.decorators.http import require_http_methods

from contrataciones.models import Contratacion
from favoritos.models import Favorito
from postulaciones.models import Postulacion

from ..models import CategoriaSolucion, Proyecto


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
        .values('proyecto')
        .annotate(total=Count('*'))
        .values('total')
    )
    negociaciones_sq = (
        Postulacion.objects.filter(proyecto=OuterRef('pk'), estado='en_negociacion')
        .values('proyecto')
        .annotate(total=Count('*'))
        .values('total')
    )

    proyectos_qs = (
        Proyecto.objects.select_related('empresa__perfil_empresa')
        .annotate(
            # Hallazgo 10: distinct=True para evitar conteos inflados por joins adicionales
            num_postulaciones=Count('postulaciones', distinct=True),
            empresa_reputacion=Coalesce(
                Avg(
                    'empresa__valoraciones_como_empresa__puntuacion',
                    filter=Q(
                        empresa__valoraciones_como_empresa__rol_evaluador='desarrollador'
                    ),
                ),
                Value(0.0),
                output_field=FloatField(),
            ),
            contratos_activos=Coalesce(
                Subquery(contratos_activos_sq, output_field=IntegerField()), Value(0)
            ),
            negociaciones_abiertas=Coalesce(
                Subquery(negociaciones_sq, output_field=IntegerField()), Value(0)
            ),
        )
        .annotate(
            disponibles_anotadas=F('vacantes')
            - F('contratos_activos')
            - F('negociaciones_abiertas'),
        )
        .filter(
            # Excepción de producto: también en desarrollo, pero nunca sin cupo libre.
            Q(estado__in=('publicado', 'en_desarrollo')),
            Q(disponibles_anotadas__gt=0),
            (Q(fecha_limite__isnull=True) | Q(fecha_limite__gte=timezone.now().date())),
        )
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
        postulaciones_ids = Postulacion.objects.filter(
            desarrollador=request.user
        ).values_list('proyecto_id', flat=True)
        proyectos_qs = proyectos_qs.exclude(id__in=postulaciones_ids)
        favoritos_ids = list(
            Favorito.objects.filter(desarrollador=request.user).values_list(
                'proyecto_id', flat=True
            )
        )

    paginator = Paginator(proyectos_qs.order_by('-fecha_publicacion'), 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    proyectos = []
    for p in page_obj:
        logo = (
            p.empresa.perfil_empresa.logo.url
            if (hasattr(p.empresa, 'perfil_empresa') and p.empresa.perfil_empresa.logo)
            else None
        )
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
            'empresa_estado_verificacion': (
                perfil.estado_verificacion if perfil else 'sin_verificar'
            ),
            'vacantes': p.vacantes,
            'vacantes_disponibles': p.vacantes_disponibles,
            'modalidad': p.modalidad,
            'ciudad': p.ciudad,
            'ubicacion_display': p.ubicacion_display,
        })

    wants_json = (
        'application/json' in (request.headers.get('Accept') or '')
        or request.GET.get('format') == 'json'
    )
    is_htmx = request.headers.get('HX-Request') == 'true' and not wants_json
    is_ajax = wants_json or (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' and not is_htmx
    )
    if is_ajax:
        proyectos_json = []
        for p in proyectos:
            item = dict(p)
            if item.get('fecha_publicacion'):
                item['fecha_publicacion'] = item['fecha_publicacion'].strftime(
                    '%d/%m/%Y'
                )
            item['empresa_url'] = reverse('detalle_empresa', args=[p['empresa_id']])
            item['postular_url'] = reverse('postularse_a_proyecto', args=[p['id']])
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

    context = {
        'proyectos': proyectos,
        'page_obj': page_obj,
        'favoritos_ids': favoritos_ids,
    }
    if is_htmx:
        clean_params = []
        if q:
            clean_params.append(('q', q))
        if tipo:
            clean_params.append(('tipo', tipo))
        if prioridad:
            clean_params.append(('prioridad', prioridad))
        if modalidad:
            clean_params.append(('modalidad', modalidad))
        if ciudad:
            clean_params.append(('ciudad', ciudad))
        if page_obj.number > 1:
            clean_params.append(('page', str(page_obj.number)))
        base_url = reverse('listar_proyectos')
        clean_url = f"{base_url}?{urlencode(clean_params)}" if clean_params else base_url
        response = render(
            request, 'proyectos/partials/_catalogo_resultados.html', context
        )
        response['HX-Replace-Url'] = clean_url
        return response

    context['categorias_solucion'] = CategoriaSolucion.objects.filter(activo=True)
    return render(request, 'proyectos/listar.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Detalle de proyecto en modal (dashboards de admin, empresa y desarrollador)
# ─────────────────────────────────────────────────────────────────────────────


@login_required
@require_http_methods(["GET"])
def api_detalle_proyecto(request, proyecto_id):
    """Ficha completa de un proyecto para el modal compartido de los dashboards.

    Mantiene los mismos permisos que ``avances.views.ver_avances``: admin,
    empresa dueña y desarrollador vinculado por contrato o postulación. El
    frontend solo pinta la respuesta; las acciones se resuelven aquí para no
    duplicar reglas de negocio en JavaScript.
    """
    proyecto = get_object_or_404(
        Proyecto.objects.select_related('empresa__perfil_empresa', 'categoria'),
        id=proyecto_id,
    )
    user = request.user
    es_admin = user.rol == 'administrador'
    es_empresa = user.rol == 'empresa' and proyecto.empresa_id == user.id
    esta_contratado = Contratacion.objects.filter(
        proyecto=proyecto, desarrollador=user
    ).exists()
    tiene_postulacion = Postulacion.objects.filter(
        proyecto=proyecto, desarrollador=user
    ).exists()
    es_publicado = proyecto.estado == 'publicado'

    wants_htmx = (
        request.headers.get('HX-Request') == 'true'
        and 'application/json' not in request.headers.get('Accept', '')
        and request.GET.get('format') != 'json'
    )

    es_dev = user.rol == 'desarrollador' and (
        esta_contratado or tiene_postulacion or es_publicado
    )
    if not (es_admin or es_empresa or es_dev):
        if wants_htmx:
            return render(
                request,
                'proyectos/partials/_modal_detalle_proyecto.html',
                {'error_mensaje': 'No tienes permisos para ver este proyecto.'},
                status=403,
            )
        return JsonResponse(
            {'ok': False, 'mensaje': 'No tienes permisos para ver este proyecto.'},
            status=403,
        )

    hitos_qs = proyecto.entregables.order_by('fecha_creacion')
    hitos = [
        {
            'id': h.id,
            'titulo': h.titulo,
            'descripcion': h.descripcion or '',
            'estado': h.estado,
            'estado_label': h.get_estado_display(),
        }
        for h in hitos_qs
    ]
    total_hitos = len(hitos)
    completados = sum(1 for h in hitos if h['estado'] == 'completado')
    progreso = round((completados / total_hitos) * 100) if total_hitos else 0

    contrataciones_qs = proyecto.contrataciones.select_related(
        'desarrollador'
    ).order_by('fecha_inicio')
    if es_admin or es_empresa or esta_contratado:
        contrataciones = [
            {
                'id': c.id,
                'desarrollador': c.desarrollador.nombre or c.desarrollador.username,
                'username': c.desarrollador.username,
                'estado': c.estado,
                'estado_label': c.get_estado_display(),
            }
            for c in contrataciones_qs
        ]
    else:
        contrataciones = []
    num_desarrolladores = contrataciones_qs.count()

    perfil_empresa = getattr(proyecto.empresa, 'perfil_empresa', None)
    badge = perfil_empresa.badge_info if perfil_empresa else None
    empresa_nombre = (
        (perfil_empresa.nombre_empresa if perfil_empresa else '')
        or proyecto.empresa.nombre
        or proyecto.empresa.username
    )

    acciones = []
    if es_admin:
        acciones.append({
            'label': 'Gestionar avances',
            'url': reverse('ver_avances', args=[proyecto.id]),
            'icono': 'git-branch',
            'estilo': 'primary',
        })
        acciones.append({
            'label': 'Gestionar hitos',
            'url': reverse('gestionar_hitos', args=[proyecto.id]),
            'icono': 'list-checks',
            'estilo': 'secondary',
        })
        acciones.append({
            'label': 'Ver empresa',
            'url': reverse('detalle_empresa', args=[proyecto.empresa_id]),
            'icono': 'building',
            'estilo': 'secondary',
        })
    elif es_empresa:
        acciones.append({
            'label': 'Ver avances',
            'url': reverse('ver_avances', args=[proyecto.id]),
            'icono': 'git-branch',
            'estilo': 'primary',
        })
        acciones.append({
            'label': 'Gestionar hitos',
            'url': reverse('gestionar_hitos', args=[proyecto.id]),
            'icono': 'list-checks',
            'estilo': 'secondary',
        })
        if proyecto.vacantes_disponibles > 0 and proyecto.acepta_postulaciones:
            acciones.append({
                'label': 'Ver candidatos',
                'url': reverse('ver_postulaciones_empresa', args=[proyecto.id]),
                'icono': 'user-plus',
                'estilo': 'secondary',
            })
    else:
        # Desarrollador
        if esta_contratado:
            acciones.append({
                'label': 'Ver historial completo',
                'url': reverse('ver_avances', args=[proyecto.id]),
                'icono': 'git-branch',
                'estilo': 'primary',
            })
            if proyecto.estado == 'en_desarrollo':
                acciones.append({
                    'label': 'Registrar avance',
                    'url': reverse('registrar_avance', args=[proyecto.id]),
                    'icono': 'pen',
                    'estilo': 'secondary',
                })
        elif tiene_postulacion:
            acciones.append({
                'label': 'Ver mi postulación',
                'url': reverse('dashboard_desarrollador') + '#postulaciones',
                'icono': 'send',
                'estilo': 'secondary',
            })
        elif (
            es_publicado
            and proyecto.acepta_postulaciones
            and proyecto.vacantes_disponibles > 0
        ):
            acciones.append({
                'label': 'Postularme',
                'url': reverse('postularse_a_proyecto', args=[proyecto.id]),
                'icono': 'send',
                'estilo': 'primary',
            })

    if num_desarrolladores >= 2 and (es_admin or es_empresa or esta_contratado):
        acciones.append({
            'label': 'Chat grupal',
            'url': reverse('sala_chat_grupal', args=[proyecto.id]),
            'icono': 'users',
            'estilo': 'secondary',
        })

    payload = {
        'ok': True,
        'proyecto': {
            'id': proyecto.id,
            'titulo': proyecto.titulo,
            'descripcion': proyecto.descripcion,
            'estado': proyecto.estado,
            'estado_label': proyecto.get_estado_display(),
            'tipo': proyecto.get_tipo_solucion_display(),
            'prioridad': proyecto.prioridad,
            'prioridad_label': proyecto.get_prioridad_display(),
            'modalidad': proyecto.modalidad,
            'modalidad_label': proyecto.get_modalidad_display(),
            'ciudad': proyecto.ciudad or '',
            'ubicacion_display': proyecto.ubicacion_display,
            'vacantes': proyecto.vacantes,
            'vacantes_disponibles': proyecto.vacantes_disponibles,
            'fecha_publicacion': date_format(proyecto.fecha_publicacion, 'd M Y'),
            'fecha_limite': (
                date_format(proyecto.fecha_limite, 'd M Y')
                if proyecto.fecha_limite
                else 'Sin límite'
            ),
            'categoria': proyecto.categoria.nombre if proyecto.categoria_id else '',
            'empresa': {
                'id': proyecto.empresa_id,
                'nombre': empresa_nombre,
                'verificada': bool(perfil_empresa and perfil_empresa.es_verificada),
                'badge': badge['label'] if badge else '',
                'calificacion': (
                    float(perfil_empresa.calificacion_promedio or 0)
                    if perfil_empresa
                    else 0
                ),
            },
            'hitos': hitos,
            'hitos_completados': completados,
            'hitos_totales': total_hitos,
            'progreso': progreso,
            'contrataciones': contrataciones,
            'num_desarrolladores': num_desarrolladores,
            'acepta_postulaciones': proyecto.acepta_postulaciones,
        },
        'acciones': acciones,
    }
    if wants_htmx:
        return render(
            request, 'proyectos/partials/_modal_detalle_proyecto.html', payload
        )
    return JsonResponse(payload)
