from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('proyectos', '0020_proyecto_fecha_cumplimiento'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RegularizacionCierreProyecto',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('fecha_cierre', models.DateTimeField()),
                ('motivo', models.TextField()),
                (
                    'referencia_evidencia',
                    models.CharField(blank=True, default='', max_length=300),
                ),
                ('registrado_en', models.DateTimeField(auto_now_add=True)),
                (
                    'proyecto',
                    models.OneToOneField(
                        db_column='proyecto_id',
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='regularizacion_cierre',
                        to='proyectos.proyecto',
                    ),
                ),
                (
                    'registrado_por',
                    models.ForeignKey(
                        db_column='registrado_por_id',
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='regularizaciones_cierre_registradas',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Regularización de cierre de proyecto',
                'verbose_name_plural': 'Regularizaciones de cierre de proyectos',
                'db_table': 'regularizaciones_cierre_proyecto',
            },
        ),
    ]
