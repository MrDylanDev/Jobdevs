import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from logs.models import LogAuditoria
from mensajes.models import Mensaje
from proyectos.models import Proyecto

User = get_user_model()
URL_NAME = 'admin_auditar_mensajes'


def _user(username, nombre, rol='desarrollador'):
    return User.objects.create_user(
        username=username, email=f'{username}@test.jobdevs', nombre=nombre,
        rol=rol, estado='activo', password='TestPass123!',
    )


@pytest.fixture
def escenario(db, empresa_user, desarrollador_user):
    ana = _user('ana_dev', 'Ana Gomez')
    beto = _user('beto_dev', 'Beto Ruiz')
    proyecto = Proyecto.objects.create(
        empresa=empresa_user, titulo='Portal Alfa', descripcion='d',
        tipo_solucion='sitio_web',
    )
    otro = Proyecto.objects.create(
        empresa=empresa_user, titulo='App Omega', descripcion='d',
        tipo_solucion='otro',
    )
    privado = Mensaje.objects.create(
        remitente=ana, receptor=beto, titulo='Saludo', contenido='hola secreto uno',
    )
    grupal = Mensaje.objects.create(
        remitente=beto, receptor=None, proyecto=proyecto,
        contenido='aviso grupal del equipo',
    )
    otro_msg = Mensaje.objects.create(
        remitente=empresa_user, receptor=ana, proyecto=otro,
        contenido='reunion mañana',
    )
    return {
        'ana': ana, 'beto': beto, 'proyecto': proyecto, 'otro': otro,
        'privado': privado, 'grupal': grupal, 'otro_msg': otro_msg,
    }


def _get_json(client, **params):
    params['format'] = 'json'
    return client.get(reverse(URL_NAME), params)


def _ids(response):
    return {m['id'] for m in response.json()['mensajes']}


class TestAccesoAuditoriaChats:
    def test_anonimo_redirigido_a_login(self, client, escenario):
        resp = client.get(reverse(URL_NAME))
        assert resp.status_code == 302
        assert 'login' in resp.url

    def test_desarrollador_recibe_403(self, dev_client, escenario):
        assert dev_client.get(reverse(URL_NAME)).status_code == 403
        assert _get_json(dev_client).status_code == 403

    def test_empresa_recibe_403(self, auth_client, escenario):
        assert auth_client.get(reverse(URL_NAME)).status_code == 403
        assert _get_json(auth_client).status_code == 403

    def test_no_admin_no_genera_log(self, dev_client, escenario):
        _get_json(dev_client)
        assert not LogAuditoria.objects.filter(tabla_afectada='mensajes').exists()


class TestListadoAuditoriaChats:
    def test_admin_lista_todos(self, admin_client, escenario):
        resp = _get_json(admin_client)
        assert resp.status_code == 200
        assert _ids(resp) == {
            escenario['privado'].id, escenario['grupal'].id, escenario['otro_msg'].id,
        }

    def test_accept_header_json(self, admin_client, escenario):
        resp = admin_client.get(reverse(URL_NAME), HTTP_ACCEPT='application/json')
        assert resp.status_code == 200
        assert resp['Content-Type'].startswith('application/json')

    def test_respuesta_html_por_defecto(self, admin_client, escenario):
        resp = admin_client.get(reverse(URL_NAME))
        assert resp.status_code == 200
        assert 'text/html' in resp['Content-Type']
        assert 'Grupal de Proyecto' in resp.content.decode()

    def test_campos_serializados(self, admin_client, escenario):
        resp = _get_json(admin_client, remitente='ana_dev')
        m = next(x for x in resp.json()['mensajes'] if x['id'] == escenario['privado'].id)
        assert m['remitente_username'] == 'ana_dev'
        assert m['remitente_nombre'] == 'Ana Gomez'
        assert m['receptor_username'] == 'beto_dev'
        assert m['receptor_nombre'] == 'Beto Ruiz'
        assert m['proyecto_titulo'] is None
        assert m['titulo'] == 'Saludo'
        assert m['contenido'] == 'hola secreto uno'
        assert m['es_grupal'] is False
        assert m['fecha_envio']

    def test_paginacion_25_por_pagina(self, admin_client, escenario):
        for i in range(30):
            Mensaje.objects.create(
                remitente=escenario['ana'], receptor=escenario['beto'], contenido=f'bulk {i}',
            )
        r1 = _get_json(admin_client).json()
        assert len(r1['mensajes']) == 25
        assert r1['total'] == 33 and r1['total_paginas'] == 2
        r2 = _get_json(admin_client, page=2).json()
        assert len(r2['mensajes']) == 8

    def test_fecha_filtros(self, admin_client, escenario):
        assert len(_ids(_get_json(admin_client, fecha_desde='2999-01-01'))) == 0
        assert len(_ids(_get_json(admin_client, fecha_hasta='2000-01-01'))) == 0
        assert len(_ids(_get_json(admin_client, fecha_desde='2000-01-01', fecha_hasta='2999-01-01'))) == 3
        # fecha inválida se ignora
        assert len(_ids(_get_json(admin_client, fecha_desde='basura'))) == 3


