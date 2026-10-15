import pytest
from django.urls import reverse

from proyectos.models import Proyecto
from usuarios.models import PerfilEmpresa


@pytest.fixture
def perfil(empresa_user):
    return PerfilEmpresa.objects.create(usuario=empresa_user)


@pytest.fixture
def proyecto(empresa_user):
    return Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto Badge', descripcion='Desc',
        tipo_solucion='sitio_web', estado='publicado',
    )


def _listado(dev_client):
    response = dev_client.get(reverse('listar_proyectos'))
    assert response.status_code == 200
    return response.content.decode()


# --- Listado de proyectos ---

def test_listado_empresa_verificada_juridica(dev_client, perfil, proyecto):
    perfil.estado_verificacion = 'verificada'
    perfil.tipo_persona = 'juridica'
    perfil.save()
    html = _listado(dev_client)
    assert 'Empresa Verificada' in html
    assert 'Negocio Verificado' not in html


def test_listado_empresa_verificada_natural(dev_client, perfil, proyecto):
    perfil.estado_verificacion = 'verificada'
    perfil.tipo_persona = 'natural'
    perfil.save()
    html = _listado(dev_client)
    assert 'Negocio Verificado' in html
    assert 'Empresa Verificada' not in html


@pytest.mark.parametrize('estado,texto', [
    ('sin_verificar', 'Sin Verificar'),
    ('en_revision', 'En Revisión'),
    ('rechazada', 'Verificación Rechazada'),
])
def test_listado_empresa_no_verificada_muestra_advertencia(dev_client, perfil, proyecto, estado, texto):
    perfil.estado_verificacion = estado
    perfil.save()
    html = _listado(dev_client)
    assert texto in html
    assert 'Empresa Verificada' not in html
    assert 'Negocio Verificado' not in html
    assert 'badge-warning' in html or 'badge-danger' in html


def test_listado_empresa_sin_perfil_no_falla(dev_client, proyecto):
    response = dev_client.get(reverse('listar_proyectos'))
    assert response.status_code == 200
    assert 'Empresa Verificada' not in response.content.decode()


def test_listado_contexto_incluye_datos_verificacion(dev_client, perfil, proyecto):
    perfil.estado_verificacion = 'verificada'
    perfil.save()
    response = dev_client.get(reverse('listar_proyectos'))
    item = response.context['proyectos'][0]
    assert item['empresa_verificada'] is True
    assert item['empresa_badge']['label'] == 'Empresa Verificada'
    assert item['empresa_estado_verificacion'] == 'verificada'


# --- Dashboard empresa ---

def test_dashboard_empresa_enlace_verificacion(auth_client, perfil):
    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200
    html = response.content.decode()
    assert f'href="{reverse("solicitar_verificacion_empresa")}"' in html
    assert 'Verificación NIT / Identidad' in html


@pytest.mark.parametrize('estado,tipo,texto', [
    ('sin_verificar', 'juridica', 'Sin Verificar'),
    ('en_revision', 'juridica', 'En Revisión'),
    ('verificada', 'juridica', 'Empresa Verificada'),
    ('verificada', 'natural', 'Negocio Verificado'),
])
def test_dashboard_empresa_muestra_badge_estado(auth_client, perfil, estado, tipo, texto):
    perfil.estado_verificacion = estado
    perfil.tipo_persona = tipo
    perfil.save()
    html = auth_client.get(reverse('dashboard_empresa')).content.decode()
    assert 'data-testid="badge-verificacion-header"' in html
    assert texto in html


# --- Dashboard desarrollador ---

def test_dashboard_desarrollador_contexto_badge_empresa(dev_client, desarrollador_user, empresa_user, perfil):
    from proyectos.models import Equipo
    perfil.estado_verificacion = 'verificada'
    perfil.save()
    p = Proyecto.objects.create(
        empresa=empresa_user, titulo='En Dev', descripcion='d',
        tipo_solucion='sitio_web', estado='en_desarrollo',
    )
    equipo = Equipo.objects.create(proyecto=p, nombre='Eq')
    equipo.miembros.add(desarrollador_user)
    response = dev_client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200
    item = response.context['mis_proyectos_activos_v'][0]
    assert item['empresa_badge']['label'] == 'Empresa Verificada'
    assert 'Empresa Verificada' in response.content.decode()
