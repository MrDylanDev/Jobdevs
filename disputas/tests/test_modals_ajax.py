import json
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from contrataciones.models import Contratacion, ContratoDigital
from disputas.models import Disputa
from postulaciones.models import Postulacion
from proyectos.models import Proyecto
from usuarios.models import Usuario


@pytest.mark.django_db
def test_detalle_disputa_json_incluye_resoluciones_validas_para_admin(client):
    """SCRUM-471: El JSON de detalle de disputa expone las resoluciones reales del modelo Disputa."""
    empresa = Usuario.objects.create_user(
        username='emp_471', email='emp_471@test.com', password='Password123!',
        rol='empresa', estado='activo',
    )
    dev = Usuario.objects.create_user(
        username='dev_471', email='dev_471@test.com', password='Password123!',
        rol='desarrollador', estado='activo',
    )
    admin = Usuario.objects.create_user(
        username='adm_471', email='adm_471@test.com', password='Password123!',
        rol='administrador', estado='activo',
    )
    proyecto = Proyecto.objects.create(
        titulo='Proyecto 471', descripcion='Desc', empresa=empresa,
        estado='en_disputa',
    )
    contratacion = Contratacion.objects.create(
        proyecto=proyecto, empresa=empresa, desarrollador=dev, estado='activa',
    )
    disputa = Disputa.objects.create(
        proyecto=proyecto, contratacion=contratacion, iniciado_por=dev,
        categoria='retencion_fondos', motivo='Motivo de prueba suficientemente largo ' * 3,
        estado='abierta',
    )

    client.force_login(admin)
    resp = client.get(
        reverse('disputas:detalle_disputa', args=[disputa.id]),
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['ok'] is True
    codigos = [r['codigo'] for r in data['disputa']['resoluciones']]
    assert codigos == [r[0] for r in Disputa.RESOLUCION]


def test_dashboard_modals_js_no_contiene_resoluciones_invalidas():
    """SCRUM-471: El script de modales no debe contener los valores inválidos de resolución."""
    script_dir = Path(settings.BASE_DIR) / 'static/dashboard/script'
    js_files = [script_dir / 'dashboard_modals.js', *sorted((script_dir / 'modules').glob('*.js'))]
    js_text = '\n'.join(p.read_text(encoding='utf-8') for p in js_files)
    assert js_text.strip()
    for invalido in ('favor_empresa', 'favor_desarrollador', 'acuerdo_mutuo', 'cancelacion_sin_sancion'):
        assert invalido not in js_text


@pytest.mark.django_db
def test_abrir_disputa_ajax_categoria_invalida_retorna_json_400(client):
    """SCRUM-470: Un POST AJAX con categoría inválida para el rol devuelve JSON 400, no HTML."""
    empresa = Usuario.objects.create_user(
        username='emp_470', email='emp_470@test.com', password='Password123!',
        rol='empresa', estado='activo',
    )
    dev = Usuario.objects.create_user(
        username='dev_470', email='dev_470@test.com', password='Password123!',
        rol='desarrollador', estado='activo',
    )
    proyecto = Proyecto.objects.create(
        titulo='Proyecto 470', descripcion='Desc', empresa=empresa,
        estado='en_desarrollo',
    )
    Contratacion.objects.create(
        proyecto=proyecto, empresa=empresa, desarrollador=dev, estado='activa',
    )

    client.force_login(dev)
    resp = client.post(
        reverse('disputas:abrir_disputa', args=[proyecto.id]),
        data={
            'categoria': 'entrega_defectuosa',  # exclusiva de empresa
            'motivo': 'Motivo de prueba suficientemente largo ' * 3,
            'origen': 'dashboard',
        },
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )
    assert resp.status_code == 400
    assert resp['Content-Type'].startswith('application/json')
    data = resp.json()
    assert data['ok'] is False
    assert 'mensaje' in data


@pytest.mark.django_db
def test_ver_contrato_digital_ajax_retorna_estructura_compatible_con_modal(client):
    """SCRUM-465: El GET AJAX del contrato digital retorna ok=True, contrato y clausulas en lista."""
    empresa = Usuario.objects.create_user(
        username='emp_465', email='emp_465@test.com', password='Password123!',
        rol='empresa', estado='activo',
    )
    dev = Usuario.objects.create_user(
        username='dev_465', email='dev_465@test.com', password='Password123!',
        rol='desarrollador', estado='activo',
    )
    proyecto = Proyecto.objects.create(
        titulo='Proyecto 465', descripcion='Desc', empresa=empresa,
        estado='publicado',
    )
    postulacion = Postulacion.objects.create(
        proyecto=proyecto, desarrollador=dev, estado='en_negociacion',
    )
    contrato = ContratoDigital.objects.create(
        postulacion=postulacion,
        monto=Decimal('1000000.00'),
        clausulas='1. Primera cláusula.\n2. Segunda cláusula.',
        estado='pendiente_firma',
    )

    client.force_login(dev)
    resp = client.get(
        reverse('ver_contrato_digital', args=[contrato.id]),
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['ok'] is True
    assert isinstance(data['contrato'], dict)
    assert data['contrato']['id'] == contrato.id
    assert isinstance(data['contrato']['clausulas'], list)
    assert len(data['contrato']['clausulas']) == 2


@pytest.mark.django_db
def test_abrir_disputa_htmx_get_retorna_partial_modal(client):
    """S5: GET con HX-Request devuelve el partial _modal_abrir_disputa.html."""
    empresa = Usuario.objects.create_user(
        username='emp_s5_get', email='emp_s5_get@test.com', password='Password123!',
        rol='empresa', estado='activo',
    )
    dev = Usuario.objects.create_user(
        username='dev_s5_get', email='dev_s5_get@test.com', password='Password123!',
        rol='desarrollador', estado='activo',
    )
    proyecto = Proyecto.objects.create(
        titulo='Proyecto <script>alert(1)</script>', descripcion='Desc', empresa=empresa,
        estado='en_desarrollo',
    )
    Contratacion.objects.create(
        proyecto=proyecto, empresa=empresa, desarrollador=dev, estado='activa',
    )

    client.force_login(empresa)
    resp = client.get(
        reverse('disputas:abrir_disputa', args=[proyecto.id]),
        HTTP_HX_REQUEST='true',
    )
    assert resp.status_code == 200
    html = resp.content.decode('utf-8')
    assert '<!DOCTYPE html>' not in html
    assert 'id="form-disputa"' in html
    assert 'hx-post=' in html
    assert 'hx-target="#modalDisputaBody"' in html
    assert 'id="char-count"' in html
    assert 'id="confirma_intento_previo"' in html


@pytest.mark.django_db
def test_abrir_disputa_htmx_post_error_rerenderiza_partial(client):
    """S5: POST HTMX con error de validación re-renderiza el partial con mensaje de error."""
    empresa = Usuario.objects.create_user(
        username='emp_s5_err', email='emp_s5_err@test.com', password='Password123!',
        rol='empresa', estado='activo',
    )
    dev = Usuario.objects.create_user(
        username='dev_s5_err', email='dev_s5_err@test.com', password='Password123!',
        rol='desarrollador', estado='activo',
    )
    proyecto = Proyecto.objects.create(
        titulo='Proyecto S5 Error', descripcion='Desc', empresa=empresa,
        estado='en_desarrollo',
    )
    Contratacion.objects.create(
        proyecto=proyecto, empresa=empresa, desarrollador=dev, estado='activa',
    )

    client.force_login(empresa)
    resp = client.post(
        reverse('disputas:abrir_disputa', args=[proyecto.id]),
        data={'categoria': 'incumplimiento_contractual', 'motivo': ''},
        HTTP_HX_REQUEST='true',
    )
    assert resp.status_code == 200
    html = resp.content.decode('utf-8')
    assert '<!DOCTYPE html>' not in html
    assert 'id="form-disputa"' in html
    assert 'Debes indicar el motivo de la disputa.' in html
    assert not Disputa.objects.filter(proyecto=proyecto).exists()


@pytest.mark.django_db
def test_abrir_disputa_htmx_post_exito_retorna_hx_trigger(client):
    """S5: POST HTMX exitoso crea la disputa y retorna 200 con HX-Trigger."""
    empresa = Usuario.objects.create_user(
        username='emp_s5_ok', email='emp_s5_ok@test.com', password='Password123!',
        rol='empresa', estado='activo',
    )
    dev = Usuario.objects.create_user(
        username='dev_s5_ok', email='dev_s5_ok@test.com', password='Password123!',
        rol='desarrollador', estado='activo',
    )
    proyecto = Proyecto.objects.create(
        titulo='Proyecto S5 Exito', descripcion='Desc', empresa=empresa,
        estado='en_desarrollo',
    )
    Contratacion.objects.create(
        proyecto=proyecto, empresa=empresa, desarrollador=dev, estado='activa',
    )

    client.force_login(empresa)
    motivo_valido = (
        'El desarrollador incumplió los hitos pactados el día 10 de enero y no respondió '
        'los mensajes de seguimiento enviados durante dos semanas consecutivas.'
    )
    resp = client.post(
        reverse('disputas:abrir_disputa', args=[proyecto.id]),
        data={
            'categoria': 'incumplimiento_contractual',
            'motivo': motivo_valido,
            'evidencia_url': 'https://github.com/org/repo/issues/1',
            'confirma_intento_previo': '1',
            'confirma_gravedad': '1',
            'acepta_sanciones': '1',
        },
        HTTP_HX_REQUEST='true',
    )
    assert resp.status_code == 200
    assert Disputa.objects.filter(proyecto=proyecto).exists()
    assert 'HX-Trigger' in resp
    triggers = json.loads(resp['HX-Trigger'])
    assert 'jobdevs:toast' in triggers
    assert triggers['jobdevs:toast']['tipo'] == 'success'
    assert 'jobdevs:disputa-creada' in triggers


@pytest.mark.django_db
def test_abrir_disputa_htmx_con_accept_json_preserva_json(client):
    """S5: Accept: application/json preserva el contrato JSON incluso con HX-Request."""
    empresa = Usuario.objects.create_user(
        username='emp_s5_json', email='emp_s5_json@test.com', password='Password123!',
        rol='empresa', estado='activo',
    )
    dev = Usuario.objects.create_user(
        username='dev_s5_json', email='dev_s5_json@test.com', password='Password123!',
        rol='desarrollador', estado='activo',
    )
    proyecto = Proyecto.objects.create(
        titulo='Proyecto S5 JSON', descripcion='Desc', empresa=empresa,
        estado='en_desarrollo',
    )
    Contratacion.objects.create(
        proyecto=proyecto, empresa=empresa, desarrollador=dev, estado='activa',
    )

    client.force_login(empresa)
    resp = client.get(
        reverse('disputas:abrir_disputa', args=[proyecto.id]),
        HTTP_HX_REQUEST='true',
        HTTP_ACCEPT='application/json',
    )
    assert resp.status_code == 200
    assert resp['Content-Type'].startswith('application/json')
    data = resp.json()
    assert data['ok'] is True
    assert 'categorias' in data

