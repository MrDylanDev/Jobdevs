import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from proyectos.models import Proyecto, Entregable, Equipo
from contrataciones.models import Contratacion
from avances.models import Avance

User = get_user_model()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestAvanceWorkflowE2E:

    def _setup_data(self):
        """Idempotent setup for avance workflow."""
        empresa, _ = User.objects.get_or_create(
            username='e2e_av_emp',
            defaults={'email': 'e2e_av_emp@t.jobdevs', 'nombre': 'E2E Emp',
                      'rol': 'empresa', 'estado': 'activo'},
        )
        empresa.set_password('E2ETest123!')
        empresa.save()
        dev, _ = User.objects.get_or_create(
            username='e2e_av_dev',
            defaults={'email': 'e2e_av_dev@t.jobdevs', 'nombre': 'E2E Dev',
                      'rol': 'desarrollador', 'estado': 'activo'},
        )
        dev.set_password('E2ETest123!')
        dev.save()
        proyecto, _ = Proyecto.objects.get_or_create(
            empresa=empresa, titulo='E2E Proy Av',
            defaults={'descripcion': 'Test', 'tipo_solucion': 'sitio_web',
                      'estado': 'en_desarrollo'},
        )
        equipo, _ = Equipo.objects.get_or_create(proyecto=proyecto, nombre='Eq')
        equipo.miembros.add(dev)
        Contratacion.objects.get_or_create(
            proyecto=proyecto, empresa=empresa, desarrollador=dev,
            defaults={'estado': 'activa'},
        )
        Entregable.objects.get_or_create(
            proyecto=proyecto, titulo='Hito Frontend',
            defaults={'descripcion': 'UI', 'estado': 'pendiente'},
        )
        Entregable.objects.get_or_create(
            proyecto=proyecto, titulo='Hito Backend',
            defaults={'descripcion': 'API', 'estado': 'pendiente'},
        )
        return empresa, dev, proyecto

    def _login_as(self, page, live_server, username, password):
        """Login helper - handles redirect to landing with modal."""
        page.goto(live_server.url + reverse('login'))
        page.wait_for_timeout(2000)
        # May have redirected to landing with ?login=1
        # Wait for modal if visible, or open it manually
        modal = page.locator('#loginModal')
        if not modal.is_visible():
            # Click AUTH button to open
            page.locator('[data-bs-target="#loginModal"]').click()
            page.wait_for_timeout(1000)
        if not modal.is_visible():
            # Force via JS
            page.evaluate('() => new bootstrap.Modal(document.getElementById("loginModal")).show()')
            page.wait_for_timeout(1000)
        page.fill('#username', username)
        page.fill('#password', password)
        page.locator('.btn-submit-tech:has-text("INGRESAR")').click(force=True)
        page.wait_for_timeout(2000)

    def test_dev_submits_avance(self, page, live_server):
        """Dev submits an avance with archivo_url, hito moves to en_revision."""
        empresa, dev, proyecto = self._setup_data()

        self._login_as(page, live_server, 'e2e_av_dev', 'E2ETest123!')

        url = live_server.url + reverse('registrar_avance', args=[proyecto.id])
        page.goto(url)
        page.wait_for_timeout(1000)

        page.select_option('select[name="entregable_id"]', index=1)
        page.fill('textarea[name="descripcion"]', 'Frontend implementado')
        page.fill('input[name="archivo_url"]', 'https://github.com/test/pr/1')
        page.locator('button:has-text("Enviar Avance")').click(force=True)
        page.wait_for_timeout(2000)

        avance = Avance.objects.filter(proyecto=proyecto).first()
        assert avance is not None
        assert avance.estado == 'pendiente'
        assert avance.archivo_url == 'https://github.com/test/pr/1'
        avance.entregable.refresh_from_db()
        assert avance.entregable.estado == 'en_revision'

    def test_empresa_acepta_avance(self, page, live_server):
        """Empresa accepts avance → hito completado."""
        empresa, dev, proyecto = self._setup_data()

        # Dev submits first
        from django.test import Client
        c = Client()
        c.login(username='e2e_av_dev', password='E2ETest123!')
        c.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': Entregable.objects.filter(proyecto=proyecto, estado='pendiente').first().id,
            'descripcion': 'Backend listo',
            'archivo_url': 'https://github.com/test/pr/2',
        })

        # Empresa accepts via browser
        self._login_as(page, live_server, 'e2e_av_emp', 'E2ETest123!')

        url = live_server.url + reverse('ver_avances', args=[proyecto.id])
        page.goto(url)
        page.wait_for_timeout(1000)

        page.fill('textarea[name="comentario"]', 'Aprobado!')
        page.locator('button[name="accion"][value="aceptar"]').click(force=True)
        page.wait_for_timeout(2000)

        avance = Avance.objects.filter(proyecto=proyecto).first()
        avance.refresh_from_db()
        assert avance.estado == 'aceptado'
        avance.entregable.refresh_from_db()
        assert avance.entregable.estado == 'completado'

    def test_empresa_rechaza_avance(self, page, live_server):
        """Empresa rejects avance → hito pendiente, proyecto en_desarrollo."""
        empresa, dev, proyecto = self._setup_data()

        # Dev submits via client
        from django.test import Client
        c = Client()
        c.login(username='e2e_av_dev', password='E2ETest123!')
        hito = Entregable.objects.filter(proyecto=proyecto, estado='pendiente').first()
        c.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': hito.id,
            'descripcion': 'Endpoint usuarios',
            'archivo_url': 'https://github.com/test/pr/3',
        })

        # Empresa rejects via browser
        self._login_as(page, live_server, 'e2e_av_emp', 'E2ETest123!')

        url = live_server.url + reverse('ver_avances', args=[proyecto.id])
        page.goto(url)
        page.wait_for_timeout(1000)

        page.fill('textarea[name="comentario"]', 'Falta el endpoint /users')
        page.locator('button[name="accion"][value="rechazar"]').click(force=True)
        page.wait_for_timeout(2000)

        avance = Avance.objects.filter(proyecto=proyecto).first()
        avance.refresh_from_db()
        assert avance.estado == 'rechazado'
        assert 'endpoint' in avance.comentario_revision
        avance.entregable.refresh_from_db()
        assert avance.entregable.estado == 'pendiente'
        proyecto.refresh_from_db()
        assert proyecto.estado == 'en_desarrollo'
