import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from proyectos.models import Proyecto
from postulaciones.models import Postulacion

User = get_user_model()


class TestListarProyectos:
    """Tests for listar_proyectos view."""

    def test_listar_publicados(self, auth_client, empresa_user, desarrollador_user):
        """La vitrina oculta proyectos en desarrollo que ya no tienen cupo (RF 3.1.1)."""
        from contrataciones.models import Contratacion
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Public', descripcion='P',
            tipo_solucion='sitio_web', estado='publicado',
        )
        cerrado = Proyecto.objects.create(
            empresa=empresa_user, titulo='Hidden', descripcion='H',
            tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=1,
        )
        Contratacion.objects.create(
            proyecto=cerrado, desarrollador=desarrollador_user,
            empresa=empresa_user, estado='activa',
        )
        response = auth_client.get(reverse('listar_proyectos'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Public' in content
        assert 'Hidden' not in content

    def test_listar_proyecto_en_desarrollo_con_cupo(self, auth_client, empresa_user, desarrollador_user):
        """Un proyecto en desarrollo con vacantes libres sigue visible (RF 3.1.1)."""
        from contrataciones.models import Contratacion
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='CupoAbierto', descripcion='C',
            tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=2,
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            empresa=empresa_user, estado='activa',
        )
        response = auth_client.get(reverse('listar_proyectos'))
        content = response.content.decode()
        assert 'CupoAbierto' in content
        assert '1 de 2 cupos libres' in content

    def test_filtrar_por_tipo(self, auth_client, empresa_user):
        """Filter by tipo_solucion works."""
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Web App', descripcion='W',
            tipo_solucion='sitio_web', estado='publicado',
        )
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Mobile App', descripcion='M',
            tipo_solucion='aplicacion_movil', estado='publicado',
        )
        response = auth_client.get(reverse('listar_proyectos') + '?tipo=sitio_web')
        content = response.content.decode()
        assert 'Web App' in content
        assert 'Mobile App' not in content
        assert response.status_code == 200

    def test_desarrollador_excludes_already_applied_projects(self, dev_client, desarrollador_user, empresa_user):
        """Desarrollador should not see projects they have already applied to (filtered at SQL level)."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        p_aplicado = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto Ya Aplicado', descripcion='Desc',
            tipo_solucion='sitio_web', estado='publicado',
        )
        p_disponible = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto Disponible', descripcion='Desc',
            tipo_solucion='sitio_web', estado='publicado',
        )
        Postulacion.objects.create(
            proyecto=p_aplicado, desarrollador=desarrollador_user,
            mensaje='Propuesta', estado='pendiente',
        )

        with CaptureQueriesContext(connection) as captured_queries:
            response = dev_client.get(reverse('listar_proyectos'))

        assert response.status_code == 200
        proyectos_ids = [p['id'] for p in response.context['proyectos']]
        assert p_aplicado.id not in proyectos_ids
        assert p_disponible.id in proyectos_ids

        # Assert that SQL contains the exclusion condition directly
        sql_statements = [q['sql'] for q in captured_queries]
        assert any(('NOT' in q or 'NOT IN' in q) and 'proyectos' in q for q in sql_statements)

    def test_listar_proyectos_paginacion_12_por_pagina(self, auth_client, empresa_user):
        """SCRUM-176: El listado principal de proyectos pagina a 12 items por página."""
        proyectos_creados = [
            Proyecto(
                empresa=empresa_user,
                titulo=f'Proyecto Paginado {i:02d}',
                descripcion='Desc',
                tipo_solucion='sitio_web',
                estado='publicado',
            ) for i in range(15)
        ]
        Proyecto.objects.bulk_create(proyectos_creados)

        response = auth_client.get(reverse('listar_proyectos') + '?page=1')
        assert response.status_code == 200
        assert len(response.context['proyectos']) == 12
        assert response.context['page_obj'].paginator.count >= 15
        assert response.context['page_obj'].paginator.num_pages >= 2

        # Segunda página debe traer los 3 restantes
        response2 = auth_client.get(reverse('listar_proyectos') + '?page=2')
        assert response2.status_code == 200
        assert len(response2.context['proyectos']) >= 3

    def test_listar_proyectos_busqueda_q(self, auth_client, empresa_user):
        """SCRUM-195: Búsqueda por texto libre en título o descripción."""
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Backend Django Asincrono',
            descripcion='Servicios REST y Channels', tipo_solucion='sitio_web', estado='publicado',
        )
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Frontend Vue SPA',
            descripcion='Interfaces web', tipo_solucion='sitio_web', estado='publicado',
        )

        response = auth_client.get(reverse('listar_proyectos') + '?q=django')
        assert response.status_code == 200
        titulos = [p['titulo'] for p in response.context['proyectos']]
        assert 'Backend Django Asincrono' in titulos
        assert 'Frontend Vue SPA' not in titulos

    def test_listar_proyectos_ajax_retorna_json(self, auth_client, empresa_user):
        """SCRUM-195: Petición con Accept: application/json retorna estructura JSON para Fetch."""
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto JSON Test',
            descripcion='Desc', tipo_solucion='sitio_web', estado='publicado',
        )
        response = auth_client.get(
            reverse('listar_proyectos'),
            headers={'Accept': 'application/json'}
        )
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/json'
        data = response.json()
        assert data['status'] == 'ok'
        assert isinstance(data['proyectos'], list)
        assert data['total_proyectos'] >= 1
        assert 'total_paginas' in data
        assert 'pagina_actual' in data

    def test_template_listar_proyectos_incluye_buscador_y_catalogo_async(self, auth_client):
        """SCRUM-195: El template proyectos/listar.html contiene el input de búsqueda q y carga catalogo_async.js."""
        with open('templates/proyectos/listar.html', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'name="q"' in content
        assert 'catalogo_async.js' in content



class TestCrearProyecto:
    """Tests for crear_proyecto view."""

    def test_empresa_puede_crear(self, auth_client, empresa_user):
        """Empresa user can create a project."""
        response = auth_client.post(reverse('crear_proyecto'), {
            'titulo': 'Nuevo Proyecto',
            'descripcion': 'Descripción del proyecto',
            'tipo_solucion': 'sitio_web',
            'prioridad': 'alta',
            'vacantes': '2',
        })
        assert response.status_code == 302
        assert Proyecto.objects.filter(titulo='Nuevo Proyecto').exists()

    def test_dev_no_puede_crear(self, dev_client):
        """Dev user cannot create a project."""
        response = dev_client.post(reverse('crear_proyecto'), {
            'titulo': 'Proyecto Dev',
            'descripcion': 'No debería crearse',
            'tipo_solucion': 'sitio_web',
        })
        assert response.status_code == 302
        assert not Proyecto.objects.filter(titulo='Proyecto Dev').exists()

    def test_anonimo_no_puede_crear(self, client):
        """Anonymous cannot create projects."""
        response = client.post(reverse('crear_proyecto'), {
            'titulo': 'Anon',
            'descripcion': 'Nope',
            'tipo_solucion': 'sitio_web',
        })
        assert response.status_code == 302
        assert not Proyecto.objects.filter(titulo='Anon').exists()

    def test_crear_registra_historial(self, auth_client, empresa_user):
        """Creating a project registers initial estado in historial."""
        auth_client.post(reverse('crear_proyecto'), {
            'titulo': 'Con Historial',
            'descripcion': 'Test',
            'tipo_solucion': 'sitio_web',
        })
        proyecto = Proyecto.objects.get(titulo='Con Historial')
        historial = proyecto.historial_estados.first()
        assert historial is not None
        assert historial.estado_nuevo == 'publicado'

    @pytest.mark.parametrize('vacantes_invalidas', ['0', '-1', '-5', 'abc', ''])
    def test_crear_proyecto_vacantes_invalidas_no_guarda(self, auth_client, vacantes_invalidas):
        """Validar RF 2.1.2 (SCRUM-50): Vacantes < 1 o inválidas no deben guardar el proyecto."""
        response = auth_client.post(reverse('crear_proyecto'), {
            'titulo': f'Proyecto Invalido {vacantes_invalidas}',
            'descripcion': 'Test vacantes',
            'tipo_solucion': 'sitio_web',
            'vacantes': vacantes_invalidas,
        }, follow=True)
        assert response.status_code == 200
        assert not Proyecto.objects.filter(titulo=f'Proyecto Invalido {vacantes_invalidas}').exists()
        content = response.content.decode('utf-8')
        assert 'Las vacantes deben ser un número mayor o igual a 1' in content

    def test_crear_proyecto_con_prioridades(self, auth_client, empresa_user):
        """SCRUM-312: La empresa puede seleccionar la prioridad (alta, media, baja)."""
        auth_client.post(reverse('crear_proyecto'), {
            'titulo': 'Proyecto Urgente',
            'descripcion': 'Test prioridad alta',
            'tipo_solucion': 'sitio_web',
            'prioridad': 'alta',
        })
        p_alta = Proyecto.objects.get(titulo='Proyecto Urgente')
        assert p_alta.prioridad == 'alta'

        auth_client.post(reverse('crear_proyecto'), {
            'titulo': 'Proyecto Calmo',
            'descripcion': 'Test prioridad baja',
            'tipo_solucion': 'sitio_web',
            'prioridad': 'baja',
        })
        p_baja = Proyecto.objects.get(titulo='Proyecto Calmo')
        assert p_baja.prioridad == 'baja'

    def test_modal_crear_proyecto_contiene_selector_prioridad(self, auth_client, empresa_user):
        """SCRUM-312: El modal de nueva oferta en el dashboard de empresa incluye selector de prioridad."""
        response = auth_client.get(reverse('dashboard_empresa'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'name="prioridad"' in content
        assert 'value="alta"' in content
        assert 'value="media"' in content
        assert 'value="baja"' in content


class TestEditarProyecto:
    """Tests for editar_proyecto view (SCRUM-103 / RF 2.2.2)."""

    def _proyecto_publicado(self, empresa):
        return Proyecto.objects.create(
            empresa=empresa, titulo='Editable', descripcion='E',
            tipo_solucion='sitio_web', estado='publicado', vacantes=2,
        )

    def test_empresa_duena_ve_formulario(self, auth_client, empresa_user):
        """Empresa owner can GET the edit form prefilled."""
        proyecto = self._proyecto_publicado(empresa_user)
        response = auth_client.get(
            reverse('editar_proyecto', args=[proyecto.id])
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Editable' in content
        assert 'value="2"' in content  # vacantes pre-llenado

    def test_empresa_puede_editar(self, auth_client, empresa_user):
        """Empresa owner can POST valid edits."""
        proyecto = self._proyecto_publicado(empresa_user)
        response = auth_client.post(
            reverse('editar_proyecto', args=[proyecto.id]),
            {
                'titulo': 'Titulo Nuevo',
                'descripcion': 'Desc nueva',
                'tipo_solucion': 'aplicacion_movil',
                'prioridad': 'alta',
                'vacantes': '5',
                'fecha_limite': '',
            },
        )
        assert response.status_code == 302
        proyecto.refresh_from_db()
        assert proyecto.titulo == 'Titulo Nuevo'
        assert proyecto.tipo_solucion == 'aplicacion_movil'
        assert proyecto.vacantes == 5

    def test_otra_empresa_no_puede(self, db, empresa_user):
        """Another empresa cannot edit (404 via get_object_or_404)."""
        otra = User.objects.create_user(
            username='otra_edit', email='otra2@test.jobdevs',
            nombre='Otra', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        proyecto = self._proyecto_publicado(otra)
        from django.test import Client
        client = Client()
        client.login(username='empresa_test', password='TestPass123!')
        response = client.get(
            reverse('editar_proyecto', args=[proyecto.id])
        )
        assert response.status_code == 404

    def test_dev_no_puede_editar(self, dev_client, empresa_user):
        """Dev user cannot edit projects."""
        proyecto = self._proyecto_publicado(empresa_user)
        response = dev_client.get(
            reverse('editar_proyecto', args=[proyecto.id])
        )
        assert response.status_code == 302  # redirect a dashboard_empresa

    def test_no_editable_si_estado_no_publicado(self, auth_client, empresa_user):
        """Project in en_desarrollo cannot be edited."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='En Desarrollo',
            descripcion='D', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        response = auth_client.get(
            reverse('editar_proyecto', args=[proyecto.id])
        )
        assert response.status_code == 302  # blocked

    def test_no_editable_con_contrato_activo(self, auth_client, empresa_user):
        """Project with an active contratacion cannot be edited."""
        proyecto = self._proyecto_publicado(empresa_user)
        from contrataciones.models import Contratacion
        dev = User.objects.create_user(
            username='dev_contratado', email='devc@test.jobdevs',
            nombre='Dev', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=dev, empresa=empresa_user,
            estado='activa',
        )
        response = auth_client.get(
            reverse('editar_proyecto', args=[proyecto.id])
        )
        assert response.status_code == 302  # blocked by active contract

    def test_vacantes_invalidas_no_guardan(self, auth_client, empresa_user):
        """vacantes < 1 is rejected and nothing is saved."""
        proyecto = self._proyecto_publicado(empresa_user)
        response = auth_client.post(
            reverse('editar_proyecto', args=[proyecto.id]),
            {
                'titulo': 'No Debe Guardar',
                'descripcion': 'X',
                'tipo_solucion': 'sitio_web',
                'prioridad': 'media',
                'vacantes': '0',
            },
        )
        assert response.status_code == 302
        proyecto.refresh_from_db()
        assert proyecto.titulo == 'Editable'  # unchanged

    def test_editar_proyecto_bloquea_reducir_vacantes_por_debajo_de_negociaciones(self, auth_client, empresa_user):
        """SCRUM-216: No se pueden reducir vacantes por debajo de las negociaciones en curso."""
        proyecto = self._proyecto_publicado(empresa_user)
        proyecto.vacantes = 3
        proyecto.save()

        from postulaciones.models import Postulacion
        dev1 = User.objects.create_user(
            username='dev_neg1', email='dev_neg1@test.jobdevs', nombre='Dev 1',
            rol='desarrollador', estado='activo', password='TestPass123!',
        )
        dev2 = User.objects.create_user(
            username='dev_neg2', email='dev_neg2@test.jobdevs', nombre='Dev 2',
            rol='desarrollador', estado='activo', password='TestPass123!',
        )
        Postulacion.objects.create(proyecto=proyecto, desarrollador=dev1, estado='en_negociacion')
        Postulacion.objects.create(proyecto=proyecto, desarrollador=dev2, estado='en_negociacion')

        response = auth_client.post(
            reverse('editar_proyecto', args=[proyecto.id]),
            {
                'titulo': proyecto.titulo,
                'descripcion': proyecto.descripcion,
                'tipo_solucion': proyecto.tipo_solucion,
                'prioridad': 'media',
                'vacantes': '1',
            },
            follow=True,
        )
        assert response.status_code == 200
        proyecto.refresh_from_db()
        assert proyecto.vacantes == 3  # No se redujo
        content = response.content.decode()
        assert 'comprometida' in content.lower() or 'negociación' in content.lower()


