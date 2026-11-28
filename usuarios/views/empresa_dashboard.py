import json
from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q, Count, Prefetch, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from ..models import Usuario, PerfilEmpresa
from ..decorators import requiere_usuario_activo
from ..utils import get_admin_id
from proyectos.models import Proyecto, Valoracion, CategoriaSolucion, Entregable
from postulaciones.models import Postulacion
from contrataciones.models import Contratacion, ContratoDigital
from contrataciones.services import datos_dashboard_cancelaciones
from avances.models import Avance
from disputas.services import datos_dashboard_disputas
from mensajes.models import Mensaje
from ._helpers import get_notificaciones_context


# SCRUM-228 (RF 2.2.1): estados que representan proyectos fuera del ciclo activo.
ESTADOS_HISTORIAL = ('finalizado', 'rechazado', 'inactivo', 'en_disputa')


def _build_inicio_activity_series(empresa_user, hoy=None):
    """Construye la serie diaria real (últimos 30 días) de actividad operativa para #inicio."""
    if hoy is None:
        hoy = timezone.localdate()
    inicio_30d = hoy - timedelta(days=29)

    avances_por_dia = dict(
        Avance.objects.filter(
            proyecto__empresa=empresa_user,
            fecha_hora__date__gte=inicio_30d,
        )
        .annotate(dia=TruncDate('fecha_hora'))
        .values('dia')
        .annotate(c=Count('id'))
        .values_list('dia', 'c')
    )
    postulaciones_por_dia = dict(
        Postulacion.objects.filter(
            proyecto__empresa=empresa_user,
            fecha__date__gte=inicio_30d,
        )
        .annotate(dia=TruncDate('fecha'))
        .values('dia')
        .annotate(c=Count('id'))
        .values_list('dia', 'c')
    )
    hitos_por_dia = dict(
        Entregable.objects.filter(
            proyecto__empresa=empresa_user,
            estado='completado',
            fecha_creacion__date__gte=inicio_30d,
        )
        .annotate(dia=TruncDate('fecha_creacion'))
        .values('dia')
        .annotate(c=Count('id'))
        .values_list('dia', 'c')
    )

    dias_30 = [inicio_30d + timedelta(days=i) for i in range(30)]

    def _serie(conteo_map, label):
        puntos_30d = [
            {
                'fecha': d.isoformat(),
                'etiqueta': d.strftime('%d %b'),
                'valor': int(conteo_map.get(d, 0)),
            }
            for d in dias_30
        ]
        puntos_14d = puntos_30d[-14:]
        return {
            'label': label,
            'puntos_14d': puntos_14d,
            'puntos_30d': puntos_30d,
            'total_14d': sum(p['valor'] for p in puntos_14d),
            'total_30d': sum(p['valor'] for p in puntos_30d),
        }

    return {
        'avances': _serie(avances_por_dia, 'Entregables enviados'),
        'postulaciones': _serie(postulaciones_por_dia, 'Postulaciones recibidas'),
        'hitos': _serie(hitos_por_dia, 'Hitos completados'),
        'updated_at': timezone.now().isoformat(),
    }


@login_required
@requiere_usuario_activo
def api_inicio_actividad_empresa(request):
    """Devuelve las series diarias reales de #inicio para actualización en vivo."""
    if request.user.rol != 'empresa':
        return JsonResponse({'error': 'No autorizado'}, status=403)
    return JsonResponse(_build_inicio_activity_series(request.user))


