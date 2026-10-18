import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from proyectos.models import CategoriaSolucion, Proyecto

User = get_user_model()


@pytest.fixture
def empresa(db):
    return User.objects.create_user(
        username='cat_empresa', email='cat@test.jobdevs',
        nombre='Cat Empresa', rol='empresa', estado='activo',
        password='TestPass123!',
    )


def _proyecto(empresa, **kwargs):
    data = dict(empresa=empresa, titulo='P', descripcion='D')
    data.update(kwargs)
    return Proyecto.objects.create(**data)


def _categoria(slug, nombre):
    categoria, _ = CategoriaSolucion.objects.get_or_create(
        slug=slug, defaults={'nombre': nombre},
    )
    return categoria


class TestCategoriaSolucionModel:
    def test_crear_categoria(self, db):
        c = CategoriaSolucion.objects.create(nombre='Inteligencia Artificial', slug='ia-test')
        assert c.pk is not None
        assert c.activo is True
        assert c.descripcion == ''
        assert c.fecha_creacion is not None
        assert str(c) == 'Inteligencia Artificial'

    def test_slug_y_nombre_unicos(self, db):
        CategoriaSolucion.objects.create(nombre='Uno', slug='uno-test')
        with pytest.raises(IntegrityError), transaction.atomic():
            CategoriaSolucion.objects.create(nombre='Uno', slug='otro-slug')
        with pytest.raises(IntegrityError), transaction.atomic():
            CategoriaSolucion.objects.create(nombre='Otro nombre', slug='uno-test')

    def test_ordenado_por_nombre(self, db):
        CategoriaSolucion.objects.create(nombre='ZZZ Cat', slug='zzz-cat')
        CategoriaSolucion.objects.create(nombre='AAA Cat', slug='aaa-cat')
        nombres = list(CategoriaSolucion.objects.filter(
            slug__in=['zzz-cat', 'aaa-cat']).values_list('nombre', flat=True))
        assert nombres == ['AAA Cat', 'ZZZ Cat']


class TestSincronizacionCategoriaTipo:
    def test_categoria_asigna_tipo_solucion(self, empresa):
        c = CategoriaSolucion.objects.create(nombre='Blockchain', slug='blockchain-test')
        p = _proyecto(empresa, categoria=c)
        p.refresh_from_db()
        assert p.tipo_solucion == 'blockchain-test'
        assert p.categoria == c

    def test_tipo_solucion_asigna_categoria_existente(self, empresa):
        c = _categoria('sitio_web', 'Sitio Web')
        p = _proyecto(empresa, tipo_solucion='sitio_web')
        p.refresh_from_db()
        assert p.categoria_id == c.pk

    def test_tipo_solucion_sin_categoria_existente(self, empresa):
        CategoriaSolucion.objects.filter(slug='otro').delete()
        p = _proyecto(empresa, tipo_solucion='otro')
        p.refresh_from_db()
        assert p.categoria is None
        assert p.tipo_solucion == 'otro'

    def test_ambos_definidos_no_se_sobrescriben(self, empresa):
        c = CategoriaSolucion.objects.create(nombre='Cat X', slug='cat-x')
        p = _proyecto(empresa, categoria=c, tipo_solucion='otro')
        p.refresh_from_db()
        assert p.categoria == c
        assert p.tipo_solucion == 'otro'

    def test_eliminar_categoria_deja_proyecto(self, empresa):
        c = CategoriaSolucion.objects.create(nombre='Temp', slug='temp-cat')
        p = _proyecto(empresa, categoria=c)
        c.delete()
        p.refresh_from_db()
        assert p.categoria is None