class TestFinalizarProyecto:
    """Tests for finalizar_proyecto view."""

    def test_empresa_puede_acceder(self, auth_client, empresa_user):
        """Empresa can access finalizar page (redirects if no hitos)."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Para Finalizar',
            descripcion='T', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        response = auth_client.get(
            reverse('finalizar_proyecto', args=[proyecto.id])
        )
        # Redirects because no hitos defined — but page is accessible (not 404/403)
        assert response.status_code == 302

    def test_otra_empresa_no_puede(self, db, empresa_user):
        """Empresa cannot finalize another empresa's project."""
        otra = User.objects.create_user(
            username='otra_emp', email='otra@test.jobdevs',
            nombre='Otra', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=otra, titulo='Ajeno', descripcion='A',
            tipo_solucion='sitio_web', estado='en_desarrollo',
        )
        from django.test import Client
        client = Client()
        client.login(username='empresa_test', password='TestPass123!')
        response = client.get(
            reverse('finalizar_proyecto', args=[proyecto.id])
        )
        assert response.status_code == 404


class TestCalificarEmpresa:
    """RF 5.2.2: el desarrollador califica a la empresa con comentario obligatorio."""

    @pytest.fixture
    def proyecto_finalizado(self, empresa_user, desarrollador_user):
        from contrataciones.models import Contratacion
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto terminado', descripcion='P',
            tipo_solucion='sitio_web', estado='finalizado',
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            empresa=empresa_user, estado='finalizada',
        )
        return proyecto

    def test_rechaza_comentario_vacio(self, dev_client, proyecto_finalizado, desarrollador_user):
        from proyectos.models import Valoracion
        response = dev_client.post(
            reverse('calificar_empresa', args=[proyecto_finalizado.id]),
            {'puntuacion': '5', 'comentario': '   '},
        )

        assert response.status_code == 302
        assert response.url == reverse('calificar_empresa', args=[proyecto_finalizado.id])
        assert not Valoracion.objects.filter(
            proyecto=proyecto_finalizado, desarrollador=desarrollador_user
        ).exists()

    def test_califica_y_actualiza_reputacion_empresa(
        self, dev_client, proyecto_finalizado, desarrollador_user, empresa_user
    ):
        from proyectos.models import Valoracion
        from usuarios.models import PerfilEmpresa
        perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=empresa_user)

        response = dev_client.post(
            reverse('calificar_empresa', args=[proyecto_finalizado.id]),
            {'puntuacion': '5', 'comentario': 'Buena comunicación y pagos puntuales'},
        )

        assert response.status_code == 302
        assert Valoracion.objects.filter(
            proyecto=proyecto_finalizado, desarrollador=desarrollador_user,
            rol_evaluador='desarrollador', puntuacion=5,
        ).exists()
        perfil.refresh_from_db()
        assert perfil.calificacion_promedio == 5

    def test_doble_post_concurrente_no_duplica(self, dev_client, proyecto_finalizado, desarrollador_user):
        from proyectos.models import Valoracion
        datos = {'puntuacion': '4', 'comentario': 'Trabajo claro y bien coordinado'}
        dev_client.post(reverse('calificar_empresa', args=[proyecto_finalizado.id]), datos)
        dev_client.post(reverse('calificar_empresa', args=[proyecto_finalizado.id]), datos)

        assert Valoracion.objects.filter(
            proyecto=proyecto_finalizado, desarrollador=desarrollador_user
        ).count() == 1
