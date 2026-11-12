import pytest
from django.test import AsyncRequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from notificaciones.models import Notificacion
from notificaciones.views import (
    notificaciones_event_generator,
    notificaciones_event_generator_async,
    notificaciones_stream,
)

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestNotificacionesSSE:
    """Tests unitarios y de integración para Server-Sent Events (SCRUM-188)."""

    def test_sse_endpoint_rechaza_anonimo(self, client):
        """Usuarios no autenticados reciben 401 Unauthorized."""
        url = reverse('notificaciones_stream')
        response = client.get(url)
        assert response.status_code == 401

    def test_sse_endpoint_headers_para_autenticado(self, auth_client, desarrollador_user):
        """Verificar headers esenciales para streaming SSE y proxies inversos."""
        url = reverse('notificaciones_stream')
        response = auth_client.get(url + '?max_iterations=1&interval=0.1')
        assert response.status_code == 200
        assert 'text/event-stream' in response['Content-Type']
        assert 'no-cache' in response['Cache-Control']
        assert response['X-Accel-Buffering'] == 'no'
        # El cliente de tests usa WSGI: el driver debe ser el síncrono.
        assert response.streaming is True
        assert response.is_async is False

    def test_sse_endpoint_ignora_params_en_produccion(self, auth_client, desarrollador_user, monkeypatch):
        """SCRUM-447: En producción no se permite forzar interval bajo ni max_iterations vía query params."""
        from django.test import override_settings
        import notificaciones.views as n_views

        generator_args = {}

        def mock_generator(user, interval=2.0, max_iterations=None):
            generator_args['interval'] = interval
            generator_args['max_iterations'] = max_iterations
            def _empty():
                yield "event: init\ndata: {}\n\n"
            return _empty()

        monkeypatch.setattr(n_views, 'notificaciones_event_generator', mock_generator)

        with override_settings(TESTING=False):
            url = reverse('notificaciones_stream')
            response = auth_client.get(url + '?interval=0.01&max_iterations=5')
            assert response.status_code == 200
            assert generator_args['interval'] == 2.0
            assert generator_args['max_iterations'] is None

    def test_generador_emite_init_y_notificacion(self):
        """El generador emite evento init inicial y evento notificacion al detectar nuevas."""
        user = User.objects.create_user(
            username='sse_user', email='sse@test.jobdevs', password='Password123!', rol='desarrollador'
        )
        Notificacion.objects.create(
            usuario=user, mensaje='Notif previa', tipo='alerta'
        )

        gen = notificaciones_event_generator(user, interval=0.05, max_iterations=2)
        # Primer evento: init
        ev1 = next(gen)
        assert ev1.startswith("event: init\n")
        assert '"unread_count": 1' in ev1

        # Crear nueva notificación mientras corre el generador
        Notificacion.objects.create(
            usuario=user, mensaje='Nueva notif SSE', tipo='postulacion'
        )

        # Segundo evento: notificacion
        ev2 = next(gen)
        assert ev2.startswith("event: notificacion\n")
        assert "Nueva notif SSE" in ev2
        assert '"unread_count": 2' in ev2

    def test_generador_emite_sync_al_marcar_leidas(self):
        """El generador emite evento sync cuando el conteo no leído cambia sin nuevas notificaciones."""
        user = User.objects.create_user(
            username='sse_user_sync', email='ssesync@test.jobdevs', password='Password123!', rol='empresa'
        )
        notif = Notificacion.objects.create(
            usuario=user, mensaje='Para leer', tipo='mensaje'
        )

        gen = notificaciones_event_generator(user, interval=0.05, max_iterations=2)
        ev1 = next(gen)
        assert '"unread_count": 1' in ev1

        # Marcar como leída
        notif.leida = True
        notif.save(update_fields=['leida'])

        # Siguiente evento: sync
        ev2 = next(gen)
        assert ev2.startswith("event: sync\n")
        assert '"unread_count": 0' in ev2

    def test_templates_incluyen_script_notificaciones_sse(self, client):
        """Los dashboards y templates base cargan el cliente notificaciones_sse.js."""
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        factory = RequestFactory()
        user = User.objects.create_user(
            username='tpl_user', email='tpl@test.jobdevs', password='Password123!', rol='desarrollador'
        )

        request = factory.get('/')
        request.user = user

        # Verificar render de base.html
        base_rendered = render_to_string('base.html', request=request)
        assert 'notificaciones_sse.js' in base_rendered

        # Verificar presencia en templates de dashboards
        for tpl in ['Desarrollador/Desarrollador.html', 'empresa/empresa.html', 'administrador/Administrador.html']:
            with open(f'templates/{tpl}', 'r', encoding='utf-8') as f:
                content = f.read()
            assert 'notificaciones_sse.js' in content, f"Template {tpl} debe cargar notificaciones_sse.js"


@pytest.mark.asyncio
async def test_generador_async_emite_init(desarrollador_user):
    """El driver ASGI emite el evento inicial sin bloquear el stream."""
    generador = notificaciones_event_generator_async(
        desarrollador_user, interval=0.05, max_iterations=1
    )

    evento = await anext(generador)
    assert evento.startswith("event: init\n")
    assert '"tipo": "init"' in evento

    await generador.aclose()


def test_sse_bajo_asgi_usa_iterador_asincrono(desarrollador_user):
    """
    Bajo ASGI (producción: Gunicorn + UvicornWorker) la respuesta debe
    exponer un iterador async; un iterador síncrono infinito se consumiría
    completo con sync_to_async(list) y nunca enviaría el primer evento.

    Se construye la ASGIRequest directamente para no depender del cliente
    async (SQLite bloquea la BD compartida entre hilos al autenticar).
    """
    request = AsyncRequestFactory().get(reverse('notificaciones_stream'))
    request.user = desarrollador_user

    response = notificaciones_stream(request)

    assert response.status_code == 200
    assert response.streaming is True
    assert response.is_async is True
