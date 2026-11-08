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
