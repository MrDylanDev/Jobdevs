import pytest
from django.db import connection
from usuarios.models import Usuario


@pytest.mark.django_db
def test_usuarios_column_identificacion_exists():
    with connection.cursor() as cursor:
        cols = [col.name.lower() for col in connection.introspection.get_table_description(cursor, 'usuarios')]
    assert 'identificacion' in cols
    assert 'cedula' not in cols


@pytest.mark.django_db
def test_usuario_identificacion_query():
    usuario = Usuario.objects.create_user(
        username='testident',
        email='testident@example.com',
        password='Password123!',
        identificacion='123456789',
        rol='desarrollador',
    )
    reloaded = Usuario.objects.get(id=usuario.id)
    assert reloaded.identificacion == '123456789'
