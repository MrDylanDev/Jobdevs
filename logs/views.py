import csv
from collections import deque
from datetime import datetime

import pymupdf

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Value, FloatField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date
from contrataciones.models import Contratacion
from proyectos.models import Proyecto, Valoracion
from usuarios.models import Usuario, PerfilDesarrollador, PerfilEmpresa
from logs.models import LogAuditoria


def _exigir_admin(request):
    if request.user.rol != 'administrador':
        raise PermissionDenied


@login_required
def historial_actividad(request):
    """Consulta filtrable adicional de la bitácora para administración."""
    _exigir_admin(request)

    logs = LogAuditoria.objects.select_related('usuario').order_by('-fecha_hora')
    usuario = request.GET.get('usuario', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    accion = request.GET.get('accion', '').strip()
    desde_texto = request.GET.get('desde', '').strip()
    hasta_texto = request.GET.get('hasta', '').strip()

    if usuario:
        if usuario.isdigit():
            logs = logs.filter(usuario_id=int(usuario))
        else:
            logs = logs.filter(usuario__username__icontains=usuario)
    if tipo:
        logs = logs.filter(tabla_afectada__iexact=tipo)
    if accion:
        logs = logs.filter(accion__icontains=accion)

    desde = parse_date(desde_texto) if desde_texto else None
    hasta = parse_date(hasta_texto) if hasta_texto else None
    if (desde_texto and desde is None) or (hasta_texto and hasta is None):
        return JsonResponse({'error': 'Las fechas deben usar el formato AAAA-MM-DD.'}, status=400)
    if desde:
        logs = logs.filter(fecha_hora__date__gte=desde)
    if hasta:
        logs = logs.filter(fecha_hora__date__lte=hasta)

    resultados = list(logs[:200])
    return JsonResponse({
        'total': len(resultados),
        'resultados': [
            {
                'id': log.id,
                'usuario': log.usuario.username if log.usuario else 'Sistema',
                'accion': log.accion,
                'tipo': log.tabla_afectada,
                'registro_id': log.registro_id,
                'valor_anterior': log.valor_anterior,
                'valor_nuevo': log.valor_nuevo,
                'fecha_hora': timezone.localtime(log.fecha_hora).isoformat(),
            }
            for log in resultados
        ],
    })


@login_required
def reporte_mensual_pdf(request):
    """Reporte mensual adicional con totales de actividad de la plataforma."""
    _exigir_admin(request)

    mes_texto = request.GET.get('mes') or timezone.localdate().strftime('%Y-%m')
    try:
        mes = datetime.strptime(mes_texto, '%Y-%m')
    except ValueError:
        return JsonResponse({'error': 'El mes debe usar el formato AAAA-MM.'}, status=400)

    filtros = {'year': mes.year, 'month': mes.month}
    usuarios = Usuario.objects.filter(
        date_joined__year=filtros['year'],
        date_joined__month=filtros['month'],
    ).count()
    proyectos = Proyecto.objects.filter(
        fecha_publicacion__year=filtros['year'],
        fecha_publicacion__month=filtros['month'],
    ).count()
    contrataciones = Contratacion.objects.filter(
        fecha_inicio__year=filtros['year'],
        fecha_inicio__month=filtros['month'],
    ).count()

    documento = pymupdf.open()
    pagina = documento.new_page()
    lineas = [
        f"Reporte mensual JobDevs - {mes_texto}",
        f"Usuarios registrados: {usuarios}",
        f"Proyectos publicados: {proyectos}",
        f"Contrataciones realizadas: {contrataciones}",
    ]
    for indice, linea in enumerate(lineas):
        pagina.insert_text((72, 72 + indice * 28), linea, fontsize=14 if indice == 0 else 11)
    contenido = documento.tobytes()
    documento.close()

    response = HttpResponse(contenido, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_mensual_{mes_texto}.pdf"'
    return response

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
