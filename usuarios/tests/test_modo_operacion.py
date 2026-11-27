from datetime import timedelta

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from logs.models import LogAuditoria
from mensajes.models import Mensaje
from postulaciones.models import Postulacion
from proyectos.models import Proyecto
from usuarios.models import (
    PerfilDesarrollador,
    PerfilEmpresa,
    es_modo_institucional,
)
from usuarios.services_sena import depurar_cuentas_sin_verificar
from usuarios.tasks import depurar_cuentas_sin_verificar_task

User = get_user_model()


def _crear_dev(username, estado_verificacion='sin_verificar', dias_antiguedad=0):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@test.jobdevs',
        nombre=f'Dev {username}',
        rol='desarrollador',
        estado='activo',
        password='TestPass123!',
    )
    if dias_antiguedad:
        User.objects.filter(pk=user.pk).update(
            date_joined=timezone.now() - timedelta(days=dias_antiguedad)
        )
        user.refresh_from_db()
    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=user)
    perfil.estado_verificacion = estado_verificacion
    perfil.save()
    return user, perfil


def _crear_empresa(username, estado_verificacion='sin_verificar', dias_antiguedad=0):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@test.jobdevs',
        nombre=f'Empresa {username}',
        rol='empresa',
        estado='activo',
        password='TestPass123!',
    )
    if dias_antiguedad:
        User.objects.filter(pk=user.pk).update(
            date_joined=timezone.now() - timedelta(days=dias_antiguedad)
        )
        user.refresh_from_db()
    perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=user)
    perfil.estado_verificacion = estado_verificacion
    perfil.save()
    return user, perfil


class TestConfiguracionModoOperacion:
    def test_allow_public_registration_controla_modo_institucional(self, settings):
        settings.ALLOW_PUBLIC_REGISTRATION = True
        assert es_modo_institucional() is False

        settings.ALLOW_PUBLIC_REGISTRATION = False
        assert es_modo_institucional() is True

    def test_dias_limite_verificacion_piloto_por_defecto_es_3(self):
        assert django_settings.DIAS_LIMITE_VERIFICACION_PILOTO == 3


class TestComportamientoVerificacionPorModo:
    def test_modo_institucional_permite_postulacion_dev_sin_verificar_y_empresa_verificada(
        self, settings, empresa_user
    ):
        settings.ALLOW_PUBLIC_REGISTRATION = False

        dev_user, dev_perfil = _crear_dev('dev_inst_unverified', estado_verificacion='sin_verificar')
        _, emp_perfil = _crear_empresa('emp_inst_unverified', estado_verificacion='sin_verificar')

        assert dev_perfil.es_verificado_sena is True
        assert emp_perfil.es_verificada is True

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto Institucional',
            descripcion='Proyecto de prueba para modo institucional',
            tipo_solucion='sitio_web',
            estado='publicado',
        )

        dev_c = Client()
        assert dev_c.login(username=dev_user.username, password='TestPass123!')
        resp = dev_c.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'Me interesa colaborar en este proyecto'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert resp.status_code == 200
        assert Postulacion.objects.filter(proyecto=proyecto, desarrollador=dev_user).exists()

    def test_modo_piloto_bloquea_postulacion_dev_sin_verificar_y_empresa_no_verificada(
        self, settings, empresa_user
    ):
        settings.ALLOW_PUBLIC_REGISTRATION = True

        dev_user, dev_perfil = _crear_dev('dev_piloto_unverified', estado_verificacion='sin_verificar')
        _, emp_perfil = _crear_empresa('emp_piloto_unverified', estado_verificacion='sin_verificar')

        assert dev_perfil.es_verificado_sena is False
        assert emp_perfil.es_verificada is False

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto Piloto',
            descripcion='Proyecto de prueba para modo piloto',
            tipo_solucion='sitio_web',
            estado='publicado',
        )

        dev_c = Client()
        assert dev_c.login(username=dev_user.username, password='TestPass123!')

        resp_ajax = dev_c.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'mensaje': 'Intento sin verificar'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert resp_ajax.status_code == 403

        resp_html = dev_c.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'mensaje': 'Intento sin verificar HTML'},
        )
        assert resp_html.status_code == 302
        assert reverse('solicitar_verificacion_desarrollador') in resp_html['Location']
        assert not Postulacion.objects.filter(proyecto=proyecto, desarrollador=dev_user).exists()