class TestGetTipoSolucionDisplay:
    def test_display_con_categoria(self, empresa):
        c = CategoriaSolucion.objects.create(nombre='Realidad Virtual', slug='vr-test')
        p = _proyecto(empresa, categoria=c)
        assert p.get_tipo_solucion_display() == 'Realidad Virtual'

    def test_display_legacy_con_categoria_sembrada(self, empresa):
        _categoria('aplicacion_movil', 'Aplicación Móvil')
        p = _proyecto(empresa, tipo_solucion='aplicacion_movil')
        assert p.get_tipo_solucion_display() == 'Aplicación Móvil'

    def test_display_busca_por_slug_sin_fk(self, empresa):
        CategoriaSolucion.objects.filter(slug='automatizacion').delete()
        p = _proyecto(empresa, tipo_solucion='automatizacion')
        assert p.categoria is None
        CategoriaSolucion.objects.create(nombre='Automatización Pro', slug='automatizacion')
        assert p.get_tipo_solucion_display() == 'Automatización Pro'

    def test_display_fallback_legacy_dict(self, empresa):
        CategoriaSolucion.objects.filter(slug='sistema_escritorio').delete()
        p = _proyecto(empresa, tipo_solucion='sistema_escritorio')
        assert p.categoria is None
        assert p.get_tipo_solucion_display() == 'Sistema de Escritorio'

    def test_display_fallback_slug_desconocido(self, empresa):
        p = _proyecto(empresa, tipo_solucion='desconocido')
        assert p.get_tipo_solucion_display() == 'desconocido'


# ---------------------------------------------------------------------------
# API administrativa y consumo dinámico
# ---------------------------------------------------------------------------
import json

from django.core.cache import cache
from django.urls import reverse

from logs.models import LogAuditoria


@pytest.fixture(autouse=True)
def _limpiar_cache_ratelimit():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def admin_client(db, client):
    admin = User.objects.create_user(
        username='cat_admin', email='catadmin@test.jobdevs',
        nombre='Cat Admin', rol='administrador', estado='activo',
        password='TestPass123!',
    )
    client.force_login(admin)
    client.admin_user = admin
    return client


def _json(client, method, url, data=None):
    return getattr(client, method)(
        url, data=json.dumps(data or {}), content_type='application/json',
    )


def test_api_categorias_listar_admin_success(admin_client, empresa):
    c = CategoriaSolucion.objects.create(nombre='Zeta API', slug='zeta-api')
    _proyecto(empresa, categoria=c)
    response = admin_client.get(reverse('api_categorias_listar'))
    assert response.status_code == 200
    data = response.json()
    item = next(i for i in data if i['slug'] == 'zeta-api')
    assert item == {
        'id': c.id, 'nombre': 'Zeta API', 'slug': 'zeta-api',
        'descripcion': '', 'activo': True, 'proyectos_count': 1,
    }
    nombres = [i['nombre'] for i in data]
    assert nombres == sorted(nombres)


def test_api_categorias_listar_non_admin_forbidden(client, empresa):
    client.force_login(empresa)
    assert client.get(reverse('api_categorias_listar')).status_code == 403
    assert _json(client, 'post', reverse('api_categoria_crear'), {'nombre': 'X'}).status_code == 403
    assert not CategoriaSolucion.objects.filter(nombre='X').exists()


def test_api_categoria_crear_success(admin_client):
    response = _json(admin_client, 'post', reverse('api_categoria_crear'), {
        'nombre': 'Inteligencia Artificial', 'descripcion': 'IA y ML',
    })
    assert response.status_code == 201
    body = response.json()
    assert body['slug'] == 'inteligencia-artificial'
    assert body['activo'] is True
    categoria = CategoriaSolucion.objects.get(pk=body['id'])
    assert categoria.descripcion == 'IA y ML'
    assert LogAuditoria.objects.filter(
        usuario=admin_client.admin_user, tabla_afectada='categorias_solucion',
        registro_id=categoria.id,
    ).exists()


def test_api_categoria_crear_requeridos_y_slug_explicito(admin_client):
    url = reverse('api_categoria_crear')
    assert _json(admin_client, 'post', url, {'nombre': '  '}).status_code == 400
    response = _json(admin_client, 'post', url, {'nombre': 'Con Slug', 'slug': 'mi-slug', 'activo': False})
    assert response.status_code == 201
    assert response.json()['slug'] == 'mi-slug'
    assert response.json()['activo'] is False