@login_required
@requiere_usuario_activo
def dashboard_empresa(request):
    if request.user.rol != 'empresa': return redirect('inicio')
    
    hoy = timezone.localdate()
    resumen_proyectos = Proyecto.objects.filter(empresa=request.user).aggregate(
        total=Count('id', distinct=True),
        activos=Count('id', filter=Q(estado='en_desarrollo'), distinct=True),
        postulaciones_pendientes=Count(
            'postulaciones',
            filter=Q(
                postulaciones__estado='pendiente',
                estado__in=['publicado', 'en_desarrollo'],
            ),
        ),
    )
    resumen_contratos = Contratacion.objects.filter(empresa=request.user).aggregate(
        total=Count('id'),
        activos=Count('id', filter=Q(estado='activa')),
    )
    p_act = resumen_proyectos['activos']
    dev_con = resumen_contratos['activos']
    ha_publicado = resumen_proyectos['total'] > 0
    ha_contratado = resumen_contratos['total'] > 0
    post_pen = resumen_proyectos['postulaciones_pendientes']

    en_desarrollo_qs = Proyecto.objects.filter(
        empresa=request.user, estado__in=['en_desarrollo', 'en_revision']
    ).select_related('categoria').annotate(
        hitos_completados=Count('entregables', filter=Q(entregables__estado='completado')),
        hitos_totales=Count('entregables'),
    ).prefetch_related(
        Prefetch('contrataciones',
            queryset=Contratacion.objects.filter(estado='activa').select_related('desarrollador'),
            to_attr='contratos_activos'),
        Prefetch('entregables',
            queryset=Entregable.objects.order_by('fecha_creacion'),
            to_attr='lista_hitos'),
    )
    # RNF-10: precarga los conteos de postulaciones 'en_negociacion' en una
    # sola query en lugar de una consulta por proyecto (evita N+1).
    en_desarrollo_list = list(en_desarrollo_qs)
    negociacion_counts = dict(
        Postulacion.objects.filter(
            proyecto_id__in=[p.id for p in en_desarrollo_list],
            estado='en_negociacion',
        ).values('proyecto_id').annotate(c=Count('id')).values_list('proyecto_id', 'c')
    )
    avances_pendientes = list(
        Avance.objects.filter(
            proyecto_id__in=[p.id for p in en_desarrollo_list],
            estado='pendiente'
        ).select_related('desarrollador', 'entregable', 'proyecto').order_by('-fecha_hora')
    )
    avances_pendientes_revision = [
        {
            'id': a.id,
            'proyecto_id': a.proyecto_id,
            'proyecto_titulo': a.proyecto.titulo if a.proyecto else '',
            'entregable_id': a.entregable_id,
            'entregable_titulo': a.entregable.titulo if a.entregable else '',
            'desarrollador_nombre': (a.desarrollador.nombre or a.desarrollador.username) if a.desarrollador else '',
            'descripcion': a.descripcion,
            'archivo_url': a.archivo_url,
            'archivo_adjunto': a.archivo_adjunto.url if a.archivo_adjunto else None,
            'fecha_hora': a.fecha_hora,
        }
        for a in avances_pendientes
    ]
    total_avances_pendientes = len(avances_pendientes_revision)
    avances_map = {}
    for a in avances_pendientes:
        if a.proyecto_id not in avances_map:
            avances_map[a.proyecto_id] = a

    en_desarrollo_v = []
    for p in en_desarrollo_list:
        dev_ids = [c.desarrollador_id for c in p.contratos_activos]
        dev_nombres = ', '.join([c.desarrollador.nombre for c in p.contratos_activos])
        cupos_comprometidos = len(dev_ids) + negociacion_counts.get(p.id, 0)
        vacantes_disponibles = max(0, p.vacantes - cupos_comprometidos) if p.estado == 'en_desarrollo' else 0
        ap = avances_map.get(p.id)
        en_desarrollo_v.append({
            'proyecto_id': p.id,
            'titulo': p.titulo,
            'desarrolladores': dev_nombres,
            'hitos_completados': p.hitos_completados,
            'hitos_totales': p.hitos_totales,
            'lista_hitos': [
                {
                    'id': h.id,
                    'titulo': h.titulo,
                    'estado': h.estado,
                    'descripcion': h.descripcion,
                }
                for h in getattr(p, 'lista_hitos', [])
            ],
            'avance_pendiente': {
                'id': ap.id,
                'entregable_titulo': ap.entregable.titulo if ap.entregable else '',
                'desarrollador_nombre': ap.desarrollador.nombre if ap.desarrollador else '',
                'descripcion': ap.descripcion,
                'archivo_url': ap.archivo_url,
                'archivo_adjunto': ap.archivo_adjunto.url if ap.archivo_adjunto else None,
                'fecha_hora': ap.fecha_hora,
            } if ap else None,
            'ultimo_avance': None,
            'fecha_fin': p.fecha_cumplimiento,
            'cumplimiento_vencido': bool(
                p.fecha_cumplimiento and p.fecha_cumplimiento < timezone.localdate()
            ),
            'estado': p.estado,
            'ids': ','.join(map(str, dev_ids)),
            'primer_dev_id': dev_ids[0] if dev_ids else None,
            'num_desarrolladores': len(dev_ids),
            'permite_edicion_basica': not dev_ids,
            'vacantes_totales': p.vacantes,
            'vacantes_disponibles': vacantes_disponibles,
        })

    # Información de próxima entrega técnica y roadmap por proyecto (Command Center)
    proyectos_roadmap = []
    for idx, p in enumerate(en_desarrollo_v):
        hito_activo = None
        for h in p.get('lista_hitos', []):
            if h['estado'] in ('en_revision', 'pendiente'):
                hito_activo = h
                break

        dias_restantes = None
        if p.get('fecha_fin'):
            dias_restantes = (p['fecha_fin'] - hoy).days

        pct = round((p['hitos_completados'] / p['hitos_totales'] * 100)) if p['hitos_totales'] > 0 else 0

        proyectos_roadmap.append({
            'proyecto_id': p['proyecto_id'],
            'titulo': p['titulo'],
            'hitos_completados': p['hitos_completados'],
            'hitos_totales': p['hitos_totales'],
            'porcentaje': pct,
            'dias_restantes': dias_restantes,
            'vencido': dias_restantes is not None and dias_restantes < 0,
            'hito_activo_titulo': hito_activo['titulo'] if hito_activo else 'Entregable técnico final',
            'fecha': p.get('fecha_fin'),
            'hitos': p.get('lista_hitos', []),
            'es_primero': idx == 0,
        })
    proxima_entrega_info = proyectos_roadmap[0] if proyectos_roadmap else None

    # El GET del dashboard no debe crear datos. Los registros normales ya
    # reciben su perfil en el formulario de registro; para cuentas heredadas
    # sin perfil basta una instancia transitoria con los valores por defecto.
    perfil = (
        PerfilEmpresa.objects.filter(usuario=request.user).first()
        or PerfilEmpresa(usuario=request.user)
    )
    mis_ofertas = list(
        Proyecto.objects.filter(empresa=request.user, estado='publicado')
        .select_related('categoria')
        .annotate(
            num_candidatos=Count(
                'postulaciones',
                filter=Q(postulaciones__estado__in=['pendiente', 'en_negociacion']),
                distinct=True
            ),
            num_pendientes=Count(
                'postulaciones',
                filter=Q(postulaciones__estado='pendiente'),
                distinct=True
            ),
            num_contratos=Count('contrataciones', distinct=True),
            num_contratos_cancelados=Count(
                'contrataciones', filter=Q(contrataciones__estado='cancelada'),
                distinct=True,
            ),
            num_contratos_activos=Count(
                'contrataciones', filter=Q(contrataciones__estado='activa'),
                distinct=True,
            ),
            num_negociaciones=Count(
                'postulaciones',
                filter=Q(postulaciones__estado='en_negociacion'), distinct=True,
            ),
        )
        .order_by('-fecha_publicacion')
    )
    p_pub = len(mis_ofertas)
    total_vacantes_ofertas = sum(p.vacantes for p in mis_ofertas)

    # RF 2.2.1: marca las convocatorias que cierran en las próximas 48 horas.
    hoy = timezone.localdate()
    limite_48h = hoy + timedelta(days=2)
    for proyecto in mis_ofertas:
        proyecto.cierra_pronto = bool(
            proyecto.fecha_limite and hoy <= proyecto.fecha_limite <= limite_48h
        )
        proyecto.puede_reabrir = bool(
            proyecto.fecha_limite and proyecto.fecha_limite < hoy
            and proyecto.num_contratos_cancelados
            and proyecto.vacantes > proyecto.num_contratos_activos + proyecto.num_negociaciones
        )

    # Onboarding: 4 pasos iniciales para que la empresa active su cuenta.
    pasos_onboarding = [
        {
            'clave': 'perfil',
            'titulo': 'Completa el perfil de tu empresa',
            'descripcion': 'Añade el logo y una descripción que genere confianza en el talento.',
            'completado': bool(perfil.logo and (perfil.descripcion or '').strip()),
            'en_revision': False,
        },
        {
            'clave': 'verificacion',
            'titulo': 'Verifica tu NIT',
            'descripcion': 'Obtén el sello de empresa verificada y publica con mayor respaldo.',
            'completado': perfil.estado_verificacion == 'verificada',
            'en_revision': perfil.estado_verificacion == 'en_revision',
        },
        {
            'clave': 'publicar',
            'titulo': 'Publica tu primera convocatoria',
            'descripcion': 'Describe tu proyecto y encuentra el talento que necesitas.',
            'completado': ha_publicado,
            'en_revision': False,
        },
        {
            'clave': 'contratar',
            'titulo': 'Contrata tu primer talento',
            'descripcion': 'Inicia un contrato activo con un desarrollador de la plataforma.',
            'completado': ha_contratado,
            'en_revision': False,
        },
    ]
    onboarding_completados = sum(1 for paso in pasos_onboarding if paso['completado'])
    total_pasos_onboarding = len(pasos_onboarding)
    onboarding_porcentaje = round((onboarding_completados / total_pasos_onboarding) * 100)
    
    postulaciones_pendientes_obj = Postulacion.objects.filter(
        proyecto__empresa=request.user, 
        estado='pendiente',
        proyecto__estado__in=['publicado', 'en_desarrollo']
    )
    admin_id = get_admin_id()

    valoraciones_dev = list(
        Valoracion.objects.filter(empresa=request.user, rol_evaluador='desarrollador')
        .select_related('desarrollador', 'desarrollador__perfil_desarrollador', 'proyecto')
        .order_by('-fecha')
    )
    total_valoraciones = len(valoraciones_dev)
    promedio_empresa = (
        sum(v.puntuacion for v in valoraciones_dev) / total_valoraciones
        if total_valoraciones > 0 else 0.0
    )

    conteo_estrellas = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for val in valoraciones_dev:
        if val.puntuacion in conteo_estrellas:
            conteo_estrellas[val.puntuacion] += 1
    porcentaje_estrellas = {
        k: round((conteo_estrellas[k] / total_valoraciones) * 100) if total_valoraciones > 0 else 0
        for k in conteo_estrellas
    }

    notificaciones_recientes, notificaciones_pendientes_count = get_notificaciones_context(request.user.id)

    colaboradores_activos = Contratacion.objects.filter(
        empresa=request.user, 
        estado='activa',
        proyecto__estado='en_desarrollo'
    ).select_related('desarrollador__perfil_desarrollador', 'proyecto')

    # Módulo 8 / SCRUM-204: contratos digitales gestionados 100% in-situ desde el panel.
    mis_contratos_digitales = ContratoDigital.objects.filter(
        postulacion__proyecto__empresa=request.user
    ).select_related(
        'postulacion__proyecto',
        'postulacion__desarrollador',
        'postulacion__desarrollador__perfil_desarrollador',
        'contratacion',
    ).order_by('-fecha_actualizacion')
    contratos_pendientes_firma_count = sum(
        1 for c in mis_contratos_digitales
        if not c.firmado_empresa and c.estado in ('borrador', 'pendiente_firma')
    )

    # Flujo Financiero y Fondos en Custodia (Command Center)
    contratos_formalizados = [
        c for c in mis_contratos_digitales
        if (c.firmado_empresa and c.firmado_desarrollador)
        or c.estado == 'firmado'
        or (c.contratacion_id is not None and c.contratacion.estado == 'activa')
    ]
    proyecto_ids_escrow = list({c.postulacion.proyecto_id for c in contratos_formalizados})
    hitos_por_proyecto = {}
    if proyecto_ids_escrow:
        hitos_rows = (
            Entregable.objects.filter(proyecto_id__in=proyecto_ids_escrow)
            .values('proyecto_id')
            .annotate(
                completados=Count('id', filter=Q(estado='completado')),
                totales=Count('id'),
            )
        )
        hitos_por_proyecto = {
            row['proyecto_id']: (row['completados'] or 0, row['totales'] or 0)
            for row in hitos_rows
        }

    totales_por_moneda = {}
    for c in contratos_formalizados:
        moneda_c = (getattr(c, 'moneda', None) or 'COP').upper()
        monto_c = Decimal(str(c.monto)) if c.monto is not None else Decimal(0)
        bucket = totales_por_moneda.setdefault(
            moneda_c, {'comprometido': Decimal(0), 'devengado': Decimal(0)}
        )
        bucket['comprometido'] += monto_c
        proyecto_c = c.postulacion.proyecto
        if proyecto_c.estado == 'finalizado':
            bucket['devengado'] += monto_c
        else:
            hitos_comp, hitos_tot = hitos_por_proyecto.get(proyecto_c.id, (0, 0))
            if hitos_tot > 0:
                bucket['devengado'] += Decimal(
                    round(monto_c * (Decimal(hitos_comp) / Decimal(hitos_tot)))
                )

    if 'COP' in totales_por_moneda:
        moneda_principal = 'COP'
    elif totales_por_moneda:
        moneda_principal = next(iter(totales_por_moneda))
    else:
        moneda_principal = 'COP'

    principal = totales_por_moneda.get(
        moneda_principal, {'comprometido': Decimal(0), 'devengado': Decimal(0)}
    )
    presupuesto_total_comprometido = principal['comprometido']
    fondos_liberados = principal['devengado']
    fondos_en_custodia = max(Decimal(0), presupuesto_total_comprometido - fondos_liberados)
    porcentaje_fondos_liberados = (
        round((fondos_liberados / presupuesto_total_comprometido) * 100)
        if presupuesto_total_comprometido > 0 else 0
    )
    resumen_monedas_secundarias = [
        {
            'moneda': mon,
            'comprometido': datos['comprometido'],
            'devengado': datos['devengado'],
            'por_devengar': max(Decimal(0), datos['comprometido'] - datos['devengado']),
        }
        for mon, datos in totales_por_moneda.items()
        if mon != moneda_principal and datos['comprometido'] > 0
    ]

    historial_v = Proyecto.objects.filter(
        empresa=request.user, 
        estado='finalizado'
    ).select_related('categoria').annotate(num_desarrolladores=Count('contrataciones')).prefetch_related('contrataciones__desarrollador').order_by('-fecha_publicacion')

    # SCRUM-228 (RF 2.2.1): historial completo (finalizado, rechazado, inactivo,
    # en_disputa) con filtro opcional por estado vía GET 'historial_estado'.
    historial_estado_actual = request.GET.get('historial_estado', '')
    historial_inactivos_qs = Proyecto.objects.filter(
        empresa=request.user, estado__in=ESTADOS_HISTORIAL
    )
    if historial_estado_actual in ESTADOS_HISTORIAL:
        historial_inactivos_qs = historial_inactivos_qs.filter(estado=historial_estado_actual)
    else:
        historial_estado_actual = ''

    historial_inactivos = list(historial_inactivos_qs.select_related('categoria').annotate(
        num_desarrolladores=Count('contrataciones', distinct=True),
        hitos_completados=Count('entregables', filter=Q(entregables__estado='completado'), distinct=True),
        hitos_totales=Count('entregables', distinct=True),
    ).prefetch_related(
        'contrataciones__desarrollador',
        'contrataciones__desarrollador__perfil_desarrollador',
    ).order_by('-fecha_publicacion'))
    historial_inactivos_count = len(historial_inactivos)

    finalizados_ids = [p.id for p in historial_inactivos if p.estado == 'finalizado']
    valorados_por_proyecto = {}
    if finalizados_ids:
        for pid, did in Valoracion.objects.filter(
            proyecto_id__in=finalizados_ids, rol_evaluador='empresa'
        ).values_list('proyecto_id', 'desarrollador_id'):
            valorados_por_proyecto.setdefault(pid, set()).add(did)
    for p in historial_inactivos:
        if p.estado == 'finalizado':
            ya_valorados = valorados_por_proyecto.get(p.id, set())
            p.tiene_pendientes_calificar = any(
                c.estado in ('activa', 'finalizada') and c.desarrollador_id not in ya_valorados
                for c in p.contrataciones.all()
            )
        else:
            p.tiene_pendientes_calificar = False

    conteos_historial = dict(
        Proyecto.objects.filter(empresa=request.user, estado__in=ESTADOS_HISTORIAL)
        .values('estado')
        .annotate(c=Count('id'))
        .values_list('estado', 'c')
    )
    historial_por_estado = {estado: conteos_historial.get(estado, 0) for estado in ESTADOS_HISTORIAL}

    # Métricas de Auditoría y Ledger para el Historial (Stripe Analytics)
    montos_mensuales = list(
        ContratoDigital.objects.filter(postulacion__proyecto__empresa=request.user)
        .annotate(mes_ledger=TruncMonth('fecha_creacion'))
        .values('mes_ledger').annotate(total=Sum('monto'))
    )
    capital_ejecutado = sum((fila['total'] for fila in montos_mensuales), 0)
    montos_por_mes = {
        (fila['mes_ledger'].year, fila['mes_ledger'].month): fila['total']
        for fila in montos_mensuales
    }

    contratos_por_dev = (
        Contratacion.objects.filter(empresa=request.user)
        .values('desarrollador_id')
        .annotate(total=Count('id'))
    )
    total_devs_historicos = len(contratos_por_dev)
    devs_recontratados = sum(1 for d in contratos_por_dev if d['total'] > 1)
    tasa_recontratacion = round((devs_recontratados / total_devs_historicos * 100), 1) if total_devs_historicos > 0 else 0

    hitos_stats = Entregable.objects.filter(
        proyecto__empresa=request.user
    ).aggregate(
        completados=Count('id', filter=Q(estado='completado')),
        totales=Count('id')
    )
    hitos_completados_total = hitos_stats['completados'] or 0
    hitos_totales_total = hitos_stats['totales'] or 0
    tasa_cumplimiento_hitos = round((hitos_completados_total / hitos_totales_total * 100), 1) if hitos_totales_total > 0 else 100.0

    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    ultimos_12_meses = []
    for i in range(11, -1, -1):
        anio = hoy.year
        mes = hoy.month - i
        while mes <= 0:
            mes += 12
            anio -= 1
        ultimos_12_meses.append((anio, mes, meses_nombres[mes - 1]))

    meses_ledger = [
        {'mes': nombre_mes, 'monto': float(montos_por_mes.get((anio, mes), 0))}
        for anio, mes, nombre_mes in ultimos_12_meses[-6:]
    ]

    # Datasets dinámicos para la gráfica analítica de Historial (6m / 12m)
    monto_por_proyecto = {}
    for contrato in mis_contratos_digitales:
        pid = contrato.postulacion.proyecto_id
        monto_por_proyecto[pid] = monto_por_proyecto.get(pid, 0.0) + float(contrato.monto or 0)

    totales_hitos_por_proyecto = dict(
        Entregable.objects.filter(proyecto__empresa=request.user)
        .values('proyecto_id')
        .annotate(totales=Count('id'))
        .values_list('proyecto_id', 'totales')
    )

    hitos_completados_mensuales = list(
        Entregable.objects.filter(proyecto__empresa=request.user, estado='completado')
        .annotate(mes_hito=TruncMonth('fecha_creacion'))
        .values('mes_hito', 'proyecto_id')
        .annotate(cantidad=Count('id'))
    )

    hitos_qty_por_mes = {}
    liquidado_por_mes = {}
    for fila in hitos_completados_mensuales:
        mes_dt = fila['mes_hito']
        if not mes_dt:
            continue
        clave = (mes_dt.year, mes_dt.month)
        cant = int(fila['cantidad'] or 0)
        hitos_qty_por_mes[clave] = hitos_qty_por_mes.get(clave, 0) + cant

        pid = fila['proyecto_id']
        tot_hitos = totales_hitos_por_proyecto.get(pid, 0)
        monto_proy = monto_por_proyecto.get(pid, 0.0)
        if tot_hitos > 0 and monto_proy > 0:
            liquidado_por_mes[clave] = liquidado_por_mes.get(clave, 0.0) + (monto_proy / tot_hitos) * cant

    puntos_contratado_12m = [
        {'mes': nombre, 'valor': round(float(montos_por_mes.get((anio, mes), 0)), 2)}
        for anio, mes, nombre in ultimos_12_meses
    ]
    puntos_liquidado_12m = [
        {'mes': nombre, 'valor': round(float(liquidado_por_mes.get((anio, mes), 0.0)), 2)}
        for anio, mes, nombre in ultimos_12_meses
    ]
    puntos_hitos_12m = [
        {'mes': nombre, 'valor': int(hitos_qty_por_mes.get((anio, mes), 0))}
        for anio, mes, nombre in ultimos_12_meses
    ]

    chart_datasets = {
        'contratado': {
            'label': 'Presupuesto Contratado (COP)',
            'puntos_6m': puntos_contratado_12m[-6:],
            'puntos_12m': puntos_contratado_12m,
            'total_6m': round(sum(p['valor'] for p in puntos_contratado_12m[-6:]), 2),
            'total_12m': round(sum(p['valor'] for p in puntos_contratado_12m), 2),
        },
        'liquidado': {
            'label': 'Liquidaciones por Hitos Aprobados (COP)',
            'puntos_6m': puntos_liquidado_12m[-6:],
            'puntos_12m': puntos_liquidado_12m,
            'total_6m': round(sum(p['valor'] for p in puntos_liquidado_12m[-6:]), 2),
            'total_12m': round(sum(p['valor'] for p in puntos_liquidado_12m), 2),
        },
        'hitos_qty': {
            'label': 'Volumen de Hitos Aprobados (Cant.)',
            'puntos_6m': puntos_hitos_12m[-6:],
            'puntos_12m': puntos_hitos_12m,
            'total_6m': sum(p['valor'] for p in puntos_hitos_12m[-6:]),
            'total_12m': sum(p['valor'] for p in puntos_hitos_12m),
        },
    }
    chart_datasets_json = json.dumps(chart_datasets)

    # Inversión / Proyectos por Stack o Área de Solución (Dona SVG)
    # El queryset del panel ya está evaluado para contar firmas pendientes.
    # Reutilizarlo evita una consulta adicional por cada carga del dashboard.
    gasto_por_tipo_map = {}
    for contrato in mis_contratos_digitales:
        tipo = contrato.postulacion.proyecto.tipo_solucion
        if tipo not in gasto_por_tipo_map:
            gasto_por_tipo_map[tipo] = {
                'postulacion__proyecto__tipo_solucion': tipo,
                'total': Decimal(0),
                'cantidad': 0,
            }
        gasto_por_tipo_map[tipo]['total'] += (contrato.monto or Decimal(0))
        gasto_por_tipo_map[tipo]['cantidad'] += 1
    gasto_por_tipo = list(gasto_por_tipo_map.values())
    total_monto_gasto = sum((g['total'] for g in gasto_por_tipo), Decimal(0))
    breakdown_stack = []
    colores_stack = ['#00c853', '#38bdf8', '#a855f7', '#f59e0b', '#ec4899', '#10b981']
    tipo_choices = dict(Proyecto.TIPO_SOLUCION)
    tiene_datos_reales_stack = False

    if gasto_por_tipo and total_monto_gasto > 0:
        tiene_datos_reales_stack = True
        cum_dash = 0.0
        for i, item in enumerate(gasto_por_tipo):
            pct = round((float(item['total']) / float(total_monto_gasto)) * 100)
            tipo_label = tipo_choices.get(item['postulacion__proyecto__tipo_solucion'], 'General')
            dash_len = round(pct * 2.3876, 1)
            breakdown_stack.append({
                'label': tipo_label,
                'total': float(item['total']),
                'es_cantidad_proyectos': False,
                'porcentaje': pct,
                'color': colores_stack[i % len(colores_stack)],
                'dash_length': dash_len,
                'dash_offset': round(-cum_dash, 1),
            })
            cum_dash += dash_len
    else:
        # Si no hay desembolsos contractuales aún, calcular por tipo de proyectos publicados
        proy_por_tipo = list(
            Proyecto.objects.filter(empresa=request.user)
            .values('tipo_solucion')
            .annotate(cantidad=Count('id'))
        )
        total_proy_tipo = sum(p['cantidad'] for p in proy_por_tipo)
        if proy_por_tipo and total_proy_tipo > 0:
            tiene_datos_reales_stack = True
            cum_dash = 0.0
            for i, item in enumerate(proy_por_tipo):
                pct = round((float(item['cantidad']) / float(total_proy_tipo)) * 100)
                tipo_label = tipo_choices.get(item['tipo_solucion'], 'General')
                dash_len = round(pct * 2.3876, 1)
                breakdown_stack.append({
                    'label': tipo_label,
                    'total': item['cantidad'],
                    'es_cantidad_proyectos': True,
                    'porcentaje': pct,
                    'color': colores_stack[i % len(colores_stack)],
                    'dash_length': dash_len,
                    'dash_offset': round(-cum_dash, 1),
                })
                cum_dash += dash_len
        else:
            demo_items = [
                {'label': 'Sitio Web', 'porcentaje': 45, 'dash_length': 107.4},
                {'label': 'Aplicación Móvil', 'porcentaje': 30, 'dash_length': 71.6},
                {'label': 'Automatización', 'porcentaje': 25, 'dash_length': 59.7},
            ]
            cum_dash = 0.0
            for i, d in enumerate(demo_items):
                breakdown_stack.append({
                    'label': d['label'],
                    'porcentaje': d['porcentaje'],
                    'total': 0,
                    'es_cantidad_proyectos': False,
                    'color': colores_stack[i % len(colores_stack)],
                    'dash_length': d['dash_length'],
                    'dash_offset': round(-cum_dash, 1),
                })
                cum_dash += d['dash_length']

    gauge_dash_hitos = int(float(tasa_cumplimiento_hitos) * 2.3876)

    context = {
        'proyectos_roadmap': proyectos_roadmap,
        'proxima_entrega_info': proxima_entrega_info,
        'capital_ejecutado': capital_ejecutado,
        'total_devs_historicos': total_devs_historicos,
        'tasa_recontratacion': tasa_recontratacion,
        'hitos_completados_total': hitos_completados_total,
        'hitos_totales_total': hitos_totales_total,
        'tasa_cumplimiento_hitos': tasa_cumplimiento_hitos,
        'gauge_dash_hitos': gauge_dash_hitos,
        'breakdown_stack': breakdown_stack,
        'tiene_datos_reales_stack': tiene_datos_reales_stack,
        'meses_ledger': meses_ledger,
        'chart_datasets_json': chart_datasets_json,
        'inicio_activity_json': json.dumps(_build_inicio_activity_series(request.user, hoy=hoy)),
        'ha_publicado': ha_publicado,
        'ha_contratado': ha_contratado,
        'es_cuenta_nueva': not ha_publicado and not ha_contratado,
        'total_proyectos': p_pub,
        'proyectos_activos': p_act,
        'total_postulaciones': post_pen,
        'total_contratados': dev_con,
        'mis_ofertas': mis_ofertas,
        'fecha_minima_reapertura': (hoy + timedelta(days=1)).isoformat(),
        'total_vacantes_ofertas': total_vacantes_ofertas,
        'pasos_onboarding': pasos_onboarding,
        'onboarding_completados': onboarding_completados,
        'onboarding_porcentaje': onboarding_porcentaje,
        'avances_pendientes_revision': avances_pendientes_revision,
        'total_avances_pendientes': total_avances_pendientes,
        'en_desarrollo_v': en_desarrollo_v,
        'colaboradores_activos': colaboradores_activos,
        'mis_contratos_digitales': mis_contratos_digitales,
        'contratos_pendientes_firma_count': contratos_pendientes_firma_count,
        'presupuesto_total_comprometido': presupuesto_total_comprometido,
        'fondos_liberados': fondos_liberados,
        'fondos_en_custodia': fondos_en_custodia,
        'porcentaje_fondos_liberados': porcentaje_fondos_liberados,
        'moneda_principal': moneda_principal,
        'resumen_monedas_secundarias': resumen_monedas_secundarias,
        'historial': historial_v,
        'historial_inactivos': historial_inactivos,
        'historial_inactivos_count': historial_inactivos_count,
        'historial_por_estado': historial_por_estado,
        'historial_estado_actual': historial_estado_actual,
        'valoraciones_recibidas': valoraciones_dev,
        'total_valoraciones': total_valoraciones,
        'conteo_estrellas': conteo_estrellas,
        'porcentaje_estrellas': porcentaje_estrellas,
        'promedio_empresa': round(float(promedio_empresa), 1),
        'postulaciones_pendientes': postulaciones_pendientes_obj,
        'notificaciones': notificaciones_recientes,
        'notificaciones_pendientes_count': notificaciones_pendientes_count,
        'mensajes_no_leidos': Mensaje.objects.filter(receptor=request.user, leido=False).count(),
        'perfil': perfil,
        'tipos_persona': PerfilEmpresa.TIPO_PERSONA_CHOICES,
        'tipos_documento': PerfilEmpresa.TIPO_DOCUMENTO_CHOICES,
        'admin_id': admin_id,
        'categorias_solucion': CategoriaSolucion.objects.filter(activo=True),
    }
    context.update(datos_dashboard_disputas(request.user, estado=request.GET.get('estado')))
    context.update(datos_dashboard_cancelaciones(request.user))
    context['disputas_activas_count'] = len(context['disputas_activas'])
    return render(request, 'empresa/empresa.html', context)


