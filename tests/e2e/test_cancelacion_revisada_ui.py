"""RF 3.4.1: conflicto tramitado por disputa y cupo en el navegador."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from playwright.sync_api import expect

from contrataciones.models import Contratacion, SolicitudCancelacion
from disputas.models import Disputa
from proyectos.models import Proyecto

User = get_user_model()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_conflicto_se_media_y_libera_cupo_solo_tras_fallo(
    page, live_server, login_user
):
    empresa = User.objects.create_user(
        username='cancel_emp', email='cancel_emp@example.com',
        rol='empresa', estado='activo', password='TestPass123!',
    )
    dev = User.objects.create_user(
        username='cancel_dev', email='cancel_dev@example.com',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    admin = User.objects.create_user(
        username='cancel_admin', email='cancel_admin@example.com',
        rol='administrador', estado='activo', password='TestPass123!',
    )
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo='Oferta con cupo reservado', descripcion='Proyecto de prueba',
        tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=1,
    )
    contrato = Contratacion.objects.create(
        empresa=empresa, desarrollador=dev, proyecto=proyecto, estado='activa',
    )
    login_user(empresa)
    page.goto(live_server.url + reverse('solicitudes_cancelacion'))
    page.get_by_role('link', name='Abrir una disputa formal para este contrato').click()
    expect(page.locator('#modalReportarDisputa')).to_be_visible()
    expect(page.locator('#form-disputa')).to_have_attribute(
        'action',
        reverse('disputas:abrir_disputa', args=[proyecto.pk])
        + f'?contratacion_id={contrato.pk}',
    )
    page.locator('#motivo').fill(
        'El hito comprometido venció sin entrega; intentamos acordar una solución por chat, pero no hubo respuesta.',
    )
    page.locator('#form-disputa [name="evidencia_url"]').fill('https://evidencia.test/hito')
    page.locator('#form-disputa [name="confirma_intento_previo"]').check()
    page.locator('#form-disputa [name="confirma_gravedad"]').check()
    page.locator('#form-disputa [name="acepta_sanciones"]').check()
    with page.expect_response(
        lambda response: '/disputas/abrir/' in response.url
        and response.request.method == 'POST'
    ) as enviada:
        page.get_by_role('button', name='Iniciar Mediación Formal').click()
    assert enviada.value.json()['ok'] is True
    disputa = Disputa.objects.get(contratacion=contrato)
    contrato.refresh_from_db()
    proyecto.refresh_from_db()
    assert contrato.estado == 'en_disputa'
    assert proyecto.vacantes_disponibles == 0
    assert proyecto.estado == 'en_disputa'
    assert not SolicitudCancelacion.objects.filter(contratacion=contrato).exists()

    login_user(admin)
    page.goto(live_server.url + reverse('disputas:detalle_disputa', args=[disputa.pk]))
    page.locator('#toggle-resolucion').click()
    page.locator('#resolucion').select_option('cancelar_contrato')
    page.locator('#dictamen').fill('Incumplimiento acreditado tras revisar el historial del hito.')
    page.locator(f'form[action="{reverse("disputas:resolver_disputa", args=[disputa.pk])}"] button[type="submit"]').click()
    confirm_btn = page.locator('#jdmConfirmBtnOk')
    if confirm_btn.is_visible():
        confirm_btn.click()
    else:
        page.once('dialog', lambda dialog: dialog.accept())
    contrato.refresh_from_db()
    proyecto.refresh_from_db()
    disputa.refresh_from_db()
    assert disputa.estado == 'resuelta'
    assert contrato.estado == 'cancelada'
    assert proyecto.vacantes_disponibles == 1
    assert proyecto.estado == 'publicado'


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_fuerza_mayor_sin_respuesta_se_revisa_desde_modal(
    page, live_server, login_user
):
    from contrataciones.services import solicitar_cancelacion

    empresa = User.objects.create_user(
        username='revision_emp', email='revision_emp@example.com',
        rol='empresa', estado='activo', password='TestPass123!',
    )
    dev = User.objects.create_user(
        username='revision_dev', email='revision_dev@example.com',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo='Revisión neutral de emergencia', descripcion='Prueba',
        tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=1,
    )
    contrato = Contratacion.objects.create(
        empresa=empresa, desarrollador=dev, proyecto=proyecto, estado='activa',
    )
    solicitud = solicitar_cancelacion(
        contrato.pk, dev, causal='fuerza_mayor', motivo='Emergencia que impide continuar el contrato.',
    )
    login_user(empresa)
    page.goto(live_server.url + reverse('solicitudes_cancelacion'))
    # El API público del modal usa el mismo endpoint y contrato del enlace.
    url = page.get_by_role('link', name='Solicitar revisión por fuerza mayor').get_attribute('href')
    page.evaluate('(url) => window.JdDashboardModals.abrirFormularioDisputa(url)', url)
    expect(page.locator('#jdmCatDisputa')).to_have_value('fuerza_mayor')
    expect(page.locator('#jdmFormNuevaDisputa [name="confirma_gravedad"]')).to_be_disabled()
    page.locator('#jdmCatDisputa').select_option('incumplimiento_contractual')
    expect(page.locator('#jdmFormNuevaDisputa [name="confirma_gravedad"]')).to_be_enabled()
    expect(page.locator('#jdmFormNuevaDisputa [name="confirma_gravedad"]')).to_have_attribute('required', '')
    page.locator('#jdmCatDisputa').select_option('fuerza_mayor')
    expect(page.locator('#jdmFormNuevaDisputa [name="confirma_gravedad"]')).to_be_disabled()
    page.locator('#jdmMotivoDisputa').fill(
        'Una emergencia sobrevenida impide continuar; intentamos acordar una salida por chat, pero no hubo respuesta.',
    )
    page.locator('#jdmEvidenciaDisputa').fill('https://evidencia.test/fuerza-mayor')
    page.locator('#jdmFormNuevaDisputa [name="confirma_intento_previo"]').check()
    page.locator('#jdmAceptaSanciones').check()
    with page.expect_response(lambda r: '/disputas/abrir/' in r.url and r.request.method == 'POST') as enviada:
        page.locator('#jdmBtnConfirmarDisputa').click()
    assert enviada.value.json()['ok'] is True
    disputa = Disputa.objects.get(contratacion=contrato)
    solicitud.refresh_from_db()
    contrato.refresh_from_db()
    proyecto.refresh_from_db()
    assert disputa.categoria == 'fuerza_mayor'
    assert solicitud.estado == 'rechazada'
    assert contrato.estado == 'en_disputa'
    assert proyecto.vacantes_disponibles == 0
    for actor in (empresa, dev):
        actor.refresh_from_db()
        assert actor.estado == 'activo'


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('inicia_empresa', [True, False])
def test_fuerza_mayor_bilateral_solo_cancela_tras_confirmacion(
    page, live_server, login_user, inicia_empresa
):
    empresa = User.objects.create_user(
        username='fuerza_emp', email='fuerza_emp@example.com',
        rol='empresa', estado='activo', password='TestPass123!',
    )
    dev = User.objects.create_user(
        username='fuerza_dev', email='fuerza_dev@example.com',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo='Terminación por emergencia', descripcion='Proyecto de prueba',
        tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=1,
    )
    contrato = Contratacion.objects.create(
        empresa=empresa, desarrollador=dev, proyecto=proyecto, estado='activa',
    )
    proponente, contraparte = (empresa, dev) if inicia_empresa else (dev, empresa)
    login_user(proponente)
    page.goto(live_server.url + reverse('solicitudes_cancelacion'))
    formulario = page.locator(f'form[action="{reverse("cancelar_contratacion", args=[contrato.pk])}"]')
    formulario.locator('select[name="causal"]').select_option('fuerza_mayor')
    formulario.locator('textarea[name="motivo_cancelacion"]').fill('Una emergencia impide continuar el contrato.')
    formulario.get_by_role('button', name='Proponer acuerdo (no cancela aún)').click()
    expect(page.locator('body')).to_contain_text('Pendiente de confirmación de la contraparte')
    solicitud = SolicitudCancelacion.objects.get(contratacion=contrato)
    contrato.refresh_from_db()
    proyecto.refresh_from_db()
    assert contrato.estado == 'activa'
    assert proyecto.vacantes_disponibles == 0
    assert not Disputa.objects.filter(contratacion=contrato).exists()
    expect(page.get_by_role('button', name='Confirmar acuerdo y finalizar contrato')).to_have_count(0)
    expect(page.get_by_role('link', name='Solicitar revisión por fuerza mayor')).to_be_visible()

    login_user(contraparte)
    page.goto(live_server.url + reverse('solicitudes_cancelacion'))
    page.get_by_role('button', name='Confirmar acuerdo y finalizar contrato').click()
    expect(page.locator('body')).to_contain_text('Aprobada')
    solicitud.refresh_from_db()
    contrato.refresh_from_db()
    proyecto.refresh_from_db()
    assert solicitud.resuelto_por == contraparte
    assert contrato.estado == 'cancelada'
    assert proyecto.vacantes_disponibles == 1
    for actor in (empresa, dev):
        actor.refresh_from_db()
        assert actor.estado == 'activo'
        assert actor.is_active
