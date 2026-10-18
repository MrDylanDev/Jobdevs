import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from proyectos.models import Proyecto
from favoritos.models import Favorito

User = get_user_model()


class TestFavoritoModel:
    """Tests for Favorito model."""

    def test_crear_favorito(self, db):
        """Favorito links dev to proyecto."""
        empresa = User.objects.create_user(
            username='fe', email='fe@test.jobdevs',
            nombre='FE', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='fd', email='fd@test.jobdevs',
            nombre='FD', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='Fav Proy',
            descripcion='D', tipo_solucion='sitio_web',
            estado='publicado',
        )
        fav = Favorito.objects.create(desarrollador=dev, proyecto=proyecto)
        assert fav.id is not None
        assert fav.desarrollador == dev
        assert fav.proyecto == proyecto

    def test_favorito_unique(self, db):
        """Same dev can't favorite the same proyecto twice."""
        empresa = User.objects.create_user(
            username='fe2', email='fe2@test.jobdevs',
            nombre='FE2', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='fd2', email='fd2@test.jobdevs',
            nombre='FD2', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='Fav Proy 2',
            descripcion='D', tipo_solucion='sitio_web',
            estado='publicado',
        )
        Favorito.objects.create(desarrollador=dev, proyecto=proyecto)
        with pytest.raises(Exception):
            Favorito.objects.create(desarrollador=dev, proyecto=proyecto)

    def test_favorito_str(self, db):
        """__str__ shows dev and proyecto."""
        empresa = User.objects.create_user(
            username='fe3', email='fe3@test.jobdevs',
            nombre='FE3', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='fd3', email='fd3@test.jobdevs',
            nombre='FD3', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='Str Test',
            descripcion='D', tipo_solucion='sitio_web',
            estado='publicado',
        )
        fav = Favorito.objects.create(desarrollador=dev, proyecto=proyecto)
        assert 'fd3' in str(fav)
        assert 'Str Test' in str(fav)


class TestToggleFavorito:
    """Tests for toggle_favorito view."""

    def test_toggle_add_favorito(self, dev_client, desarrollador_user, empresa_user):
        """Dev can add a project to favorites."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Toggle Proy',
            descripcion='D', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = dev_client.post(
            reverse('toggle_favorito', args=[proyecto.id])
        )
        assert response.status_code == 302
        assert Favorito.objects.filter(
            desarrollador=desarrollador_user, proyecto=proyecto
        ).exists()

    def test_toggle_remove_favorito(self, dev_client, desarrollador_user, empresa_user):
        """Toggle removes favorite if already favorited."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Toggle Off',
            descripcion='D', tipo_solucion='sitio_web',
            estado='publicado',
        )
        Favorito.objects.create(desarrollador=desarrollador_user, proyecto=proyecto)
        response = dev_client.post(
            reverse('toggle_favorito', args=[proyecto.id])
        )
        assert response.status_code == 302
        assert not Favorito.objects.filter(
            desarrollador=desarrollador_user, proyecto=proyecto
        ).exists()

    def test_empresa_no_puede_favoritear(self, auth_client, empresa_user):
        """Empresa cannot favorite projects."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Emp Fav',
            descripcion='D', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = auth_client.post(
            reverse('toggle_favorito', args=[proyecto.id])
        )
        assert response.status_code == 302
        assert not Favorito.objects.filter(proyecto=proyecto).exists()

    def test_toggle_favorito_open_redirect_bloqueado(self, dev_client, desarrollador_user, empresa_user):
        """Auditoría SCRUM-160: Open redirect vía HTTP_REFERER debe ser neutralizado."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Fav Redirect',
            descripcion='D', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = dev_client.post(
            reverse('toggle_favorito', args=[proyecto.id]),
            HTTP_REFERER='https://sitio-malicioso.com/phishing',
        )
        assert response.status_code == 302
        assert response.url == reverse('listar_proyectos')

    def test_toggle_favorito_referer_legitimo_permitido(self, dev_client, desarrollador_user, empresa_user):
        """Un referer interno legítimo debe ser respetado tras el toggle."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Fav Legitimo',
            descripcion='D', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = dev_client.post(
            reverse('toggle_favorito', args=[proyecto.id]),
            HTTP_REFERER='http://testserver/proyectos/publicados/',
        )
        assert response.status_code == 302
        assert response.url == 'http://testserver/proyectos/publicados/'

    @pytest.mark.parametrize('estado_no_publicado', ['en_desarrollo', 'en_revision', 'finalizado', 'inactivo'])
    def test_toggle_favorito_solo_proyectos_publicados(self, dev_client, empresa_user, estado_no_publicado):
        """Auditoría SCRUM-160: No se pueden favoritear proyectos que no estén publicados."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo=f'Fav {estado_no_publicado}',
            descripcion='D', tipo_solucion='sitio_web',
            estado=estado_no_publicado,
        )
        response = dev_client.post(reverse('toggle_favorito', args=[proyecto.id]))
        assert response.status_code == 404
        assert not Favorito.objects.filter(proyecto=proyecto).exists()

