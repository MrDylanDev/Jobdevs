from django.db import migrations


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
        ('usuarios', '0012_alter_usuario_managers'),
    ]

    operations = [
        migrations.RunPython(
            rename_cedula_to_identificacion_if_exists,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