@login_required
@requiere_usuario_activo
def detalle_empresa(request, empresa_id):
    """
    Vista de perfil público institucional y reputación de la empresa (RF 3.1.2 / SCRUM-56).
    Permite a desarrolladores y usuarios consultar:
    - Información corporativa (razón social / nombre, sector, ciudad, descripción, logo).
    - Estado e insignia de verificación oficial (Empresa Verificada / Negocio Verificado / Sin Verificar).
    - Métricas de proyectos (publicados disponibles, en desarrollo, finalizados).
    - Resumen y desglose de reputación por estrellas.
    - Historial de comentarios previos y valoraciones realizadas por desarrolladores.
    - Proyectos abiertos actualmente disponibles para postulación.
    """
    empresa = get_object_or_404(Usuario, id=empresa_id, rol='empresa')
    perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=empresa)

    # Reseñas dejadas por desarrolladores a esta empresa
    resenas = list(
        Valoracion.objects.filter(empresa=empresa, rol_evaluador='desarrollador')
        .select_related('desarrollador', 'desarrollador__perfil_desarrollador', 'proyecto')
        .order_by('-fecha')
    )

    total_resenas = len(resenas)
    promedio = (
        Valoracion.objects.filter(empresa=empresa, rol_evaluador='desarrollador')
        .aggregate(Avg('puntuacion'))['puntuacion__avg']
        or 0.0
    )

    # Desglose de estrellas para barra de distribución
    conteo_estrellas = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in resenas:
        if r.puntuacion in conteo_estrellas:
            conteo_estrellas[r.puntuacion] += 1

    # Proyectos publicados abiertos de esta empresa
    proyectos_abiertos = list(
        Proyecto.objects.filter(empresa=empresa, estado='publicado')
        .select_related('categoria')
        .order_by('-fecha_publicacion')
    )
    proyectos_finalizados_count = Proyecto.objects.filter(empresa=empresa, estado='finalizado').count()
    proyectos_activos_count = Proyecto.objects.filter(empresa=empresa, estado='en_desarrollo').count()

    es_htmx = (
        request.headers.get('HX-Request') == 'true'
        and request.GET.get('format') != 'json'
        and 'application/json' not in request.headers.get('Accept', '')
    )
    quiere_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
        or request.GET.get('format') == 'json'
    )

    if es_htmx or quiere_json:
        resenas_data = [
            {
                'desarrollador': r.desarrollador.nombre or r.desarrollador.username,
                'puntuacion': r.puntuacion,
                'comentario': r.comentario,
                'fecha': r.fecha.strftime('%d/%m/%Y'),
                'proyecto_titulo': r.proyecto.titulo,
            }
            for r in resenas[:5]
        ]
        logo_url = None
        if perfil.logo:
            try:
                logo_url = perfil.logo.url
            except Exception:
                logo_url = None

        nombre_empresa = perfil.nombre_empresa or empresa.nombre or empresa.username
        sector = perfil.sector or 'No especificado'
        ciudad = perfil.ciudad or 'No especificada'
        descripcion = perfil.descripcion or 'Sin descripción registrada.'
        promedio_redondeado = round(float(promedio), 1)

        if es_htmx:
            return render(request, 'empresa/partials/_modal_perfil_publico.html', {
                'empresa': empresa,
                'perfil': perfil,
                'nombre_empresa': nombre_empresa,
                'sector': sector,
                'ciudad': ciudad,
                'descripcion': descripcion,
                'badge_label': perfil.badge_info['label'] if perfil.badge_info else 'Sin verificar',
                'logo_url': logo_url,
                'promedio_reputacion': promedio_redondeado,
                'total_resenas': total_resenas,
                'proyectos_activos_count': proyectos_activos_count,
                'proyectos_finalizados_count': proyectos_finalizados_count,
                'resenas_modal': resenas_data,
            })

        return JsonResponse({
            'ok': True,
            'empresa': {
                'id': empresa.id,
                'nombre': nombre_empresa,
                'username': empresa.username,
                'sector': sector,
                'ciudad': ciudad,
                'descripcion': descripcion,
                'es_verificada': perfil.es_verificada,
                'badge_label': perfil.badge_info['label'] if perfil.badge_info else 'Sin Verificar',
                'reputacion': promedio_redondeado,
                'total_resenas': total_resenas,
                'proyectos_activos': proyectos_activos_count,
                'proyectos_finalizados': proyectos_finalizados_count,
                'logo_url': logo_url,
                'resenas': resenas_data,
            }
        })

    context = {
        'empresa': empresa,
        'perfil': perfil,
        'resenas': resenas,
        'total_resenas': total_resenas,
        'promedio_reputacion': round(float(promedio), 1),
        'conteo_estrellas': conteo_estrellas,
        'proyectos_abiertos': proyectos_abiertos,
        'total_proyectos_abiertos': len(proyectos_abiertos),
        'proyectos_finalizados_count': proyectos_finalizados_count,
        'proyectos_activos_count': proyectos_activos_count,
    }
    return render(request, 'empresa/detalle_publico.html', context)

