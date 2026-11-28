from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from proyectos.models import Proyecto

User = get_user_model()


class TestAlertasCumplimiento:
    def test_retraso_depende_de_cumplimiento_no_del_cierre_de_oferta(self, admin_client, empresa_user):
        from django.core.cache import cache

        hoy = timezone.localdate()
        vencido = Proyecto.objects.create(
            empresa=empresa_user, titulo='Entrega vencida', descripcion='D',
            tipo_solucion='sitio_web', estado='en_desarrollo',
            fecha_limite=hoy + timedelta(days=10),
            fecha_cumplimiento=hoy - timedelta(days=1),
        )
        vigente = Proyecto.objects.create(
            empresa=empresa_user, titulo='Entrega vigente', descripcion='D',
            tipo_solucion='sitio_web', estado='en_desarrollo',
            fecha_limite=hoy - timedelta(days=1),
            fecha_cumplimiento=hoy + timedelta(days=10),
        )
        sin_fecha = Proyecto.objects.create(
            empresa=empresa_user, titulo='Sin entrega acordada', descripcion='D',
            tipo_solucion='sitio_web', estado='en_desarrollo',
            fecha_limite=hoy - timedelta(days=1),
        )
        cache.clear()
        response = admin_client.get(reverse('dashboard_admin'))
        ids = {p.id for p in response.context['proyectos_cumplimiento_vencido']}
        assert ids == {vencido.id}
        assert vigente.id not in ids
        assert sin_fecha.id not in ids
        assert response.context['p_ret'] == 1


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
        """Usuarios comunes y anónimos quedan fuera del admin nativo y terminan en
        el modal de login de la landing: no hay pantalla de acceso aparte."""
        for c in [auth_client, dev_client, client]:
            response = c.get('/django-admin/', follow=True)
            assert response.status_code == 200
            assert response.redirect_chain, 'Tiene que pasar por un redirect'
            assert response.redirect_chain[-1][0].startswith('/?login=1'), response.redirect_chain

    def test_el_admin_nativo_no_tiene_login_propio(self, client):
        """Un solo formulario de acceso: el del sitio, no /django-admin/login/."""
        respuesta = client.get('/django-admin/login/?next=/django-admin/')
        assert respuesta.status_code == 302
        assert respuesta['Location'] == '/login/?next=/django-admin/', respuesta['Location']

    def test_django_admin_solo_superusuarios(self, admin_client, admin_user, empresa_user):
        """El admin nativo queda para superusuarios: `is_staff` es una propiedad
        mapeada a `is_superuser`, así que un rol común no entra."""
        assert admin_client.get('/django-admin/').status_code == 200
        assert admin_user.is_superuser is True

    def test_is_staff_es_alias_de_is_superuser(self, admin_user, empresa_user):
        """Contrato del modelo: no existe "staff sin superusuario"."""
        assert admin_user.is_staff == admin_user.is_superuser == True
        assert empresa_user.is_staff == empresa_user.is_superuser == False


class TestContinuacionProyectoFinalizado:
    def test_admin_crea_sucesor_sin_reactivar_original_ni_contratos(
        self, admin_client, empresa_user, desarrollador_user
    ):
        from contrataciones.models import Contratacion

        original = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto cerrado', descripcion='Alcance original',
            tipo_solucion='sitio_web', prioridad='alta', modalidad='remoto',
            vacantes=2, estado='finalizado',
        )
        contrato = Contratacion.objects.create(
            proyecto=original, empresa=empresa_user,
            desarrollador=desarrollador_user, estado='finalizada',
        )

        response = admin_client.post(
            reverse('admin_reactivar_proyecto', args=[original.pk])
        )

        assert response.status_code == 302
        original.refresh_from_db()
        contrato.refresh_from_db()
        assert original.estado == 'finalizado'
        assert contrato.estado == 'finalizada'
        sucesor = Proyecto.objects.get(proyecto_origen=original)
        assert sucesor.estado == 'publicado'
        assert sucesor.empresa == original.empresa
        assert sucesor.descripcion == original.descripcion
        assert sucesor.vacantes == original.vacantes
        assert sucesor.pk != original.pk
        assert not sucesor.contrataciones.exists()


