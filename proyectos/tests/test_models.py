import pytest
from django.contrib.auth import get_user_model
from proyectos.models import Proyecto, HistorialEstadoProyecto

User = get_user_model()


class TestProyectoModel:
    """Tests for the Proyecto model."""

    def test_crear_proyecto(self, db):
        """Proyecto can be created with minimum fields."""
        empresa = User.objects.create_user(
            username='proy_empresa', email='proy@test.jobdevs',
            nombre='Proy Empresa', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa,
            titulo='Test Project',
            descripcion='A test project description',
            tipo_solucion='sitio_web',
            prioridad='alta',
            vacantes=3,
            estado='publicado',
        )
        assert proyecto.id is not None
        assert proyecto.titulo == 'Test Project'
        assert proyecto.estado == 'publicado'
        assert proyecto.vacantes == 3

    def test_proyecto_str(self, db):
        """__str__ returns titulo + estado."""
        empresa = User.objects.create_user(
            username='p2', email='p2@test.jobdevs',
            nombre='P2', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='Mi Web', descripcion='Web',
            tipo_solucion='sitio_web', estado='publicado',
        )
        assert 'Mi Web' in str(proyecto)
        assert 'Publicado' in str(proyecto)

    def test_registrar_cambio_estado(self, db):
        """registrar_cambio_estado creates a history entry."""
        empresa = User.objects.create_user(
            username='p3', email='p3@test.jobdevs',
            nombre='P3', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='P', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )
        proyecto.registrar_cambio_estado('en_desarrollo', empresa, 'publicado')
        historial = HistorialEstadoProyecto.objects.filter(proyecto=proyecto)
        assert historial.count() == 1
        assert historial.first().estado_nuevo == 'en_desarrollo'

    def test_estados_disponibles(self, db):
        """Proyecto can transition through estados."""
        empresa = User.objects.create_user(
            username='p4', email='p4@test.jobdevs',
            nombre='P4', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='Test', descripcion='T',
            tipo_solucion='sitio_web',
        )
        # Default estado is 'publicado'
        assert proyecto.estado == 'publicado'
        # Can change estado
        proyecto.estado = 'finalizado'
        proyecto.save()
        proyecto.refresh_from_db()
        assert proyecto.estado == 'finalizado'
