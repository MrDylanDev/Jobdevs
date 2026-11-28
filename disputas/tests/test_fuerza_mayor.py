"""Fuerza mayor solicita revisión, sin imputar incumplimiento ni sancionar."""
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.urls import reverse

from contrataciones.models import Contratacion, SolicitudCancelacion
from disputas.models import Disputa
from disputas.tests import test_apertura_disputa

escenario = test_apertura_disputa.escenario


PAYLOAD = {
    'categoria': 'fuerza_mayor',
    'motivo': (
        'Una emergencia médica sobrevenida impide continuar temporalmente el trabajo. '
        'Intentamos acordar una salida por chat, pero no hubo acuerdo ni respuesta.'
    ),
    'confirma_intento_previo': '1',
    'acepta_sanciones': '1',  # Aceptación de reglas, no declaración de culpa.
    'declara_evidencia_no_disponible': '1',
}


def abrir(client, caso, rol):
    client.force_login(caso[rol])
    return client.post(
        reverse('disputas:abrir_disputa', args=[caso['proyecto'].pk]),
        PAYLOAD, HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )


def comprobar_sin_sanciones(caso):
    for rol in ('empresa', 'dev'):
        caso[rol].refresh_from_db()
        assert caso[rol].estado == 'activo'
        assert caso[rol].is_active


