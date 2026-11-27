import pytest
from django.urls import reverse

from logs.models import LogAuditoria
from usuarios.models import PerfilDesarrollador, PerfilEmpresa, Usuario
from usuarios.services_sena import admin_resolver_verificacion_desarrollador


def _crear_admin():
    return Usuario.objects.create_user(
        username='admin_intentos',
        email='admin_intentos@test.com',
        password='Password123',
        rol='administrador',
        nombre='Admin Intentos',
    )


def _crear_dev(username='dev_intentos'):
    user = Usuario.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password='Password123',
        rol='desarrollador',
        nombre='Dev Intentos',
    )
    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=user)
    perfil.ficha = '2900001'
    perfil.estado_verificacion = 'en_revision'
    perfil.save()
    return user, perfil


def _crear_empresa(username='emp_intentos'):
    user = Usuario.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password='Password123',
        rol='empresa',
        nombre='Empresa Intentos',
    )
    perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=user)
    perfil.razon_social = 'Empresa Intentos SAS'
    perfil.estado_verificacion = 'en_revision'
    perfil.save()
    return user, perfil


@pytest.mark.django_db
def test_dev_rechazo_incrementa_intentos_y_no_depura_antes_del_tercero():
    admin = _crear_admin()
    user, perfil = _crear_dev('dev_2_rechazos')

    # solicitar_documento no consume intento
    ok, _ = admin_resolver_verificacion_desarrollador(
        perfil.id, admin, 'solicitar_documento', notas='Foto borrosa'
    )
    assert ok is True
    perfil.refresh_from_db()
    assert perfil.intentos_verificacion == 0

    # Reenvío y 1er rechazo
    perfil.estado_verificacion = 'en_revision'
    perfil.save()
    ok, _ = admin_resolver_verificacion_desarrollador(
        perfil.id, admin, 'rechazar', notas='Documento inválido 1'
    )
    assert ok is True
    perfil.refresh_from_db()
    assert perfil.intentos_verificacion == 1
    assert Usuario.objects.filter(id=user.id, is_active=True).exists()

    # Reenvío y 2do rechazo
    perfil.estado_verificacion = 'en_revision'
    perfil.save()
    ok, _ = admin_resolver_verificacion_desarrollador(
        perfil.id, admin, 'rechazar', notas='Documento inválido 2'
    )
    assert ok is True
    perfil.refresh_from_db()
    assert perfil.intentos_verificacion == 2
    assert Usuario.objects.filter(id=user.id, is_active=True).exists()


@pytest.mark.django_db
def test_dev_tercer_rechazo_sin_actividad_elimina_cuenta():
    admin = _crear_admin()
    user, perfil = _crear_dev('dev_3_rechazos_del')
    perfil.intentos_verificacion = 2
    perfil.save()

    ok, msg = admin_resolver_verificacion_desarrollador(
        perfil.id, admin, 'rechazar', notas='Documento inválido 3'
    )
    assert ok is True
    assert 'eliminada' in msg.lower()
    assert not Usuario.objects.filter(id=user.id).exists()
    assert LogAuditoria.objects.filter(
        tabla_afectada='usuarios',
        registro_id=user.id,
        accion__icontains='intentos',
    ).exists()


@pytest.mark.django_db
def test_dev_tercer_rechazo_con_actividad_desactiva_cuenta():
    from mensajes.models import Mensaje

    admin = _crear_admin()
    user, perfil = _crear_dev('dev_3_rechazos_deact')
    perfil.intentos_verificacion = 2
    perfil.save()

    Mensaje.objects.create(remitente=user, receptor=admin, contenido='Hola')

    ok, msg = admin_resolver_verificacion_desarrollador(
        perfil.id, admin, 'rechazar', notas='Documento inválido 3'
    )
    assert ok is True
    assert 'desactivada' in msg.lower()
    user.refresh_from_db()
    assert user.is_active is False
    assert user.estado == 'inactivo'


@pytest.mark.django_db
def test_empresa_tercer_rechazo_sin_actividad_elimina_cuenta(client):
    admin = _crear_admin()
    user, perfil = _crear_empresa('emp_3_rechazos_del')
    perfil.intentos_verificacion = 2
    perfil.save()

    client.force_login(admin)
    url = reverse('admin_resolver_verificacion_empresa', args=[perfil.id])
    resp = client.post(url, {'accion': 'rechazar', 'notas': 'RUT inválido 3'})
    assert resp.status_code == 302
    assert not Usuario.objects.filter(id=user.id).exists()
    assert LogAuditoria.objects.filter(
        tabla_afectada='usuarios',
        registro_id=user.id,
        accion__icontains='intentos',
    ).exists()


@pytest.mark.django_db
def test_empresa_tercer_rechazo_con_actividad_desactiva_cuenta(client):
    from mensajes.models import Mensaje

    admin = _crear_admin()
    user, perfil = _crear_empresa('emp_3_rechazos_deact')
    perfil.intentos_verificacion = 2
    perfil.save()

    Mensaje.objects.create(remitente=user, receptor=admin, contenido='Consulta')

    client.force_login(admin)
    url = reverse('admin_resolver_verificacion_empresa', args=[perfil.id])
    resp = client.post(url, {'accion': 'rechazar', 'notas': 'RUT inválido 3'})
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.is_active is False
    assert user.estado == 'inactivo'
