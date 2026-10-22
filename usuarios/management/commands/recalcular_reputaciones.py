"""Recalcula los campos denormalizados de reputación y proyectos completados.

RF 5.3.1 y RF 7.2.1: los campos `calificacion_promedio` y
`num_proyectos_completados` solo se escriben desde los flujos de valoración y
finalización. Este comando los pone al día con los datos históricos (por
ejemplo, tras desplegar el arreglo sobre una base existente).

Uso:
    python manage.py recalcular_reputaciones
"""

from django.core.management.base import BaseCommand

from proyectos.services import (
    recalcular_proyectos_completados,
    recalcular_reputacion_desarrollador,
    recalcular_reputacion_empresa,
)
from usuarios.models import PerfilDesarrollador, PerfilEmpresa


class Command(BaseCommand):
    help = "Recalcula calificacion_promedio y num_proyectos_completados."

    def handle(self, *args, **options):
        devs = 0
        for perfil in PerfilDesarrollador.objects.select_related('usuario'):
            recalcular_reputacion_desarrollador(perfil.usuario_id)
            recalcular_proyectos_completados(perfil.usuario_id)
            devs += 1

        empresas = 0
        for perfil in PerfilEmpresa.objects.select_related('usuario'):
            recalcular_reputacion_empresa(perfil.usuario_id)
            empresas += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Recalculados {devs} perfiles de desarrollador y "
                f"{empresas} perfiles de empresa."
            )
        )
