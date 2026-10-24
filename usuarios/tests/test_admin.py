import pytest
from datetime import timedelta
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, override_settings
from django.utils import timezone
from proyectos.models import Proyecto

User = get_user_model()


class TestDashboardAdmin:
    """Tests for dashboard_admin view and admin-only features."""

    def test_admin_access_dashboard(self, admin_client):
        """Admin can access their dashboard."""
        response = admin_client.get(reverse('dashboard_admin'))
        assert response.status_code == 200

    def test_non_admin_blocked(self, auth_client, dev_client, client):
        """Non-admin users cannot access admin dashboard."""
        for c in [auth_client, dev_client, client]:
            response = c.get(reverse('dashboard_admin'))
            assert response.status_code == 302

    def test_django_admin_route_accessible(self, admin_client):
        """SCRUM-183: Superusuario puede acceder al panel Django Admin en /django-admin/."""
        response = admin_client.get('/django-admin/')
        assert response.status_code == 200

    def test_django_admin_route_blocked_para_usuarios_comunes(self, auth_client, dev_client, client):
        """SCRUM-183: Usuarios no-staff son redirigidos al login de admin en /django-admin/."""
        for c in [auth_client, dev_client, client]:
            response = c.get('/django-admin/')
            assert response.status_code == 302


    def test_dashboard_shows_stats(self, admin_client, empresa_user, desarrollador_user):
        """Admin dashboard includes statistics."""
        response = admin_client.get(reverse('dashboard_admin'))
        assert response.status_code == 200
        assert 'total_usuarios' in response.context
        # total_usuarios cuenta empresas + desarrolladores activos (el rol admin no suma)
        assert response.context['total_usuarios'] == 2

    def test_dashboard_lists_users(self, admin_client, empresa_user, desarrollador_user):
        """Admin dashboard lists all users."""
        response = admin_client.get(reverse('dashboard_admin'))
        content = response.content.decode()
        assert 'empresa_test' in content
        assert 'dev_test' in content

    def test_dashboard_lists_projects(self, admin_client, empresa_user):
        """Admin dashboard shows project data when projects exist."""
        Proyecto.objects.create(
            empresa=empresa_user, titulo='Admin Proj',
            descripcion='Test', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = admin_client.get(reverse('dashboard_admin'))
        content = response.content.decode()
        assert 'Admin Proj' in content


class TestAdminToggleUsuario:
    """Tests for admin_toggle_usuario view."""

    def test_admin_can_toggle_user(self, admin_client, empresa_user):
        """Admin can activate/suspend a user."""
        response = admin_client.post(
            reverse('admin_toggle_usuario', args=[empresa_user.id])
        )
        assert response.status_code == 302
        empresa_user.refresh_from_db()
        assert not empresa_user.is_active

    def test_non_admin_cannot_toggle(self, auth_client, desarrollador_user):
        """Non-admin cannot toggle users."""
        response = auth_client.post(
            reverse('admin_toggle_usuario', args=[desarrollador_user.id])
        )
        assert response.status_code == 302

    def test_admin_toggle_usuario_invalida_sesion_activa_inmediatamente(self, admin_client, desarrollador_user):
        """RF 1.3.2 (SCRUM-44): Suspender usuario elimina su sesión activa de django_session en tiempo real."""
        dev_client = Client()
        login_ok = dev_client.login(username=desarrollador_user.username, password='TestPass123!')
        assert login_ok is True
        session_key = dev_client.cookies['sessionid'].value
        assert Session.objects.filter(session_key=session_key).exists()

        # Admin suspende al desarrollador
        response = admin_client.post(reverse('admin_toggle_usuario', args=[desarrollador_user.id]))
        assert response.status_code == 302
        desarrollador_user.refresh_from_db()
        assert not desarrollador_user.is_active

        # Sesión destruida en base de datos inmediatamente
        assert not Session.objects.filter(session_key=session_key).exists()

        # Próxima petición del usuario es expulsada a login
        res_dev = dev_client.get(reverse('dashboard_desarrollador'))
        assert res_dev.status_code == 302
        assert '/login/' in res_dev.url


class TestAdminReactivarProyecto:
    """Tests for admin_reactivar_proyecto view."""

    def test_admin_can_reactivate(self, admin_client, empresa_user):
        """Admin can reactivate a finalized project."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Finalizado Proj',
            descripcion='T', tipo_solucion='sitio_web',
            estado='finalizado',
        )
        response = admin_client.post(
            reverse('admin_reactivar_proyecto', args=[proyecto.id])
        )
        assert response.status_code == 302
        proyecto.refresh_from_db()
        assert proyecto.estado != 'finalizado'

    def test_non_admin_cannot_reactivate(self, auth_client, empresa_user):
        """Non-admin cannot reactivate projects."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Otro Finalizado',
            descripcion='T', tipo_solucion='sitio_web',
            estado='finalizado',
        )
        response = auth_client.post(
            reverse('admin_reactivar_proyecto', args=[proyecto.id])
        )
        assert response.status_code == 302
        proyecto.refresh_from_db()
        assert proyecto.estado == 'finalizado'


