from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('contrataciones', '0016_contratodigital_medio_pago'),
    ]

    operations = [
        migrations.AddField(
            model_name='contratodigital',
            name='perfil_profesional',
            field=models.JSONField(
                blank=True,
                null=True,
                help_text='Evidencia del perfil y mensaje de postulación fijada en la primera firma.',
            ),
        ),
    ]
