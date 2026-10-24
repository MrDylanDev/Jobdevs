import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from contrataciones.models import Contratacion
from postulaciones.models import Postulacion
from proyectos.models import Proyecto, Valoracion
from usuarios.models import PerfilDesarrollador

Usuario = get_user_model()


@pytest.fixture
def empresa_user(db):
    return Usuario.objects.create_user(
        username='empresa_contratante',
        email='talento@contratante.com',
        nombre='Soluciones Cloud Colombia S.A.S.',
        password='Password123!',
        rol='empresa',
        identificacion='900333444',
    )


@pytest.fixture
def dev_user(db):
    user = Usuario.objects.create_user(
        username='dev_perfil_publico',
        email='dev@perfilpublico.com',
        nombre='Andrés Felipe Gómez',
        password='Password123!',
        rol='desarrollador',
        identificacion='1020304060',
    )
    perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=user)
    perfil.condicion_sena = 'aprendiz'
    perfil.programa_formacion = 'Análisis y Desarrollo de Software'
    perfil.ficha = '2558104'
    perfil.habilidades = 'Python, Django, PostgreSQL, Docker'
    perfil.portafolio_url = 'https://portafolio.andres.dev'
    perfil.estado_verificacion = 'verificado'
    perfil.fecha_verificacion = timezone.now()
    perfil.save()
    return user


@pytest.fixture
def empresa_viewer(db):
    return Usuario.objects.create_user(
        username='empresa_visitante',
        email='visita@empresa.com',
        nombre='Empresa Visitante S.A.S.',
        password='Password123!',
        rol='empresa',
        identificacion='900333445',
    )


@pytest.fixture
def proyecto_finalizado(db, empresa_user, dev_user):
    proyecto = Proyecto.objects.create(
        empresa=empresa_user,
        titulo='Plataforma de Reservas',
        descripcion='Sistema de reservas con Django y PostgreSQL',
        tipo_solucion='sitio_web',
        estado='finalizado',
    )
    Contratacion.objects.create(
        proyecto=proyecto,
        desarrollador=dev_user,
        empresa=empresa_user,
        estado='finalizada',
    )
    return proyecto


@pytest.mark.django_db
class TestDetalleDesarrolladorView:
    """Pruebas para la vista detalle_desarrollador (RF 5.3.1 / SCRUM-222)."""

    def test_anonimo_redirige_a_login(self, client, dev_user):
        url = reverse('detalle_desarrollador', args=[dev_user.id])
        response = client.get(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_desarrollador_inexistente_retorna_404(self, client, empresa_viewer):
        client.force_login(empresa_viewer)
        url = reverse('detalle_desarrollador', args=[999999])
        response = client.get(url)
        assert response.status_code == 404

    def test_usuario_sin_rol_desarrollador_retorna_404(self, client, empresa_viewer, empresa_user):
        client.force_login(empresa_viewer)
        url = reverse('detalle_desarrollador', args=[empresa_user.id])
        response = client.get(url)
        assert response.status_code == 404

    def test_empresa_ve_perfil_publico_del_desarrollador(self, client, empresa_viewer, dev_user):
        client.force_login(empresa_viewer)
        url = reverse('detalle_desarrollador', args=[dev_user.id])
        response = client.get(url)
        assert response.status_code == 200

        content = response.content.decode('utf-8')
        assert 'Andrés Felipe Gómez' in content
        assert 'data-testid="badge-desarrollador"' in content
        assert 'Aprendiz SENA' in content
        assert 'Análisis y Desarrollo de Software' in content
        assert '2558104' in content
        assert 'Python' in content
        assert 'Django' in content
        assert 'data-testid="habilidades-dev"' in content
        assert 'https://portafolio.andres.dev' in content
        assert 'data-testid="metricas-dev"' in content

    def test_calculo_reputacion_y_resenas_de_empresas(
        self, client, empresa_viewer, empresa_user, dev_user, proyecto_finalizado
    ):
        Valoracion.objects.create(
            proyecto=proyecto_finalizado,
            empresa=empresa_user,
            desarrollador=dev_user,
            rol_evaluador='empresa',
            puntuacion=5,
            comentario='Entrega impecable y comunicación constante.',
        )

        client.force_login(empresa_viewer)
        response = client.get(reverse('detalle_desarrollador', args=[dev_user.id]))
        assert response.status_code == 200
        assert response.context['promedio_reputacion'] == 5.0
        assert response.context['total_resenas'] == 1
        assert response.context['conteo_estrellas'][5] == 1
        assert response.context['conteo_estrellas'][4] == 0
        assert response.context['proyectos_finalizados_count'] == 1

        content = response.content.decode('utf-8')
        assert 'data-testid="lista-resenas"' in content
        assert 'Entrega impecable y comunicación constante.' in content
        assert 'Plataforma de Reservas' in content
        assert 'Soluciones Cloud Colombia S.A.S.' in content

    def test_resenas_de_desarrolladores_no_se_muestran_como_reputacion(
        self, client, empresa_viewer, empresa_user, dev_user, proyecto_finalizado
    ):
        # Una valoración emitida por el desarrollador evalúa a la empresa, no al dev.
        Valoracion.objects.create(
            proyecto=proyecto_finalizado,
            empresa=empresa_user,
            desarrollador=dev_user,
            rol_evaluador='desarrollador',
            puntuacion=1,
            comentario='Comentario que el desarrollador dio a la empresa.',
        )

        client.force_login(empresa_viewer)
        response = client.get(reverse('detalle_desarrollador', args=[dev_user.id]))
        assert response.status_code == 200
        assert response.context['total_resenas'] == 0
        assert response.context['promedio_reputacion'] == 0.0
        content = response.content.decode('utf-8')
        assert 'Comentario que el desarrollador dio a la empresa.' not in content

    def test_desarrollador_sin_resenas_muestra_estado_vacio(self, client, empresa_viewer, dev_user):
        client.force_login(empresa_viewer)
        response = client.get(reverse('detalle_desarrollador', args=[dev_user.id]))
        assert response.status_code == 200
        assert response.context['total_resenas'] == 0
        content = response.content.decode('utf-8')
        assert 'aún no cuenta con valoraciones' in content

    def test_lista_recibidas_enlaza_al_perfil_publico(
        self, client, empresa_user, dev_user
    ):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Portal de Compras',
            descripcion='Portal interno para compras',
            tipo_solucion='sitio_web',
            estado='publicado',
        )
        Postulacion.objects.create(
            proyecto=proyecto,
            desarrollador=dev_user,
            mensaje='Me interesa el proyecto.',
        )

        client.force_login(empresa_user)
        response = client.get(
            reverse('ver_postulaciones_empresa', args=[proyecto.id])
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert reverse('detalle_desarrollador', args=[dev_user.id]) in content