def test_fuerza_mayor_exige_evidencia_o_declaracion_de_indisponibilidad(
        client, escenario):
    client.force_login(escenario['dev'])
    payload_sin_evidencia = {
        clave: valor for clave, valor in PAYLOAD.items()
        if clave != 'declara_evidencia_no_disponible'
    }

    response = client.post(
        reverse('disputas:abrir_disputa', args=[escenario['proyecto'].pk]),
        payload_sin_evidencia,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 400
    assert not Disputa.objects.exists()
    escenario['contratacion'].refresh_from_db()
    assert escenario['contratacion'].estado == 'activa'


@pytest.mark.parametrize('rol', ['empresa', 'dev'])
def test_fuerza_mayor_http_congela_reserva_cupo_hasta_fallo_sin_sancion(client, escenario, rol):
    response = abrir(client, escenario, rol)
    assert response.status_code == 200
    assert response.json()['ok'] is True
    disputa = Disputa.objects.get()
    assert disputa.categoria == 'fuerza_mayor'
    assert disputa.iniciado_por == escenario[rol]
    assert disputa.estado == 'abierta'
    assert disputa.resolucion is None
    disputa.full_clean()
    escenario['proyecto'].refresh_from_db()
    escenario['contratacion'].refresh_from_db()
    assert escenario['proyecto'].estado == 'en_disputa'
    assert escenario['contratacion'].estado == 'en_disputa'
    assert Contratacion.objects.filter(
        proyecto=escenario['proyecto'], estado__in=['activa', 'en_disputa'],
    ).count() == escenario['proyecto'].vacantes
    comprobar_sin_sanciones(escenario)

    client.force_login(escenario['admin'])
    response = client.post(reverse('disputas:resolver_disputa', args=[disputa.pk]), {
        'resolucion': 'cancelar_contrato',
        'dictamen': 'Se acredita fuerza mayor. Se cancela sin atribución de incumplimiento.',
    })
    assert response.status_code == 302
    disputa.refresh_from_db()
    escenario['proyecto'].refresh_from_db()
    escenario['contratacion'].refresh_from_db()
    assert disputa.estado == 'resuelta'
    assert disputa.resolucion == 'cancelar_contrato'
    assert disputa.mediador == escenario['admin']
    assert escenario['contratacion'].estado == 'cancelada'
    assert escenario['proyecto'].estado == 'publicado'
    assert not Contratacion.objects.filter(
        proyecto=escenario['proyecto'], estado__in=['activa', 'en_disputa'],
    ).exists()
    comprobar_sin_sanciones(escenario)


@pytest.mark.parametrize('rol', ['empresa', 'dev'])
def test_formulario_fuerza_mayor_no_exige_declarar_conflicto_grave(client, escenario, rol):
    client.force_login(escenario[rol])
    response = client.get(
        reverse('disputas:abrir_disputa', args=[escenario['proyecto'].pk]),
        {'categoria': 'fuerza_mayor', 'contratacion_id': escenario['contratacion'].pk},
    )
    content = response.content.decode()
    assert '<option value="fuerza_mayor" selected>' in content
    assert response.context['categoria'] == 'fuerza_mayor'
    assert 'no implica incumplimiento ni sanción automática' in content
    assert 'disputas/script/abrir_disputa.js' in content
    js_path = Path(settings.BASE_DIR) / 'static' / 'disputas' / 'script' / 'abrir_disputa.js'
    assert js_path.exists(), 'Debe existir el script externo de apertura de disputa'
    js_content = js_path.read_text(encoding='utf-8')
    assert "gravedad.required = !esFuerzaMayor" in js_content
    assert "gravedad.disabled = esFuerzaMayor" in js_content
    assert "gravedad.closest('label').style.display = esFuerzaMayor ? 'none' : ''" in js_content


@pytest.mark.parametrize('campo', ['confirma_intento_previo', 'acepta_sanciones'])
def test_fuerza_mayor_mantiene_intento_previo_y_reglas(client, escenario, campo):
    client.force_login(escenario['dev'])
    payload = {k: v for k, v in PAYLOAD.items() if k != campo}
    response = client.post(
        reverse('disputas:abrir_disputa', args=[escenario['proyecto'].pk]),
        payload, HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )
    assert response.status_code == 400
    assert response.json()['ok'] is False
    assert not Disputa.objects.exists()
    escenario['contratacion'].refresh_from_db()
    assert escenario['contratacion'].estado == 'activa'


def test_fallo_administrativo_fallido_no_cancela_ni_sanciona(client, escenario):
    assert abrir(client, escenario, 'dev').status_code == 200
    disputa = Disputa.objects.get()
    client.force_login(escenario['admin'])
    with patch('disputas.services.LogAuditoria.objects.create', side_effect=RuntimeError('fallo auditoría')):
        with pytest.raises(RuntimeError, match='fallo auditoría'):
            client.post(reverse('disputas:resolver_disputa', args=[disputa.pk]), {
                'resolucion': 'cancelar_contrato', 'dictamen': 'Se acepta fuerza mayor sin sanción.',
            })
    disputa.refresh_from_db()
    escenario['contratacion'].refresh_from_db()
    escenario['proyecto'].refresh_from_db()
    assert disputa.estado == 'abierta'
    assert disputa.resolucion is None
    assert disputa.mediador is None
    assert escenario['contratacion'].estado == 'en_disputa'
    assert escenario['proyecto'].estado == 'en_disputa'
    comprobar_sin_sanciones(escenario)


@pytest.mark.parametrize('rol,categoria,default', [
    ('empresa', 'bloqueo_insumos', 'incumplimiento_contractual'),
    ('dev', 'entrega_defectuosa', 'retencion_fondos'),
    ('dev', 'inexistente', 'retencion_fondos'),
])
def test_preseleccion_ignora_categoria_invalida_para_rol(client, escenario, rol, categoria, default):
    client.force_login(escenario[rol])
    response = client.get(
        reverse('disputas:abrir_disputa', args=[escenario['proyecto'].pk]),
        {'categoria': categoria},
    )
    assert response.context['categoria'] == default


@pytest.mark.parametrize('rol', ['empresa', 'dev'])
def test_sin_respuesta_sustituye_solicitud_y_conserva_historial(client, escenario, rol):
    solicitud = SolicitudCancelacion.objects.create(
        contratacion=escenario['contratacion'], solicitante=escenario['empresa'],
        causal='fuerza_mayor', motivo=PAYLOAD['motivo'], evidencia='Aviso previo por chat.',
        estado='pendiente_acuerdo',
    )
    assert abrir(client, escenario, rol).status_code == 200
    solicitud.refresh_from_db()
    disputa = Disputa.objects.get()
    assert solicitud.estado == 'rechazada'
    assert solicitud.dictamen == f'Sustituida por la disputa #{disputa.pk}.'
    assert solicitud.fecha_resolucion is not None
    assert solicitud.motivo == PAYLOAD['motivo']
    assert solicitud.evidencia == 'Aviso previo por chat.'
    comprobar_sin_sanciones(escenario)


@pytest.mark.parametrize('rol', ['empresa', 'dev'])
def test_preseleccion_ajax_respeta_rol_y_contrato(client, escenario, rol):
    client.force_login(escenario[rol])
    url = reverse('disputas:abrir_disputa', args=[escenario['proyecto'].pk])
    response = client.get(url, {
        'categoria': 'fuerza_mayor', 'contratacion_id': escenario['contratacion'].pk,
    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    data = response.json()
    assert data['categoria'] == 'fuerza_mayor'
    assert data['url_abrir'] == f"{url}?contratacion_id={escenario['contratacion'].pk}"
    assert {c['codigo'] for c in data['categorias']} == {
        codigo for codigo, _ in (
            Disputa.CATEGORIAS_EMPRESA if rol == 'empresa' else Disputa.CATEGORIAS_DESARROLLADOR
        )
    }
