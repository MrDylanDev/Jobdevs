"""Tests unitarios de los servicios de finalización/valoración de proyectos
(SCRUM-156, Fase 2)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from contrataciones.models import Contratacion
from notificaciones.models import Notificacion
from proyectos import services
from proyectos.models import Entregable, HistorialEstadoProyecto, Proyecto, Valoracion
from proyectos.services import (
    desarrolladores_pendientes,
    finalizar_proyecto,
    validar_finalizacion,
    valorar_y_finalizar_si_ultima,
)
from usuarios.models import PerfilDesarrollador

User = get_user_model()


@pytest.fixture
def proyecto(empresa_user):
    return Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto Servicios', descripcion='D',
        tipo_solucion='sitio_web', estado='en_desarrollo',
    )


@pytest.fixture
def contratacion(proyecto, empresa_user, desarrollador_user):
    return Contratacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, empresa=empresa_user, estado='activa',
    )


@pytest.fixture
def hitos_completos(proyecto):
    for i in range(2):
        Entregable.objects.create(
            proyecto=proyecto, titulo=f'Hito {i}', estado='completado',
        )
    return proyecto.entregables.all()


def _segundo_dev():
    return User.objects.create_user(
        username='dev_servicio_2', email='dev2_servicio@test.jobdevs',
        nombre='Dev Servicio 2', rol='desarrollador', estado='activo',
        password='TestPass123!',
    )


class TestDesarrolladoresPendientes:

    def test_incluye_contratados_activos_sin_valorar(self, proyecto, contratacion):
        devs = list(desarrolladores_pendientes(proyecto))
        assert [dev.id for dev in devs] == [contratacion.desarrollador_id]

    def test_excluye_a_quien_ya_fue_valorado(self, empresa_user, proyecto, contratacion):
        Valoracion.objects.create(
            proyecto=proyecto, empresa=empresa_user,
            desarrollador=contratacion.desarrollador, puntuacion=5, rol_evaluador='empresa',
        )
        assert not desarrolladores_pendientes(proyecto).exists()


class TestValidarFinalizacion:

    def test_falla_sin_hitos(self, proyecto):
        with pytest.raises(ValidationError) as exc:
            validar_finalizacion(proyecto)
        assert 'hitos definidos' in str(exc.value)

    def test_falla_con_hitos_pendientes(self, proyecto):
        Entregable.objects.create(proyecto=proyecto, titulo='H1', estado='completado')
        Entregable.objects.create(proyecto=proyecto, titulo='H2', estado='pendiente')

        with pytest.raises(ValidationError) as exc:
            validar_finalizacion(proyecto)

        assert '1 hitos sin completar' in str(exc.value)

    def test_pasa_con_todos_los_hitos_completados(self, hitos_completos):
        validar_finalizacion(hitos_completos.first().proyecto)  # no lanza


class TestFinalizarProyecto:

    def test_cierra_contratos_notifica_y_registra_historial(
        self, empresa_user, proyecto, contratacion, hitos_completos
    ):
        resultado = finalizar_proyecto(proyecto.id, empresa_user)

        resultado.refresh_from_db()
        assert resultado.estado == 'finalizado'

        contratacion.refresh_from_db()
        assert contratacion.estado == 'finalizada'

        assert Notificacion.objects.filter(
            usuario=contratacion.desarrollador, proyecto=proyecto
        ).exists()
        assert HistorialEstadoProyecto.objects.filter(
            proyecto=proyecto, estado_nuevo='finalizado', estado_anterior='en_desarrollo'
        ).exists()

    def test_no_finaliza_sin_hitos(self, empresa_user, proyecto, contratacion):
        with pytest.raises(ValidationError):
            finalizar_proyecto(proyecto.id, empresa_user)

        proyecto.refresh_from_db()
        assert proyecto.estado == 'en_desarrollo'
        contratacion.refresh_from_db()
        assert contratacion.estado == 'activa'

    def test_rechaza_proyecto_ya_finalizado(self, empresa_user, proyecto, hitos_completos):
        proyecto.estado = 'finalizado'
        proyecto.save()

        with pytest.raises(ValidationError) as exc:
            finalizar_proyecto(proyecto.id, empresa_user)

        assert 'ya ha sido finalizado' in str(exc.value)

    def test_permission_denied_para_empresa_ajena(self, db, proyecto, hitos_completos):
        intruso = User.objects.create_user(
            username='intruso_serv', email='intruso_serv@test.jobdevs',
            nombre='Intruso', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        with pytest.raises(PermissionDenied):
            finalizar_proyecto(proyecto.id, intruso)


class TestValorarYFinalizar:

    def test_empresa_valora_despues_de_finalizacion_automatica(
        self, empresa_user, proyecto, contratacion, hitos_completos
    ):
        """RF 5.2.1 oficial: la valoración ocurre después de concluir el proyecto."""
        finalizar_proyecto(proyecto.id, empresa_user)

        finalizado_ahora, restantes = valorar_y_finalizar_si_ultima(
            proyecto.id,
            contratacion.desarrollador_id,
            5,
            'Excelente trabajo, comunicación y calidad técnica',
            empresa_user,
        )

        assert finalizado_ahora is False
        assert restantes == 0
        assert Valoracion.objects.filter(
            proyecto=proyecto,
            desarrollador=contratacion.desarrollador,
            rol_evaluador='empresa',
        ).exists()

    def test_rechaza_valoracion_despues_de_treinta_dias(
        self, empresa_user, proyecto, contratacion, hitos_completos
    ):
        """RF 5.3.3 oficial: la ventana para valorar termina a los 30 días."""
        finalizar_proyecto(proyecto.id, empresa_user)
        proyecto.historial_estados.filter(estado_nuevo='finalizado').update(
            fecha=timezone.now() - timedelta(days=31)
        )

        with pytest.raises(ValidationError) as exc:
            valorar_y_finalizar_si_ultima(
                proyecto.id,
                contratacion.desarrollador_id,
                5,
                'Valoración extemporánea que no debe registrarse',
                empresa_user,
            )

        assert '30 días' in str(exc.value)
        assert not Valoracion.objects.filter(proyecto=proyecto).exists()

    def test_valoracion_guardada_es_inmutable(
        self, empresa_user, proyecto, contratacion
    ):
        """RF 5.3.3 oficial: una valoración creada no admite modificaciones."""
        valoracion = Valoracion.objects.create(
            proyecto=proyecto,
            empresa=empresa_user,
            desarrollador=contratacion.desarrollador,
            puntuacion=5,
            comentario='Valoración original completa y verificable',
            rol_evaluador='empresa',
        )
        valoracion.puntuacion = 1

        with pytest.raises(ValidationError) as exc:
            valoracion.save()

        assert 'no puede modificarse' in str(exc.value)
        valoracion.refresh_from_db()
        assert valoracion.puntuacion == 5

    def test_devuelve_false_si_quedan_pendientes(
        self, empresa_user, proyecto, contratacion, hitos_completos
    ):
        segundo = _segundo_dev()
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=segundo, empresa=empresa_user, estado='activa',
        )

        finalizado, restantes = valorar_y_finalizar_si_ultima(
            proyecto.id, contratacion.desarrollador_id, 5,
            'Excelente trabajo, muy profesional y puntual', empresa_user,
        )

        assert finalizado is False
        assert restantes == 1
        assert Valoracion.objects.filter(
            proyecto=proyecto, desarrollador=contratacion.desarrollador
        ).exists()

    def test_finaliza_si_era_el_ultimo(
        self, empresa_user, proyecto, contratacion, hitos_completos
    ):
        finalizado, restantes = valorar_y_finalizar_si_ultima(
            proyecto.id, contratacion.desarrollador_id, 4,
            'Buen trabajo, cumplió con todos los hitos', empresa_user,
        )

        assert finalizado is True
        assert restantes == 0
        proyecto.refresh_from_db()
        assert proyecto.estado == 'finalizado'

    def test_rechaza_valoracion_duplicada(self, empresa_user, proyecto, contratacion, hitos_completos):
        valorar_y_finalizar_si_ultima(
            proyecto.id, contratacion.desarrollador_id, 5,
            'Primera entrega impecable y bien documentada', empresa_user,
        )

        # El proyecto ya quedó finalizado, así que recreamos uno en desarrollo
        proyecto.estado = 'en_desarrollo'
        proyecto.save()

        with pytest.raises(ValidationError) as exc:
            valorar_y_finalizar_si_ultima(
                proyecto.id, contratacion.desarrollador_id, 3,
                'Segunda valoración de prueba con texto válido', empresa_user,
            )

        assert 'Ya has calificado' in str(exc.value)

    def test_rechaza_puntuacion_fuera_de_rango(self, empresa_user, proyecto, contratacion, hitos_completos):
        with pytest.raises(ValidationError) as exc:
            valorar_y_finalizar_si_ultima(
                proyecto.id, contratacion.desarrollador_id, 9, '', empresa_user,
            )

        assert 'entre 1 y 5' in str(exc.value)

    def test_rechaza_puntuacion_ausente(self, empresa_user, proyecto, contratacion, hitos_completos):
        with pytest.raises(ValidationError) as exc:
            valorar_y_finalizar_si_ultima(
                proyecto.id, contratacion.desarrollador_id, None, '', empresa_user,
            )

        assert 'Debes seleccionar una puntuación' in str(exc.value)


    def test_rechaza_comentario_vacio(self, empresa_user, proyecto, contratacion, hitos_completos):
        """RF 5.2.1: sin comentario no hay valoración."""
        with pytest.raises(ValidationError) as exc:
            valorar_y_finalizar_si_ultima(
                proyecto.id, contratacion.desarrollador_id, 5, '   ', empresa_user,
            )

        assert 'comentario es obligatorio' in str(exc.value)
        assert not Valoracion.objects.filter(proyecto=proyecto).exists()

    def test_rechaza_comentario_corto(self, empresa_user, proyecto, contratacion, hitos_completos):
        """RF 5.2.1: un comentario de dos palabras no justifica la nota."""
        with pytest.raises(ValidationError) as exc:
            valorar_y_finalizar_si_ultima(
                proyecto.id, contratacion.desarrollador_id, 1, 'Muy malo', empresa_user,
            )

        assert 'al menos 20 caracteres' in str(exc.value)
        assert not Valoracion.objects.filter(proyecto=proyecto).exists()

    def test_actualiza_reputacion_del_desarrollador(
        self, empresa_user, proyecto, contratacion, hitos_completos
    ):
        """RF 5.3.1: el campo denormalizado queda en sincronía al calificar."""
        valorar_y_finalizar_si_ultima(
            proyecto.id, contratacion.desarrollador_id, 4,
            'Trabajo sólido, buena comunicación y entregas a tiempo', empresa_user,
        )

        perfil = PerfilDesarrollador.objects.get(usuario=contratacion.desarrollador)
        assert perfil.calificacion_promedio == 4

    def test_reputacion_promedia_varias_valoraciones(
        self, empresa_user, proyecto, contratacion, hitos_completos
    ):
        """RF 5.3.1: el promedio se recalcula, no se sobrescribe con la última nota."""
        valorar_y_finalizar_si_ultima(
            proyecto.id, contratacion.desarrollador_id, 5,
            'Excelente desempeño durante todo el proyecto', empresa_user,
        )
        segundo = Proyecto.objects.create(
            empresa=empresa_user, titulo='Segundo proyecto', descripcion='D',
            tipo_solucion='sitio_web', estado='en_desarrollo',
        )
        Entregable.objects.create(proyecto=segundo, titulo='Hito', estado='completado')
        Contratacion.objects.create(
            proyecto=segundo, desarrollador=contratacion.desarrollador,
            empresa=empresa_user, estado='activa',
        )
        valorar_y_finalizar_si_ultima(
            segundo.id, contratacion.desarrollador_id, 3,
            'Cumplió, aunque con retrasos en la última entrega', empresa_user,
        )

        perfil = PerfilDesarrollador.objects.get(usuario=contratacion.desarrollador)
        assert perfil.calificacion_promedio == 4

    def test_actualiza_proyectos_completados_al_finalizar(
        self, empresa_user, proyecto, contratacion, hitos_completos
    ):
        """RF 7.2.1: el contador sale de las contrataciones finalizadas."""
        finalizar_proyecto(proyecto.id, empresa_user)

        perfil = PerfilDesarrollador.objects.get(usuario=contratacion.desarrollador)
        assert perfil.num_proyectos_completados == 1


class TestReputacionBayesiana:
    def test_pondera_promedio_personal_con_promedio_global(self):
        resultado = services.calcular_reputacion_bayesiana(
            promedio_simple=Decimal('5'),
            cantidad=1,
            promedio_global=Decimal('4'),
            minimo_confianza=5,
        )

        assert resultado == Decimal('4.17')

    def test_sin_valoraciones_usa_referencia_global(self):
        resultado = services.calcular_reputacion_bayesiana(
            promedio_simple=Decimal('0'),
            cantidad=0,
            promedio_global=Decimal('4.2'),
            minimo_confianza=5,
        )

        assert resultado == Decimal('4.20')

    @pytest.mark.django_db
    def test_minimo_confianza_predeterminado_es_cinco(self):
        assert services.obtener_minimo_confianza_reputacion() == 5

    @pytest.mark.django_db
    def test_cambio_de_minimo_confianza_es_auditado(self, admin_user):
        from logs.models import LogAuditoria

        services.actualizar_minimo_confianza_reputacion(8, admin_user)

        assert services.obtener_minimo_confianza_reputacion() == 8
        log = LogAuditoria.objects.get(
            tabla_afectada='configuracion_reputacion', registro_id=1
        )
        assert log.valor_anterior == 'minimo_confianza=5'
        assert log.valor_nuevo == 'minimo_confianza=8'

    @pytest.mark.django_db
    def test_metricas_exponen_reputacion_promedio_y_cantidad(
            self, empresa_user, desarrollador_user):
        otro = User.objects.create_user(
            username='reput_otro', email='reput_otro@test.jobdevs',
            rol='desarrollador', estado='activo', password='TestPass123!',
        )
        for indice, (dev, puntuacion) in enumerate((
            (desarrollador_user, 5),
            (desarrollador_user, 3),
            (otro, 2),
        )):
            proyecto = Proyecto.objects.create(
                empresa=empresa_user, titulo=f'Reputación {indice}', descripcion='D',
                tipo_solucion='sitio_web', estado='finalizado',
            )
            Valoracion.objects.create(
                proyecto=proyecto, empresa=empresa_user, desarrollador=dev,
                rol_evaluador='empresa', puntuacion=puntuacion,
            )

        metricas = services.obtener_metricas_reputacion_desarrollador(
            desarrollador_user.id
        )

        assert metricas['promedio_simple'] == Decimal('4.00')
        assert metricas['cantidad'] == 2
        assert metricas['reputacion'] == Decimal('3.52')
        assert metricas['minimo_confianza'] == 5

