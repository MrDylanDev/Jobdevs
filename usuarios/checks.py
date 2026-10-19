from django.core.checks import register, Tags


@register(Tags.database)
def check_sql_dependencies(app_configs, **kwargs):
    """
    Chequeo de dependencias de base de datos (SCRUM-186).
    En PostgreSQL 16 y SQLite, la integridad y reglas de negocio están centralizadas
    en el ORM y modelos de Django. Los triggers legados de MySQL quedan deprecados.
    """
    return []
