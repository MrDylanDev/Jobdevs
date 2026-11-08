from django.urls import reverse

from notificaciones.models import Notificacion
from usuarios.views._helpers import get_notificaciones_context


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
    assert 'data-notif-ver-todas' in html
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
    assert 'data-notif-mark-all' not in html
    assert 'data-notif-ver-todas' in html
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
