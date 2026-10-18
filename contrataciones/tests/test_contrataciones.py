import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from proyectos.models import Proyecto
from contrataciones.models import Contratacion

User = get_user_model()


class TestContratacionModel:
    """Tests for Contratacion model."""

    def test_crear_contratacion(self, db):
        """Contratacion links empresa, dev, and proyecto."""
        empresa = User.objects.create_user(
            username='ce', email='ce@test.jobdevs',
            nombre='CE', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='cd', email='cd@test.jobdevs',
            nombre='CD', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='CP',
            descripcion='D', tipo_solucion='sitio_web',
            estado='publicado',
        )
        c = Contratacion.objects.create(
            proyecto=proyecto, empresa=empresa,
            desarrollador=dev, estado='activa',
        )
        assert c.id is not None
        assert c.estado == 'activa'
        assert c.fecha_inicio is not None
        assert Contratacion._meta.get_field('fecha_inicio').null is False

    def test_contratacion_str(self, db):
        """__str__ shows proyecto title."""
        empresa = User.objects.create_user(
            username='ce2', email='ce2@test.jobdevs',
            nombre='CE2', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='cd2', email='cd2@test.jobdevs',
            nombre='CD2', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='CP2',
            descripcion='D', tipo_solucion='sitio_web',
            estado='publicado',
        )
        c = Contratacion.objects.create(
            proyecto=proyecto, empresa=empresa,
            desarrollador=dev, estado='activa',
        )
        assert 'CP2' in str(c)


class TestListarContrataciones:
    """Tests for listar_contrataciones_empresa view."""

    def test_empresa_accede(self, auth_client, empresa_user):
        """Empresa can list their contrataciones."""
        response = auth_client.get(reverse('listar_contrataciones_empresa'))
        assert response.status_code == 200

    def test_dev_no_accede(self, dev_client):
        """Dev cannot access empresa contrataciones list."""
        response = dev_client.get(reverse('listar_contrataciones_empresa'))
        assert response.status_code == 302
