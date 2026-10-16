import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from proyectos.models import Proyecto, Valoracion
from usuarios.models import PerfilEmpresa

Usuario = get_user_model()


@pytest.fixture
def empresa_user(db):
    user = Usuario.objects.create_user(
        username='empresa_reputacion',
        email='contacto@reputacion.com',
        nombre='Soluciones Cloud Colombia S.A.S.',
        password='Password123!',
        rol='empresa',
        identificacion='900111222',
    )
    perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=user)
    perfil.nombre_empresa = 'Soluciones Cloud Colombia'
    perfil.razon_social = 'Soluciones Cloud Colombia S.A.S.'
    perfil.sector = 'Tecnología e Infraestructura'
    perfil.ciudad = 'Medellín'
    perfil.descripcion = 'Empresa especializada en arquitecturas cloud y microservicios.'
    perfil.estado_verificacion = 'verificada'
    perfil.tipo_persona = 'juridica'
    perfil.save()
    return user


@pytest.fixture
def dev_user(db):
    return Usuario.objects.create_user(
        username='dev_evaluador',
        email='dev@evaluador.com',
        nombre='Andrés Felipe',
        password='Password123!',
        rol='desarrollador',
        identificacion='1020304050',
    )


@pytest.fixture
def otro_dev(db):
    return Usuario.objects.create_user(
        username='dev_colaborador2',
        email='dev2@colaborador.com',
        nombre='Camila Torres',
        password='Password123!',
        rol='desarrollador',
        identificacion='1020304051',
    )


@pytest.mark.django_db
class TestDetalleEmpresaView:
    """Pruebas para la vista detalle_empresa (RF 3.1.2 / SCRUM-56)."""

    def test_detalle_empresa_anonimo_redirige_a_login(self, client, empresa_user):
        url = reverse('detalle_empresa', args=[empresa_user.id])
        response = client.get(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_detalle_empresa_inexistente_retorna_404(self, client, dev_user):
        client.force_login(dev_user)
        url = reverse('detalle_empresa', args=[999999])
        response = client.get(url)
        assert response.status_code == 404

    def test_detalle_empresa_usuario_no_empresa_retorna_404(self, client, dev_user, otro_dev):
        client.force_login(dev_user)
        # Intentar consultar el perfil de empresa de otro desarrollador debe dar 404
        url = reverse('detalle_empresa', args=[otro_dev.id])
        response = client.get(url)
        assert response.status_code == 404

    def test_desarrollador_accede_y_ve_datos_corporativos(self, client, dev_user, empresa_user):
        client.force_login(dev_user)
        url = reverse('detalle_empresa', args=[empresa_user.id])
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Soluciones Cloud Colombia S.A.S.' in content
        assert 'Tecnología e Infraestructura' in content
        assert 'Medellín' in content
        assert 'Empresa especializada en arquitecturas cloud' in content
        assert 'Empresa Verificada' in content
        assert 'data-testid="badge-empresa"' in content

    def test_calculo_promedio_reputacion_y_comentarios_previos(
        self, client, dev_user, otro_dev, empresa_user
    ):
        p1 = Proyecto.objects.create(
            empresa=empresa_user, titulo='Plataforma API REST',
            descripcion='Backend en Django', tipo_solucion='sitio_web',
            estado='finalizado',
        )
        p2 = Proyecto.objects.create(
            empresa=empresa_user, titulo='App Móvil Flutter',
            descripcion='App para clientes', tipo_solucion='aplicacion_movil',
            estado='finalizado',
        )

        # Dev 1 evalúa a la empresa con 5 estrellas
        Valoracion.objects.create(
            proyecto=p1, empresa=empresa_user, desarrollador=dev_user,
            rol_evaluador='desarrollador', puntuacion=5,
            comentario='Excelente trato del equipo técnico y pagos puntuales.',
        )
        # Dev 2 evalúa a la empresa con 4 estrellas
        Valoracion.objects.create(
            proyecto=p2, empresa=empresa_user, desarrollador=otro_dev,
            rol_evaluador='desarrollador', puntuacion=4,
            comentario='Muy buena comunicación y requerimientos claros.',
        )

        client.force_login(dev_user)
        url = reverse('detalle_empresa', args=[empresa_user.id])
        response = client.get(url)
        assert response.status_code == 200

        # Verificaciones en el contexto
        assert response.context['promedio_reputacion'] == 4.5
        assert response.context['total_resenas'] == 2
        assert response.context['conteo_estrellas'][5] == 1
        assert response.context['conteo_estrellas'][4] == 1
        assert response.context['proyectos_finalizados_count'] == 2

        # Verificaciones en el HTML renderizado (RF 3.1.2: estrellas y comentarios previos)
        content = response.content.decode('utf-8')
        assert '4.5' in content
        assert 'Excelente trato del equipo técnico y pagos puntuales.' in content
        assert 'Muy buena comunicación y requerimientos claros.' in content
        assert 'Andrés Felipe' in content
        assert 'Camila Torres' in content
        assert 'Plataforma API REST' in content
        assert 'data-testid="lista-resenas"' in content

    def test_empresa_sin_resenas_muestra_estado_vacio(self, client, dev_user, empresa_user):
        client.force_login(dev_user)
        url = reverse('detalle_empresa', args=[empresa_user.id])
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['promedio_reputacion'] == 0.0
        assert response.context['total_resenas'] == 0
        content = response.content.decode('utf-8')
        assert 'Esta empresa aún no cuenta con comentarios o reseñas' in content

    def test_detalle_empresa_lista_proyectos_abiertos_para_postular(
        self, client, dev_user, empresa_user
    ):
        p_abierto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Portal E-Commerce React',
            descripcion='Tienda en línea responsiva', tipo_solucion='sitio_web',
            estado='publicado', vacantes=3,
        )
        client.force_login(dev_user)
        url = reverse('detalle_empresa', args=[empresa_user.id])
        response = client.get(url)
        assert response.status_code == 200
        assert p_abierto in response.context['proyectos_abiertos']
        content = response.content.decode('utf-8')
        assert 'Portal E-Commerce React' in content
        assert '3 vacantes' in content
        assert reverse('postularse_a_proyecto', args=[p_abierto.id]) in content
