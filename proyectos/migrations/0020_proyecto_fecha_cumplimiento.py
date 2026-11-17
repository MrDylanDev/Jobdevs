from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('proyectos', '0019_proyecto_ciudad_proyecto_modalidad'),
    ]

    operations = [
        migrations.AddField(
            model_name='proyecto',
            name='fecha_cumplimiento',
            field=models.DateField(blank=True, null=True),
        ),
    ]