class TestDepuracionCuentasSinVerificar:
    def test_piloto_depura_eliminando_sin_actividad_y_desactivando_con_actividad(
        self, settings, admin_user
    ):
        settings.ALLOW_PUBLIC_REGISTRATION = True
        settings.DIAS_LIMITE_VERIFICACION_PILOTO = 3

        # Deben eliminarse (>3 días, sin_verificar, sin actividad)
        dev_viejo, _ = _crear_dev('dev_viejo_sin_act', 'sin_verificar', dias_antiguedad=5)
        emp_vieja, _ = _crear_empresa('emp_vieja_sin_act', 'sin_verificar', dias_antiguedad=4)
        dev_viejo_id = dev_viejo.id
        emp_vieja_id = emp_vieja.id

        # Deben conservarse (<3 días)
        dev_reciente, _ = _crear_dev('dev_reciente', 'sin_verificar', dias_antiguedad=1)
        emp_reciente, _ = _crear_empresa('emp_reciente', 'sin_verificar', dias_antiguedad=2)

        # Deben conservarse (en_revision y verificado/verificada aunque >3 días)
        dev_en_rev, _ = _crear_dev('dev_en_rev', 'en_revision', dias_antiguedad=10)
        dev_verif, _ = _crear_dev('dev_verif', 'verificado', dias_antiguedad=10)
        emp_en_rev, _ = _crear_empresa('emp_en_rev', 'en_revision', dias_antiguedad=10)
        emp_verif, _ = _crear_empresa('emp_verif', 'verificada', dias_antiguedad=10)

        # Debe desactivarse, NO eliminarse (>3 días, sin_verificar, con mensaje)
        dev_con_msg, _ = _crear_dev('dev_con_msg', 'sin_verificar', dias_antiguedad=6)
        Mensaje.objects.create(
            remitente=dev_con_msg,
            receptor=admin_user,
            contenido='Hola soporte, tengo una duda',
        )

        # Debe desactivarse, NO eliminarse (>3 días, sin_verificar, con proyecto)
        emp_con_proy, _ = _crear_empresa('emp_con_proy', 'sin_verificar', dias_antiguedad=6)
        Proyecto.objects.create(
            empresa=emp_con_proy,
            titulo='Proyecto existente',
            descripcion='Desc',
            tipo_solucion='sitio_web',
            estado='publicado',
        )

        resultado = depurar_cuentas_sin_verificar()

        assert resultado == {'ejecutado': True, 'eliminados': 2, 'desactivados': 2}

        # Eliminados
        assert not User.objects.filter(pk=dev_viejo_id).exists()
        assert not User.objects.filter(pk=emp_vieja_id).exists()

        # Conservados activos
        for u in (dev_reciente, emp_reciente, dev_en_rev, dev_verif, emp_en_rev, emp_verif):
            u.refresh_from_db()
            assert u.is_active is True
            assert u.estado == 'activo'

        # Desactivados pero existentes
        dev_con_msg.refresh_from_db()
        assert dev_con_msg.is_active is False
        assert dev_con_msg.estado == 'inactivo'

        emp_con_proy.refresh_from_db()
        assert emp_con_proy.is_active is False
        assert emp_con_proy.estado == 'inactivo'

        # Auditoría registrada para eliminaciones y desactivaciones
        for uid in (dev_viejo_id, emp_vieja_id, dev_con_msg.id, emp_con_proy.id):
            assert LogAuditoria.objects.filter(
                usuario=None,
                tabla_afectada='usuarios',
                registro_id=uid,
            ).exists()

    def test_institucional_no_depura_ni_modifica_usuarios(self, settings):
        settings.ALLOW_PUBLIC_REGISTRATION = False
        settings.DIAS_LIMITE_VERIFICACION_PILOTO = 3

        dev_viejo, _ = _crear_dev('dev_inst_viejo', 'sin_verificar', dias_antiguedad=10)
        emp_vieja, _ = _crear_empresa('emp_inst_vieja', 'sin_verificar', dias_antiguedad=10)

        resultado = depurar_cuentas_sin_verificar()

        assert resultado == {
            'ejecutado': False,
            'motivo': 'modo_institucional',
            'eliminados': 0,
            'desactivados': 0,
        }
        assert User.objects.filter(pk=dev_viejo.id, is_active=True).exists()
        assert User.objects.filter(pk=emp_vieja.id, is_active=True).exists()

    def test_celery_task_y_management_command_y_schedule(self, settings):
        settings.ALLOW_PUBLIC_REGISTRATION = True
        settings.DIAS_LIMITE_VERIFICACION_PILOTO = 3

        dev_viejo, _ = _crear_dev('dev_cmd_viejo', 'sin_verificar', dias_antiguedad=5)
        res_task = depurar_cuentas_sin_verificar_task()
        assert res_task['ejecutado'] is True
        assert res_task['eliminados'] == 1
        assert not User.objects.filter(pk=dev_viejo.id).exists()

        dev_cmd, _ = _crear_dev('dev_cmd_viejo_2', 'sin_verificar', dias_antiguedad=5)
        call_command('depurar_cuentas_sin_verificar')
        assert not User.objects.filter(pk=dev_cmd.id).exists()

        tareas_programadas = [
            entry['task'] for entry in django_settings.CELERY_BEAT_SCHEDULE.values()
        ]
        assert 'usuarios.depurar_cuentas_sin_verificar' in tareas_programadas
