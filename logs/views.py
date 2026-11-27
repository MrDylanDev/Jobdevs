import csv
from collections import deque
from datetime import datetime

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
from logs.pdf_reports import render_reporte_mensual_pdf, render_reporte_tabla_pdf


MAX_EXPORT_AUDITORIA = 5000


def _exigir_admin(request):
    if request.user.rol != 'administrador':
        raise PermissionDenied


def _parsear_rango_fechas(fecha_desde, fecha_hasta):
    """Valida fechas AAAA-MM-DD y devuelve (desde, hasta, error_response)."""
    try:
        desde = parse_date(fecha_desde) if fecha_desde else None
        hasta = parse_date(fecha_hasta) if fecha_hasta else None
    except ValueError:
        return None, None, JsonResponse(
            {'error': 'Las fechas deben usar el formato AAAA-MM-DD.'},
            status=400,
        )
    if (fecha_desde and desde is None) or (fecha_hasta and hasta is None):
        return None, None, JsonResponse(
            {'error': 'Las fechas deben usar el formato AAAA-MM-DD.'},
            status=400,
        )
    return desde, hasta, None


def _csv_safe(value):
    text = '' if value is None else str(value)
    if text and text[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + text
    return text


def _registrar_auditoria_reporte(user, nombre, filtros=None):
    detalle = ''
    if filtros:
        activos = ', '.join(f'{k}={v}' for k, v in filtros.items() if v)
        if activos:
            detalle = f' [{activos}]'
    LogAuditoria.objects.create(
        usuario=user,
        accion=f'Generó {nombre}{detalle}'[:300],
        tabla_afectada='reportes',
    )


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

    desde, hasta, error_fechas = _parsear_rango_fechas(desde_texto, hasta_texto)
    if error_fechas is not None:
        return error_fechas
    if desde:
        logs = logs.filter(fecha_hora__date__gte=desde)
    if hasta:
        logs = logs.filter(fecha_hora__date__lte=hasta)

    total = logs.count()
    resultados = list(logs[:200])
    return JsonResponse({
        'total': total,
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
    usuarios_qs = Usuario.objects.filter(
        date_joined__year=filtros['year'],
        date_joined__month=filtros['month'],
    )
    proyectos_qs = Proyecto.objects.filter(
        fecha_publicacion__year=filtros['year'],
        fecha_publicacion__month=filtros['month'],
    )
    contrataciones_qs = Contratacion.objects.filter(
        fecha_inicio__year=filtros['year'],
        fecha_inicio__month=filtros['month'],
    )

    usuarios = usuarios_qs.count()
    proyectos = proyectos_qs.count()
    contrataciones = contrataciones_qs.count()

    desglose_roles = [
        ('Desarrolladores', usuarios_qs.filter(rol='desarrollador').count()),
        ('Empresas', usuarios_qs.filter(rol='empresa').count()),
        ('Administradores', usuarios_qs.filter(rol='administrador').count()),
    ]
    conteos_estado = dict(
        proyectos_qs.values('estado')
        .annotate(total=Count('id'))
        .values_list('estado', 'total')
    )
    desglose_proyectos = [
        (etiqueta, conteos_estado.get(codigo, 0))
        for codigo, etiqueta in Proyecto.ESTADO
    ]

    _registrar_auditoria_reporte(request.user, 'Reporte mensual PDF', {'mes': mes_texto})

    return render_reporte_mensual_pdf(
        mes_texto=mes_texto,
        usuario_gen=request.user.username or 'Administrador',
        usuarios=usuarios,
        proyectos=proyectos,
        contrataciones=contrataciones,
        desglose_roles=desglose_roles,
        desglose_proyectos=desglose_proyectos,
    )

@login_required
def reporte_proyectos_csv(request):
    """Generar reporte detallado de proyectos en Excel"""
    if request.user.rol != 'administrador':
        return redirect('inicio')

    estado = request.GET.get('estado', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

    # Traemos proyectos con su empresa y calculamos métricas en una sola ráfaga SQL
    proyectos = Proyecto.objects.select_related('empresa', 'empresa__perfil_empresa', 'categoria').annotate(
        num_devs=Count('contrataciones', filter=Q(contrataciones__estado='activa'))
    ).order_by('-fecha_publicacion')
    if estado:
        proyectos = proyectos.filter(estado=estado)
    fecha_desde_parsed, fecha_hasta_parsed, error_fechas = _parsear_rango_fechas(
        fecha_desde, fecha_hasta
    )
    if error_fechas is not None:
        return error_fechas
    if fecha_desde_parsed:
        proyectos = proyectos.filter(fecha_publicacion__date__gte=fecha_desde_parsed)
    if fecha_hasta_parsed:
        proyectos = proyectos.filter(fecha_publicacion__date__lte=fecha_hasta_parsed)

    formato = request.GET.get('formato', 'csv').strip().lower()
    etiqueta_formato = 'PDF' if formato == 'pdf' else 'CSV'
    _registrar_auditoria_reporte(
        request.user,
        f'Reporte de proyectos {etiqueta_formato}',
        {'estado': estado, 'fecha_desde': fecha_desde, 'fecha_hasta': fecha_hasta},
    )

    encabezados = ['Título', 'Empresa', 'Tipo', 'Prioridad', 'Estado', 'Desarrolladores', 'Vacantes Totales', 'Fecha Publicación']

    def _fila_proyecto(p):
        nombre_empresa = getattr(p.empresa, 'perfil_empresa', None)
        empresa_display = nombre_empresa.nombre_empresa if nombre_empresa and nombre_empresa.nombre_empresa else p.empresa.nombre
        return [
            p.titulo,
            empresa_display,
            p.get_tipo_solucion_display(),
            p.get_prioridad_display(),
            p.get_estado_display(),
            p.num_devs,
            p.vacantes,
            p.fecha_publicacion.strftime('%d/%m/%Y %H:%M'),
        ]

    if formato == 'pdf':
        filas_datos = [_fila_proyecto(p) for p in proyectos]
        filtros_txt = ', '.join(
            f'{k}={v}' for k, v in (('estado', estado), ('desde', fecha_desde), ('hasta', fecha_hasta)) if v
        )
        total_vacantes = sum(f[6] for f in filas_datos)
        total_devs = sum(f[5] for f in filas_datos)
        return render_reporte_tabla_pdf(
            codigo='JD-REP-PROY',
            titulo='Reporte de Proyectos',
            subtitulo='Listado oficial de necesidades tecnológicas y estados actuales',
            usuario_gen=request.user.username or 'Administrador',
            filtros_texto=filtros_txt,
            kpis=[
                ('Proyectos listados', len(filas_datos), 'Total según filtros aplicados'),
                ('Vacantes totales', total_vacantes, 'Cupos solicitados por empresas'),
                ('Aprendices vinculados', total_devs, 'Contrataciones activas actuales'),
            ],
            encabezados=encabezados,
            filas=filas_datos,
            filename='reporte_proyectos.pdf',
            numeric_cols=(5, 6),
            badge_cols=(3, 4),
        )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="reporte_proyectos_tem.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(encabezados)
    for p in proyectos.iterator(chunk_size=500):
        fila = _fila_proyecto(p)
        writer.writerow([
            _csv_safe(fila[0]),
            _csv_safe(fila[1]),
            _csv_safe(fila[2]),
            _csv_safe(fila[3]),
            _csv_safe(fila[4]),
            fila[5],
            fila[6],
            fila[7],
        ])
    return response

@login_required
def reporte_aprendices_csv(request):
    """Generar reporte de desempeño de aprendices en CSV (SCRUM-177 / sin N+1)"""
    if request.user.rol != 'administrador':
        return redirect('inicio')

    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

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
    fecha_desde_parsed, fecha_hasta_parsed, error_fechas = _parsear_rango_fechas(
        fecha_desde, fecha_hasta
    )
    if error_fechas is not None:
        return error_fechas
    if fecha_desde_parsed:
        aprendices = aprendices.filter(usuario__date_joined__date__gte=fecha_desde_parsed)
    if fecha_hasta_parsed:
        aprendices = aprendices.filter(usuario__date_joined__date__lte=fecha_hasta_parsed)

    formato = request.GET.get('formato', 'csv').strip().lower()
    etiqueta_formato = 'PDF' if formato == 'pdf' else 'CSV'
    _registrar_auditoria_reporte(
        request.user,
        f'Reporte de aprendices {etiqueta_formato}',
        {'fecha_desde': fecha_desde, 'fecha_hasta': fecha_hasta},
    )

    encabezados = ['Usuario', 'Nombre', 'Programa', 'Ficha', 'Promedio', 'Proyectos']

    if formato == 'pdf':
        filas_datos = [
            [
                a.usuario.username,
                a.usuario.nombre,
                a.programa_formacion or '-',
                a.ficha or '-',
                round(a.promedio_estrellas, 2),
                a.num_proyectos_completados,
            ]
            for a in aprendices
        ]
        filtros_txt = ', '.join(
            f'{k}={v}' for k, v in (('desde', fecha_desde), ('hasta', fecha_hasta)) if v
        )
        prom_global = round(sum(f[4] for f in filas_datos) / len(filas_datos), 2) if filas_datos else 0.0
        total_completados = sum(f[5] for f in filas_datos)
        return render_reporte_tabla_pdf(
            codigo='JD-REP-APR',
            titulo='Reporte de Aprendices',
            subtitulo='Estadísticas de desempeño, fichas SENA y calificaciones de desarrolladores',
            usuario_gen=request.user.username or 'Administrador',
            filtros_texto=filtros_txt,
            kpis=[
                ('Aprendices registrados', len(filas_datos), 'Talento SENA en el listado'),
                ('Promedio general', f'{prom_global} ★', 'Calificación media de empresas'),
                ('Proyectos completados', total_completados, 'Entregas acumuladas'),
            ],
            encabezados=encabezados,
            filas=filas_datos,
            filename='reporte_aprendices.pdf',
            numeric_cols=(4, 5),
        )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="reporte_aprendices_tem.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(encabezados)
    for a in aprendices.iterator(chunk_size=500):
        writer.writerow([
            _csv_safe(a.usuario.username),
            _csv_safe(a.usuario.nombre),
            _csv_safe(a.programa_formacion or '-'),
            _csv_safe(a.ficha or '-'),
            round(a.promedio_estrellas, 2),
            a.num_proyectos_completados,
        ])
    return response

@login_required
def reporte_vista_impresion(request):
    """Vista optimizada para imprimir reportes generales"""
    if request.user.rol != 'administrador':
        return redirect('inicio')

    _registrar_auditoria_reporte(request.user, 'Vista de impresión de reportes')
    
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

    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

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
    fecha_desde_parsed, fecha_hasta_parsed, error_fechas = _parsear_rango_fechas(
        fecha_desde, fecha_hasta
    )
    if error_fechas is not None:
        return error_fechas
    if fecha_desde_parsed:
        empresas = empresas.filter(usuario__date_joined__date__gte=fecha_desde_parsed)
    if fecha_hasta_parsed:
        empresas = empresas.filter(usuario__date_joined__date__lte=fecha_hasta_parsed)

    formato = request.GET.get('formato', 'csv').strip().lower()
    etiqueta_formato = 'PDF' if formato == 'pdf' else 'CSV'
    _registrar_auditoria_reporte(
        request.user,
        f'Reporte de empresas {etiqueta_formato}',
        {'fecha_desde': fecha_desde, 'fecha_hasta': fecha_hasta},
    )

    encabezados = ['Empresa', 'NIT', 'Sector', 'Ciudad', 'Telefono', 'Email', 'Proyectos Publicados', 'Reputación (★)']

    if formato == 'pdf':
        filas_datos = [
            [
                e.nombre_empresa or e.usuario.username,
                e.usuario.identificacion or '-',
                e.sector or '-',
                e.ciudad or '-',
                e.telefono or '-',
                e.usuario.email,
                e.proyectos_count,
                round(e.promedio_estrellas, 2),
            ]
            for e in empresas
        ]
        filtros_txt = ', '.join(
            f'{k}={v}' for k, v in (('desde', fecha_desde), ('hasta', fecha_hasta)) if v
        )
        total_pub = sum(f[6] for f in filas_datos)
        prom_rep = round(sum(f[7] for f in filas_datos) / len(filas_datos), 2) if filas_datos else 0.0
        return render_reporte_tabla_pdf(
            codigo='JD-REP-EMP',
            titulo='Reporte de Empresas',
            subtitulo='Directorio institucional de empresas registradas, publicaciones y reputación',
            usuario_gen=request.user.username or 'Administrador',
            filtros_texto=filtros_txt,
            kpis=[
                ('Empresas registradas', len(filas_datos), 'Aliados productivos en el listado'),
                ('Proyectos publicados', total_pub, 'Oportunidades totales registradas'),
                ('Reputación promedio', f'{prom_rep} ★', 'Evaluación media de aprendices'),
            ],
            encabezados=encabezados,
            filas=filas_datos,
            filename='reporte_empresas.pdf',
            numeric_cols=(6, 7),
        )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="reporte_empresas_tem.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(encabezados)
    for e in empresas.iterator(chunk_size=500):
        writer.writerow([
            _csv_safe(e.nombre_empresa or e.usuario.username),
            _csv_safe(e.usuario.identificacion or '-'),
            _csv_safe(e.sector or '-'),
            _csv_safe(e.ciudad or '-'),
            _csv_safe(e.telefono or '-'),
            _csv_safe(e.usuario.email),
            e.proyectos_count,
            round(e.promedio_estrellas, 2),
        ])

    return response


@login_required
def reporte_auditoria_csv(request):
    """Generar reporte de registros de auditoría en CSV o PDF."""
    if request.user.rol != 'administrador':
        return redirect('inicio')

    tabla = request.GET.get('tabla', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

    qs = LogAuditoria.objects.select_related('usuario').order_by('-fecha_hora', '-id')
    if tabla:
        qs = qs.filter(tabla_afectada__icontains=tabla)
    fecha_desde_parsed, fecha_hasta_parsed, error_fechas = _parsear_rango_fechas(
        fecha_desde, fecha_hasta
    )
    if error_fechas is not None:
        return error_fechas
    if fecha_desde_parsed:
        qs = qs.filter(fecha_hora__date__gte=fecha_desde_parsed)
    if fecha_hasta_parsed:
        qs = qs.filter(fecha_hora__date__lte=fecha_hasta_parsed)

    formato = request.GET.get('formato', 'csv').strip().lower()
    etiqueta_formato = 'PDF' if formato == 'pdf' else 'CSV'
    _registrar_auditoria_reporte(
        request.user,
        f'Reporte de auditoría {etiqueta_formato}',
        {'tabla': tabla, 'fecha_desde': fecha_desde, 'fecha_hasta': fecha_hasta},
    )

    if formato == 'pdf':
        registros = list(qs[:MAX_EXPORT_AUDITORIA + 1])
        truncado = len(registros) > MAX_EXPORT_AUDITORIA
        if truncado:
            registros = registros[:MAX_EXPORT_AUDITORIA]
        encabezados = ['ID', 'Usuario', 'Acción', 'Tabla', 'Registro ID', 'Fecha y Hora']
        filas_datos = [
            [
                f'#{log.id}',
                log.usuario.username if log.usuario else 'Sistema',
                log.accion,
                log.tabla_afectada or '-',
                '' if log.registro_id is None else f'#{log.registro_id}',
                timezone.localtime(log.fecha_hora).strftime('%d/%m/%Y %H:%M:%S') if log.fecha_hora else '-',
            ]
            for log in registros
        ]
        filtros_txt = ', '.join(
            f'{k}={v}' for k, v in (('tabla', tabla), ('desde', fecha_desde), ('hasta', fecha_hasta)) if v
        )
        usuarios_distintos = len({f[1] for f in filas_datos})
        tablas_distintas = len({f[3] for f in filas_datos if f[3] != '-'})
        response = render_reporte_tabla_pdf(
            codigo='JD-REP-AUD',
            titulo='Reporte de Auditoría',
            subtitulo='Trazabilidad institucional de acciones administrativas y del sistema',
            usuario_gen=request.user.username or 'Administrador',
            filtros_texto=filtros_txt,
            kpis=[
                ('Eventos registrados', len(filas_datos), 'Total según filtros aplicados'),
                ('Usuarios / Actores', usuarios_distintos, 'Actores distintos en el período'),
                ('Módulos auditados', tablas_distintas, 'Tablas afectadas registradas'),
            ],
            encabezados=encabezados,
            filas=filas_datos,
            filename='reporte_auditoria.pdf',
            numeric_cols=(0, 4),
        )
        if truncado:
            response['X-Export-Truncated'] = 'true'
        return response

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="reporte_auditoria_tem.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['ID', 'Usuario', 'Acción', 'Tabla', 'Registro ID', 'Valor Anterior', 'Valor Nuevo', 'Fecha y Hora'])
    truncado = False
    for idx, log in enumerate(qs[:MAX_EXPORT_AUDITORIA + 1].iterator(chunk_size=500)):
        if idx >= MAX_EXPORT_AUDITORIA:
            truncado = True
            break
        writer.writerow([
            log.id,
            _csv_safe(log.usuario.username if log.usuario else 'Sistema'),
            _csv_safe(log.accion),
            _csv_safe(log.tabla_afectada or ''),
            '' if log.registro_id is None else log.registro_id,
            _csv_safe(log.valor_anterior or ''),
            _csv_safe(log.valor_nuevo or ''),
            timezone.localtime(log.fecha_hora).strftime('%d/%m/%Y %H:%M:%S') if log.fecha_hora else '',
        ])
    if truncado:
        response['X-Export-Truncated'] = 'true'
        writer.writerow([
            '',
            'ADVERTENCIA',
            f'Exportación truncada: se superó el límite de {MAX_EXPORT_AUDITORIA} registros. Aplique filtros de fecha o tabla para obtener el resto.',
            '',
            '',
            '',
            '',
            '',
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
