import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from postulaciones.models import Postulacion
from proyectos.models import Proyecto
from usuarios.models import FichaSena, PerfilDesarrollador

Usuario = get_user_model()


@pytest.fixture
def admin_user(db):
    return Usuario.objects.create_user(
        username='admin_sena',
        email='admin@sena.edu.co',
        password='Password123!',
        rol='administrador',
        identificacion='1000000001',
    )


@pytest.fixture
def empresa_user(db):
    return Usuario.objects.create_user(
        username='empresa_badge',
        email='empresa@badge.com',
        password='Password123!',
        rol='empresa',
        identificacion='900999111',
    )


@pytest.fixture
def dev_verificado(db, admin_user):
    ficha = FichaSena.objects.create(
        numero_ficha='2670123',
        programa_formacion='ADSO',
        activa=True,
        creada_por=admin_user,
    )
    user = Usuario.objects.create_user(
        username='dev_verificado',
        email='dev_verif@sena.edu.co',
        nombre='Carlos Verificado',
        password='Password123!',
        rol='desarrollador',
        identificacion='1000000002',
    )
    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=user)
    perfil.ficha_sena = ficha
    perfil.ficha = ficha.numero_ficha
    perfil.programa_formacion = ficha.programa_formacion
    perfil.estado_verificacion = 'verificado'
    perfil.save()
    return user


@pytest.fixture
def dev_sin_verificar(db):
    user = Usuario.objects.create_user(
        username='dev_sin_verificar',
        email='dev_sin@sena.edu.co',
        nombre='Pedro Sin Verificar',
        password='Password123!',
        rol='desarrollador',
        identificacion='1000000003',
    )
    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=user)
    perfil.estado_verificacion = 'sin_verificar'
    perfil.save()
    return user


@pytest.fixture
def dev_egresado_verificado(db):
    user = Usuario.objects.create_user(
        username='dev_egresado',
        email='egresado@sena.edu.co',
        nombre='Mariana Egresada',
        password='Password123!',
        rol='desarrollador',
        identificacion='1000000004',
    )
    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=user)
    perfil.condicion_sena = 'egresado'
    perfil.programa_formacion = 'Tecnólogo ADSO'
    perfil.estado_verificacion = 'verificado'
    perfil.save()
    return user


@pytest.mark.django_db
class TestBadgesVerificacionSena:
    def test_dashboard_dev_verificado_muestra_badge_verificado(self, client, dev_verificado):
        client.force_login(dev_verificado)
        response = client.get(reverse('dashboard_desarrollador'))
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Aprendiz SENA' in content
        assert 'data-testid="badge-verificacion-sena"' in content
        assert 'alerta-verificacion-sena' not in content

    def test_dashboard_dev_sin_verificar_muestra_alerta_y_badge(self, client, dev_sin_verificar):
        client.force_login(dev_sin_verificar)
        response = client.get(reverse('dashboard_desarrollador'))
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Sin Verificar' in content
        assert 'alerta-verificacion-sena' in content
        assert reverse('solicitar_verificacion_desarrollador') in content

    def test_ver_postulaciones_empresa_muestra_badge_verificado_sena(
        self, client, empresa_user, dev_verificado
    ):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto Test Badges',
            descripcion='Desc',
            tipo_solucion='sitio_web',
            estado='publicado',
        )
        Postulacion.objects.create(
            proyecto=proyecto,
            desarrollador=dev_verificado,
            mensaje='Carta de prueba',
            estado='pendiente',
        )

        client.force_login(empresa_user)
        response = client.get(reverse('ver_postulaciones_empresa', args=[proyecto.id]))
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Aprendiz SENA' in content
        assert 'data-testid="badge-sena-postulante"' in content

    def test_dashboard_dev_egresado_verificado_muestra_badge_egresado(self, client, dev_egresado_verificado):
        client.force_login(dev_egresado_verificado)
        response = client.get(reverse('dashboard_desarrollador'))
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Egresado SENA' in content
        assert 'data-testid="badge-verificacion-sena"' in content
        assert 'alerta-verificacion-sena' not in content

    def test_ver_postulaciones_empresa_muestra_badge_egresado_sena(
        self, client, empresa_user, dev_egresado_verificado
    ):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto Test Egresados',
            descripcion='Desc',
            tipo_solucion='sitio_web',
            estado='publicado',
        )
        Postulacion.objects.create(
            proyecto=proyecto,
            desarrollador=dev_egresado_verificado,
            mensaje='Carta de egresada',
            estado='pendiente',
        )

        client.force_login(empresa_user)
        response = client.get(reverse('ver_postulaciones_empresa', args=[proyecto.id]))
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Egresado SENA' in content
        assert 'data-testid="badge-sena-postulante"' in content

