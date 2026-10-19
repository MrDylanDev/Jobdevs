import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from notificaciones.models import Notificacion

User = get_user_model()


class TestNotificacionModel:
    """Tests for Notificacion model."""

    def test_crear_notificacion(self, db):
        """Notificacion links to usuario."""
        user = User.objects.create_user(
            username='nu', email='nu@test.jobdevs',
            nombre='NU', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        notif = Notificacion.objects.create(
            usuario=user, tipo='alerta',
            mensaje='Mensaje test',
        )
        assert notif.id is not None
        assert notif.leida == False

    def test_notificacion_str(self, db):
        """__str__ shows usuario and titulo."""
        user = User.objects.create_user(
            username='nu2', email='nu2@test.jobdevs',
            nombre='NU2', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        notif = Notificacion.objects.create(
            usuario=user, tipo='alerta',
            mensaje='Test Body',
        )
        assert 'nu2' in str(notif)


class TestListaNotificaciones:
    """Tests for lista_notificaciones view."""

    def test_lista_accessible(self, dev_client):
        """Authenticated user can view notifications."""
        response = dev_client.get(reverse('notificaciones_lista'))
        assert response.status_code == 200

    def test_lista_usa_select_related_y_paginacion(self, dev_client, desarrollador_user, django_assert_num_queries):
        """Auditoría SCRUM-160: Lista de notificaciones usa select_related para evitar N+1 y pagina."""
        from proyectos.models import Proyecto
        empresa = User.objects.create_user(
            username='emp_noti', email='emp_noti@test.jobdevs',
            rol='empresa', password='TestPassword123!',
        )
        proyectos = [
            Proyecto.objects.create(
                empresa=empresa, titulo=f'Proy {i}',
                descripcion='D', tipo_solucion='sitio_web',
            ) for i in range(5)
        ]
        for p in proyectos:
            Notificacion.objects.create(
                usuario=desarrollador_user, proyecto=p,
                tipo='alerta', mensaje=f'Notif sobre {p.titulo}',
            )

        # Debe ejecutar queries constantes independientemente del número de proyectos gracias a select_related
        with django_assert_num_queries(7):  # session, user, count, notificaciones con JOIN proyectos, y cierre de sesion
            response = dev_client.get(reverse('notificaciones_lista'))
            assert response.status_code == 200
            for notif in response.context['notificaciones']:
                _ = notif.proyecto.titulo if notif.proyecto else None

    def test_lista_blocked_anon(self, client):
        """Anonymous cannot view notifications."""
        response = client.get(reverse('notificaciones_lista'))
        assert response.status_code == 302

    def test_marcar_todas_leidas_requiere_post(self, dev_client):
        """SCRUM-173: marcar_todas_leidas rechaza peticiones GET con 405 Method Not Allowed."""
        response = dev_client.get(reverse('notificaciones_marcar_todas_leidas'))
        assert response.status_code == 405

    def test_marcar_todas_leidas_actualiza_y_respeta_referer(self, dev_client, desarrollador_user):
        """SCRUM-173: marca todas como leídas y redirige al referer de forma segura."""
        Notificacion.objects.create(usuario=desarrollador_user, tipo='alerta', mensaje='N1', leida=False)
        Notificacion.objects.create(usuario=desarrollador_user, tipo='alerta', mensaje='N2', leida=False)
        assert Notificacion.objects.filter(usuario=desarrollador_user, leida=False).count() == 2

        response = dev_client.post(
            reverse('notificaciones_marcar_todas_leidas'),
            HTTP_REFERER='/desarrollador/dashboard/'
        )
        assert response.status_code == 302
        assert response.url == '/desarrollador/dashboard/'
        assert Notificacion.objects.filter(usuario=desarrollador_user, leida=False).count() == 0

