from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('notificaciones', '0005_notificacion_idx_notif_usr_leida_and_more'),
        ('proyectos', '0020_proyecto_fecha_cumplimiento'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AvisoCumplimiento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_cumplimiento', models.DateField()),
                ('etapa', models.CharField(max_length=12)),
                ('notificacion', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='notificaciones.notificacion')),
                ('proyecto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='proyectos.proyecto')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'avisos_cumplimiento',
                'constraints': [models.UniqueConstraint(
                    fields=('proyecto', 'usuario', 'fecha_cumplimiento', 'etapa'),
                    name='uniq_aviso_cumplimiento_destinatario',
                )],
            },
        ),
    ]
