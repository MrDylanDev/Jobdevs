"""Tests unitarios de los servicios de finalización/valoración de proyectos
(SCRUM-156, Fase 2)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from contrataciones.models import Contratacion
from notificaciones.models import Notificacion
from proyectos.models import Entregable, HistorialEstadoProyecto, Proyecto, Valoracion
from usuarios.models import PerfilDesarrollador
from proyectos.services import (
    desarrolladores_pendientes,
    finalizar_proyecto,
    validar_finalizacion,
    valorar_y_finalizar_si_ultima,
)

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
