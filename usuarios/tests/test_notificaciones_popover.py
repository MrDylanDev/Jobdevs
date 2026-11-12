import re
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from notificaciones.models import Notificacion
from usuarios.views._helpers import get_notificaciones_context

User = get_user_model()


def _html(response):
    return response.content.decode()


def test_dev_dashboard_incluye_popover_notificaciones(dev_client, desarrollador_user):
    Notificacion.objects.create(
        usuario=desarrollador_user,
        tipo='mensaje',
        mensaje='Mensaje popover dev',
        leida=False,
    )

    response = dev_client.get(reverse('dashboard_desarrollador'))
    html = _html(response)

    assert response.status_code == 200
    assert 'id="notifPopover"' in html
    assert 'data-notif-toggle' in html
    assert 'Mensaje popover dev' in html
    assert 'notificaciones_popover.js' in html
    assert 'notificaciones_popover.css' in html
    assert 'is-unread' in html
    assert 'data-notif-mark-all' in html
    assert 'data-notif-clear' in html
    # "Ver todas" no debe sacar del dashboard: es un botón, no un enlace.
    assert re.search(r'<button[^>]*data-notif-ver-todas', html)
    assert re.search(r'<a[^>]*data-notif-ver-todas', html) is None
    assert 'class="notif-popover-footer" href=' not in html


def test_admin_dashboard_incluye_popover_notificaciones(admin_client, admin_user):
    Notificacion.objects.create(
        usuario=admin_user,
        tipo='alerta',
        mensaje='Alerta popover admin',
        leida=True,
    )

    response = admin_client.get(reverse('dashboard_admin'))
    html = _html(response)

    assert response.status_code == 200
    assert 'id="notifPopover"' in html
    assert 'data-notif-toggle' in html
    assert 'Alerta popover admin' in html
    assert 'notificaciones_popover.js' in html
    assert 'notificaciones_popover.css' in html
    # Una notificación ya leída no debe marcarse como no leída.
    assert 'is-unread' not in html
    assert re.search(r'<button[^>]*data-notif-mark-all[^>]*hidden', html)
    assert re.search(r'<button[^>]*data-notif-ver-todas', html)
    assert re.search(r'<a[^>]*data-notif-ver-todas', html) is None
    assert 'class="notif-popover-footer" href=' not in html


def test_get_notificaciones_context_expone_id_y_tipo_display(desarrollador_user):
    notificacion = Notificacion.objects.create(
        usuario=desarrollador_user,
        tipo='postulacion',
        mensaje='Contexto',
    )

    notificaciones, pendientes = get_notificaciones_context(desarrollador_user.id)

    assert pendientes == 1
    assert notificaciones[0]['id'] == notificacion.id
    assert notificaciones[0]['tipo'] == 'postulacion'
    assert notificaciones[0]['tipo_display'] == 'Postulación'
    assert notificaciones[0]['leida'] is False


def test_api_lista_notificaciones_devuelve_historial(dev_client, desarrollador_user):
    no_leida = Notificacion.objects.create(
        usuario=desarrollador_user, tipo='mensaje', mensaje='No leída', leida=False,
    )
    leida = Notificacion.objects.create(
        usuario=desarrollador_user, tipo='avance', mensaje='Leída', leida=True,
    )

    response = dev_client.get(reverse('notificaciones_api_lista'))

    assert response.status_code == 200
    data = response.json()
    ids = {item['id'] for item in data['notificaciones']}
    assert ids == {no_leida.id, leida.id}
    assert data['unread_count'] == 1
    item = next(n for n in data['notificaciones'] if n['id'] == leida.id)
    assert item['mensaje'] == 'Leída'
    assert item['tipo'] == 'avance'
    assert item['tipo_display'] == 'Avance'
    assert item['leida'] is True
    assert item['fecha']


def test_api_lista_notificaciones_respeta_limite(dev_client, desarrollador_user):
    for indice in range(3):
        Notificacion.objects.create(
            usuario=desarrollador_user, tipo='otro', mensaje=f'Notificación {indice}',
        )

    response = dev_client.get(reverse('notificaciones_api_lista'), {'limite': 1})

    assert response.status_code == 200
    assert len(response.json()['notificaciones']) == 1


def test_api_lista_notificaciones_requiere_login(client):
    response = client.get(reverse('notificaciones_api_lista'))

    assert response.status_code == 302
    assert reverse('login') in response.url


def test_api_lista_notificaciones_no_expone_notificaciones_de_otros_usuarios(
    dev_client, desarrollador_user
):
    """La API debe filtrar estrictamente por request.user."""
    otra_persona = User.objects.create_user(
        username='otro_dev',
        email='otro@test.jobdevs',
        password='Password123!',
        rol='desarrollador',
    )
    propia = Notificacion.objects.create(
        usuario=desarrollador_user, tipo='mensaje', mensaje='Solo para el usuario actual',
    )
    ajena = Notificacion.objects.create(
        usuario=otra_persona, tipo='alerta', mensaje='Información privada de otro usuario',
    )

    response = dev_client.get(reverse('notificaciones_api_lista'))

    assert response.status_code == 200
    data = response.json()
    ids = {item['id'] for item in data['notificaciones']}
    mensajes = {item['mensaje'] for item in data['notificaciones']}

    assert ids == {propia.id}
    assert ajena.id not in ids
    assert 'Información privada de otro usuario' not in mensajes
    assert data['unread_count'] == 1


def test_api_lista_notificaciones_usa_zona_horaria_local(dev_client, desarrollador_user):
    """La fecha se formatea en America/Bogota, no en UTC."""
    notificacion = Notificacion.objects.create(
        usuario=desarrollador_user, tipo='avance', mensaje='Fecha local',
    )
    # 15/01/2026 12:00 UTC = 07:00 en America/Bogota (UTC-5).
    fecha_utc = datetime(2026, 1, 15, 12, 0, tzinfo=dt_timezone.utc)
    Notificacion.objects.filter(pk=notificacion.pk).update(fecha=fecha_utc)

    response = dev_client.get(reverse('notificaciones_api_lista'))

    assert response.status_code == 200
    item = next(n for n in response.json()['notificaciones'] if n['id'] == notificacion.id)
    assert item['fecha'] == '15/01/2026 07:00'
    # Comprobación explícita contra la conversión de Django.
    assert item['fecha'] == timezone.localtime(fecha_utc).strftime('%d/%m/%Y %H:%M')
