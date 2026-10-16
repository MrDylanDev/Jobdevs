import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from proyectos.models import Proyecto, Valoracion
from usuarios.models import Usuario, PerfilDesarrollador, PerfilEmpresa

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
    """Generar reporte de desempeño de aprendices en CSV"""
    if request.user.rol != 'administrador':
        return redirect('inicio')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte_aprendices_tem.csv"'

    writer = csv.writer(response)
    writer.writerow(['Usuario', 'Nombre', 'Programa', 'Ficha', 'Promedio', 'Proyectos'])

    aprendices = PerfilDesarrollador.objects.select_related('usuario').all()
    for a in aprendices:
        # Calcular promedio real de estrellas recibidas de empresas
        promedio = Valoracion.objects.filter(desarrollador=a.usuario, rol_evaluador='empresa').aggregate(Avg('puntuacion'))['puntuacion__avg'] or 0
        
        writer.writerow([
            a.usuario.username,
            a.usuario.nombre,
            a.programa_formacion or '-',
            a.ficha or '-',
            round(promedio, 2),
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
    """Generar reporte de todas las empresas en CSV (Excel)"""
    if request.user.rol != 'administrador':
        return redirect('inicio')
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte_empresas_tem.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Empresa', 'NIT', 'Sector', 'Ciudad', 'Telefono', 'Email', 'Proyectos Publicados', 'Reputación (★)'])
    
    empresas = PerfilEmpresa.objects.select_related('usuario').all()
    for e in empresas:
        proyectos_count = Proyecto.objects.filter(empresa=e.usuario).count()
        # Calcular promedio de reputación recibida de desarrolladores
        promedio = Valoracion.objects.filter(empresa=e.usuario, rol_evaluador='desarrollador').aggregate(Avg('puntuacion'))['puntuacion__avg'] or 0
        
        writer.writerow([
            e.nombre_empresa or e.usuario.username,
            e.usuario.identificacion or '-',
            e.sector or '-',
            e.ciudad or '-',
            e.telefono or '-',
            e.usuario.email,
            proyectos_count,
            round(promedio, 2)
        ])
        
    return response
