import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from proyectos.models import Proyecto
from postulaciones.models import Postulacion

User = get_user_model()


class TestPostulacionModel:
    """Tests for the Postulacion model."""

    def test_crear_postulacion(self, db):
        """Postulacion links dev to proyecto."""
        empresa = User.objects.create_user(
            username='pe', email='pe@test.teir',
            nombre='PE', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='pd', email='pd@test.teir',
            nombre='PD', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='P', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )
        postulacion = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=dev,
            mensaje='Me interesa', estado='pendiente',
        )
        assert postulacion.id is not None
        assert postulacion.estado == 'pendiente'
        assert postulacion.desarrollador == dev

    def test_unique_postulacion(self, db):
        """Same dev can't apply twice to the same proyecto."""
        empresa = User.objects.create_user(
            username='pe2', email='pe2@test.teir',
            nombre='PE2', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='pd2', email='pd2@test.teir',
            nombre='PD2', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='P2', descripcion='D2',
            tipo_solucion='sitio_web', estado='publicado',
        )
        Postulacion.objects.create(proyecto=proyecto, desarrollador=dev)
        with pytest.raises(Exception):
            Postulacion.objects.create(proyecto=proyecto, desarrollador=dev)

    def test_postulacion_str(self, db):
        """__str__ shows dev and proyecto."""
        empresa = User.objects.create_user(
            username='pe3', email='pe3@test.teir',
            nombre='PE3', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='pd3', email='pd3@test.teir',
            nombre='PD3', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='P3', descripcion='D3',
            tipo_solucion='sitio_web', estado='publicado',
        )
        p = Postulacion.objects.create(proyecto=proyecto, desarrollador=dev)
        assert 'pd3' in str(p)
        assert 'P3' in str(p)


class TestPostularse:
    """Tests for postularse_a_proyecto view."""

    def test_dev_puede_postularse(self, dev_client, desarrollador_user, empresa_user):
        """Dev can apply to a published project."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy Post',
            descripcion='DP', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = dev_client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'Hola', 'experiencia': 'Mucha', 'link': 'http://example.com'}
        )
        assert response.status_code == 302
        assert Postulacion.objects.filter(
            proyecto=proyecto, desarrollador=desarrollador_user
        ).exists()

    def test_empresa_no_puede_postularse(self, auth_client, empresa_user):
        """Empresa cannot apply to projects."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='No Post',
            descripcion='NP', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = auth_client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'X', 'experiencia': 'Y', 'link': 'Z'}
        )
        assert response.status_code == 302
        assert not Postulacion.objects.filter(proyecto=proyecto).exists()

    def test_no_postularse_proyecto_no_publicado(self, dev_client, empresa_user):
        """Cannot apply to non-published projects."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Cerrado',
            descripcion='C', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        response = dev_client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'H', 'experiencia': 'E', 'link': 'L'}
        )
        assert response.status_code == 302
        assert not Postulacion.objects.filter(proyecto=proyecto).exists()


class TestAceptarPostulacion:
    """Tests for aceptar_postulacion view."""

    def test_empresa_acepta_postulacion(self, auth_client, empresa_user, desarrollador_user):
        """Empresa can accept a pending postulacion."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='PA', descripcion='DA',
            tipo_solucion='sitio_web', estado='publicado',
        )
        postulacion = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            estado='pendiente',
        )
        response = auth_client.post(
            reverse('aceptar_postulacion', args=[postulacion.id])
        )
        assert response.status_code == 302
        postulacion.refresh_from_db()
        assert postulacion.estado == 'aceptada'

    def test_dev_no_puede_aceptar(self, dev_client, empresa_user, desarrollador_user):
        """Dev cannot accept postulaciones."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='PAD', descripcion='DAD',
            tipo_solucion='sitio_web', estado='publicado',
        )
        postulacion = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            estado='pendiente',
        )
        response = dev_client.post(
            reverse('aceptar_postulacion', args=[postulacion.id])
        )
        assert response.status_code == 302
        postulacion.refresh_from_db()
        assert postulacion.estado == 'pendiente'

    def test_no_puede_aceptar_si_limite_de_vacantes_alcanzado(self, auth_client, empresa_user, desarrollador_user):
        """RF 3.3.2: No se permite contratar si el proyecto ya cubrió sus vacantes."""
        from contrataciones.models import Contratacion
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='P Vacantes', descripcion='DV',
            tipo_solucion='sitio_web', estado='publicado', vacantes=1,
        )
        post1 = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, estado='pendiente',
        )
        dev2 = User.objects.create_user(
            username='dev2_cupos', email='dev2_cupos@test.teir',
            nombre='Dev 2 Cupos', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        post2 = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=dev2, estado='pendiente',
        )

        # 1. Aceptar la primera postulación (ocupa la única vacante disponible)
        res1 = auth_client.post(reverse('aceptar_postulacion', args=[post1.id]))
        assert res1.status_code == 302
        post1.refresh_from_db()
        assert post1.estado == 'aceptada'
        assert Contratacion.objects.filter(proyecto=proyecto, estado='activa').count() == 1

        # 2. Intentar aceptar la segunda postulación debe ser rechazado
        res2 = auth_client.post(reverse('aceptar_postulacion', args=[post2.id]), follow=True)
        assert res2.status_code == 200
        post2.refresh_from_db()
        assert post2.estado == 'pendiente'
        assert Contratacion.objects.filter(proyecto=proyecto, estado='activa').count() == 1
        messages = list(res2.context['messages'])
        assert any('vacantes' in str(m).lower() for m in messages)

    def test_no_puede_aceptar_si_proyecto_finalizado(self, auth_client, empresa_user, desarrollador_user):
        """No se pueden aceptar postulaciones si el proyecto ya está finalizado."""
        from contrataciones.models import Contratacion
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='P Fin', descripcion='DF',
            tipo_solucion='sitio_web', estado='finalizado', vacantes=2,
        )
        post = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, estado='pendiente',
        )
        res = auth_client.post(reverse('aceptar_postulacion', args=[post.id]), follow=True)
        assert res.status_code == 200
        post.refresh_from_db()
        assert post.estado == 'pendiente'
        assert not Contratacion.objects.filter(proyecto=proyecto).exists()
        messages = list(res.context['messages'])
        assert any('finalizado' in str(m).lower() or 'estado' in str(m).lower() for m in messages)

