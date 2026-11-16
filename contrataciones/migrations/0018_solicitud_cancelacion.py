from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('contrataciones', '0017_contratodigital_perfil_profesional'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SolicitudCancelacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('causal', models.CharField(choices=[
                    ('acuerdo_mutuo', 'Acuerdo mutuo'),
                    ('incumplimiento', 'Incumplimiento de obligaciones'),
                    ('inactividad', 'Inactividad demostrable'),
                    ('fuerza_mayor', 'Fuerza mayor'),
                ], max_length=25)),
                ('motivo', models.TextField()),
                ('evidencia', models.TextField(blank=True)),
                ('estado', models.CharField(choices=[
                    ('pendiente_acuerdo', 'Pendiente de confirmación del desarrollador'),
                    ('pendiente_revision', 'Pendiente de revisión administrativa'),
                    ('aprobada', 'Aprobada'),
                    ('rechazada', 'Rechazada'),
                ], max_length=25)),
                ('dictamen', models.TextField(blank=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_resolucion', models.DateTimeField(blank=True, null=True)),
                ('contratacion', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='solicitudes_cancelacion', to='contrataciones.contratacion',
                )),
                ('solicitante', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='+', to=settings.AUTH_USER_MODEL,
                )),
                ('resuelto_por', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='+', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'solicitudes_cancelacion'},
        ),
        migrations.AddConstraint(
            model_name='solicitudcancelacion',
            constraint=models.UniqueConstraint(
                condition=models.Q(estado__in=['pendiente_acuerdo', 'pendiente_revision']),
                fields=('contratacion',), name='uq_cancelacion_pendiente_contrato',
            ),
        ),
    ]
