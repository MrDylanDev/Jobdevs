from django.shortcuts import render
from django.db.models import Avg, Q, Count, Prefetch, Value, FloatField
from django.db.models.functions import Coalesce
from django.views.decorators.csrf import ensure_csrf_cookie
from proyectos.models import Proyecto
from contrataciones.models import Contratacion


@ensure_csrf_cookie
def inicio(request):
    proyectos_qs = Proyecto.objects.filter(estado='finalizado').select_related(
        'empresa__perfil_empresa'
    ).prefetch_related(
        Prefetch('contrataciones',
            queryset=Contratacion.objects.filter(estado='finalizada').select_related('desarrollador'),
            to_attr='contratos_finalizados')
    ).annotate(
        calificacion=Coalesce(Avg('valoraciones__puntuacion',
            filter=Q(valoraciones__rol_evaluador='empresa')),
            Value(0.0), output_field=FloatField())
    ).order_by('-fecha_publicacion')[:4]

    casos_exito = []
    for p in proyectos_qs:
        dev_nombre = p.contratos_finalizados[0].desarrollador.nombre if p.contratos_finalizados else ''
        casos_exito.append({
            'titulo': p.titulo,
            'tipo_solucion': p.tipo_solucion,
            'empresa_nombre': p.empresa.nombre,
            'desarrollador_nombre': dev_nombre,
            'calificacion': round(p.calificacion, 1),
        })

    return render(request, 'publico/index.html', {'casos_exito': casos_exito})