class TestApiBulkToggle:
    """Tests for api_bulk_toggle endpoint."""

    def test_admin_bulk_activate(self, admin_client, db):
        """Admin can bulk activate users."""
        user1 = User.objects.create_user(
            username='bulk1', email='bulk1@t.jobdevs', nombre='B1',
            rol='desarrollador', estado='suspendido', is_active=False,
            password='TestPass123!',
        )
        user2 = User.objects.create_user(
            username='bulk2', email='bulk2@t.jobdevs', nombre='B2',
            rol='desarrollador', estado='suspendido', is_active=False,
            password='TestPass123!',
        )
        import json
        response = admin_client.post(
            reverse('api_bulk_toggle'),
            data=json.dumps({'ids': [user1.id, user2.id], 'action': 'activate'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 2
        user1.refresh_from_db()
        user2.refresh_from_db()
        assert user1.is_active
        assert user2.is_active

    def test_admin_bulk_suspend(self, admin_client, desarrollador_user):
        """Admin can bulk suspend users and their active sessions are deleted (SCRUM-44)."""
        import json
        user2 = User.objects.create_user(
            username='bulk3', email='bulk3@t.jobdevs', nombre='B3',
            rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        c1 = Client()
        c1.login(username=desarrollador_user.username, password='TestPass123!')
        s1 = c1.cookies['sessionid'].value

        c2 = Client()
        c2.login(username='bulk3', password='TestPass123!')
        s2 = c2.cookies['sessionid'].value

        assert Session.objects.filter(session_key=s1).exists()
        assert Session.objects.filter(session_key=s2).exists()

        response = admin_client.post(
            reverse('api_bulk_toggle'),
            data=json.dumps({'ids': [desarrollador_user.id, user2.id], 'action': 'suspend'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        desarrollador_user.refresh_from_db()
        user2.refresh_from_db()
        assert not desarrollador_user.is_active
        assert not user2.is_active

        # Ambas sesiones activas fueron destruidas de raíz
        assert not Session.objects.filter(session_key=s1).exists()
        assert not Session.objects.filter(session_key=s2).exists()

    def test_non_admin_cannot_bulk(self, auth_client, desarrollador_user):
        """Non-admin cannot use bulk toggle."""
        import json
        response = auth_client.post(
            reverse('api_bulk_toggle'),
            data=json.dumps({'ids': [desarrollador_user.id], 'action': 'activate'}),
            content_type='application/json',
        )
        assert response.status_code == 403

    def test_admin_cannot_suspend_self(self, admin_client, admin_user):
        """Admin cannot suspend themselves via bulk."""
        import json
        response = admin_client.post(
            reverse('api_bulk_toggle'),
            data=json.dumps({'ids': [admin_user.id], 'action': 'suspend'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        admin_user.refresh_from_db()
        assert admin_user.is_active  # Not suspended


class TestApiRateLimit:
    """Tests for rate limiting on admin API endpoints."""

    def test_api_usuarios_rate_limit(self, admin_client):
        """Exceeding rate limit on api_usuarios returns 429 Too Many Requests."""
        import time
        from django.core.cache import cache
        cache.clear()

        response = admin_client.get(reverse('api_usuarios'))
        assert response.status_code == 200

        # Simulate reaching rate limit
        user_id = admin_client.session['_auth_user_id']
        window_bucket = int(time.time() // 60)
        cache_key = f"rl:api_usuarios:user_{user_id}:127.0.0.1:{window_bucket}"
        cache.set(cache_key, 60, timeout=60)

        response = admin_client.get(reverse('api_usuarios'))
        assert response.status_code == 429
        data = response.json()
        assert 'Demasiadas solicitudes' in data['error']
        assert int(response['Retry-After']) <= 60

    def test_api_crear_usuario_rate_limit(self, admin_client):
        """Mutation endpoints like api_crear_usuario enforce tighter rate limiting."""
        import time
        from django.core.cache import cache
        cache.clear()

        user_id = admin_client.session['_auth_user_id']
        window_bucket = int(time.time() // 60)
        cache_key = f"rl:api_crear_usuario:user_{user_id}:127.0.0.1:{window_bucket}"
        cache.set(cache_key, 30, timeout=60)

        response = admin_client.post(
            reverse('api_crear_usuario'),
            data='{}',
            content_type='application/json',
        )
        assert response.status_code == 429
        assert 'Demasiadas solicitudes' in response.json()['error']


class TestAdminPaginacionYBusqueda:
    """Tests para SCRUM-172: Búsqueda y paginación server-side en dashboard administrativo."""

    def test_dashboard_admin_busqueda_usuarios(self, admin_client, db):
        """Búsqueda por parámetro user_q filtra usuarios coincidentes."""
        User.objects.create_user(
            username='usuario_unico_busqueda',
            email='unico@test.jobdevs',
            nombre='Objetivo Busqueda',
            rol='desarrollador',
            password='TestPass123!',
        )
        response = admin_client.get(reverse('dashboard_admin') + '?user_q=unico_busqueda')
        assert response.status_code == 200
        usuarios = list(response.context['usuarios_todos'])
        assert len(usuarios) == 1
        assert usuarios[0].username == 'usuario_unico_busqueda'

    def test_dashboard_admin_paginacion_usuarios(self, admin_client, db):
        """Si hay más de 25 usuarios, se aplica paginación a 25 registros por página."""
        usuarios_creados = [
            User(
                username=f'page_user_{i}',
                email=f'page{i}@test.jobdevs',
                nombre=f'Page User {i}',
                rol='desarrollador',
            ) for i in range(30)
        ]
        User.objects.bulk_create(usuarios_creados)

        response = admin_client.get(reverse('dashboard_admin'))
        assert response.status_code == 200
        assert len(response.context['usuarios_todos']) == 25
        assert response.context['usuarios_todos'].paginator.count >= 30

    def test_api_usuarios_busqueda_y_paginacion(self, admin_client, db):
        """api_usuarios soporta parámetros q, limit y page."""
        target = User.objects.create_user(
            username='api_search_target',
            email='apisearch@test.jobdevs',
            nombre='Api Target',
            rol='empresa',
            password='TestPass123!',
        )
        response = admin_client.get(reverse('api_usuarios') + '?q=api_search_target&limit=10')
        assert response.status_code == 200
        data = response.json()
        assert 'total' in data
        assert data['total'] == 1
        assert data['usuarios'][0]['username'] == 'api_search_target'

    def test_api_usuarios_paginacion_segunda_pagina(self, admin_client, db):
        """api_usuarios página 2 retorna registros distintos y metadatos correctos."""
        usuarios_creados = [
            User(
                username=f'api_pag_user_{i:02d}',
                email=f'apipag{i}@test.jobdevs',
                nombre=f'Api Pag User {i}',
                rol='desarrollador',
            ) for i in range(15)
        ]
        User.objects.bulk_create(usuarios_creados)

        # Página 1 con limit=10
        resp1 = admin_client.get(reverse('api_usuarios') + '?limit=10&page=1')
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1['page'] == 1
        assert data1['total_pages'] >= 2
        assert len(data1['usuarios']) == 10

        # Página 2 con limit=10
        resp2 = admin_client.get(reverse('api_usuarios') + '?limit=10&page=2')
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2['page'] == 2
        assert len(data2['usuarios']) >= 5

        # Los IDs de página 1 y página 2 deben ser disjuntos
        p1_ids = {u['id'] for u in data1['usuarios']}
        p2_ids = {u['id'] for u in data2['usuarios']}
        assert p1_ids.isdisjoint(p2_ids)

    def test_api_usuarios_parametros_invalidos_retorna_400(self, admin_client):
        """api_usuarios con limit o page inválidos retorna 400."""
        resp = admin_client.get(reverse('api_usuarios') + '?limit=invalid&page=1')
        assert resp.status_code == 400
        assert 'inválidos' in resp.json()['error']


class TestAdminDepurarNotificaciones:
    """Tests para SCRUM-316 (HU-A16): depuración de notificaciones desde UI admin."""

    def _crear_notificaciones(self, usuario):
        from notificaciones.models import Notificacion

        ahora = timezone.now()
        vieja_leida = Notificacion.objects.create(
            usuario=usuario, tipo='alerta', mensaje='Vieja leída', leida=True,
        )
        Notificacion.objects.filter(id=vieja_leida.id).update(fecha=ahora - timedelta(days=120))

        vieja_no_leida = Notificacion.objects.create(
            usuario=usuario, tipo='alerta', mensaje='Vieja no leída', leida=False,
        )
        Notificacion.objects.filter(id=vieja_no_leida.id).update(fecha=ahora - timedelta(days=120))

        reciente_leida = Notificacion.objects.create(
            usuario=usuario, tipo='alerta', mensaje='Reciente leída', leida=True,
        )
        Notificacion.objects.filter(id=reciente_leida.id).update(fecha=ahora - timedelta(days=5))

        return vieja_leida, vieja_no_leida, reciente_leida

    def test_no_administrador_recibe_403(self, dev_client, desarrollador_user):
        """Un usuario autenticado que no es administrador recibe 403."""
        self._crear_notificaciones(desarrollador_user)

        response = dev_client.post(reverse('admin_depurar_notificaciones'), {'dias': 90})

        assert response.status_code == 403

    def test_get_no_permitido_recibe_405(self, admin_client):
        """El endpoint solo acepta POST; GET responde 405."""
        response = admin_client.get(reverse('admin_depurar_notificaciones'))

        assert response.status_code == 405

    def test_administrador_ejecuta_depuracion_y_audita(self, admin_client, admin_user, desarrollador_user):
        """Admin POST borra notificaciones antiguas leídas, audita y redirige al dashboard."""
        from django.contrib.messages import get_messages
        from logs.models import LogAuditoria
        from notificaciones.models import Notificacion

        vieja_leida, vieja_no_leida, reciente_leida = self._crear_notificaciones(desarrollador_user)

        response = admin_client.post(
            reverse('admin_depurar_notificaciones'), {'dias': 90},
        )

        assert response.status_code == 302
        assert response.url == reverse('dashboard_admin') + '?section=reportsSection'

        assert not Notificacion.objects.filter(id=vieja_leida.id).exists()
        assert Notificacion.objects.filter(id=vieja_no_leida.id).exists()
        assert Notificacion.objects.filter(id=reciente_leida.id).exists()

        log = LogAuditoria.objects.get(tabla_afectada='notificaciones')
        assert log.usuario == admin_user
        assert '1 eliminadas' in log.accion
        assert '> 90 días' in log.accion

        mensajes = [str(m) for m in get_messages(response.wsgi_request)]
        assert any('Se depuraron 1 notificaciones antiguas exitosamente.' in m for m in mensajes)

    def test_dias_invalidos_y_negativos_se_normalizan(self, admin_client, desarrollador_user):
        """Un valor no numérico cae al default 90 y un negativo se normaliza a 0."""
        from logs.models import LogAuditoria
        from notificaciones.models import Notificacion

        vieja_leida, _, _ = self._crear_notificaciones(desarrollador_user)

        response_invalido = admin_client.post(
            reverse('admin_depurar_notificaciones'), {'dias': 'abc'},
        )
        assert response_invalido.status_code == 302
        # Default 90 días: la notificación de 120 días se elimina
        assert not Notificacion.objects.filter(id=vieja_leida.id).exists()

        response_negativo = admin_client.post(
            reverse('admin_depurar_notificaciones'), {'dias': '-5'},
        )
        assert response_negativo.status_code == 302
        # Cada ejecución queda auditada, incluso cuando no hay nada que borrar
        assert LogAuditoria.objects.filter(tabla_afectada='notificaciones').count() == 2



class TestAdminAlertaRetrasoParametrizada:
    """SCRUM-315 (HU-A07): umbral de alerta por inactividad parametrizable."""

    def _crear_proyecto_en_desarrollo(self, empresa_user, titulo):
        return Proyecto.objects.create(
            empresa=empresa_user, titulo=titulo, descripcion='Proyecto de prueba',
            tipo_solucion='sitio_web', estado='en_desarrollo',
        )

    def _proyecto_con_avance_de_dias(self, empresa_user, titulo, dias):
        """Crea un proyecto en desarrollo cuyo último entregable es de hace `dias`."""
        from proyectos.models import Entregable

        proyecto = self._crear_proyecto_en_desarrollo(empresa_user, titulo)
        entregable = Entregable.objects.create(proyecto=proyecto, titulo='Hito inicial')
        Entregable.objects.filter(id=entregable.id).update(
            fecha_creacion=timezone.now() - timedelta(days=dias)
        )
        return proyecto

    def _proyecto_sin_avances_con_contrato_de_dias(
        self, empresa_user, desarrollador_user, titulo, dias
    ):
        """Proyecto sin entregables cuya contratación activa inició hace `dias`."""
        from contrataciones.models import Contratacion

        proyecto = self._crear_proyecto_en_desarrollo(empresa_user, titulo)
        contratacion = Contratacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, empresa=empresa_user,
            estado='activa',
        )
        Contratacion.objects.filter(id=contratacion.id).update(
            fecha_inicio=(timezone.now() - timedelta(days=dias)).date()
        )
        return proyecto

    @staticmethod
    def _titulos_alerta(response):
        return [alerta[0] for alerta in response.context['alertas_retraso']]

    @override_settings(PROYECTO_DIAS_ALERTA_RETRASO=15)
    def test_avance_de_10_dias_no_genera_alerta_con_umbral_15(
        self, admin_client, empresa_user
    ):
        """Con umbral de 15 días, un avance de hace 10 días no alerta."""
        self._proyecto_con_avance_de_dias(empresa_user, 'Proyecto Reciente', 10)

        response = admin_client.get(reverse('dashboard_admin'))

        assert response.status_code == 200
        assert response.context['dias_alerta_retraso'] == 15
        assert 'Proyecto Reciente' not in self._titulos_alerta(response)

    @override_settings(PROYECTO_DIAS_ALERTA_RETRASO=15)
    def test_avance_de_20_dias_genera_alerta_con_umbral_15(
        self, admin_client, empresa_user
    ):
        """Con umbral de 15 días, un avance de hace 20 días sí alerta."""
        self._proyecto_con_avance_de_dias(empresa_user, 'Proyecto Retrasado', 20)

        response = admin_client.get(reverse('dashboard_admin'))

        assert 'Proyecto Retrasado' in self._titulos_alerta(response)

    @override_settings(PROYECTO_DIAS_ALERTA_RETRASO=15)
    def test_proyecto_sin_avances_con_contrato_de_20_dias_genera_alerta(
        self, admin_client, empresa_user, desarrollador_user
    ):
        """Sin entregables, la inactividad se mide desde el inicio del contrato."""
        self._proyecto_sin_avances_con_contrato_de_dias(
            empresa_user, desarrollador_user, 'Proyecto Sin Avances', 20
        )

        response = admin_client.get(reverse('dashboard_admin'))

        alertas = {alerta[0]: alerta[3] for alerta in response.context['alertas_retraso']}
        assert alertas.get('Proyecto Sin Avances') == 20

    @override_settings(PROYECTO_DIAS_ALERTA_RETRASO=5)
    def test_umbral_configurable_a_5_dias_alerta_proyecto_de_10_dias(
        self, admin_client, empresa_user
    ):
        """Con umbral de 5 días, el mismo avance de 10 días sí alerta."""
        self._proyecto_con_avance_de_dias(empresa_user, 'Proyecto Reciente', 10)

        response = admin_client.get(reverse('dashboard_admin'))

        assert response.context['dias_alerta_retraso'] == 5
        assert 'Proyecto Reciente' in self._titulos_alerta(response)

    @override_settings(PROYECTO_DIAS_ALERTA_RETRASO=15)
    def test_template_muestra_umbral_y_testid_de_alertas(self, admin_client, empresa_user):
        """La sección de alertas indica el umbral vigente y expone su testid."""
        self._proyecto_con_avance_de_dias(empresa_user, 'Proyecto Retrasado', 20)

        content = admin_client.get(reverse('dashboard_admin')).content.decode()

        assert 'data-testid="tabla-alertas-inactividad"' in content
        assert '&gt; 15 días' in content


class TestAdminMetricasUsuariosSCRUM226:
    """SCRUM-226 (RF 1.3.1): métricas de usuarios inactivos y suspendidos."""

    def test_dashboard_admin_expone_metricas_inactivos_y_suspendidos(self, admin_client, db):
        """El contexto incluye los conteos de usuarios inactivos y suspendidos."""
        User.objects.create_user(
            username='inactivo_metric', email='inactivo@test.jobdevs',
            nombre='Inactivo Metric', rol='desarrollador',
            estado='inactivo', password='TestPass123!',
        )
        User.objects.create_user(
            username='suspendido_metric', email='suspendido@test.jobdevs',
            nombre='Suspendido Metric', rol='empresa',
            estado='suspendido', password='TestPass123!',
        )

        response = admin_client.get(reverse('dashboard_admin'))

        assert response.status_code == 200
        assert response.context['usuarios_inactivos'] == 1
        assert response.context['usuarios_suspendidos'] == 1

    def test_dashboard_admin_total_usuarios_preservado_con_metricas(self, admin_client, empresa_user, desarrollador_user):
        """Las nuevas métricas no alteran el cálculo de total_usuarios (empresas + devs activos)."""
        inactivo = User.objects.create_user(
            username='inactivo_preserva', email='inactivop@test.jobdevs',
            nombre='Inactivo Preserva', rol='desarrollador',
            estado='inactivo', password='TestPass123!',
        )
        inactivo.is_active = False
        inactivo.save()

        response = admin_client.get(reverse('dashboard_admin'))

        assert response.context['total_usuarios'] == 2
        assert response.context['usuarios_inactivos'] == 1

    def test_template_muestra_metricas_de_usuarios(self, admin_client, db):
        """El grid de métricas incluye tarjetas identificables de inactivos y suspendidos."""
        content = admin_client.get(reverse('dashboard_admin')).content.decode()

        assert 'data-testid="metric-usuarios-inactivos"' in content
        assert 'data-testid="metric-usuarios-suspendidos"' in content


class TestAdminFiltroFechaRegistroSCRUM226:
    """SCRUM-226 (RF 1.3.3): filtro por rango de fecha de registro."""

    def _crear_usuario_con_registro(self, username, fecha):
        user = User.objects.create_user(
            username=username, email=f'{username}@test.jobdevs',
            nombre=username.replace('_', ' ').title(), rol='desarrollador',
            password='TestPass123!',
        )
        User.objects.filter(id=user.id).update(date_joined=fecha)
        return user

    def test_dashboard_admin_filtra_por_fecha_desde(self, admin_client, db):
        """fecha_desde excluye usuarios registrados antes del rango."""
        self._crear_usuario_con_registro('viejo_desde', timezone.now() - timedelta(days=60))
        self._crear_usuario_con_registro('nuevo_desde', timezone.now() - timedelta(days=1))

        desde = (timezone.now() - timedelta(days=10)).date().isoformat()
        response = admin_client.get(reverse('dashboard_admin') + f'?fecha_desde={desde}')

        assert response.status_code == 200
        usernames = [u.username for u in response.context['usuarios_todos']]
        assert 'nuevo_desde' in usernames
        assert 'viejo_desde' not in usernames
        assert response.context['fecha_desde'] == desde

    def test_dashboard_admin_filtra_por_fecha_hasta(self, admin_client, db):
        """fecha_hasta excluye usuarios registrados después del rango."""
        self._crear_usuario_con_registro('viejo_hasta', timezone.now() - timedelta(days=60))
        self._crear_usuario_con_registro('nuevo_hasta', timezone.now() - timedelta(days=1))

        hasta = (timezone.now() - timedelta(days=10)).date().isoformat()
        response = admin_client.get(reverse('dashboard_admin') + f'?fecha_hasta={hasta}')

        assert response.status_code == 200
        usernames = [u.username for u in response.context['usuarios_todos']]
        assert 'viejo_hasta' in usernames
        assert 'nuevo_hasta' not in usernames
        assert response.context['fecha_hasta'] == hasta

    def test_dashboard_admin_rango_de_fechas_combinado(self, admin_client, db):
        """fecha_desde y fecha_hasta delimitan un rango inclusivo de registros."""
        self._crear_usuario_con_registro('fuera_rango', timezone.now() - timedelta(days=60))
        self._crear_usuario_con_registro('dentro_rango', timezone.now() - timedelta(days=10))

        desde = (timezone.now() - timedelta(days=20)).date().isoformat()
        hasta = (timezone.now() - timedelta(days=5)).date().isoformat()
        response = admin_client.get(
            reverse('dashboard_admin') + f'?fecha_desde={desde}&fecha_hasta={hasta}'
        )

        usernames = [u.username for u in response.context['usuarios_todos']]
        assert 'dentro_rango' in usernames
        assert 'fuera_rango' not in usernames

    def test_template_incluye_controles_de_fecha_de_registro(self, admin_client, db):
        """Los filtros de fecha exponen sus inputs y las filas llevan data-fecha-registro."""
        content = admin_client.get(reverse('dashboard_admin')).content.decode()

        assert 'data-testid="filtro-fecha-desde"' in content
        assert 'data-testid="filtro-fecha-hasta"' in content
        assert 'name="fecha_desde"' in content
        assert 'name="fecha_hasta"' in content
        assert 'data-fecha-registro=' in content

    def test_api_usuarios_filtra_por_fecha_desde(self, admin_client, db):
        """api_usuarios respeta el parámetro fecha_desde."""
        self._crear_usuario_con_registro('api_viejo_desde', timezone.now() - timedelta(days=60))
        self._crear_usuario_con_registro('api_nuevo_desde', timezone.now() - timedelta(days=1))

        desde = (timezone.now() - timedelta(days=10)).date().isoformat()
        response = admin_client.get(reverse('api_usuarios') + f'?fecha_desde={desde}')

        assert response.status_code == 200
        usernames = {u['username'] for u in response.json()}
        assert 'api_nuevo_desde' in usernames
        assert 'api_viejo_desde' not in usernames

    def test_api_usuarios_filtra_por_fecha_hasta(self, admin_client, db):
        """api_usuarios respeta el parámetro fecha_hasta."""
        self._crear_usuario_con_registro('api_viejo_hasta', timezone.now() - timedelta(days=60))
        self._crear_usuario_con_registro('api_nuevo_hasta', timezone.now() - timedelta(days=1))

        hasta = (timezone.now() - timedelta(days=10)).date().isoformat()
        response = admin_client.get(reverse('api_usuarios') + f'?fecha_hasta={hasta}')

        assert response.status_code == 200
        usernames = {u['username'] for u in response.json()}
        assert 'api_viejo_hasta' in usernames
        assert 'api_nuevo_hasta' not in usernames

    def test_api_usuarios_rango_de_fechas_combinado(self, admin_client, db):
        """api_usuarios combina fecha_desde y fecha_hasta."""
        self._crear_usuario_con_registro('api_fuera_rango', timezone.now() - timedelta(days=60))
        self._crear_usuario_con_registro('api_dentro_rango', timezone.now() - timedelta(days=10))

        desde = (timezone.now() - timedelta(days=20)).date().isoformat()
        hasta = (timezone.now() - timedelta(days=5)).date().isoformat()
        response = admin_client.get(
            reverse('api_usuarios') + f'?fecha_desde={desde}&fecha_hasta={hasta}'
        )

        usernames = {u['username'] for u in response.json()}
        assert 'api_dentro_rango' in usernames
        assert 'api_fuera_rango' not in usernames


class TestAdminModoVerificacionSenaSCRUM311:
    """SCRUM-311: el panel expone el mecanismo oficial de verificación SENA."""

    def test_dashboard_admin_expone_modo_padron_oficial(self, admin_client, db):
        """Sin SENA_API_URL el mecanismo activo es el padrón institucional local."""
        response = admin_client.get(reverse('dashboard_admin'))

        assert response.status_code == 200
        assert response.context['sena_modo_verificacion'] == 'padron_oficial'
        assert not response.context['sena_api_url']

    @override_settings(SENA_API_URL='https://sofia.sena.edu.co/api')
    def test_dashboard_admin_expone_modo_pasarela_externa(self, admin_client, db):
        """Con SENA_API_URL configurada el mecanismo activo es la pasarela externa."""
        response = admin_client.get(reverse('dashboard_admin'))

        assert response.context['sena_modo_verificacion'] == 'pasarela_externa'
        assert response.context['sena_api_url'] == 'https://sofia.sena.edu.co/api'

    def test_template_renderiza_badge_modo_verificacion_sena(self, admin_client, db):
        """La sección de fichas SENA muestra el badge del mecanismo oficial activo."""
        content = admin_client.get(reverse('dashboard_admin')).content.decode()

        assert 'data-testid="badge-modo-verificacion-sena"' in content
        assert 'Padrón Institucional Local' in content
        assert 'SOFIA Plus' in content