class TestLoginUnico:
    """La administración entra por el mismo login de la página."""

    def test_no_existe_la_pantalla_de_login_de_admin(self):
        from pathlib import Path

        from django.conf import settings

        assert not (Path(settings.BASE_DIR) / 'templates' / 'admin' / 'login.html').exists()

    def test_login_con_next_invita_al_modal_de_la_landing(self, client):
        respuesta = client.get('/login/?next=/django-admin/')
        assert respuesta.status_code == 302
        assert respuesta['Location'] == '/?login=1&next=/django-admin/'

    def test_el_modal_conserva_el_next(self, client):
        contenido = client.get('/?login=1&next=/django-admin/').content.decode()
        assert 'name="next" value="/django-admin/"' in contenido


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

    def test_admin_toggle_usuario_limpia_bloqueado_por_intentos(self, admin_client, empresa_user):
        """SCRUM-463: Al desactivar un usuario con admin_toggle_usuario se debe limpiar bloqueado_por_intentos."""
        empresa_user.bloqueado_por_intentos = True
        empresa_user.save(update_fields=['bloqueado_por_intentos'])

        admin_client.post(reverse('admin_toggle_usuario', args=[empresa_user.id]))
        empresa_user.refresh_from_db()
        assert not empresa_user.is_active
        assert empresa_user.estado == 'inactivo'
        assert not empresa_user.bloqueado_por_intentos

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
        """Admin creates a published continuation from a finalized project."""
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
        assert proyecto.estado == 'finalizado'
        sucesor = Proyecto.objects.get(proyecto_origen=proyecto)
        assert sucesor.estado == 'publicado'
        assert sucesor.titulo == 'Continuación de Finalizado Proj'

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

        from logs.models import LogAuditoria
        logs = LogAuditoria.objects.filter(
            tabla_afectada='usuarios', registro_id__in=[user1.id, user2.id]
        )
        assert logs.count() == 2
        assert all(log.valor_anterior == 'estado=suspendido' for log in logs)
        assert all(log.valor_nuevo == 'estado=activo' for log in logs)

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
        User.objects.create_user(
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

    def test_boton_aplicar_filtro_fecha_no_recarga_pagina(self, admin_client, db):
        """El botón Aplicar del filtro Registro no debe enviar el formulario ni recargar la página."""
        content = admin_client.get(reverse('dashboard_admin')).content.decode()

        assert 'data-testid="btn-aplicar-fecha-registro"' in content
        assert 'type="button" class="btn btn-secondary btn-sm" data-testid="btn-aplicar-fecha-registro" onclick="filterUsers()"' in content
        assert 'onsubmit="event.preventDefault(); filterUsers();"' in content

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

    def test_template_oculta_banner_modo_verificacion_sena(self, admin_client, db):
        """La sección de fichas SENA no muestra el banner redundante de modo de verificación."""
        content = admin_client.get(reverse('dashboard_admin')).content.decode()

        assert 'data-testid="badge-modo-verificacion-sena"' not in content
        assert 'fichasSenaSection' in content


class TestAdminExcepcionesFichaSenaSCRUM225:
    """SCRUM-225 (RF 9.1.2): gestión de excepciones individuales a la lista blanca SENA."""

    def _crear_excepcion(self, admin_user, perfil, numero_ficha='3000123',
                         activa=True, fecha_expiracion=None):
        from usuarios.models import ExcepcionFichaSena
        return ExcepcionFichaSena.objects.create(
            desarrollador=perfil,
            numero_ficha=numero_ficha,
            justificacion='Caso especial aprobado por coordinación académica.',
            autorizado_por=admin_user,
            activa=activa,
            fecha_expiracion=fecha_expiracion,
        )

    def test_admin_crea_excepcion(self, admin_client, admin_user, desarrollador_user):
        """El administrador registra una excepción con vigencia y queda auditada."""
        from logs.models import LogAuditoria
        from usuarios.models import ExcepcionFichaSena

        perfil = desarrollador_user.perfil_desarrollador
        response = admin_client.post(reverse('admin_crear_excepcion_ficha_sena'), {
            'desarrollador_id': perfil.id,
            'numero_ficha': ' 3000-123 ',
            'justificacion': 'Ficha pendiente de cargue en SOFIA Plus.',
            'dias_vigencia': '30',
        })

        assert response.status_code == 302
        assert response.url == reverse('dashboard_admin') + '?section=fichasSenaSection'
        excepcion = ExcepcionFichaSena.objects.get(desarrollador=perfil)
        assert excepcion.numero_ficha == '3000123'
        assert excepcion.activa is True
        assert excepcion.autorizado_por == admin_user
        assert excepcion.fecha_expiracion is not None
        assert excepcion.fecha_expiracion > timezone.now()
        assert LogAuditoria.objects.filter(
            tabla_afectada='excepciones_ficha_sena', registro_id=excepcion.id
        ).exists()

    def test_admin_crea_excepcion_sin_vigencia(self, admin_client, desarrollador_user):
        """Sin dias_vigencia la excepción queda sin fecha de expiración."""
        from usuarios.models import ExcepcionFichaSena

        perfil = desarrollador_user.perfil_desarrollador
        response = admin_client.post(reverse('admin_crear_excepcion_ficha_sena'), {
            'desarrollador_id': perfil.id,
            'numero_ficha': '3000456',
            'justificacion': 'Excepción permanente aprobada por el comité.',
        })

        assert response.status_code == 302
        excepcion = ExcepcionFichaSena.objects.get(numero_ficha='3000456')
        assert excepcion.fecha_expiracion is None

    def test_admin_no_crea_excepcion_sin_desarrollador_valido(self, admin_client, db):
        """Un desarrollador inexistente no genera excepción."""
        from usuarios.models import ExcepcionFichaSena

        response = admin_client.post(reverse('admin_crear_excepcion_ficha_sena'), {
            'desarrollador_id': '999999',
            'numero_ficha': '3000789',
            'justificacion': 'Justificación válida.',
        })

        assert response.status_code == 302
        assert not ExcepcionFichaSena.objects.exists()

    def test_no_admin_no_puede_crear_excepcion(self, auth_client, desarrollador_user):
        """Un usuario no administrador recibe 403 y no se crea la excepción."""
        from usuarios.models import ExcepcionFichaSena

        perfil = desarrollador_user.perfil_desarrollador
        response = auth_client.post(reverse('admin_crear_excepcion_ficha_sena'), {
            'desarrollador_id': perfil.id,
            'numero_ficha': '3000123',
            'justificacion': 'Intento no autorizado.',
        })

        assert response.status_code == 403
        assert not ExcepcionFichaSena.objects.exists()

    def test_admin_revoca_excepcion(self, admin_client, admin_user, desarrollador_user):
        """Revocar desactiva la excepción y registra auditoría."""
        from logs.models import LogAuditoria

        excepcion = self._crear_excepcion(admin_user, desarrollador_user.perfil_desarrollador)
        response = admin_client.post(
            reverse('admin_revocar_excepcion_ficha_sena', args=[excepcion.id])
        )

        assert response.status_code == 302
        assert response.url == reverse('dashboard_admin') + '?section=fichasSenaSection'
        excepcion.refresh_from_db()
        assert excepcion.activa is False
        assert LogAuditoria.objects.filter(
            tabla_afectada='excepciones_ficha_sena', registro_id=excepcion.id
        ).exists()

    def test_no_admin_no_puede_revocar_excepcion(self, admin_client, auth_client,
                                                 admin_user, desarrollador_user):
        """Un usuario no administrador no puede revocar excepciones."""
        excepcion = self._crear_excepcion(admin_user, desarrollador_user.perfil_desarrollador)

        response = auth_client.post(
            reverse('admin_revocar_excepcion_ficha_sena', args=[excepcion.id])
        )

        assert response.status_code == 403
        excepcion.refresh_from_db()
        assert excepcion.activa is True

    def test_dashboard_expone_excepciones_en_contexto(self, admin_client, admin_user,
                                                      desarrollador_user):
        """El dashboard expone las excepciones y su total en el contexto."""
        excepcion = self._crear_excepcion(admin_user, desarrollador_user.perfil_desarrollador)

        response = admin_client.get(reverse('dashboard_admin'))

        assert response.status_code == 200
        assert response.context['total_excepciones_fichas_sena'] == 1
        assert list(response.context['excepciones_fichas_sena']) == [excepcion]

    def test_template_renderiza_tabla_de_excepciones(self, admin_client, admin_user,
                                                     desarrollador_user):
        """La sección de fichas SENA incluye la tabla de excepciones."""
        excepcion = self._crear_excepcion(admin_user, desarrollador_user.perfil_desarrollador)

        content = admin_client.get(reverse('dashboard_admin')).content.decode()

        assert 'data-testid="tabla-excepciones-sena"' in content
        assert excepcion.numero_ficha in content
        assert reverse('admin_crear_excepcion_ficha_sena') in content


class TestVisorLogsTecnicosTemplate:
    """El panel admin ya no expone el visor de logs técnicos del servidor."""

    def test_dashboard_oculta_visor_logs_tecnicos(self, admin_client):
        response = admin_client.get(reverse('dashboard_admin'))
        assert response.status_code == 200
        contenido = response.content.decode('utf-8')
        assert 'logsTecnicosSection' not in contenido
        assert 'data-testid="visor-logs-tecnicos"' not in contenido


@pytest.mark.django_db
class TestProteccionPermisosAdmin:
    """Un admin no puede auto-suspenderse ni gestionar otros admins salvo que sea superuser."""

    def test_admin_no_puede_suspenderse_a_si_mismo(self, admin_client, admin_user):
        response = admin_client.post(reverse('admin_toggle_usuario', args=[admin_user.id]))
        assert response.status_code == 302
        admin_user.refresh_from_db()
        assert admin_user.is_active is True
        assert admin_user.estado == 'activo'

    def test_admin_comun_no_puede_suspender_otro_admin(self, client):
        admin_comun = User.objects.create_user(
            username='admin_comun_1', email='ac1@test.jobdevs',
            password='Password123!', rol='administrador', is_superuser=False,
        )
        otro_admin = User.objects.create_user(
            username='admin_comun_2', email='ac2@test.jobdevs',
            password='Password123!', rol='administrador', is_superuser=False,
        )
        client.force_login(admin_comun)
        response = client.post(reverse('admin_toggle_usuario', args=[otro_admin.id]))
        assert response.status_code == 302
        otro_admin.refresh_from_db()
        assert otro_admin.is_active is True

    def test_admin_si_puede_suspender_desarrollador(self, client):
        admin_comun = User.objects.create_user(
            username='admin_ok_1', email='aok1@test.jobdevs',
            password='Password123!', rol='administrador',
        )
        dev_target = User.objects.create_user(
            username='dev_target_1', email='dt1@test.jobdevs',
            password='Password123!', rol='desarrollador',
        )
        client.force_login(admin_comun)
        response = client.post(reverse('admin_toggle_usuario', args=[dev_target.id]))
        assert response.status_code == 302
        dev_target.refresh_from_db()
        assert dev_target.is_active is False

    def test_admin_comun_no_puede_eliminar_otro_admin(self, client):
        admin_comun = User.objects.create_user(
            username='admin_del_1', email='ad1@test.jobdevs',
            password='Password123!', rol='administrador', is_superuser=False,
        )
        otro_admin = User.objects.create_user(
            username='admin_del_2', email='ad2@test.jobdevs',
            password='Password123!', rol='administrador', is_superuser=False,
        )
        client.force_login(admin_comun)
        response = client.delete(reverse('api_eliminar_usuario', args=[otro_admin.id]))
        assert response.status_code == 403
        assert User.objects.filter(id=otro_admin.id).exists()

    def test_admin_comun_no_puede_editar_otro_admin(self, client):
        import json as _json
        admin_comun = User.objects.create_user(
            username='admin_upd_1', email='au1@test.jobdevs',
            password='Password123!', rol='administrador', is_superuser=False,
        )
        otro_admin = User.objects.create_user(
            username='admin_upd_2', email='au2@test.jobdevs',
            password='Password123!', rol='administrador', is_superuser=False,
        )
        client.force_login(admin_comun)
        response = client.put(
            reverse('api_actualizar_usuario', args=[otro_admin.id]),
            data=_json.dumps({'nombre': 'Hackeado'}),
            content_type='application/json',
        )
        assert response.status_code == 403
        otro_admin.refresh_from_db()
        assert otro_admin.nombre != 'Hackeado'

    def test_bulk_toggle_no_suspende_propio_ni_otros_admins(self, client):
        import json as _json
        admin_comun = User.objects.create_user(
            username='admin_blk_1', email='ab1@test.jobdevs',
            password='Password123!', rol='administrador', is_superuser=False,
        )
        otro_admin = User.objects.create_user(
            username='admin_blk_2', email='ab2@test.jobdevs',
            password='Password123!', rol='administrador', is_superuser=False,
        )
        client.force_login(admin_comun)
        response = client.post(
            reverse('api_bulk_toggle'),
            data=_json.dumps({'ids': [admin_comun.id, otro_admin.id], 'action': 'suspend'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        admin_comun.refresh_from_db()
        otro_admin.refresh_from_db()
        assert admin_comun.is_active is True
        assert otro_admin.is_active is True

    def test_crear_empresa_valida_nit_con_algoritmo_dian(self, admin_client):
        import json as _json
        res_bad = admin_client.post(
            reverse('api_crear_usuario'),
            data=_json.dumps({
                'nombre': 'Empresa NIT Malo',
                'username': 'emp_nit_malo',
                'email': 'nitmalo@test.jobdevs',
                'identificacion': '899.999.034-9',
                'password': 'Password123!',
                'rol': 'empresa',
            }),
            content_type='application/json',
        )
        assert res_bad.status_code == 400
        assert not User.objects.filter(username='emp_nit_malo').exists()

        res_ok = admin_client.post(
            reverse('api_crear_usuario'),
            data=_json.dumps({
                'nombre': 'Empresa NIT Bueno',
                'username': 'emp_nit_bueno',
                'email': 'nitbueno@test.jobdevs',
                'identificacion': '899.999.034-1',
                'password': 'Password123!',
                'rol': 'empresa',
            }),
            content_type='application/json',
        )
        assert res_ok.status_code == 201
        assert User.objects.filter(username='emp_nit_bueno').exists()

    def test_crear_usuario_valida_y_sanitiza_cc_y_ti(self, admin_client):
        import json as _json
        res_bad_cc = admin_client.post(
            reverse('api_crear_usuario'),
            data=_json.dumps({
                'nombre': 'Dev CC Mala',
                'username': 'dev_cc_mala',
                'email': 'devccmala@test.jobdevs',
                'identificacion': '123',
                'password': 'Password123!',
                'rol': 'desarrollador',
            }),
            content_type='application/json',
        )
        assert res_bad_cc.status_code == 400
        assert 'error' in res_bad_cc.json()

        res_ok_cc = admin_client.post(
            reverse('api_crear_usuario'),
            data=_json.dumps({
                'nombre': 'Dev CC Buena',
                'username': 'dev_cc_buena',
                'email': 'devccbuena@test.jobdevs',
                'identificacion': '1.020.304.050',
                'password': 'Password123!',
                'rol': 'desarrollador',
            }),
            content_type='application/json',
        )
        assert res_ok_cc.status_code == 201
        assert User.objects.get(username='dev_cc_buena').identificacion == '1020304050'

        res_ok_ti = admin_client.post(
            reverse('api_crear_usuario'),
            data=_json.dumps({
                'nombre': 'Dev TI Buena',
                'username': 'dev_ti_buena',
                'email': 'devtibuena@test.jobdevs',
                'tipo_documento': 'ti',
                'identificacion': '1000234567',
                'password': 'Password123!',
                'rol': 'desarrollador',
            }),
            content_type='application/json',
        )
        assert res_ok_ti.status_code == 201
        assert User.objects.get(username='dev_ti_buena').identificacion == '1000234567'


class TestApiAuditoria:
    """Tests for admin audit log API, filters, pagination, CSV export, and UI controls."""

    def test_solo_administradores_acceden_a_api_auditoria(self, auth_client, dev_client, client):
        url = reverse('api_auditoria')
        assert client.get(url).status_code == 403
        assert auth_client.get(url).status_code == 403
        assert dev_client.get(url).status_code == 403

    def test_api_auditoria_filtra_pagina_y_expone_campos_detalle(self, admin_client, admin_user):
        from logs.models import LogAuditoria

        LogAuditoria.objects.create(
            usuario=admin_user,
            accion='Aprobó empresa Acme',
            tabla_afectada='perfiles_empresa',
            registro_id=42,
            valor_anterior='pendiente',
            valor_nuevo='verificada',
        )
        LogAuditoria.objects.create(
            usuario=None,
            accion='Depuración automática de notificaciones',
            tabla_afectada='notificaciones',
            registro_id=None,
            valor_anterior='',
            valor_nuevo='15 eliminadas',
        )

        # Listado paginado
        res = admin_client.get(reverse('api_auditoria'), {'limit': 1, 'page': 1})
        assert res.status_code == 200
        data = res.json()
        assert data['total'] >= 2
        assert data['total_pages'] >= 2
        assert data['page'] == 1
        assert len(data['logs']) == 1
        assert 'perfiles_empresa' in data['tablas']

        # Filtro por tabla y texto
        res_filt = admin_client.get(reverse('api_auditoria'), {'tabla': 'perfiles_empresa', 'q': 'Acme'})
        assert res_filt.status_code == 200
        logs = res_filt.json()['logs']
        assert len(logs) == 1
        assert logs[0]['registro_id'] == 42
        assert logs[0]['valor_anterior'] == 'pendiente'
        assert logs[0]['valor_nuevo'] == 'verificada'
        assert logs[0]['usuario'] == admin_user.username

        # Usuario null aparece como Sistema y se puede filtrar por "Sistema"
        res_sys = admin_client.get(reverse('api_auditoria'), {'usuario': 'Sistema'})
        assert res_sys.status_code == 200
        sys_logs = res_sys.json()['logs']
        assert any(l['usuario'] == 'Sistema' and l['tabla_afectada'] == 'notificaciones' for l in sys_logs)

        # Paginación inválida -> 400
        assert admin_client.get(reverse('api_auditoria'), {'page': '0'}).status_code == 400
        assert admin_client.get(reverse('api_auditoria'), {'limit': 'abc'}).status_code == 400

    def test_api_auditoria_exporta_csv_y_neutraliza_formulas(self, admin_client, admin_user):
        from logs.models import LogAuditoria

        LogAuditoria.objects.create(
            usuario=admin_user,
            accion='=CMD("calc")',
            tabla_afectada='usuarios',
            registro_id=7,
            valor_anterior='activo',
            valor_nuevo='inactivo',
        )

        res = admin_client.get(reverse('api_auditoria'), {'export': 'csv', 'tabla': 'usuarios'})
        assert res.status_code == 200
        assert 'text/csv' in res['Content-Type']
        assert 'attachment; filename="auditoria.csv"' in res['Content-Disposition']
        body = res.content.decode('utf-8-sig')
        assert 'ID,Usuario,Acción,Tabla,Registro ID,Valor Anterior,Valor Nuevo,Fecha y Hora' in body
        assert "'=CMD(" in body

    def test_dashboard_admin_renderiza_controles_auditoria_y_fechas_chats(self, admin_client):
        res = admin_client.get(reverse('dashboard_admin'))
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'id="auditLogsForm"' in html
        assert 'id="auditLogDetailModal"' in html
        assert 'id="auditExportCsvBtn"' not in html
        assert 'id="auditChatsNoticeModal"' in html
        assert 'name="fecha_desde"' in html
        assert 'name="fecha_hasta"' in html

    def test_api_auditoria_filtra_por_rango_fechas_y_filtros_combinados(self, admin_client, admin_user, empresa_user):
        from logs.models import LogAuditoria

        hoy = timezone.now()
        hace_10_dias = hoy - timedelta(days=10)

        log_viejo = LogAuditoria.objects.create(
            usuario=admin_user,
            accion='Suspendió cuenta antigua',
            tabla_afectada='usuarios',
            registro_id=101,
            valor_anterior='activo',
            valor_nuevo='suspendido',
        )
        LogAuditoria.objects.filter(pk=log_viejo.pk).update(fecha_hora=hace_10_dias)

        log_reciente = LogAuditoria.objects.create(
            usuario=empresa_user,
            accion='Actualizó perfil comercial',
            tabla_afectada='perfiles_empresa',
            registro_id=202,
            valor_anterior='borrador',
            valor_nuevo='publicado',
        )

        # Rango de fechas: últimos 2 días solo trae log_reciente
        desde = (hoy - timedelta(days=2)).date().isoformat()
        hasta = hoy.date().isoformat()
        res_rango = admin_client.get(reverse('api_auditoria'), {
            'fecha_desde': desde,
            'fecha_hasta': hasta,
            'tabla': 'perfiles_empresa',
            'usuario': empresa_user.username,
            'q': 'publicado',
        })
        assert res_rango.status_code == 200
        ids = [item['id'] for item in res_rango.json()['logs']]
        assert ids == [log_reciente.id]

        # Rango antiguo solo trae log_viejo
        desde_viejo = (hace_10_dias - timedelta(days=1)).date().isoformat()
        hasta_viejo = (hace_10_dias + timedelta(days=1)).date().isoformat()
        res_viejo = admin_client.get(reverse('api_auditoria'), {
            'fecha_desde': desde_viejo,
            'fecha_hasta': hasta_viejo,
            'tabla': 'usuarios',
        })
        assert res_viejo.status_code == 200
        ids_viejo = [item['id'] for item in res_viejo.json()['logs']]
        assert ids_viejo == [log_viejo.id]

        # CSV respeta el mismo filtro de fechas
        res_csv = admin_client.get(reverse('api_auditoria'), {
            'export': 'csv',
            'fecha_desde': desde_viejo,
            'fecha_hasta': hasta_viejo,
            'tabla': 'usuarios',
        })
        assert res_csv.status_code == 200
        csv_text = res_csv.content.decode('utf-8-sig')
        assert 'Suspendió cuenta antigua' in csv_text
        assert 'Actualizó perfil comercial' not in csv_text


class TestAdminSidebar:
    """Tests for the Admin sidebar structure matching Developer sidebar."""

    def test_admin_sidebar_tiene_logo_boton_colapsar_y_sin_cerrar_sesion(self, admin_client):
        response = admin_client.get(reverse('dashboard_admin'))
        assert response.status_code == 200
        html = response.content.decode()

        sidebar_start = html.index('id="adminSidebar"')
        sidebar_end = html.index('</aside>', sidebar_start)
        sidebar_html = html[sidebar_start:sidebar_end]

        assert 'JobDevs_logo_vector_transparente.svg' in sidebar_html
        assert 'class="sidebar-brand-logo"' in sidebar_html
        assert '[ PANEL MAESTRO ]' in sidebar_html
        assert 'id="sidebarCollapseBtn"' in sidebar_html
        assert 'onclick="toggleSidebarCollapse()"' in sidebar_html
        assert 'Cerrar Sesión' not in sidebar_html
        assert 'sidebar-sep' not in sidebar_html

        # Cerrar Sesión sigue disponible en el menú desplegable del usuario
        dropdown_start = html.index('id="adminUserDropdownMenu"')
        dropdown_end = html.index('</header>', dropdown_start)
        assert 'Cerrar Sesión' in html[dropdown_start:dropdown_end]


class TestAdminChatAvatars:
    """Avatars/logos in Admin conversation list render <img> with onerror fallback."""

    def test_admin_conversaciones_renderiza_logo_empresa_y_foto_dev(
        self, admin_client, admin_user, empresa_user, desarrollador_user, tmp_path
    ):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from mensajes.models import Mensaje
        from usuarios.models import PerfilDesarrollador, PerfilEmpresa

        gif_bytes = (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00'
            b'!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01'
            b'\x00\x00\x02\x02D\x01\x00;'
        )
        sin_perfil_user = User.objects.create_user(
            username='sin_perfil_chat',
            email='sinperfil@test.com',
            password='Password123!',
            rol='empresa',
            estado='activo',
        )

        with override_settings(MEDIA_ROOT=tmp_path):
            perfil_emp, _ = PerfilEmpresa.objects.get_or_create(usuario=empresa_user)
            perfil_emp.logo = SimpleUploadedFile('logo_emp.gif', gif_bytes, content_type='image/gif')
            perfil_emp.save()

            perfil_dev, _ = PerfilDesarrollador.objects.get_or_create(usuario=desarrollador_user)
            perfil_dev.foto_perfil = SimpleUploadedFile('foto_dev.gif', gif_bytes, content_type='image/gif')
            perfil_dev.save()

            Mensaje.objects.create(
                remitente=empresa_user, receptor=admin_user, contenido='Hola admin emp'
            )
            Mensaje.objects.create(
                remitente=desarrollador_user, receptor=admin_user, contenido='Hola admin dev'
            )
            Mensaje.objects.create(
                remitente=sin_perfil_user, receptor=admin_user, contenido='Hola sin perfil'
            )

            response = admin_client.get(reverse('dashboard_admin'))
            assert response.status_code == 200
            html = response.content.decode()

            chat_start = html.index('id="chatSection"')
            chat_end = html.index('</section>', chat_start)
            chat_html = html[chat_start:chat_end]

            assert perfil_emp.logo.url in chat_html
            assert perfil_dev.foto_perfil.url in chat_html
            assert '<img ' in chat_html
            assert 'onerror=' in chat_html
            # Usuario sin perfil hace fallback a la inicial
            import re
            inicial = sin_perfil_user.username[:1].upper()
            assert re.search(rf'<span class="jd-chat-avatar">\s*{re.escape(inicial)}\s*</span>', chat_html)


class TestApiUsuariosYActualizarAdmin:
    """TDD tests for Admin points 1 & 2: date_joined in api_usuarios & identificacion in api_actualizar_usuario."""

    def test_api_usuarios_incluye_date_joined_paginado_y_sin_paginar(self, admin_client, empresa_user):
        """Point 1: api_usuarios incluye date_joined en respuestas paginadas y no paginadas."""
        resp_all = admin_client.get(reverse('api_usuarios'))
        assert resp_all.status_code == 200
        data_all = resp_all.json()
        assert len(data_all) >= 1
        for u in data_all:
            assert 'date_joined' in u
            assert u['date_joined']

        resp_pag = admin_client.get(reverse('api_usuarios') + '?limit=5&page=1')
        assert resp_pag.status_code == 200
        data_pag = resp_pag.json()
        assert len(data_pag['usuarios']) >= 1
        for u in data_pag['usuarios']:
            assert 'date_joined' in u
            assert u['date_joined']

    def test_api_usuarios_filtra_mas_de_25_usuarios_por_fechas_y_q(self, admin_client, db):
        """Point 1: api_usuarios filtra correctamente sobre >25 usuarios por fecha_desde, fecha_hasta y q."""
        ahora = timezone.now()
        usuarios = [
            User(
                username=f'bulk_filter_{i:02d}',
                email=f'bulk_filter_{i:02d}@test.jobdevs',
                nombre=f'Bulk Filter {i:02d}',
                rol='desarrollador',
                date_joined=ahora - timedelta(days=40 if i < 26 else 2),
            )
            for i in range(30)
        ]
        User.objects.bulk_create(usuarios)
        # Ensure bulk_create dates are persisted as intended
        for i in range(30):
            User.objects.filter(username=f'bulk_filter_{i:02d}').update(
                date_joined=ahora - timedelta(days=40 if i < 26 else 2)
            )

        desde = (ahora - timedelta(days=5)).date().isoformat()
        hasta = ahora.date().isoformat()
        resp = admin_client.get(
            reverse('api_usuarios'),
            {'fecha_desde': desde, 'fecha_hasta': hasta, 'q': 'bulk_filter_'},
        )
        assert resp.status_code == 200
        usernames = {u['username'] for u in resp.json()}
        assert usernames == {f'bulk_filter_{i:02d}' for i in range(26, 30)}

        # Also check older user beyond 25 when filtering by q and older fecha_hasta
        hasta_viejo = (ahora - timedelta(days=30)).date().isoformat()
        resp_old = admin_client.get(
            reverse('api_usuarios'),
            {'fecha_hasta': hasta_viejo, 'q': 'bulk_filter_00'},
        )
        assert resp_old.status_code == 200
        old_data = resp_old.json()
        assert len(old_data) == 1
        assert old_data[0]['username'] == 'bulk_filter_00'
        assert 'date_joined' in old_data[0]

    def test_api_actualizar_usuario_actualiza_cc_sanitizada_y_audita(self, admin_client, desarrollador_user):
        """Point 2: api_actualizar_usuario valida y sanitiza CC, actualiza y registra en LogAuditoria."""
        import json as _json

        from logs.models import LogAuditoria

        resp = admin_client.put(
            reverse('api_actualizar_usuario', args=[desarrollador_user.id]),
            data=_json.dumps({'identificacion': '1.020.304.050'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['status'] == 'updated'

        desarrollador_user.refresh_from_db()
        assert desarrollador_user.identificacion == '1020304050'

        log = LogAuditoria.objects.filter(
            tabla_afectada='usuarios', registro_id=desarrollador_user.id
        ).order_by('-id').first()
        assert log is not None
        assert 'identificacion' in log.accion
        assert 'identificacion=1020304050' in log.valor_nuevo

    def test_api_actualizar_usuario_rechaza_cc_invalida(self, admin_client, desarrollador_user):
        """Point 2: api_actualizar_usuario retorna 400 con CC inválida sin modificar BD."""
        import json as _json

        ident_original = desarrollador_user.identificacion
        resp = admin_client.put(
            reverse('api_actualizar_usuario', args=[desarrollador_user.id]),
            data=_json.dumps({'identificacion': '123'}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert 'error' in resp.json()

        desarrollador_user.refresh_from_db()
        assert desarrollador_user.identificacion == ident_original

    def test_api_actualizar_usuario_rechaza_identificacion_duplicada(
        self, admin_client, desarrollador_user, empresa_user
    ):
        """Point 2: api_actualizar_usuario retorna 400 si otro usuario ya tiene esa identificación."""
        import json as _json

        empresa_user.identificacion = '1098765432'
        empresa_user.save(update_fields=['identificacion'])
        ident_original = desarrollador_user.identificacion

        resp = admin_client.put(
            reverse('api_actualizar_usuario', args=[desarrollador_user.id]),
            data=_json.dumps({'identificacion': '1.098.765.432'}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert resp.json()['error'] == 'Ya existe otro usuario con esa identificación.'

        desarrollador_user.refresh_from_db()
        assert desarrollador_user.identificacion == ident_original

    def test_api_actualizar_usuario_preserva_comportamiento_sin_identificacion(
        self, admin_client, desarrollador_user
    ):
        """Point 2 (PRESERVE): omitir identificacion mantiene el comportamiento existente."""
        import json as _json

        desarrollador_user.identificacion = '1011223344'
        desarrollador_user.save(update_fields=['identificacion'])

        resp = admin_client.put(
            reverse('api_actualizar_usuario', args=[desarrollador_user.id]),
            data=_json.dumps({'nombre': 'Nuevo Nombre Dev'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        desarrollador_user.refresh_from_db()
        assert desarrollador_user.nombre == 'Nuevo Nombre Dev'
        assert desarrollador_user.identificacion == '1011223344'


class TestAdminEsModules:
    """Verifica la arquitectura ES Modules del Panel Administrador y sus bindings globales."""

    def test_template_carga_administrador_js_como_modulo(self, admin_client):
        res = admin_client.get(reverse('dashboard_admin'))
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert '<script type="module" src="' in html
        assert 'administrador/script/administrador.js?v=20261126_mod1' in html
        assert 'id="auditLogsForm" data-api-url=' in html
        assert 'id="auditChatsForm" data-api-url=' in html
        assert 'data-url-crear=' in html

    def test_todos_los_handlers_inline_tienen_binding_window(self):
        import re
        from pathlib import Path

        from django.conf import settings

        base = Path(settings.BASE_DIR)
        js_files = [
            base / 'static/administrador/script/administrador.js',
            base / 'static/administrador/script/modules/ui_core.js',
            base / 'static/administrador/script/modules/usuarios_verificaciones.js',
            base / 'static/administrador/script/modules/auditoria_reportes.js',
        ]
        window_bindings = set()
        for js_file in js_files:
            assert js_file.exists(), f'Falta módulo ES: {js_file}'
            text = js_file.read_text(encoding='utf-8')
            for imp in re.findall(r"from\s+['\"](\.[^'\"]+)['\"]", text):
                assert (js_file.parent / imp).resolve().exists(), f'Import roto {imp} en {js_file}'
            for match in re.findall(r'window\.([A-Za-z_$][A-Za-z0-9_$]*)\s*=(?!=)', text):
                window_bindings.add(match)

        admin_tpl_dir = base / 'templates/administrador'
        partials = sorted((admin_tpl_dir / 'partials').glob('*.html'))
        assert partials, 'Se esperaban parciales en templates/administrador/partials/'
        html = '\n'.join(
            p.read_text(encoding='utf-8') for p in [admin_tpl_dir / 'Administrador.html', *partials]
        )
        handlers = re.findall(r'on(?:click|change|submit|input)="([^"]+)"', html)
        called_fns = set()
        for handler in handlers:
            for fn in re.findall(r'\b([A-Za-z_$][A-Za-z0-9_$]*)\s*\(', handler):
                if fn not in ('if', 'preventDefault'):
                    called_fns.add(fn)

        missing = sorted(called_fns - window_bindings)
        assert not missing, f'Handlers inline sin binding window.*: {missing}'


class TestAuditoriaHtmxPartials:
    """S2: Tests HTMX partials para Auditoría de Logs y Auditoría de Chats."""

    def test_api_auditoria_htmx_retorna_partial_html_escapado_y_pager_oob(self, admin_client, admin_user):
        from logs.models import LogAuditoria

        LogAuditoria.objects.create(
            usuario=admin_user,
            accion='Cambio seguro',
            tabla_afectada='usuarios',
            registro_id=10,
            valor_anterior='a',
            valor_nuevo='b',
        )
        LogAuditoria.objects.create(
            usuario=admin_user,
            accion='<script>alert(1)</script>',
            tabla_afectada='perfiles_empresa',
            registro_id=11,
            valor_anterior='old',
            valor_nuevo='<b>xss</b>',
        )

        res = admin_client.get(
            reverse('api_auditoria'),
            {'limit': 1, 'page': 1},
            HTTP_HX_REQUEST='true',
        )
        assert res.status_code == 200
        assert 'text/html' in res['Content-Type']
        html = res.content.decode('utf-8')
        assert '<tr' in html
        assert 'data-log-id=' in html
        assert 'data-log-accion=' in html
        assert 'id="auditLogsPager"' in html
        assert 'hx-swap-oob="innerHTML"' in html
        assert 'id="auditTablasList"' in html
        assert 'Siguiente' in html
        assert '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html

    def test_api_auditoria_htmx_con_format_json_preserva_json(self, admin_client):
        res = admin_client.get(
            reverse('api_auditoria'),
            {'format': 'json'},
            HTTP_HX_REQUEST='true',
        )
        assert res.status_code == 200
        assert res['Content-Type'].startswith('application/json')
        assert 'logs' in res.json()

    def test_admin_auditar_mensajes_htmx_retorna_partial_html_escapado_y_pager_oob(
        self, admin_client, empresa_user, desarrollador_user
    ):
        from mensajes.models import Mensaje

        for i in range(25):
            Mensaje.objects.create(
                remitente=empresa_user,
                receptor=desarrollador_user,
                contenido=f'Mensaje de auditoria {i}',
            )
        Mensaje.objects.create(
            remitente=empresa_user,
            receptor=desarrollador_user,
            titulo='XSS',
            contenido='<img src=x onerror=alert(1)>',
        )

        res = admin_client.get(
            reverse('admin_auditar_mensajes'),
            HTTP_HX_REQUEST='true',
        )
        assert res.status_code == 200
        assert 'text/html' in res['Content-Type']
        html = res.content.decode('utf-8')
        assert '<tr' in html
        assert 'data-chat-contenido=' in html
        assert 'id="auditChatsPager"' in html
        assert 'hx-swap-oob="innerHTML"' in html
        assert 'Siguiente' in html
        assert '<img src=x onerror=alert(1)>' not in html
        assert '&lt;img src=x onerror=alert(1)&gt;' in html

    def test_admin_auditar_mensajes_htmx_con_format_json_preserva_json(self, admin_client):
        res = admin_client.get(
            reverse('admin_auditar_mensajes'),
            {'format': 'json'},
            HTTP_HX_REQUEST='true',
        )
        assert res.status_code == 200
        assert res['Content-Type'].startswith('application/json')
        assert 'mensajes' in res.json()

    def test_dashboard_admin_wiring_htmx_en_formularios_auditoria(self, admin_client):
        res = admin_client.get(reverse('dashboard_admin'))
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'hx-target="#auditLogsBody"' in html
        assert 'hx-target="#auditChatsBody"' in html
        assert 'hx-sync="this:replace"' in html


class TestUsuariosHtmxPartial:
    """S3: Tests HTMX partial para el Directorio de Usuarios en Panel Administrador."""

    def test_api_usuarios_htmx_retorna_partial_html_fechas_oob_y_filtros(
        self, admin_client, admin_user, desarrollador_user, empresa_user
    ):
        from django.template.defaultfilters import date as django_date

        suspendido = User.objects.create_user(
            username='dev_suspendido_htmx',
            email='susp_htmx@test.jobdevs',
            nombre='Dev Suspendido',
            rol='desarrollador',
            estado='suspendido',
            is_active=False,
            password='TestPass123!',
        )

        res = admin_client.get(reverse('api_usuarios'), HTTP_HX_REQUEST='true')
        assert res.status_code == 200
        assert 'text/html' in res['Content-Type']
        html = res.content.decode('utf-8')
        assert '<tr ' in html
        assert f'@{desarrollador_user.username}' in html
        assert f'@{empresa_user.username}' in html
        assert 'hx-swap-oob="innerHTML"' in html
        assert 'id="usersResultCount"' in html
        assert 'Mostrando ' in html
        assert 'Tu cuenta' in html
        fecha_esperada = django_date(timezone.localtime(desarrollador_user.date_joined), 'd M Y')
        assert fecha_esperada in html
        assert f'data-fecha-registro="{timezone.localtime(desarrollador_user.date_joined).strftime("%Y-%m-%d")}"' in html

        # Filtro por rol
        res_rol = admin_client.get(
            reverse('api_usuarios'), {'rol': 'empresa'}, HTTP_HX_REQUEST='true'
        )
        assert res_rol.status_code == 200
        html_rol = res_rol.content.decode('utf-8')
        assert f'@{empresa_user.username}' in html_rol
        assert f'@{desarrollador_user.username}' not in html_rol
        assert 'Mostrando 1 usuarios' in html_rol

        # Filtro por búsqueda q
        res_q = admin_client.get(
            reverse('api_usuarios'), {'q': 'dev_suspendido_htmx'}, HTTP_HX_REQUEST='true'
        )
        assert res_q.status_code == 200
        html_q = res_q.content.decode('utf-8')
        assert '@dev_suspendido_htmx' in html_q
        assert 'Suspendido' in html_q
        assert 'Mostrando 1 usuarios' in html_q

        # Filtro por estado=inactive / estado=active
        res_inact = admin_client.get(
            reverse('api_usuarios'), {'estado': 'inactive'}, HTTP_HX_REQUEST='true'
        )
        assert res_inact.status_code == 200
        html_inact = res_inact.content.decode('utf-8')
        assert f'@{suspendido.username}' in html_inact
        assert f'@{empresa_user.username}' not in html_inact

        res_act = admin_client.get(
            reverse('api_usuarios'), {'estado': 'active'}, HTTP_HX_REQUEST='true'
        )
        assert res_act.status_code == 200
        html_act = res_act.content.decode('utf-8')
        assert f'@{empresa_user.username}' in html_act
        assert f'@{suspendido.username}' not in html_act

        # Estado vacío
        res_empty = admin_client.get(
            reverse('api_usuarios'), {'q': 'usuario_inexistente_xyz_999'}, HTTP_HX_REQUEST='true'
        )
        assert res_empty.status_code == 200
        html_empty = res_empty.content.decode('utf-8')
        assert 'No se encontraron usuarios con esos filtros.' in html_empty
        assert 'Mostrando 0 usuarios' in html_empty

    def test_api_usuarios_htmx_escapa_xss(self, admin_client, db):
        User.objects.create_user(
            username='xss_user_htmx',
            email='xss_htmx@test.jobdevs',
            nombre='<script>alert(1)</script>',
            rol='desarrollador',
            password='TestPass123!',
        )

        res = admin_client.get(
            reverse('api_usuarios'), {'q': 'xss_user_htmx'}, HTTP_HX_REQUEST='true'
        )
        assert res.status_code == 200
        assert 'text/html' in res['Content-Type']
        html = res.content.decode('utf-8')
        assert '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html

    def test_api_usuarios_sin_htmx_y_con_format_json_preserva_json(self, admin_client, empresa_user):
        res_json = admin_client.get(reverse('api_usuarios'))
        assert res_json.status_code == 200
        assert res_json['Content-Type'].startswith('application/json')
        assert isinstance(res_json.json(), list)

        res_fmt = admin_client.get(
            reverse('api_usuarios'), {'format': 'json'}, HTTP_HX_REQUEST='true'
        )
        assert res_fmt.status_code == 200
        assert res_fmt['Content-Type'].startswith('application/json')
        assert isinstance(res_fmt.json(), list)

    def test_dashboard_admin_wiring_htmx_en_directorio_usuarios(self, admin_client):
        res = admin_client.get(reverse('dashboard_admin'))
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'id="usersTableBody"' in html
        assert 'hx-target="#usersTableBody"' in html
        assert 'hx-swap="innerHTML"' in html
        assert 'hx-sync=' in html
        assert 'debouncedFilterUsers()' in html


class TestAdminHtmxPhase4S1:
    """S1: Admin Verificaciones, Fichas SENA, Proyectos & Chat Config HTMX."""

    def test_admin_resolver_verificacion_empresa_htmx(self, admin_client, empresa_user):
        import json as _json

        from usuarios.models import PerfilEmpresa

        perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=empresa_user)
        perfil.estado_verificacion = 'en_revision'
        perfil.razon_social = 'Empresa HTMX SAS'
        perfil.tipo_documento = 'NIT'
        perfil.numero_documento = '900123456'
        perfil.save()

        # Error case (invalid accion) returns partial + error toast
        res_err = admin_client.post(
            reverse('admin_resolver_verificacion_empresa', args=[perfil.id]),
            {'accion': 'invalida'},
            HTTP_HX_REQUEST='true',
        )
        assert res_err.status_code == 200
        assert 'id="verificacionEmpresasSection"' in res_err.content.decode('utf-8')
        trigger_err = _json.loads(res_err['HX-Trigger'])
        assert trigger_err['jobdevs:toast']['tipo'] == 'error'

        # Success case (aprobar) returns updated partial + success toast
        res = admin_client.post(
            reverse('admin_resolver_verificacion_empresa', args=[perfil.id]),
            {'accion': 'aprobar'},
            HTTP_HX_REQUEST='true',
        )
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'id="verificacionEmpresasSection"' in html
        assert 'Empresa HTMX SAS' not in html
        trigger = _json.loads(res['HX-Trigger'])
        assert trigger['jobdevs:toast']['tipo'] == 'success'
        assert 'verificada correctamente' in trigger['jobdevs:toast']['mensaje']
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'verificada'

    def test_admin_resolver_verificacion_desarrollador_htmx(self, admin_client, desarrollador_user):
        import json as _json

        perfil = desarrollador_user.perfil_desarrollador
        perfil.estado_verificacion = 'en_revision'
        perfil.ficha = '2999888'
        perfil.programa_formacion = 'ADSO'
        perfil.save()

        res = admin_client.post(
            reverse('admin_resolver_verificacion_desarrollador', args=[perfil.id]),
            {'accion': 'aprobar'},
            HTTP_HX_REQUEST='true',
        )
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'id="verificacionDevsSection"' in html
        assert '2999888' not in html
        trigger = _json.loads(res['HX-Trigger'])
        assert trigger['jobdevs:toast']['tipo'] == 'success'
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'verificado'

    def test_admin_crear_y_toggle_ficha_sena_htmx(self, admin_client):
        import json as _json

        from usuarios.models import FichaSena

        # Crear ficha via HTMX
        res_create = admin_client.post(
            reverse('admin_crear_ficha_sena'),
            {
                'numero_ficha': '2888777',
                'programa_formacion': 'ADSO HTMX',
                'regional': 'Distrito Capital',
            },
            HTTP_HX_REQUEST='true',
        )
        assert res_create.status_code == 200
        html_create = res_create.content.decode('utf-8')
        assert 'id="fichasSenaSection"' in html_create
        assert '2888777' in html_create
        assert 'ADSO HTMX' in html_create
        trigger_create = _json.loads(res_create['HX-Trigger'])
        assert trigger_create['jobdevs:toast']['tipo'] == 'success'
        assert '2888777' in trigger_create['jobdevs:toast']['mensaje']

        ficha = FichaSena.objects.get(numero_ficha='2888777')
        assert ficha.activa is True

        # Duplicada -> error toast + 200 partial
        res_dup = admin_client.post(
            reverse('admin_crear_ficha_sena'),
            {'numero_ficha': '2888777', 'programa_formacion': 'ADSO HTMX'},
            HTTP_HX_REQUEST='true',
        )
        assert res_dup.status_code == 200
        assert _json.loads(res_dup['HX-Trigger'])['jobdevs:toast']['tipo'] == 'error'

        # Toggle ficha via HTMX
        res_toggle = admin_client.post(
            reverse('admin_toggle_ficha_sena', args=[ficha.id]),
            HTTP_HX_REQUEST='true',
        )
        assert res_toggle.status_code == 200
        html_toggle = res_toggle.content.decode('utf-8')
        assert 'id="fichasSenaSection"' in html_toggle
        assert 'Inactiva' in html_toggle
        trigger_toggle = _json.loads(res_toggle['HX-Trigger'])
        assert trigger_toggle['jobdevs:toast']['tipo'] == 'success'
        ficha.refresh_from_db()
        assert ficha.activa is False

    def test_admin_crear_y_revocar_excepcion_ficha_sena_htmx(
        self, admin_client, desarrollador_user
    ):
        import json as _json

        from usuarios.models import ExcepcionFichaSena

        perfil = desarrollador_user.perfil_desarrollador
        res_create = admin_client.post(
            reverse('admin_crear_excepcion_ficha_sena'),
            {
                'desarrollador_id': perfil.id,
                'numero_ficha': '3111222',
                'justificacion': 'Avalada por coordinación académica HTMX.',
                'dias_vigencia': '15',
            },
            HTTP_HX_REQUEST='true',
        )
        assert res_create.status_code == 200
        html_create = res_create.content.decode('utf-8')
        assert 'id="fichasSenaSection"' in html_create
        assert '3111222' in html_create
        trigger_create = _json.loads(res_create['HX-Trigger'])
        assert trigger_create['jobdevs:toast']['tipo'] == 'success'

        excepcion = ExcepcionFichaSena.objects.get(numero_ficha='3111222')
        assert excepcion.activa is True

        res_rev = admin_client.post(
            reverse('admin_revocar_excepcion_ficha_sena', args=[excepcion.id]),
            HTTP_HX_REQUEST='true',
        )
        assert res_rev.status_code == 200
        html_rev = res_rev.content.decode('utf-8')
        assert 'id="fichasSenaSection"' in html_rev
        assert 'Revocada' in html_rev
        trigger_rev = _json.loads(res_rev['HX-Trigger'])
        assert trigger_rev['jobdevs:toast']['tipo'] == 'success'
        excepcion.refresh_from_db()
        assert excepcion.activa is False

    def test_admin_actualizar_configuracion_negociacion_htmx(self, admin_client):
        import json as _json

        res = admin_client.post(
            reverse('admin_actualizar_configuracion_negociacion'),
            {'plazo_dias': '12'},
            HTTP_HX_REQUEST='true',
        )
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'id="configSection"' in html
        assert 'value="12"' in html
        trigger = _json.loads(res['HX-Trigger'])
        assert trigger['jobdevs:toast']['tipo'] == 'success'

        # Invalid value returns error toast
        res_err = admin_client.post(
            reverse('admin_actualizar_configuracion_negociacion'),
            {'plazo_dias': '99'},
            HTTP_HX_REQUEST='true',
        )
        assert res_err.status_code == 200
        assert _json.loads(res_err['HX-Trigger'])['jobdevs:toast']['tipo'] == 'error'

    def test_admin_depurar_notificaciones_htmx(self, admin_client, desarrollador_user):
        import json as _json

        from notificaciones.models import Notificacion

        vieja = Notificacion.objects.create(
            usuario=desarrollador_user, tipo='alerta', mensaje='Vieja HTMX', leida=True
        )
        Notificacion.objects.filter(id=vieja.id).update(
            fecha=timezone.now() - timedelta(days=120)
        )

        res = admin_client.post(
            reverse('admin_depurar_notificaciones'),
            {'dias': '90'},
            HTTP_HX_REQUEST='true',
        )
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'id="configSection"' in html
        trigger = _json.loads(res['HX-Trigger'])
        assert trigger['jobdevs:toast']['tipo'] == 'success'
        assert '1 notificaciones antiguas' in trigger['jobdevs:toast']['mensaje']
        assert not Notificacion.objects.filter(id=vieja.id).exists()

    def test_admin_regularizar_cierre_proyecto_htmx(self, admin_client, empresa_user):
        import json as _json

        from proyectos.models import RegularizacionCierreProyecto

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto Cierre HTMX',
            descripcion='Desc',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Proyecto.objects.filter(pk=proyecto.pk).update(
            fecha_publicacion=timezone.now() - timedelta(days=10)
        )
        fecha_cierre = (timezone.now() - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')

        # Error case (motivo too short) returns partial + error toast
        res_err = admin_client.post(
            reverse('admin_regularizar_cierre_proyecto', args=[proyecto.id]),
            {
                'fecha_cierre': fecha_cierre,
                'motivo': 'corto',
            },
            HTTP_HX_REQUEST='true',
        )
        assert res_err.status_code == 200
        assert 'id="projectsSection"' in res_err.content.decode('utf-8')
        assert _json.loads(res_err['HX-Trigger'])['jobdevs:toast']['tipo'] == 'error'

        res = admin_client.post(
            reverse('admin_regularizar_cierre_proyecto', args=[proyecto.id]),
            {
                'fecha_cierre': fecha_cierre,
                'motivo': 'Evidencia documental verificada en acta de entrega firmada.',
                'referencia_evidencia': 'ACTA-2026-01',
            },
            HTTP_HX_REQUEST='true',
        )
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'id="projectsSection"' in html
        trigger = _json.loads(res['HX-Trigger'])
        assert trigger['jobdevs:toast']['tipo'] == 'success'
        assert RegularizacionCierreProyecto.objects.filter(proyecto=proyecto).exists()

    def test_admin_htmx_wiring_en_partials(self, admin_client):
        res = admin_client.get(reverse('dashboard_admin'))
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert f'hx-post="{reverse("admin_crear_ficha_sena")}"' in html
        assert f'hx-post="{reverse("admin_crear_excepcion_ficha_sena")}"' in html
        assert f'hx-post="{reverse("admin_actualizar_configuracion_negociacion")}"' in html
        assert f'hx-post="{reverse("admin_depurar_notificaciones")}"' in html
        assert 'hx-target="#fichasSenaSection"' in html
        assert 'hx-target="#configSection"' in html
        assert 'hx-swap="outerHTML"' in html
        assert 'hx-disabled-elt="find button[type=\'submit\']"' in html







