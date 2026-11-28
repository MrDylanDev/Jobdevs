from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from proyectos.models import Proyecto, HistorialEstadoProyecto
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

    def test_publicado_sin_cupo_no_aparece_ni_cuenta_en_vitrina(
        self, dev_client, empresa_user, desarrollador_user,
    ):
        from contrataciones.models import Contratacion

        ocupado = Proyecto.objects.create(
            empresa=empresa_user, titulo='Cupo agotado', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado', vacantes=1,
        )
        reservado = Proyecto.objects.create(
            empresa=empresa_user, titulo='Cupo reservado', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado', vacantes=1,
        )
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Cupo abierto', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado', vacantes=1,
        )
        Contratacion.objects.create(
            proyecto=ocupado, empresa=empresa_user,
            desarrollador=desarrollador_user, estado='activa',
        )
        Postulacion.objects.create(
            proyecto=reservado, desarrollador=desarrollador_user,
            estado='en_negociacion',
        )
        response = dev_client.get(reverse('listar_proyectos'), HTTP_ACCEPT='application/json')
        assert response.status_code == 200
        assert response.json()['total_proyectos'] == 1
        assert {p['titulo'] for p in response.json()['proyectos']} == {'Cupo abierto'}

    def test_listar_proyectos_oculta_proyectos_con_fecha_limite_vencida(self, auth_client, empresa_user):
        """SCRUM-233 (RF 3.1.1): Los proyectos con fecha límite vencida se ocultan de la vitrina pública."""
        from datetime import timedelta
        hoy = timezone.now().date()
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto Caducado', descripcion='Vencido',
            tipo_solucion='sitio_web', estado='publicado', fecha_limite=hoy - timedelta(days=1),
        )
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto Vigente Plazo', descripcion='Vigente',
            tipo_solucion='sitio_web', estado='publicado', fecha_limite=hoy + timedelta(days=7),
        )
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto Sin Plazo', descripcion='Sin fecha',
            tipo_solucion='sitio_web', estado='publicado', fecha_limite=None,
        )

        response = auth_client.get(reverse('listar_proyectos'))
        assert response.status_code == 200
        content = response.content.decode()

        assert 'Proyecto Vigente Plazo' in content
        assert 'Proyecto Sin Plazo' in content
        assert 'Proyecto Caducado' not in content


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

    def test_listar_proyectos_htmx_retorna_partial_filtrado(self, dev_client, empresa_user):
        """S1: HX-Request: true devuelve solo el parcial HTML filtrado sin layout completo."""
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Portal Django HTMX',
            descripcion='Arquitectura moderna con HTMX', tipo_solucion='sitio_web', estado='publicado',
        )
        Proyecto.objects.create(
            empresa=empresa_user, titulo='App Movil Flutter',
            descripcion='App nativa', tipo_solucion='aplicacion_movil', estado='publicado',
        )

        response = dev_client.get(
            reverse('listar_proyectos') + '?q=Django&tipo=sitio_web',
            headers={'HX-Request': 'true'},
        )
        assert response.status_code == 200
        assert 'text/html' in response.headers['Content-Type']
        content = response.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in content
        assert '<html' not in content
        assert 'class="cards-grid"' in content
        assert 'Portal Django HTMX' in content
        assert 'App Movil Flutter' not in content

    def test_listar_proyectos_htmx_empty_state(self, dev_client):
        """S1: HX-Request: true sin resultados renderiza el empty state parcial."""
        response = dev_client.get(
            reverse('listar_proyectos') + '?q=termino-inexistente-xyz',
            headers={'HX-Request': 'true'},
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in content
        assert 'empty-state' in content
        assert 'No se encontraron proyectos con los filtros seleccionados.' in content

    def test_listar_proyectos_htmx_paginacion_links(self, dev_client, empresa_user):
        """S1: La paginación en el parcial HTMX conserva filtros e incluye hx-get/hx-target."""
        Proyecto.objects.bulk_create([
            Proyecto(
                empresa=empresa_user,
                titulo=f'Proyecto HTMX Pag {i:02d}',
                descripcion='Descripcion paginada',
                tipo_solucion='sitio_web',
                estado='publicado',
            )
            for i in range(15)
        ])

        res_p1 = dev_client.get(
            reverse('listar_proyectos') + '?tipo=sitio_web&page=1',
            headers={'HX-Request': 'true'},
        )
        assert res_p1.status_code == 200
        content_p1 = res_p1.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in content_p1
        assert 'aria-label="Paginación de proyectos"' in content_p1
        assert 'hx-get=' in content_p1
        assert 'page=2' in content_p1
        assert 'tipo=sitio_web' in content_p1
        assert 'hx-target="#catalogoResultados"' in content_p1
        assert 'hx-swap="innerHTML"' in content_p1
        assert 'hx-push-url="true"' in content_p1

        res_p2 = dev_client.get(
            reverse('listar_proyectos') + '?tipo=sitio_web&page=2',
            headers={'HX-Request': 'true'},
        )
        assert res_p2.status_code == 200
        content_p2 = res_p2.content.decode('utf-8')
        assert 'page=1' in content_p2
        assert 'hx-target="#catalogoResultados"' in content_p2

    def test_listar_proyectos_htmx_escapa_xss(self, dev_client, empresa_user):
        """S1: El parcial HTMX auto-escapa HTML/JS malicioso en título y descripción."""
        Proyecto.objects.create(
            empresa=empresa_user,
            titulo='<script>alert("xss")</script>',
            descripcion='<img src=x onerror=alert(1)>',
            tipo_solucion='sitio_web',
            estado='publicado',
        )

        response = dev_client.get(
            reverse('listar_proyectos'),
            headers={'HX-Request': 'true'},
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in content
        assert '<script>alert("xss")</script>' not in content
        assert '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;' in content
        assert '<img src=x onerror=alert(1)>' not in content

    def test_listar_proyectos_preserva_json_y_full_page(self, dev_client, empresa_user):
        """S1: Preserva contrato JSON (Accept/XHR/?format=json) y HTML completo con attrs HTMX."""
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto Contrato Dual',
            descripcion='Desc', tipo_solucion='sitio_web', estado='publicado',
        )
        url = reverse('listar_proyectos')

        # HX-Request + Accept: application/json -> JSON gana
        res_accept = dev_client.get(
            url, headers={'HX-Request': 'true', 'Accept': 'application/json'}
        )
        assert res_accept.status_code == 200
        assert res_accept.headers['Content-Type'] == 'application/json'
        assert res_accept.json()['status'] == 'ok'

        # HX-Request + ?format=json -> JSON gana
        res_fmt = dev_client.get(
            url + '?format=json', headers={'HX-Request': 'true'}
        )
        assert res_fmt.status_code == 200
        assert res_fmt.headers['Content-Type'] == 'application/json'
        assert res_fmt.json()['status'] == 'ok'

        # X-Requested-With: XMLHttpRequest (legacy) -> JSON preservado
        res_xhr = dev_client.get(
            url, headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        assert res_xhr.status_code == 200
        assert res_xhr.headers['Content-Type'] == 'application/json'
        assert res_xhr.json()['status'] == 'ok'

        # Regular GET -> full page HTML con contenedor HTMX y scripts vendored
        res_full = dev_client.get(url)
        assert res_full.status_code == 200
        full_html = res_full.content.decode('utf-8')
        assert '<!DOCTYPE html>' in full_html
        assert 'id="catalogoResultados"' in full_html
        assert 'vendor/htmx/htmx.min.js' in full_html
        assert 'dashboard/script/htmx_bridge.js' in full_html
        assert 'hx-target="#catalogoResultados"' in full_html
        assert 'hx-sync="this:replace"' in full_html

    def test_listar_proyectos_htmx_replace_url_limpia(self, dev_client, empresa_user):
        """T4: HTMX catalog filter emits clean HX-Replace-Url omitting empty params and encoding spaces as '+'."""
        Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Oferta de reputación',
            descripcion='Oferta de prueba',
            tipo_solucion='sitio_web',
            estado='publicado',
        )

        response = dev_client.get(
            reverse('listar_proyectos') + '?q=Oferta+de+reputaci%C3%B3n&tipo=&prioridad=&modalidad=',
            headers={'HX-Request': 'true'},
        )
        assert response.status_code == 200
        assert response['HX-Replace-Url'] == f"{reverse('listar_proyectos')}?q=Oferta+de+reputaci%C3%B3n"

        # Empty filters produce bare catalog URL without trailing '?'
        response_empty = dev_client.get(
            reverse('listar_proyectos') + '?q=&tipo=&prioridad=&modalidad=',
            headers={'HX-Request': 'true'},
        )
        assert response_empty.status_code == 200
        assert response_empty['HX-Replace-Url'] == reverse('listar_proyectos')




class TestCrearProyecto:
    """Tests for crear_proyecto view."""

    def test_empresa_puede_crear(self, auth_client, empresa_user):
        """Empresa user can create a project."""
        from datetime import timedelta
        response = auth_client.post(reverse('crear_proyecto'), {
            'titulo': 'Nuevo Proyecto',
            'descripcion': 'Descripción del proyecto',
            'tipo_solucion': 'sitio_web',
            'prioridad': 'alta',
            'vacantes': '2',
            'fecha_cumplimiento': (timezone.localdate() + timedelta(days=30)).isoformat(),
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
        from datetime import timedelta
        auth_client.post(reverse('crear_proyecto'), {
            'titulo': 'Con Historial',
            'descripcion': 'Test',
            'tipo_solucion': 'sitio_web',
            'fecha_cumplimiento': (timezone.localdate() + timedelta(days=30)).isoformat(),
        })
        proyecto = Proyecto.objects.get(titulo='Con Historial')
        historial = proyecto.historial_estados.first()
        assert historial is not None
        assert historial.estado_nuevo == 'publicado'

    def test_fecha_cumplimiento_independiente_del_cierre_de_postulaciones(self, auth_client, empresa_user):
        from datetime import timedelta

        hoy = timezone.localdate()
        response = auth_client.post(reverse('crear_proyecto'), {
            'titulo': 'Dos fechas', 'descripcion': 'D', 'tipo_solucion': 'sitio_web',
            'fecha_limite': (hoy + timedelta(days=7)).isoformat(),
            'fecha_cumplimiento': (hoy + timedelta(days=30)).isoformat(),
        })
        assert response.status_code == 302
        proyecto = Proyecto.objects.get(titulo='Dos fechas')
        assert proyecto.fecha_limite == hoy + timedelta(days=7)
        assert proyecto.fecha_cumplimiento == hoy + timedelta(days=30)

    @pytest.mark.parametrize('valor', [None, '', '   '])
    def test_fecha_cumplimiento_obligatoria_al_publicar(self, auth_client, valor):
        datos = {
            'titulo': 'Sin fecha de cumplimiento', 'descripcion': 'D',
            'tipo_solucion': 'sitio_web',
        }
        if valor is not None:
            datos['fecha_cumplimiento'] = valor
        respuesta = auth_client.post(reverse('crear_proyecto'), datos, follow=True)
        assert not Proyecto.objects.filter(titulo='Sin fecha de cumplimiento').exists()
        assert 'fecha de cumplimiento es obligatoria' in respuesta.content.decode().lower()

    def test_formulario_exige_fecha_de_cumplimiento(self, auth_client):
        respuesta = auth_client.get(reverse('dashboard_empresa'))
        assert 'id="crear_fecha_cumplimiento"' in respuesta.content.decode()
        assert 'name="fecha_cumplimiento" id="crear_fecha_cumplimiento" class="form-input-corp" required' in respuesta.content.decode()

    def test_formulario_de_creacion_distingue_las_dos_fechas(self, auth_client):
        response = auth_client.get(reverse('dashboard_empresa'))
        content = response.content.decode()
        assert 'name="fecha_limite"' in content
        assert 'name="fecha_cumplimiento"' in content
        assert 'Fecha de cumplimiento' in content

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
        from datetime import timedelta
        auth_client.post(reverse('crear_proyecto'), {
            'titulo': 'Proyecto Urgente',
            'descripcion': 'Test prioridad alta',
            'tipo_solucion': 'sitio_web',
            'prioridad': 'alta',
            'fecha_cumplimiento': (timezone.localdate() + timedelta(days=30)).isoformat(),
        })
        p_alta = Proyecto.objects.get(titulo='Proyecto Urgente')
        assert p_alta.prioridad == 'alta'

        auth_client.post(reverse('crear_proyecto'), {
            'titulo': 'Proyecto Calmo',
            'descripcion': 'Test prioridad baja',
            'tipo_solucion': 'sitio_web',
            'prioridad': 'baja',
            'fecha_cumplimiento': (timezone.localdate() + timedelta(days=30)).isoformat(),
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


class TestDesactivarProyecto:
    def test_publicado_sin_contratos_puede_retirarse(self, auth_client, empresa_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Oferta abierta', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )
        response = auth_client.post(reverse('desactivar_proyecto', args=[proyecto.pk]))
        proyecto.refresh_from_db()
        assert response.status_code == 302
        assert proyecto.estado == 'inactivo'

    @pytest.mark.parametrize('estado', ['en_desarrollo', 'en_revision'])
    def test_proyecto_en_ejecucion_no_se_retira(self, auth_client, empresa_user, desarrollador_user, estado):
        from contrataciones.models import Contratacion
        from notificaciones.models import Notificacion

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Compromiso vigente', descripcion='D',
            tipo_solucion='sitio_web', estado=estado,
        )
        contrato = Contratacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            empresa=empresa_user, estado='activa',
        )
        response = auth_client.post(reverse('desactivar_proyecto', args=[proyecto.pk]))
        proyecto.refresh_from_db()
        contrato.refresh_from_db()
        assert response.status_code == 302
        assert proyecto.estado == estado
        assert contrato.estado == 'activa'
        assert not proyecto.historial_estados.exists()
        assert not Notificacion.objects.filter(usuario=desarrollador_user).exists()

    def test_publicado_con_contrato_historico_no_se_retira(self, auth_client, empresa_user, desarrollador_user):
        from contrataciones.models import Contratacion

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Oferta con contrato', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            empresa=empresa_user, estado='finalizada',
        )
        auth_client.post(reverse('desactivar_proyecto', args=[proyecto.pk]))
        proyecto.refresh_from_db()
        assert proyecto.estado == 'publicado'


class TestReabrirPostulaciones:
    def test_empresa_amplia_plazo_tras_cancelar_sin_alterar_cumplimiento(
        self, auth_client, empresa_user, desarrollador_user,
    ):
        from datetime import timedelta
        from contrataciones.models import Contratacion
        from disputas.services import abrir_disputa, resolver_disputa
        from django.test import Client
        from logs.models import LogAuditoria
        from usuarios.models import PerfilDesarrollador

        hoy = timezone.localdate()
        vencida = hoy - timedelta(days=1)
        nueva = hoy + timedelta(days=7)
        cumplimiento = hoy + timedelta(days=30)
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Reemplazo', descripcion='D',
            tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=1,
            fecha_limite=vencida, fecha_cumplimiento=cumplimiento,
        )
        contrato = Contratacion.objects.create(
            empresa=empresa_user, desarrollador=desarrollador_user,
            proyecto=proyecto, estado='activa',
        )
        admin = User.objects.create_user(
            username='admin_reapertura', email='admin_reapertura@test.jobdevs',
            rol='administrador', estado='activo', password='TestPass123!',
        )
        disputa = abrir_disputa(
            proyecto, empresa_user, contratacion=contrato,
            motivo='El hito contractual venció sin entrega y no fue posible resolver el conflicto tras conversar con el desarrollador.',
            evidencia_url='https://evidencia.test/hito',
        )
        resolver_disputa(disputa, admin, 'cancelar_contrato', 'Se verificó el hito pendiente.')
        proyecto.refresh_from_db()
        assert proyecto.estado == 'publicado'
        assert proyecto.fecha_limite == vencida
        assert not proyecto.acepta_postulaciones
        reemplazo = User.objects.create_user(
            username='dev_reemplazo', email='dev_reemplazo@test.jobdevs',
            rol='desarrollador', estado='activo', password='TestPass123!',
        )
        perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=reemplazo)  # type: ignore[attr-defined]
        perfil.estado_verificacion = 'verificado'
        perfil.save(update_fields=['estado_verificacion'])
        candidato = Client()
        candidato.force_login(reemplazo)
        postular = reverse('postularse_a_proyecto', args=[proyecto.pk])
        candidato.post(postular, {'carta': 'Antes del plazo'})
        assert not Postulacion.objects.filter(proyecto=proyecto, desarrollador=reemplazo).exists()  # type: ignore[attr-defined]
        url = reverse('reabrir_postulaciones', args=[proyecto.pk])
        panel = auth_client.get(reverse('dashboard_empresa'))
        assert f'action="{url}"'.encode() in panel.content
        assert auth_client.get(url).status_code == 405
        response = auth_client.post(url, {
            'fecha_limite': nueva.isoformat(),
            'fecha_cumplimiento': (hoy + timedelta(days=90)).isoformat(),
            'descripcion': 'No cambiar',
        })
        assert response.status_code == 302
        proyecto.refresh_from_db()
        assert proyecto.fecha_limite == nueva
        assert proyecto.fecha_cumplimiento == cumplimiento
        assert proyecto.descripcion == 'D'
        assert proyecto.acepta_postulaciones
        candidato.post(postular, {'carta': 'Nueva postulación'})
        assert Postulacion.objects.filter(proyecto=proyecto, desarrollador=reemplazo).exists()  # type: ignore[attr-defined]
        assert LogAuditoria.objects.filter(
            usuario=empresa_user, tabla_afectada='proyectos',
            registro_id=proyecto.pk,
            valor_anterior=vencida.isoformat(), valor_nuevo=nueva.isoformat(),
        ).exists()

    @pytest.mark.parametrize('estado', ['en_desarrollo', 'finalizado', 'inactivo', 'en_disputa'])
    def test_no_reabre_estados_no_publicados(
        self, auth_client, empresa_user, desarrollador_user, estado,
    ):
        from datetime import timedelta
        from contrataciones.models import Contratacion

        hoy = timezone.localdate()
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Cerrado', descripcion='D',
            tipo_solucion='sitio_web', estado=estado,
            fecha_limite=hoy - timedelta(days=1),
        )
        Contratacion.objects.create(
            empresa=empresa_user, proyecto=proyecto,
            estado='cancelada', desarrollador=desarrollador_user,
        )
        auth_client.post(reverse('reabrir_postulaciones', args=[proyecto.pk]), {
            'fecha_limite': (hoy + timedelta(days=7)).isoformat(),
        })
        proyecto.refresh_from_db()
        assert proyecto.fecha_limite == hoy - timedelta(days=1)

    def test_no_reabre_sin_cancelacion_o_sin_cupo_ni_con_fecha_invalida(
        self, auth_client, empresa_user, desarrollador_user,
    ):
        from datetime import timedelta
        from contrataciones.models import Contratacion

        hoy = timezone.localdate()
        vencida = hoy - timedelta(days=1)
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='No reabrir', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
            fecha_limite=vencida,
        )
        url = reverse('reabrir_postulaciones', args=[proyecto.pk])
        nueva = (hoy + timedelta(days=3)).isoformat()
        auth_client.post(url, {'fecha_limite': nueva})
        proyecto.refresh_from_db()
        assert proyecto.fecha_limite == vencida
        Contratacion.objects.create(
            empresa=empresa_user, desarrollador=desarrollador_user,
            proyecto=proyecto, estado='cancelada',
        )
        for fecha in ('', '2020-99-99', vencida.isoformat(), hoy.isoformat()):
            auth_client.post(url, {'fecha_limite': fecha})
            proyecto.refresh_from_db()
            assert proyecto.fecha_limite == vencida
        otro_dev = User.objects.create_user(
            username='dev_otro_cupo', email='dev_otro_cupo@test.jobdevs',
            rol='desarrollador', estado='activo', password='TestPass123!',
        )
        Contratacion.objects.create(
            empresa=empresa_user, desarrollador=otro_dev,
            proyecto=proyecto, estado='activa',
        )
        auth_client.post(url, {'fecha_limite': nueva})
        proyecto.refresh_from_db()
        assert proyecto.fecha_limite == vencida

    def test_otra_empresa_no_puede_reabrir(self, client, empresa_user):
        from datetime import timedelta
        from django.contrib.auth import get_user_model

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Ajeno', descripcion='D',
            tipo_solucion='sitio_web', fecha_limite=timezone.localdate() - timedelta(days=1),
        )
        otra = get_user_model().objects.create_user(
            username='otra_reap', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        client.force_login(otra)
        assert client.post(reverse('reabrir_postulaciones', args=[proyecto.pk]), {
            'fecha_limite': (timezone.localdate() + timedelta(days=7)).isoformat(),
        }).status_code == 404


class TestEditarProyecto:
    """Tests for editar_proyecto view (SCRUM-103 / RF 2.2.2)."""

    def _proyecto_publicado(self, empresa):
        return Proyecto.objects.create(
            empresa=empresa, titulo='Editable', descripcion='E',
            tipo_solucion='sitio_web', estado='publicado', vacantes=2,
        )

    def test_editar_fecha_cumplimiento_sin_cambiar_cierre(self, auth_client, empresa_user):
        from datetime import timedelta

        proyecto = self._proyecto_publicado(empresa_user)
        hoy = timezone.localdate()
        proyecto.fecha_limite = hoy + timedelta(days=5)
        proyecto.save()
        response = auth_client.post(reverse('editar_proyecto', args=[proyecto.pk]), {
            'titulo': proyecto.titulo, 'descripcion': proyecto.descripcion,
            'tipo_solucion': proyecto.tipo_solucion, 'vacantes': '2',
            'fecha_limite': proyecto.fecha_limite.isoformat(),
            'fecha_cumplimiento': (hoy + timedelta(days=20)).isoformat(),
        })
        proyecto.refresh_from_db()
        assert response.status_code == 302
        assert proyecto.fecha_limite == hoy + timedelta(days=5)
        assert proyecto.fecha_cumplimiento == hoy + timedelta(days=20)

    def test_cliente_antiguo_no_borra_fecha_cumplimiento(self, auth_client, empresa_user):
        from datetime import timedelta

        proyecto = self._proyecto_publicado(empresa_user)
        proyecto.fecha_cumplimiento = timezone.localdate() + timedelta(days=20)
        proyecto.save()
        auth_client.post(reverse('editar_proyecto', args=[proyecto.pk]), {
            'titulo': proyecto.titulo, 'descripcion': proyecto.descripcion,
            'tipo_solucion': proyecto.tipo_solucion, 'vacantes': '2',
        })
        proyecto.refresh_from_db()
        assert proyecto.fecha_cumplimiento == timezone.localdate() + timedelta(days=20)

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
                'modalidad': 'hibrido',
                'ciudad': 'Barranquilla',
                'vacantes': '5',
                'fecha_limite': '',
            },
        )
        assert response.status_code == 302
        proyecto.refresh_from_db()
        assert proyecto.titulo == 'Titulo Nuevo'
        assert proyecto.tipo_solucion == 'aplicacion_movil'
        assert proyecto.modalidad == 'hibrido'
        assert proyecto.ciudad == 'Barranquilla'
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

    def test_en_desarrollo_sin_contrato_edita_solo_datos_basicos(self, auth_client, empresa_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='En Desarrollo',
            descripcion='D', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        url = reverse('editar_proyecto', args=[proyecto.id])
        response = auth_client.get(url)
        assert response.status_code == 200
        assert b'name="titulo"' in response.content
        assert b'name="descripcion"' not in response.content
        auth_client.post(url, {
            'titulo': 'Nuevo rótulo', 'prioridad': 'alta',
            'descripcion': 'Cambio indebido', 'tipo_solucion': 'aplicacion_movil',
            'vacantes': '9',
        })
        proyecto.refresh_from_db()
        assert proyecto.titulo == 'Nuevo rótulo'
        assert proyecto.prioridad == 'alta'
        assert proyecto.descripcion == 'D'
        assert proyecto.tipo_solucion == 'sitio_web'
        assert proyecto.vacantes == 1

    @pytest.mark.parametrize('estado', ['en_desarrollo', 'en_revision'])
    def test_panel_ofrece_edicion_basica_solo_sin_contrato_activo(
        self, auth_client, empresa_user, desarrollador_user, estado,
    ):
        from contrataciones.models import Contratacion

        editable = Proyecto.objects.create(
            empresa=empresa_user, titulo='Editable básica', descripcion='D',
            tipo_solucion='sitio_web', estado=estado,
        )
        bloqueado = Proyecto.objects.create(
            empresa=empresa_user, titulo='Contratada', descripcion='D',
            tipo_solucion='sitio_web', estado=estado,
        )
        Contratacion.objects.create(
            empresa=empresa_user, desarrollador=desarrollador_user,
            proyecto=bloqueado, estado='activa',
        )
        response = auth_client.get(reverse('dashboard_empresa'))
        assert response.status_code == 200
        assert f'href="{reverse("editar_proyecto", args=[editable.pk])}"'.encode() in response.content
        assert f'href="{reverse("editar_proyecto", args=[bloqueado.pk])}"'.encode() not in response.content

    def test_publicado_en_negociacion_no_cambia_condiciones_tecnicas(
        self, auth_client, empresa_user, desarrollador_user,
    ):
        proyecto = self._proyecto_publicado(empresa_user)
        Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            estado='en_negociacion',
        )
        url = reverse('editar_proyecto', args=[proyecto.pk])
        response = auth_client.get(url)
        assert response.status_code == 200
        assert b'name="descripcion"' not in response.content
        dashboard = auth_client.get(reverse('dashboard_empresa')).content.decode()
        assert f'href="{url}"' in dashboard
        assert f'onclick="abrirModalEditarProyecto(event, \'{proyecto.id}\'' not in dashboard
        auth_client.post(url, {
            'titulo': 'Rótulo nuevo', 'prioridad': 'alta',
            'descripcion': 'Requisito alterado', 'vacantes': '1',
        })
        proyecto.refresh_from_db()
        assert proyecto.titulo == 'Rótulo nuevo'
        assert proyecto.descripcion == 'E'
        assert proyecto.vacantes == 2

    def test_contrato_historico_solo_permite_cambios_basicos(
        self, auth_client, empresa_user, desarrollador_user,
    ):
        from contrataciones.models import Contratacion

        proyecto = self._proyecto_publicado(empresa_user)
        Contratacion.objects.create(
            empresa=empresa_user, desarrollador=desarrollador_user,
            proyecto=proyecto, estado='finalizada',
        )
        url = reverse('editar_proyecto', args=[proyecto.pk])
        assert b'name="descripcion"' not in auth_client.get(url).content
        auth_client.post(url, {
            'titulo': 'Identificador', 'prioridad': 'baja',
            'descripcion': 'Otro alcance', 'tipo_solucion': 'otro',
        })
        proyecto.refresh_from_db()
        assert proyecto.titulo == 'Identificador'
        assert proyecto.descripcion == 'E'
        assert proyecto.tipo_solucion == 'sitio_web'

    @pytest.mark.parametrize('estado', ['finalizado', 'rechazado', 'inactivo', 'en_disputa'])
    def test_terminal_o_disputa_no_admite_edicion(
        self, auth_client, empresa_user, estado,
    ):
        proyecto = self._proyecto_publicado(empresa_user)
        proyecto.estado = estado
        proyecto.save(update_fields=['estado'])
        url = reverse('editar_proyecto', args=[proyecto.pk])
        assert auth_client.get(url).status_code == 302
        assert auth_client.post(url, {'titulo': 'Alterado', 'prioridad': 'alta'}).status_code == 302
        proyecto.refresh_from_db()
        assert proyecto.titulo == 'Editable'

    def test_no_permite_prioridad_invalida_en_edicion_basica(
        self, auth_client, empresa_user,
    ):
        proyecto = self._proyecto_publicado(empresa_user)
        proyecto.estado = 'en_revision'
        proyecto.save(update_fields=['estado'])
        auth_client.post(reverse('editar_proyecto', args=[proyecto.pk]), {
            'titulo': 'Alterado', 'prioridad': 'inventada',
        })
        proyecto.refresh_from_db()
        assert proyecto.titulo == 'Editable'

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

    def test_empresa_califica_colaborador_despues_de_finalizado(
        self, auth_client, empresa_user, desarrollador_user
    ):
        """RF 5.2.1: el cierre automático antecede a la valoración del equipo."""
        from contrataciones.models import Contratacion
        from proyectos.models import HistorialEstadoProyecto, Valoracion

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Cerrado antes de valorar',
            descripcion='P',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Contratacion.objects.create(
            proyecto=proyecto,
            desarrollador=desarrollador_user,
            empresa=empresa_user,
            estado='finalizada',
        )
        HistorialEstadoProyecto.objects.create(
            proyecto=proyecto,
            estado_anterior='en_revision',
            estado_nuevo='finalizado',
            cambiado_por=empresa_user,
        )

        response = auth_client.post(
            reverse('finalizar_proyecto', args=[proyecto.id]),
            {
                'puntuacion': '5',
                'comentario': 'Excelente calidad técnica y comunicación durante el proyecto',
            },
            follow=True,
        )

        assert response.status_code == 200
        assert Valoracion.objects.filter(
            proyecto=proyecto,
            desarrollador=desarrollador_user,
            rol_evaluador='empresa',
            puntuacion=5,
        ).exists()

    def test_finalizar_proyecto_htmx_get_retorna_partial_modal(
        self, auth_client, empresa_user, desarrollador_user
    ):
        """S5: GET con HX-Request devuelve _modal_finalizar_proyecto.html con controles de estrellas."""
        from contrataciones.models import Contratacion
        from proyectos.models import HistorialEstadoProyecto

        desarrollador_user.nombre = 'Dev <script>alert(1)</script>'
        desarrollador_user.save(update_fields=['nombre'])
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto S5 Calificar',
            descripcion='P',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Contratacion.objects.create(
            proyecto=proyecto,
            desarrollador=desarrollador_user,
            empresa=empresa_user,
            estado='finalizada',
        )
        HistorialEstadoProyecto.objects.create(
            proyecto=proyecto,
            estado_anterior='en_revision',
            estado_nuevo='finalizado',
            cambiado_por=empresa_user,
        )

        resp = auth_client.get(
            reverse('finalizar_proyecto', args=[proyecto.id]),
            HTTP_HX_REQUEST='true',
        )
        assert resp.status_code == 200
        html = resp.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in html
        assert 'id="formCalificarModal"' in html
        assert 'hx-post=' in html
        assert 'hx-target="#modalCalificarBody"' in html
        assert 'class="corp-star-rating"' in html
        assert '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html

    def test_finalizar_proyecto_htmx_post_error_rerenderiza_partial(
        self, auth_client, empresa_user, desarrollador_user
    ):
        """S5: POST HTMX con error de validación re-renderiza el partial con .msg-error."""
        from contrataciones.models import Contratacion
        from proyectos.models import HistorialEstadoProyecto, Valoracion

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto S5 Error Calificar',
            descripcion='P',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Contratacion.objects.create(
            proyecto=proyecto,
            desarrollador=desarrollador_user,
            empresa=empresa_user,
            estado='finalizada',
        )
        HistorialEstadoProyecto.objects.create(
            proyecto=proyecto,
            estado_anterior='en_revision',
            estado_nuevo='finalizado',
            cambiado_por=empresa_user,
        )

        resp = auth_client.post(
            reverse('finalizar_proyecto', args=[proyecto.id]),
            {'puntuacion': '5', 'comentario': 'Corto'},
            HTTP_HX_REQUEST='true',
        )
        assert resp.status_code == 200
        html = resp.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in html
        assert 'id="formCalificarModal"' in html
        assert 'class="msg-error"' in html
        assert not Valoracion.objects.filter(proyecto=proyecto).exists()

    def test_finalizar_proyecto_htmx_post_exito_retorna_hx_trigger(
        self, auth_client, empresa_user, desarrollador_user
    ):
        """S5: POST HTMX exitoso guarda valoración y devuelve 200 con HX-Trigger."""
        import json
        from contrataciones.models import Contratacion
        from proyectos.models import HistorialEstadoProyecto, Valoracion

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto S5 Exito Calificar',
            descripcion='P',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Contratacion.objects.create(
            proyecto=proyecto,
            desarrollador=desarrollador_user,
            empresa=empresa_user,
            estado='finalizada',
        )
        HistorialEstadoProyecto.objects.create(
            proyecto=proyecto,
            estado_anterior='en_revision',
            estado_nuevo='finalizado',
            cambiado_por=empresa_user,
        )

        resp = auth_client.post(
            reverse('finalizar_proyecto', args=[proyecto.id]),
            {
                'puntuacion': '5',
                'comentario': 'Excelente trabajo técnico, comunicación clara y entregas a tiempo.',
            },
            HTTP_HX_REQUEST='true',
        )
        assert resp.status_code == 200
        assert Valoracion.objects.filter(
            proyecto=proyecto,
            desarrollador=desarrollador_user,
            rol_evaluador='empresa',
            puntuacion=5,
        ).exists()
        assert 'HX-Trigger' in resp
        triggers = json.loads(resp['HX-Trigger'])
        assert 'jobdevs:toast' in triggers
        assert triggers['jobdevs:toast']['tipo'] == 'success'
        assert 'jobdevs:calificacion-guardada' in triggers


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
        HistorialEstadoProyecto.objects.create(
            proyecto=proyecto, estado_anterior='en_revision',
            estado_nuevo='finalizado', cambiado_por=empresa_user,
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

    def test_rechaza_calificacion_fuera_de_ventana(
        self, dev_client, proyecto_finalizado, desarrollador_user, empresa_user
    ):
        from proyectos.models import HistorialEstadoProyecto, Valoracion

        historial = proyecto_finalizado.historial_estados.get(estado_nuevo='finalizado')
        HistorialEstadoProyecto.objects.filter(pk=historial.pk).update(
            fecha=timezone.now() - timedelta(days=31)
        )

        response = dev_client.post(
            reverse('calificar_empresa', args=[proyecto_finalizado.id]),
            {
                'puntuacion': '4',
                'comentario': 'Valoración tardía que debe rechazarse por plazo',
            },
            follow=True,
        )

        assert response.status_code == 200
        assert '30 días' in response.content.decode('utf-8')
        assert not Valoracion.objects.filter(
            proyecto=proyecto_finalizado,
            desarrollador=desarrollador_user,
            rol_evaluador='desarrollador',
        ).exists()

    def test_ajax_fuera_de_ventana_devuelve_json_error(
        self, dev_client, proyecto_finalizado
    ):
        from proyectos.models import HistorialEstadoProyecto

        historial = proyecto_finalizado.historial_estados.get(estado_nuevo='finalizado')
        HistorialEstadoProyecto.objects.filter(pk=historial.pk).update(
            fecha=timezone.now() - timedelta(days=31)
        )

        url = reverse('calificar_empresa', args=[proyecto_finalizado.id])
        headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest', 'HTTP_ACCEPT': 'application/json'}

        get_res = dev_client.get(url, **headers)
        assert get_res.status_code == 400
        get_data = get_res.json()
        assert get_data['ok'] is False
        assert '30 días' in get_data['error']

        post_res = dev_client.post(
            url,
            {'puntuacion': '4', 'comentario': 'Valoración tardía por AJAX', 'origen': 'dashboard'},
            **headers,
        )
        assert post_res.status_code == 400
        post_data = post_res.json()
        assert post_data['ok'] is False
        assert '30 días' in post_data['mensaje']

    def test_htmx_get_retorna_partial_y_escapa_xss(
        self, dev_client, proyecto_finalizado, empresa_user
    ):
        empresa_user.nombre = 'Empresa <script>alert("xss")</script>'
        empresa_user.save(update_fields=['nombre'])
        proyecto_finalizado.titulo = 'Proyecto <img src=x onerror=alert(1)>'
        proyecto_finalizado.save(update_fields=['titulo'])

        url = reverse('calificar_empresa', args=[proyecto_finalizado.id])
        response = dev_client.get(url, HTTP_HX_REQUEST='true')

        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert 'proyectos/partials/_modal_calificar_empresa.html' in template_names
        html = response.content.decode('utf-8')
        assert 'id="jdmFormCalificar"' in html
        assert 'id="jdmStars"' in html
        assert 'jdm-stars' in html
        assert 'id="jdmComentario"' in html
        assert 'id="jdmBtnEnviarCalificacion"' in html
        assert 'csrfmiddlewaretoken' in html
        assert '<script>alert("xss")</script>' not in html
        assert '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;' in html
        assert '<img src=x onerror=alert(1)>' not in html
        assert '&lt;img src=x onerror=alert(1)&gt;' in html

        ob_res = dev_client.get(f'{url}?obligatorio=1', HTTP_HX_REQUEST='true')
        assert ob_res.status_code == 200
        ob_html = ob_res.content.decode('utf-8')
        assert 'Evaluación requerida' in ob_html
        assert 'Enviar Calificación Obligatoria' in ob_html

    def test_htmx_post_error_validacion_rerenderiza_partial(
        self, dev_client, proyecto_finalizado, desarrollador_user
    ):
        from proyectos.models import Valoracion

        url = reverse('calificar_empresa', args=[proyecto_finalizado.id])
        response = dev_client.post(
            url,
            {'puntuacion': '5', 'comentario': 'Muy corto'},
            HTTP_HX_REQUEST='true',
        )

        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert 'proyectos/partials/_modal_calificar_empresa.html' in template_names
        html = response.content.decode('utf-8')
        assert 'id="jdmFormCalificar"' in html
        assert 'al menos 20 caracteres' in html
        assert 'HX-Trigger' not in response
        assert not Valoracion.objects.filter(
            proyecto=proyecto_finalizado, desarrollador=desarrollador_user
        ).exists()

        res_sin_punt = dev_client.post(
            url,
            {'puntuacion': '', 'comentario': 'Comentario suficientemente largo para validar.'},
            HTTP_HX_REQUEST='true',
        )
        assert res_sin_punt.status_code == 200
        assert 'Debes seleccionar una puntuación.' in res_sin_punt.content.decode('utf-8')

    def test_htmx_post_exito_retorna_confirmacion_y_hx_trigger(
        self, dev_client, proyecto_finalizado, desarrollador_user, empresa_user
    ):
        import json as _json
        from proyectos.models import Valoracion
        from usuarios.models import PerfilEmpresa

        perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=empresa_user)
        url = reverse('calificar_empresa', args=[proyecto_finalizado.id])

        response = dev_client.post(
            url,
            {
                'puntuacion': '5',
                'comentario': 'Excelente comunicación, requisitos claros y pagos puntuales.',
            },
            HTTP_HX_REQUEST='true',
        )

        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert 'proyectos/partials/_modal_calificar_empresa.html' in template_names
        html = response.content.decode('utf-8')
        assert 'id="jdmFormCalificar"' not in html
        assert 'calificación ha sido registrada' in html.lower() or 'ya has calificado' in html.lower()

        assert 'HX-Trigger' in response
        trigger = _json.loads(response['HX-Trigger'])
        assert 'jobdevs:toast' in trigger
        assert trigger['jobdevs:toast']['tipo'] == 'success'
        assert 'jobdevs:calificacion-empresa-guardada' in trigger
        assert trigger['jobdevs:calificacion-empresa-guardada']['proyecto_id'] == proyecto_finalizado.id
        assert trigger['jobdevs:calificacion-empresa-guardada']['puntuacion'] == 5

        assert Valoracion.objects.filter(
            proyecto=proyecto_finalizado,
            desarrollador=desarrollador_user,
            rol_evaluador='desarrollador',
            puntuacion=5,
        ).exists()
        perfil.refresh_from_db()
        assert perfil.calificacion_promedio == 5

        get_after = dev_client.get(url, HTTP_HX_REQUEST='true')
        assert get_after.status_code == 200
        assert 'id="jdmFormCalificar"' not in get_after.content.decode('utf-8')

    def test_preserva_contrato_json_y_html_completo(
        self, dev_client, proyecto_finalizado
    ):
        url = reverse('calificar_empresa', args=[proyecto_finalizado.id])

        # Full-page HTML contract
        html_res = dev_client.get(url)
        assert html_res.status_code == 200
        assert 'proyectos/calificar_empresa.html' in [t.name for t in html_res.templates]

        # JSON contract via XHR + Accept (even if HX-Request is also sent)
        json_headers = {
            'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
            'HTTP_ACCEPT': 'application/json',
            'HTTP_HX_REQUEST': 'true',
        }
        get_json = dev_client.get(url, **json_headers)
        assert get_json.status_code == 200
        data = get_json.json()
        assert data['ok'] is True
        assert data['ya_califico'] is False
        assert data['proyecto']['id'] == proyecto_finalizado.id

        post_json = dev_client.post(
            url,
            {
                'puntuacion': '4',
                'comentario': 'Experiencia positiva colaborando con la empresa.',
                'origen': 'dashboard',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
        )
        assert post_json.status_code == 200
        post_data = post_json.json()
        assert post_data['ok'] is True
        assert post_data['puntuacion'] == 4


class TestGestionarHitosAsignacionIndividual:
    """SCRUM-309 (HU-E13): la empresa puede asignar un hito a un desarrollador individual."""

    @pytest.fixture
    def proyecto_hitos(self, empresa_user):
        from contrataciones.models import Contratacion
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto Hitos Individuales',
            descripcion='D', tipo_solucion='sitio_web', estado='en_desarrollo',
        )
        dev_contratado = User.objects.create_user(
            username='dev_hitos_a', email='dev_hitos_a@test.jobdevs',
            nombre='Dev Hitos A', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=dev_contratado,
            empresa=empresa_user, estado='activa',
        )
        dev_no_contratado = User.objects.create_user(
            username='dev_hitos_b', email='dev_hitos_b@test.jobdevs',
            nombre='Dev Hitos B', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        return proyecto, dev_contratado, dev_no_contratado

    def test_asigna_hito_a_desarrollador_con_contratacion_activa(
        self, auth_client, proyecto_hitos
    ):
        """POST con desarrollador_id válido persiste la asignación y notifica al dev."""
        from proyectos.models import Entregable
        from notificaciones.models import Notificacion
        proyecto, dev_contratado, _ = proyecto_hitos

        response = auth_client.post(
            reverse('gestionar_hitos', args=[proyecto.id]),
            {
                'titulo': 'Hito individual',
                'descripcion': 'Solo para un dev',
                'desarrollador_id': str(dev_contratado.id),
            },
        )

        assert response.status_code == 302
        hito = Entregable.objects.get(proyecto=proyecto, titulo='Hito individual')
        assert hito.desarrollador_id == dev_contratado.id
        assert hito.equipo_id is None
        assert Notificacion.objects.filter(
            usuario=dev_contratado, tipo='avance'
        ).exists()

    def test_rechaza_asignacion_a_desarrollador_sin_contratacion_activa(
        self, auth_client, proyecto_hitos
    ):
        """POST con un dev sin contratación activa no crea el hito y muestra error."""
        from proyectos.models import Entregable
        proyecto, _, dev_no_contratado = proyecto_hitos

        response = auth_client.post(
            reverse('gestionar_hitos', args=[proyecto.id]),
            {
                'titulo': 'Hito invalido',
                'descripcion': 'Dev sin contrato',
                'desarrollador_id': str(dev_no_contratado.id),
            },
            follow=True,
        )

        assert response.status_code == 200
        assert not Entregable.objects.filter(
            proyecto=proyecto, titulo='Hito invalido'
        ).exists()
        assert 'no tiene una contratación activa' in response.content.decode('utf-8')

    def test_get_expone_selector_de_desarrolladores_activos(self, auth_client, proyecto_hitos):
        """El formulario de hitos ofrece el selector de desarrollador con los contratados activos."""
        from proyectos.models import Entregable
        proyecto, dev_contratado, dev_no_contratado = proyecto_hitos
        Entregable.objects.create(
            proyecto=proyecto, titulo='Hito asignado', descripcion='D',
            desarrollador=dev_contratado,
        )

        response = auth_client.get(reverse('gestionar_hitos', args=[proyecto.id]))

        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'data-testid="select-desarrollador-hito"' in content
        assert dev_contratado.nombre in content
        assert dev_no_contratado.nombre not in content

    def test_crea_equipo_y_asigna_hito_a_sus_miembros(
        self, auth_client, empresa_user, proyecto_hitos
    ):
        """RF 4.1.2 oficial: la empresa asigna un hito a un equipo del proyecto."""
        from contrataciones.models import Contratacion
        from notificaciones.models import Notificacion
        from proyectos.models import Entregable, Equipo

        proyecto, dev_uno, dev_dos = proyecto_hitos
        Contratacion.objects.create(
            proyecto=proyecto,
            desarrollador=dev_dos,
            empresa=empresa_user,
            estado='activa',
        )

        response = auth_client.post(
            reverse('gestionar_equipos', args=[proyecto.id]),
            {'nombre': 'Célula Backend', 'miembros': [dev_uno.id, dev_dos.id]},
        )
        assert response.status_code == 302
        equipo = Equipo.objects.get(proyecto=proyecto, nombre='Célula Backend')
        assert set(equipo.miembros.values_list('id', flat=True)) == {dev_uno.id, dev_dos.id}

        response = auth_client.post(
            reverse('gestionar_hitos', args=[proyecto.id]),
            {
                'titulo': 'API colaborativa',
                'descripcion': 'Entrega del equipo backend',
                'equipo_id': str(equipo.id),
            },
        )
        assert response.status_code == 302
        hito = Entregable.objects.get(proyecto=proyecto, titulo='API colaborativa')
        assert hito.equipo_id == equipo.id
        assert hito.desarrollador_id is None
        assert set(
            Notificacion.objects.filter(
                usuario_id__in=[dev_uno.id, dev_dos.id],
                tipo='avance',
                mensaje__contains='Célula Backend',
            ).values_list('usuario_id', flat=True)
        ) == {dev_uno.id, dev_dos.id}


class TestApiDetalleProyecto:
    def test_desarrollador_puede_ver_ficha_de_proyecto_publicado(self, dev_client, empresa_user):
        from proyectos.models import Proyecto
        from django.urls import reverse

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo="Proyecto Vitrina Publicado",
            descripcion="Descripción detallada para desarrolladores",
            estado="publicado",
            vacantes=2,
        )

        response = dev_client.get(reverse('api_detalle_proyecto', args=[proyecto.id]))
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['proyecto']['titulo'] == "Proyecto Vitrina Publicado"
        assert any(a['label'] == 'Postularme' for a in data['acciones'])

    def test_desarrollador_bloqueado_en_proyecto_no_publicado_sin_vinculo(self, dev_client, empresa_user):
        from proyectos.models import Proyecto
        from django.urls import reverse

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo="Proyecto Borrador",
            descripcion="Privado",
            estado="inactivo",
            vacantes=1,
        )

        response = dev_client.get(reverse('api_detalle_proyecto', args=[proyecto.id]))
        assert response.status_code == 403
        data = response.json()
        assert data['ok'] is False
        assert "No tienes permisos" in data['mensaje']

    def test_htmx_retorna_partial_html_ficha_proyecto(self, dev_client, empresa_user):
        from proyectos.models import Entregable, Proyecto
        from django.urls import reverse

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo="Proyecto HTMX Modal",
            descripcion="Descripción renderizada desde Django",
            estado="publicado",
            vacantes=3,
        )
        Entregable.objects.create(
            proyecto=proyecto,
            titulo="Hito Inicial",
            descripcion="Setup arquitectura",
            estado="completado",
        )

        response = dev_client.get(
            reverse('api_detalle_proyecto', args=[proyecto.id]),
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 200
        assert 'text/html' in response['Content-Type']
        html = response.content.decode('utf-8')
        assert 'data-jdp-partial' in html
        assert 'Proyecto HTMX Modal' in html
        assert 'Descripción renderizada desde Django' in html
        assert 'jdp-status-row' in html
        assert 'jdp-meta-grid' in html
        assert 'Hito Inicial' in html
        assert '1/1 completados (100%)' in html
        assert 'Postularme' in html

    def test_htmx_403_retorna_error_html_con_status_403(self, dev_client, empresa_user):
        from proyectos.models import Proyecto
        from django.urls import reverse

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo="Proyecto Privado HTMX",
            descripcion="No visible",
            estado="inactivo",
            vacantes=1,
        )

        response = dev_client.get(
            reverse('api_detalle_proyecto', args=[proyecto.id]),
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 403
        assert 'text/html' in response['Content-Type']
        html = response.content.decode('utf-8')
        assert 'jdp-error' in html
        assert 'No tienes permisos para ver este proyecto.' in html

    def test_htmx_escapa_xss_en_titulo_y_descripcion(self, dev_client, empresa_user):
        from proyectos.models import Proyecto
        from django.urls import reverse

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='<script>alert("xss-title")</script>',
            descripcion='<img src=x onerror=alert(1)>',
            estado="publicado",
            vacantes=1,
        )

        response = dev_client.get(
            reverse('api_detalle_proyecto', args=[proyecto.id]),
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert '<script>alert("xss-title")</script>' not in html
        assert '&lt;script&gt;alert(&quot;xss-title&quot;)&lt;/script&gt;' in html
        assert '<img src=x onerror=alert(1)>' not in html
        assert '&lt;img src=x onerror=alert(1)&gt;' in html

    def test_htmx_con_accept_json_o_format_json_preserva_json(self, dev_client, empresa_user):
        from proyectos.models import Proyecto
        from django.urls import reverse

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo="Proyecto Dual JSON",
            descripcion="D",
            estado="publicado",
            vacantes=1,
        )
        url = reverse('api_detalle_proyecto', args=[proyecto.id])

        resp_accept = dev_client.get(
            url,
            HTTP_HX_REQUEST='true',
            HTTP_ACCEPT='application/json',
        )
        assert resp_accept.status_code == 200
        assert resp_accept.json()['ok'] is True

        resp_fmt = dev_client.get(
            f"{url}?format=json",
            HTTP_HX_REQUEST='true',
        )
        assert resp_fmt.status_code == 200
        assert resp_fmt.json()['ok'] is True

