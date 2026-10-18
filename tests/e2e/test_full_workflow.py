import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client
from proyectos.models import Proyecto, Entregable, Equipo, Valoracion
from contrataciones.models import Contratacion
from avances.models import Avance
from mensajes.models import Mensaje

User = get_user_model()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestFullWorkflowE2E:

    def test_full_project_lifecycle(self, page, live_server):
        """
        Complete project lifecycle E2E:
        1. Create empresa + 2 devs, publish project, both apply, empresa accepts
        2. Create groups, assign hitos to groups
        3. Devs submit avances via browser
        4. Empresa accepts one, rejects another (with comment)
        5. Everyone chats in workspace
        6. Finalize project, rate both sides
        7. Verify history
        """
        client = Client()

        empresa = User.objects.create_user(
            username='full_emp', email='full_emp@t.jobdevs',
            nombre='Full Empresa', rol='empresa', estado='activo',
            password='FullPass123!',
        )
        # Ensure admin exists for dashboard templates
        if not User.objects.filter(rol='administrador').exists():
            User.objects.create_user(
                username='full_admin', email='full_admin@t.jobdevs',
                nombre='Full Admin', rol='administrador', estado='activo',
                password='FullPass123!',
            )
        dev1 = User.objects.create_user(
            username='full_dev1', email='full_dev1@t.jobdevs',
            nombre='Full Dev 1', rol='desarrollador', estado='activo',
            password='FullPass123!',
        )
        dev2 = User.objects.create_user(
            username='full_dev2', email='full_dev2@t.jobdevs',
            nombre='Full Dev 2', rol='desarrollador', estado='activo',
            password='FullPass123!',
        )

        # ── Empresa publishes ──
        client.login(username='full_emp', password='FullPass123!')
        client.post(reverse('crear_proyecto'), {
            'titulo': 'Full Test Project', 'descripcion': 'E2E complete',
            'tipo_solucion': 'sitio_web', 'prioridad': 'alta', 'vacantes': '2',
        })
        proyecto = Proyecto.objects.get(titulo='Full Test Project')
        assert proyecto.estado == 'publicado'

        # ── Both devs apply ──
        from postulaciones.models import Postulacion
        for dev in [dev1, dev2]:
            c = Client()
            c.login(username=dev.username, password='FullPass123!')
            c.post(reverse('postularse_a_proyecto', args=[proyecto.id]), {
                'carta': f'Hola, soy {dev.nombre}',
                'experiencia': 'Django+React', 'link': 'https://github.com/test',
            })
        assert Postulacion.objects.filter(proyecto=proyecto).count() == 2

        # ── Empresa accepts both ──
        client.login(username='full_emp', password='FullPass123!')
        for post in Postulacion.objects.filter(proyecto=proyecto):
            client.post(reverse('aceptar_postulacion', args=[post.id]))
        proyecto.refresh_from_db()
        assert proyecto.estado == 'en_desarrollo'

        # ── Groups ──
        grupo_a = Equipo.objects.create(proyecto=proyecto, nombre='Grupo Frontend')
        grupo_a.miembros.add(dev1)
        grupo_b = Equipo.objects.create(proyecto=proyecto, nombre='Grupo Backend')
        grupo_b.miembros.add(dev2)
        eq, _ = Equipo.objects.get_or_create(proyecto=proyecto, nombre=f'Equipo {proyecto.titulo}')
        eq.miembros.add(dev1, dev2)

        # ── Hitos ──
        hito_general = Entregable.objects.create(
            proyecto=proyecto, titulo='Hito General: README',
            descripcion='Documentacion', estado='pendiente',
        )
        hito_frontend = Entregable.objects.create(
            proyecto=proyecto, titulo='Hito Frontend: UI',
            descripcion='Crear interfaz', estado='pendiente', equipo=grupo_a,
        )
        hito_backend = Entregable.objects.create(
            proyecto=proyecto, titulo='Hito Backend: API',
            descripcion='Crear API REST', estado='pendiente', equipo=grupo_b,
        )

        # ═══ BROWSER: Dev1 submits avance for Frontend ═══
        page.goto(live_server.url + reverse('login'))
        page.wait_for_timeout(2000)
        # Login page redirects to landing with modal
        page.locator('#username').wait_for(state='visible', timeout=5000)
        page.fill('#username', 'full_dev1')
        page.fill('#password', 'FullPass123!')
        page.locator('.btn-submit-tech:has-text("INGRESAR")').click(force=True)
        page.wait_for_timeout(2000)

        page.goto(live_server.url + reverse('registrar_avance', args=[proyecto.id]))
        page.wait_for_timeout(1000)
        page.select_option('select[name="entregable_id"]', value=str(hito_frontend.id))
        page.fill('textarea[name="descripcion"]', 'UI React con componentes')
        page.fill('input[name="archivo_url"]', 'https://github.com/test/frontend/1')
        page.locator('button:has-text("Enviar Avance")').click(force=True)
        page.wait_for_timeout(2000)

        avance_f = Avance.objects.get(desarrollador=dev1, entregable=hito_frontend)
        assert avance_f.estado == 'pendiente'
        hito_frontend.refresh_from_db()
        assert hito_frontend.estado == 'en_revision'

        # ═══ BROWSER: Dev2 submits avance for Backend ═══
        page.goto(live_server.url + reverse('login'))
        page.wait_for_timeout(2000)
        page.locator('#username').wait_for(state='visible', timeout=5000)
        page.fill('#username', 'full_dev2')
        page.fill('#password', 'FullPass123!')
        page.locator('.btn-submit-tech:has-text("INGRESAR")').click(force=True)
        page.wait_for_timeout(2000)

        page.goto(live_server.url + reverse('registrar_avance', args=[proyecto.id]))
        page.wait_for_timeout(1000)
        page.select_option('select[name="entregable_id"]', value=str(hito_backend.id))
        page.fill('textarea[name="descripcion"]', 'API REST con CRUD')
        page.fill('input[name="archivo_url"]', 'https://github.com/test/backend/1')
        page.locator('button:has-text("Enviar Avance")').click(force=True)
        page.wait_for_timeout(2000)

        avance_b = Avance.objects.get(desarrollador=dev2, entregable=hito_backend)
        assert avance_b.estado == 'pendiente'
        hito_backend.refresh_from_db()
        assert hito_backend.estado == 'en_revision'

        # ═══ Empresa accepts Frontend, rejects Backend ═══
        client.login(username='full_emp', password='FullPass123!')
        client.post(reverse('revisar_avance', args=[avance_f.id]), {
            'accion': 'aceptar', 'comentario': 'Buen trabajo!',
        })
        avance_f.refresh_from_db()
        assert avance_f.estado == 'aceptado'
        hito_frontend.refresh_from_db()
        assert hito_frontend.estado == 'completado'

        client.post(reverse('revisar_avance', args=[avance_b.id]), {
            'accion': 'rechazar', 'comentario': 'Falta paginacion en /users',
        })
        avance_b.refresh_from_db()
        assert avance_b.estado == 'rechazado'
        assert 'paginacion' in avance_b.comentario_revision
        hito_backend.refresh_from_db()
        assert hito_backend.estado == 'pendiente'
        proyecto.refresh_from_db()
        assert proyecto.estado == 'en_desarrollo'

        # ── Dev2 re-submits + general hito ──
        c = Client()
        c.login(username='full_dev2', password='FullPass123!')
        c.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': hito_backend.id,
            'descripcion': 'API corregida con paginacion',
            'archivo_url': 'https://github.com/test/backend/2',
        })
        c.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': hito_general.id,
            'descripcion': 'README completo',
            'archivo_url': 'https://github.com/test/docs/1',
        })

        # ── Empresa accepts remaining ──
        client.login(username='full_emp', password='FullPass123!')
        for avance in Avance.objects.filter(proyecto=proyecto, estado='pendiente'):
            client.post(reverse('revisar_avance', args=[avance.id]), {
                'accion': 'aceptar', 'comentario': 'Aprobado',
            })
        assert Entregable.objects.filter(proyecto=proyecto, estado='completado').count() == 3

        # ═══ BROWSER: Chat in workspace ═══
        page.goto(live_server.url + reverse('login'))
        page.wait_for_timeout(2000)
        page.locator('#username').wait_for(state='visible', timeout=5000)
        page.locator('button[data-role="empresa"]').click()
        page.fill('#username', 'full_emp')
        page.fill('#password', 'FullPass123!')
        page.locator('.btn-submit-tech:has-text("INGRESAR")').click(force=True)
        page.wait_for_timeout(2000)

        page.goto(live_server.url + reverse('sala_chat_grupal', args=[proyecto.id]))
        page.wait_for_timeout(1000)
        page.fill('input[name="contenido"]', 'Equipo, todos los hitos completados! 🚀')
        page.locator('button[type="submit"]').click(force=True)
        page.wait_for_timeout(1500)
        assert Mensaje.objects.filter(proyecto=proyecto, receptor__isnull=True).count() >= 1

        # ── Finalize + rate both devs ──
        client.login(username='full_emp', password='FullPass123!')
        client.post(reverse('finalizar_proyecto', args=[proyecto.id]), {
            'puntuacion': '5', 'comentario': 'Excelente dev, muy profesional',
        }, follow=True)
        proyecto.refresh_from_db()
        if proyecto.estado != 'finalizado':
            client.post(reverse('finalizar_proyecto', args=[proyecto.id]), {
                'puntuacion': '4', 'comentario': 'Buen trabajo, cumplio',
            }, follow=True)
        proyecto.refresh_from_db()
        assert proyecto.estado == 'finalizado'

        # ── Both devs rate empresa ──
        for dev in [dev1, dev2]:
            c = Client()
            c.login(username=dev.username, password='FullPass123!')
            c.post(reverse('calificar_empresa', args=[proyecto.id]), {
                'puntuacion': '5', 'comentario': f'Buena experiencia con {empresa.nombre}',
            })

        # ── FINAL VERIFICATION ──
        assert proyecto.estado == 'finalizado'
        assert Valoracion.objects.filter(proyecto=proyecto, rol_evaluador='empresa').count() == 2
        assert Valoracion.objects.filter(proyecto=proyecto, rol_evaluador='desarrollador').count() == 2
        assert Contratacion.objects.filter(proyecto=proyecto, estado='finalizada').count() == 2
        assert Mensaje.objects.filter(proyecto=proyecto, receptor__isnull=True).count() >= 1
        assert Avance.objects.filter(proyecto=proyecto).count() >= 4
        assert Entregable.objects.filter(proyecto=proyecto, estado='completado').count() == 3