class TestFiltrosAuditoriaChats:
    def test_filtro_remitente_username_y_nombre(self, admin_client, escenario):
        assert _ids(_get_json(admin_client, remitente='ana_dev')) == {escenario['privado'].id}
        assert _ids(_get_json(admin_client, remitente='Beto')) == {escenario['grupal'].id}

    def test_filtro_receptor(self, admin_client, escenario):
        assert _ids(_get_json(admin_client, receptor='beto_dev')) == {escenario['privado'].id}
        assert _ids(_get_json(admin_client, receptor='Ana Gomez')) == {escenario['otro_msg'].id}

    def test_filtro_proyecto_por_titulo_e_id(self, admin_client, escenario):
        assert _ids(_get_json(admin_client, proyecto='Alfa')) == {escenario['grupal'].id}
        assert _ids(_get_json(admin_client, proyecto=str(escenario['otro'].id))) == {escenario['otro_msg'].id}

    def test_filtro_texto_contenido_y_titulo(self, admin_client, escenario):
        assert _ids(_get_json(admin_client, q='secreto')) == {escenario['privado'].id}
        assert _ids(_get_json(admin_client, q='Saludo')) == {escenario['privado'].id}

    def test_filtros_combinados(self, admin_client, escenario):
        assert _ids(_get_json(admin_client, remitente='ana', receptor='beto', q='secreto')) == {escenario['privado'].id}
        assert _ids(_get_json(admin_client, remitente='ana', q='grupal')) == set()


class TestMensajesGrupalesAuditoria:
    def test_grupal_marcado_y_sin_receptor(self, admin_client, escenario):
        resp = _get_json(admin_client, proyecto='Portal Alfa')
        data = resp.json()['mensajes']
        assert len(data) == 1
        m = data[0]
        assert m['es_grupal'] is True
        assert m['receptor_username'] is None and m['receptor_nombre'] is None
        assert m['proyecto_titulo'] == 'Portal Alfa'

    def test_grupal_visible_en_html(self, admin_client, escenario):
        html = admin_client.get(reverse(URL_NAME), {'proyecto': 'Alfa'}).content.decode()
        assert 'Grupal de Proyecto' in html
        assert 'Portal Alfa' in html


class TestLogAuditoriaChats:
    def test_cada_consulta_genera_log(self, admin_client, admin_user, escenario):
        _get_json(admin_client)
        _get_json(admin_client, remitente='ana')
        admin_client.get(reverse(URL_NAME))
        logs = LogAuditoria.objects.filter(tabla_afectada='mensajes', usuario=admin_user)
        assert logs.count() == 3

    def test_log_incluye_filtros(self, admin_client, admin_user, escenario):
        _get_json(admin_client, remitente='ana', q='hola')
        log = LogAuditoria.objects.filter(tabla_afectada='mensajes').latest('id')
        assert log.accion.startswith('Auditoría de mensajes: consultó conversaciones con filtros [')
        assert 'remitente=ana' in log.accion and 'q=hola' in log.accion

    def test_log_sin_filtros(self, admin_client, escenario):
        _get_json(admin_client)
        log = LogAuditoria.objects.filter(tabla_afectada='mensajes').latest('id')
        assert 'sin filtros' in log.accion

    def test_log_truncado_a_300(self, admin_client, escenario):
        resp = _get_json(admin_client, q='x' * 500)
        assert resp.status_code == 200
        log = LogAuditoria.objects.filter(tabla_afectada='mensajes').latest('id')
        assert len(log.accion) <= 300
