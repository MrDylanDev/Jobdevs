from django.db import migrations

CATEGORIAS = [
    ('sitio_web', 'Sitio Web'),
    ('aplicacion_movil', 'Aplicación Móvil'),
    ('automatizacion', 'Automatización'),
    ('sistema_escritorio', 'Sistema de Escritorio'),
    ('otro', 'Otro'),
]


def seed_categorias(apps, schema_editor):
    CategoriaSolucion = apps.get_model('proyectos', 'CategoriaSolucion')
    Proyecto = apps.get_model('proyectos', 'Proyecto')
    for slug, nombre in CATEGORIAS:
        categoria, _ = CategoriaSolucion.objects.get_or_create(
            slug=slug, defaults={'nombre': nombre},
        )
        Proyecto.objects.filter(
            tipo_solucion=slug, categoria__isnull=True,
        ).update(categoria=categoria)


def unseed_categorias(apps, schema_editor):
    CategoriaSolucion = apps.get_model('proyectos', 'CategoriaSolucion')
    Proyecto = apps.get_model('proyectos', 'Proyecto')
    slugs = [slug for slug, _ in CATEGORIAS]
    Proyecto.objects.filter(categoria__slug__in=slugs).update(categoria=None)
    CategoriaSolucion.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('proyectos', '0012_categoriasolucion_proyecto_categoria'),
    ]

    operations = [
        migrations.RunPython(seed_categorias, unseed_categorias),
    ]
