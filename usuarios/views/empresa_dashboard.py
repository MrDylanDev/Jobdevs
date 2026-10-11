from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q, Count, Prefetch
from ..models import Usuario, PerfilEmpresa
from ..decorators import requiere_usuario_activo
from ..utils import get_admin_id
from proyectos.models import Proyecto, Valoracion, CategoriaSolucion
from postulaciones.models import Postulacion
from contrataciones.models import Contratacion
from ._helpers import get_notificaciones_context


@login_required
@requiere_usuario_activo
def dashboard_empresa(request):
    if request.user.rol != 'empresa': return redirect('inicio')
    
    p_pub = Proyecto.objects.filter(empresa=request.user, estado='publicado').count()
    p_act = Proyecto.objects.filter(empresa=request.user, estado='en_desarrollo').count()
    dev_con = Contratacion.objects.filter(empresa=request.user, estado='activa').count()

    en_desarrollo_qs = Proyecto.objects.filter(
        empresa=request.user, estado__in=['en_desarrollo', 'en_revision']
    ).annotate(
        hitos_completados=Count('entregables', filter=Q(entregables__estado='completado')),
        hitos_totales=Count('entregables'),
    ).prefetch_related(
        Prefetch('contrataciones',
            queryset=Contratacion.objects.filter(estado='activa').select_related('desarrollador'),
            to_attr='contratos_activos')
    )
    en_desarrollo_v = []
    for p in en_desarrollo_qs:
        dev_ids = [c.desarrollador_id for c in p.contratos_activos]
        dev_nombres = ', '.join([c.desarrollador.nombre for c in p.contratos_activos])
        cupos_comprometidos = len(dev_ids) + Postulacion.objects.filter(proyecto=p, estado='en_negociacion').count()
        vacantes_disponibles = max(0, p.vacantes - cupos_comprometidos) if p.estado == 'en_desarrollo' else 0
        en_desarrollo_v.append({
            'proyecto_id': p.id,
            'titulo': p.titulo,
            'desarrolladores': dev_nombres,
            'hitos_completados': p.hitos_completados,
            'hitos_totales': p.hitos_totales,
            'ultimo_avance': None,
            'fecha_fin': p.fecha_limite,
            'estado': p.estado,
            'ids': ','.join(map(str, dev_ids)),
            'primer_dev_id': dev_ids[0] if dev_ids else None,
            'num_desarrolladores': len(dev_ids),
            'vacantes_totales': p.vacantes,
            'vacantes_disponibles': vacantes_disponibles,
        })
    perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=request.user)
    mis_ofertas = Proyecto.objects.filter(empresa=request.user, estado='publicado').order_by('-fecha_publicacion')
    
    postulaciones_pendientes_obj = Postulacion.objects.filter(
        proyecto__empresa=request.user, 
        estado='pendiente',
        proyecto__estado__in=['publicado', 'en_desarrollo']
    )
    post_pen = postulaciones_pendientes_obj.count()
    admin_id = get_admin_id()

    valoraciones_dev = Valoracion.objects.filter(empresa=request.user, rol_evaluador='desarrollador').select_related('desarrollador', 'proyecto')
    promedio_empresa = valoraciones_dev.aggregate(Avg('puntuacion'))['puntuacion__avg'] or 0

    notificaciones_recientes, notificaciones_pendientes_count = get_notificaciones_context(request.user.id)

    colaboradores_activos = Contratacion.objects.filter(
        empresa=request.user, 
        estado='activa',
        proyecto__estado='en_desarrollo'
    ).select_related('desarrollador__perfil_desarrollador', 'proyecto')

    historial_v = Proyecto.objects.filter(
        empresa=request.user, 
        estado='finalizado'
    ).annotate(num_desarrolladores=Count('contrataciones')).prefetch_related('contrataciones__desarrollador').order_by('-fecha_publicacion')

    context = {
        'total_proyectos': p_pub,
        'proyectos_activos': p_act,
        'total_postulaciones': post_pen,
        'total_contratados': dev_con,
        'mis_ofertas': mis_ofertas,
        'en_desarrollo_v': en_desarrollo_v,
        'colaboradores_activos': colaboradores_activos,
        'historial': historial_v,
        'valoraciones_recibidas': valoraciones_dev,
        'promedio_empresa': round(promedio_empresa, 1),
        'postulaciones_pendientes': postulaciones_pendientes_obj,
        'notificaciones': notificaciones_recientes,
        'notificaciones_pendientes_count': notificaciones_pendientes_count,
        'perfil': perfil,
        'admin_id': admin_id,
        'categorias_solucion': CategoriaSolucion.objects.filter(activo=True),
    }
    return render(request, 'empresa/empresa.html', context)
