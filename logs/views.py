import csv
from collections import deque

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Value, FloatField
from django.db.models.functions import Coalesce
from proyectos.models import Proyecto, Valoracion
from usuarios.models import Usuario, PerfilDesarrollador, PerfilEmpresa
from logs.models import LogAuditoria

@login_required
def reporte_proyectos_csv(request):
    """Generar reporte detallado de proyectos en Excel"""
    if request.user.rol != 'administrador':
        return redirect('inicio')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte_proyectos_tem.csv"'

    writer = csv.writer(response)
    # Encabezados simplificados
    writer.writerow(['Título', 'Empresa', 'Tipo', 'Prioridad', 'Estado', 'Desarrolladores', 'Vacantes Totales', 'Fecha Publicación'])

    # Traemos proyectos con su empresa y calculamos métricas en una sola ráfaga SQL
    proyectos = Proyecto.objects.select_related('empresa', 'categoria').annotate(
        num_devs=Count('contrataciones', filter=Q(contrataciones__estado='activa'))
    ).order_by('-fecha_publicacion')

    for p in proyectos:
        # Intentar obtener nombre comercial de la empresa si existe
        nombre_empresa = getattr(p.empresa, 'perfil_empresa', None)
        empresa_display = nombre_empresa.nombre_empresa if nombre_empresa and nombre_empresa.nombre_empresa else p.empresa.nombre

        writer.writerow([
            p.titulo, 
            empresa_display, 
            p.get_tipo_solucion_display(), 
            p.get_prioridad_display(), 
            p.get_estado_display(), 
            p.num_devs,
            p.vacantes,
            p.fecha_publicacion.strftime('%d/%m/%Y %H:%M')
        ])
    return response

@login_required
def reporte_aprendices_csv(request):
    """Generar reporte de desempeño de aprendices en CSV (SCRUM-177 / sin N+1)"""
    if request.user.rol != 'administrador':
        return redirect('inicio')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte_aprendices_tem.csv"'

    writer = csv.writer(response)
    writer.writerow(['Usuario', 'Nombre', 'Programa', 'Ficha', 'Promedio', 'Proyectos'])

    aprendices = PerfilDesarrollador.objects.select_related('usuario').annotate(
        promedio_estrellas=Coalesce(
            Avg(
                'usuario__valoraciones_como_dev__puntuacion',
                filter=Q(usuario__valoraciones_como_dev__rol_evaluador='empresa')
            ),
            Value(0.0),
            output_field=FloatField()
        )
    ).order_by('usuario__username')

    for a in aprendices:
        writer.writerow([
            a.usuario.username,
            a.usuario.nombre,
            a.programa_formacion or '-',
            a.ficha or '-',
            round(a.promedio_estrellas, 2),
            a.num_proyectos_completados
        ])
    return response

@login_required
def reporte_vista_impresion(request):
    """Vista optimizada para imprimir reportes generales"""
    if request.user.rol != 'administrador':
        return redirect('inicio')
    
    context = {
        'proyectos': Proyecto.objects.select_related('empresa', 'categoria').order_by('-fecha_publicacion'),
        'aprendices': PerfilDesarrollador.objects.all().order_by('-calificacion_promedio'),
        'total_usuarios': Usuario.objects.count(),
        'total_proyectos': Proyecto.objects.count(),
    }
    return render(request, 'logs/reporte_impresion.html', context)

@login_required
def reporte_empresas_csv(request):
    """Generar reporte de todas las empresas en CSV (Excel) (SCRUM-177 / sin N+1)"""
    if request.user.rol != 'administrador':
        return redirect('inicio')
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte_empresas_tem.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Empresa', 'NIT', 'Sector', 'Ciudad', 'Telefono', 'Email', 'Proyectos Publicados', 'Reputación (★)'])
    
    empresas = PerfilEmpresa.objects.select_related('usuario').annotate(
        proyectos_count=Count('usuario__proyectos_empresa', distinct=True),
        promedio_estrellas=Coalesce(
            Avg(
                'usuario__valoraciones_como_empresa__puntuacion',
                filter=Q(usuario__valoraciones_como_empresa__rol_evaluador='desarrollador')
            ),
            Value(0.0),
            output_field=FloatField()
        )
    ).order_by('usuario__username')

    for e in empresas:
        writer.writerow([
            e.nombre_empresa or e.usuario.username,
            e.usuario.identificacion or '-',
            e.sector or '-',
            e.ciudad or '-',
            e.telefono or '-',
            e.usuario.email,
            e.proyectos_count,
            round(e.promedio_estrellas, 2)
        ])
        
    return response


@login_required
def visor_logs_tecnicos(request):
    """SCRUM-317 (HU-A18): últimas líneas del log técnico, solo administradores."""
    if request.user.rol != 'administrador':
        raise PermissionDenied

    try:
        lineas = int(request.GET.get('lineas', 100))
    except (TypeError, ValueError):
        lineas = 100
    lineas = max(20, min(lineas, 500))

    LogAuditoria.objects.create(
        usuario=request.user,
        accion=f"Consultó visor de logs técnicos ({lineas} líneas)",
        tabla_afectada='logs_tecnicos',
    )

    archivo = settings.LOG_FILE_APP
    try:
        with open(archivo, 'r', encoding='utf-8', errors='replace') as f:
            lineas_leidas = [linea.rstrip('\n') for linea in deque(f, maxlen=lineas)]
    except OSError:
        lineas_leidas = ["(Archivo de log técnico jobdevs.log inicializándose...)"]

    if request.GET.get('format') == 'json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'lineas': lineas_leidas,
            'total': len(lineas_leidas),
            'archivo': 'jobdevs.log',
        })

    return HttpResponse(
        "\n".join(lineas_leidas),
        content_type='text/plain; charset=utf-8',
    )
