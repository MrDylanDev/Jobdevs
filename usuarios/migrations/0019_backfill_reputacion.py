"""Backfill de los campos denormalizados de reputación (RF 5.3.1 / RF 7.2.1).

SCRUM-210 y SCRUM-211: `PerfilDesarrollador.calificacion_promedio`,
`PerfilEmpresa.calificacion_promedio` y `PerfilDesarrollador.num_proyectos_completados`
existían sin escritor, así que quedaron en 0 para toda la historia previa.
Tras desplegar los escritores, esta migración pone al día las filas existentes.

Se usan los modelos históricos (`apps.get_model`) para no depender de la capa de
servicios, que evoluciona. El comando `recalcular_reputaciones` hace lo mismo
para reejecutarlo a mano si se importan datos masivos.
"""

from django.db import migrations
from django.db.models import Avg


def backfill(apps, schema_editor):
    Valoracion = apps.get_model('proyectos', 'Valoracion')
    Contratacion = apps.get_model('contrataciones', 'Contratacion')
    PerfilDesarrollador = apps.get_model('usuarios', 'PerfilDesarrollador')
    PerfilEmpresa = apps.get_model('usuarios', 'PerfilEmpresa')

    for perfil in PerfilDesarrollador.objects.all().only('id', 'usuario_id'):
        promedio = (
            Valoracion.objects.filter(
                desarrollador_id=perfil.usuario_id, rol_evaluador='empresa'
            ).aggregate(valor=Avg('puntuacion'))['valor']
            or 0
        )
        completados = (
            Contratacion.objects.filter(
                desarrollador_id=perfil.usuario_id, estado='finalizada'
            ).values('proyecto_id').distinct().count()
        )
        PerfilDesarrollador.objects.filter(pk=perfil.pk).update(
            calificacion_promedio=round(float(promedio), 2),
            num_proyectos_completados=completados,
        )

    for perfil in PerfilEmpresa.objects.all().only('id', 'usuario_id'):
        promedio = (
            Valoracion.objects.filter(
                empresa_id=perfil.usuario_id, rol_evaluador='desarrollador'
            ).aggregate(valor=Avg('puntuacion'))['valor']
            or 0
        )
        PerfilEmpresa.objects.filter(pk=perfil.pk).update(
            calificacion_promedio=round(float(promedio), 2),
        )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0018_perfildesarrollador_telefono'),
        ('proyectos', '0017_alter_valoracion_desarrollador_and_more'),
        ('contrataciones', '0013_alter_contratacion_desarrollador_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
