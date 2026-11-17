from datetime import timedelta

import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model

from notificaciones.models import Notificacion
from proyectos.models import Proyecto


@pytest.mark.django_db
class TestAvisosCumplimiento:
    def test_programacion_diaria_en_huso_local(self):
        from django.conf import settings

        entrada = settings.CELERY_BEAT_SCHEDULE['avisos-cumplimiento-diario']
        assert entrada['task'] == 'notificaciones.enviar_avisos_cumplimiento'
        assert str(entrada['schedule']) == '<crontab: 0 0 * * * (m/h/dM/MY/d)>'

    def test_anticipado_48_horas_destinado_a_empresa_y_administradores(
        self, empresa_user, admin_user, desarrollador_user
    ):
        from notificaciones.tasks import enviar_avisos_cumplimiento_task

        fecha = timezone.localdate() + timedelta(days=1)
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Entrega próxima', descripcion='D',
            tipo_solucion='sitio_web', estado='en_desarrollo',
            fecha_cumplimiento=fecha,
        )
        total = enviar_avisos_cumplimiento_task()
        avisos = Notificacion.objects.filter(proyecto=proyecto, tipo='alerta')
        admin_ids = set(get_user_model().objects.filter(
            rol='administrador', estado='activo', is_active=True,
        ).values_list('id', flat=True))
        assert total == len(admin_ids | {empresa_user.id})
        assert set(avisos.values_list('usuario_id', flat=True)) == admin_ids | {empresa_user.id}
        assert all('48 horas' in aviso.mensaje for aviso in avisos)
        assert not avisos.filter(usuario=desarrollador_user).exists()

    def test_no_avisa_antes_de_las_48_horas(self, empresa_user, admin_user):
        from notificaciones.tasks import enviar_avisos_cumplimiento_task

        Proyecto.objects.create(
            empresa=empresa_user, titulo='Entrega todavía lejana', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
            fecha_cumplimiento=timezone.localdate() + timedelta(days=2),
        )
        assert enviar_avisos_cumplimiento_task() == 0

    def test_aviso_vencido_no_se_duplica_tras_reintento_ni_purga(
        self, empresa_user, admin_user
    ):
        from notificaciones.tasks import enviar_avisos_cumplimiento_task

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Entrega vencida', descripcion='D',
            tipo_solucion='sitio_web', estado='en_revision',
            fecha_cumplimiento=timezone.localdate() - timedelta(days=1),
        )
        assert enviar_avisos_cumplimiento_task() > 0
        avisos = Notificacion.objects.filter(proyecto=proyecto, tipo='alerta')
        assert all('ha vencido' in aviso.mensaje for aviso in avisos)
        total_original = avisos.count()
        assert enviar_avisos_cumplimiento_task() == 0
        avisos.delete()
        assert enviar_avisos_cumplimiento_task() == 0
        assert total_original > 0
        assert not Notificacion.objects.filter(proyecto=proyecto).exists()

    def test_cambiar_fecha_retira_aviso_anticipado_obsoleto(
        self, empresa_user, admin_user
    ):
        from notificaciones.tasks import enviar_avisos_cumplimiento_task

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Reprogramada', descripcion='D',
            tipo_solucion='sitio_web', estado='en_desarrollo',
            fecha_cumplimiento=timezone.localdate() + timedelta(days=1),
        )
        assert enviar_avisos_cumplimiento_task() > 0
        assert Notificacion.objects.filter(proyecto=proyecto, tipo='alerta').exists()
        proyecto.fecha_cumplimiento = timezone.localdate() + timedelta(days=10)
        proyecto.save(update_fields=['fecha_cumplimiento'])
        assert enviar_avisos_cumplimiento_task() == 0
        assert not Notificacion.objects.filter(proyecto=proyecto, tipo='alerta').exists()
