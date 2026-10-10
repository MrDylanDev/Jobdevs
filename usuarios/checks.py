from django.core.checks import Warning, register, Tags
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError

# Solo los triggers son necesarios — views y procedures ya están migrados al ORM
REQUIRED_TRIGGERS = [
    'trg_validar_vacantes_antes_de_contratar',
    'trg_notificacion_mensaje',
    'trg_nueva_postulacion',
    'trg_actualizar_proyectos_completados',
    'trg_log_nuevo_usuario',
    'trg_registro_sesion',
    'trg_log_usuario_modificado',
]


@register(Tags.database)
def check_sql_dependencies(app_configs, **kwargs):
    errors = []
    # Los triggers en SQL crudo solo aplican al backend legado MySQL.
    # En PostgreSQL y SQLite la lógica está centralizada en el ORM de Django.
    if connection.vendor != 'mysql':
        return errors

    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TRIGGERS")
            existing_triggers = {row[0].lower() for row in cursor.fetchall()}

            for trigger in REQUIRED_TRIGGERS:
                if trigger.lower() not in existing_triggers:
                    errors.append(
                        Warning(
                            f"Falta el trigger requerido: '{trigger}'.",
                            hint=(
                                "Ejecutá el script 'database/init.sql' en la base de datos "
                                "para restaurar los triggers necesarios."
                            ),
                            id='usuarios.W001',
                        )
                    )
    except (OperationalError, ProgrammingError):
        pass

    return errors
