"""Regresiones de cierre fiable y valoración de proyectos históricos."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from proyectos import services
from proyectos.models import (
    HistorialEstadoProyecto,
    Proyecto,
    RegularizacionCierreProyecto,
    Valoracion,
)
from proyectos.services import validar_plazo_valoracion

User = get_user_model()


@pytest.mark.django_db
class TestCierreFiableParaValorar:
    def test_finalizado_reciente_sin_cierre_fiable_exige_regularizacion(self):
        empresa = User.objects.create_user(
            username='empresa_historica',
            email='empresa-historica@test.jobdevs',
            password='TestPass123!',
            rol='empresa',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa,
            titulo='Finalizado sin trazabilidad',
            descripcion='Proyecto legado',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )

        with pytest.raises(ValidationError, match='regularización administrativa'):
            validar_plazo_valoracion(proyecto)


@pytest.mark.django_db
class TestRegularizacionCierreHistorico:
    def test_admin_registra_fecha_real_actor_motivo_y_momento(self):
        admin = User.objects.create_user(
            username='admin_regulariza',
            email='admin-regulariza@test.jobdevs',
            password='TestPass123!',
            rol='administrador',
        )
        empresa = User.objects.create_user(
            username='empresa_legada',
            email='empresa-legada@test.jobdevs',
            password='TestPass123!',
            rol='empresa',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa,
            titulo='Cierre documentado externamente',
            descripcion='Proyecto legado',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Proyecto.objects.filter(pk=proyecto.pk).update(
            fecha_publicacion=timezone.now() - timedelta(days=100)
        )
        fecha_cierre = timezone.now() - timedelta(days=10)

        regularizacion = services.regularizar_cierre_historico(
            proyecto_id=proyecto.pk,
            fecha_cierre=fecha_cierre,
            motivo='Acta de aceptación final firmada por ambas partes.',
            registrado_por=admin,
        )

        assert regularizacion.proyecto_id == proyecto.pk
        assert regularizacion.fecha_cierre == fecha_cierre
        assert regularizacion.motivo == 'Acta de aceptación final firmada por ambas partes.'
        assert regularizacion.registrado_por_id == admin.pk
        assert regularizacion.registrado_en is not None

    def test_fecha_regularizada_inicia_el_plazo_de_valoracion(self):
        admin = User.objects.create_user(
            username='admin_habilita',
            email='admin-habilita@test.jobdevs',
            password='TestPass123!',
            rol='administrador',
        )
        empresa = User.objects.create_user(
            username='empresa_habilitada',
            email='empresa-habilitada@test.jobdevs',
            password='TestPass123!',
            rol='empresa',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa,
            titulo='Legado regularizado',
            descripcion='Proyecto legado',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Proyecto.objects.filter(pk=proyecto.pk).update(
            fecha_publicacion=timezone.now() - timedelta(days=100)
        )
        services.regularizar_cierre_historico(
            proyecto_id=proyecto.pk,
            fecha_cierre=timezone.now() - timedelta(days=10),
            motivo='Acta de cierre verificada por el administrador.',
            registrado_por=admin,
        )

        validar_plazo_valoracion(proyecto)


@pytest.mark.django_db
class TestRegularizacionCierreHistoricoHttp:
    def test_panel_lista_pendiente_y_admin_lo_regulariza_por_post(
        self, admin_client, admin_user, empresa_user
    ):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Pendiente de cierre fiable',
            descripcion='Proyecto legado',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Proyecto.objects.filter(pk=proyecto.pk).update(
            fecha_publicacion=timezone.now() - timedelta(days=100)
        )

        listado = admin_client.get(reverse('dashboard_admin'))

        assert listado.status_code == 200
        assert proyecto in listado.context['proyectos_pendientes_regularizacion']
        assert 'Regularizar cierres históricos' in listado.content.decode()

        fecha_cierre = timezone.localtime(
            timezone.now() - timedelta(days=10)
        ).strftime('%Y-%m-%dT%H:%M')
        respuesta = admin_client.post(
            reverse('admin_regularizar_cierre_proyecto', args=[proyecto.pk]),
            {
                'fecha_cierre': fecha_cierre,
                'motivo': 'Acta final validada contra el archivo contractual.',
                'referencia_evidencia': 'ACTA-LEGADO-2024-019',
            },
        )

        assert respuesta.status_code == 302
        regularizacion = RegularizacionCierreProyecto.objects.get(proyecto=proyecto)
        assert regularizacion.registrado_por == admin_user
        assert regularizacion.referencia_evidencia == 'ACTA-LEGADO-2024-019'

    def test_no_admite_get_ni_empresa_y_no_crea_registro(
        self, admin_client, empresa_user
    ):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Histórico seguro', descripcion='P',
            tipo_solucion='sitio_web', estado='finalizado',
        )
        url = reverse('admin_regularizar_cierre_proyecto', args=[proyecto.pk])
        assert admin_client.get(url).status_code == 405
        client = Client()
        client.force_login(empresa_user)
        assert client.post(url, {
            'fecha_cierre': timezone.now().isoformat(),
            'motivo': 'Una justificación con evidencia suficiente.',
        }).status_code == 403
        assert not RegularizacionCierreProyecto.objects.filter(proyecto=proyecto).exists()

    def test_fecha_invalida_no_muta_y_no_reabre_ventana_vencida(
        self, admin_client, empresa_user
    ):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Legado vencido', descripcion='P',
            tipo_solucion='sitio_web', estado='finalizado',
        )
        Proyecto.objects.filter(pk=proyecto.pk).update(
            fecha_publicacion=timezone.now() - timedelta(days=100)
        )
        url = reverse('admin_regularizar_cierre_proyecto', args=[proyecto.pk])
        assert admin_client.post(url, {
            'fecha_cierre': 'fecha falsa', 'motivo': 'Acta del cierre real validada.',
        }).status_code == 302
        assert not RegularizacionCierreProyecto.objects.filter(proyecto=proyecto).exists()
        admin_client.post(url, {
            'fecha_cierre': (timezone.now() - timedelta(days=40)).isoformat(),
            'motivo': 'Acta del cierre real validada.',
        })
        with pytest.raises(ValidationError, match='30 días'):
            validar_plazo_valoracion(proyecto)

    def test_no_lista_cierre_con_historial_ni_regularizado(
        self, admin_client, admin_user, empresa_user
    ):
        con_historial = Proyecto.objects.create(
            empresa=empresa_user, titulo='Cierre trazado', descripcion='P',
            tipo_solucion='sitio_web', estado='finalizado',
        )
        HistorialEstadoProyecto.objects.create(
            proyecto=con_historial, estado_anterior='en_revision',
            estado_nuevo='finalizado', cambiado_por=empresa_user,
        )
        regularizado = Proyecto.objects.create(
            empresa=empresa_user, titulo='Cierre documentado', descripcion='P',
            tipo_solucion='sitio_web', estado='finalizado',
        )
        services.regularizar_cierre_historico(
            regularizado.pk, timezone.now(),
            'Acta histórica de cierre ya documentada.', admin_user,
        )
        listado = admin_client.get(reverse('dashboard_admin'))
        pendientes = listado.context['proyectos_pendientes_regularizacion']
        assert con_historial not in pendientes
        assert regularizado not in pendientes

    def test_regularizar_conserva_valoracion_preexistente(
        self, admin_user, empresa_user, desarrollador_user
    ):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Valoración heredada', descripcion='P',
            tipo_solucion='sitio_web', estado='finalizado',
        )
        valoracion = Valoracion.objects.create(
            proyecto=proyecto, empresa=empresa_user,
            desarrollador=desarrollador_user, rol_evaluador='empresa',
            puntuacion=4, comentario='Valoración histórica',
        )
        services.regularizar_cierre_historico(
            proyecto.pk, timezone.now(), 'Acta del cierre conservada.', admin_user,
        )
        valoracion.refresh_from_db()
        assert valoracion.puntuacion == 4
        assert valoracion.comentario == 'Valoración histórica'
