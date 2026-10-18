
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def rename_cedula_to_identificacion_if_exists(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cols = [col.name.lower() for col in connection.introspection.get_table_description(cursor, 'usuarios')]
        if 'cedula' in cols and 'identificacion' not in cols:
            schema_editor.execute(
                f'ALTER TABLE {schema_editor.quote_name("usuarios")} RENAME COLUMN {schema_editor.quote_name("cedula")} TO {schema_editor.quote_name("identificacion")};'
            )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_alter_usuario_options_usuario_nombre_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameField(
                    model_name='usuario',
                    old_name='cedula',
                    new_name='identificacion',
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    rename_cedula_to_identificacion_if_exists,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
        ),
        migrations.AlterField(
            model_name='perfildesarrollador',
            name='usuario',
            field=models.OneToOneField(db_column='usuario_id', on_delete=django.db.models.deletion.CASCADE, related_name='perfil_desarrollador', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='perfilempresa',
            name='usuario',
            field=models.OneToOneField(db_column='usuario_id', on_delete=django.db.models.deletion.CASCADE, related_name='perfil_empresa', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='perfildesarrollador',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AddField(
            model_name='perfilempresa',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