def test_api_categoria_crear_duplicate_name_conflict(admin_client):
    CategoriaSolucion.objects.create(nombre='Duplicada', slug='duplicada')
    url = reverse('api_categoria_crear')
    assert _json(admin_client, 'post', url, {'nombre': 'Duplicada'}).status_code == 409
    assert _json(admin_client, 'post', url, {'nombre': 'Otra', 'slug': 'duplicada'}).status_code == 409
    assert CategoriaSolucion.objects.filter(nombre__in=['Duplicada', 'Otra']).count() == 1


def test_api_categoria_actualizar_success(admin_client):
    c = CategoriaSolucion.objects.create(nombre='Vieja', slug='vieja-cat')
    response = _json(admin_client, 'put', reverse('api_categoria_actualizar', args=[c.id]), {
        'nombre': 'Nueva', 'descripcion': 'Desc', 'activo': False,
    })
    assert response.status_code == 200
    c.refresh_from_db()
    assert (c.nombre, c.descripcion, c.activo, c.slug) == ('Nueva', 'Desc', False, 'vieja-cat')
    assert LogAuditoria.objects.filter(
        tabla_afectada='categorias_solucion', registro_id=c.id, accion__contains='Actualizó',
    ).exists()


def test_api_categoria_actualizar_nombre_duplicado(admin_client):
    CategoriaSolucion.objects.create(nombre='Existente', slug='existente')
    c = CategoriaSolucion.objects.create(nombre='Propia', slug='propia')
    response = _json(admin_client, 'put', reverse('api_categoria_actualizar', args=[c.id]), {'nombre': 'Existente'})
    assert response.status_code == 409


def test_api_categoria_toggle_success(admin_client):
    c = CategoriaSolucion.objects.create(nombre='Toggle', slug='toggle-cat')
    url = reverse('api_categoria_toggle', args=[c.id])
    response = admin_client.post(url)
    assert response.status_code == 200
    assert response.json()['activo'] is False
    c.refresh_from_db()
    assert c.activo is False
    assert admin_client.post(url).json()['activo'] is True
    assert LogAuditoria.objects.filter(
        tabla_afectada='categorias_solucion', registro_id=c.id,
    ).count() == 2
    assert admin_client.get(url).status_code == 405


def test_consumo_dinamico_en_vistas_crear_y_listar(client, empresa):
    activa = CategoriaSolucion.objects.create(nombre='Cat Dinámica', slug='cat-dinamica')
    inactiva = CategoriaSolucion.objects.create(nombre='Cat Inactiva', slug='cat-inactiva', activo=False)
    client.force_login(empresa)

    response = client.post(reverse('crear_proyecto'), {
        'titulo': 'Proyecto Dinámico', 'descripcion': 'Desc',
        'tipo_solucion': 'cat-dinamica', 'prioridad': 'media', 'vacantes': 1,
    })
    assert response.status_code == 302
    proyecto = Proyecto.objects.get(titulo='Proyecto Dinámico')
    assert proyecto.categoria == activa
    assert proyecto.tipo_solucion == 'cat-dinamica'

    client.post(reverse('crear_proyecto'), {
        'titulo': 'Proyecto Inactivo', 'descripcion': 'Desc',
        'tipo_solucion': 'cat-inactiva', 'prioridad': 'media', 'vacantes': 1,
    })
    assert not Proyecto.objects.filter(titulo='Proyecto Inactivo').exists()

    response = client.get(reverse('listar_proyectos'))
    assert response.status_code == 200
    categorias = list(response.context['categorias_solucion'])
    assert activa in categorias and inactiva not in categorias
    assert 'value="cat-dinamica"' in response.content.decode()

    response = client.get(reverse('editar_proyecto', args=[proyecto.id]))
    assert response.status_code == 200
    assert activa in list(response.context['categorias_solucion'])
    assert 'value="cat-dinamica" selected' in response.content.decode()
