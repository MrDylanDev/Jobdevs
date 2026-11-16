"""Recorrido visual de las decisiones del módulo 2 en navegador real."""

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from contrataciones.models import Contratacion
from notificaciones.models import Notificacion
from notificaciones.tasks import enviar_avisos_cumplimiento_task
from proyectos.models import Proyecto


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_empresa_crea_retira_y_recibe_avisos(page, live_server, empresa_user, admin_user, desarrollador_user):
    # Sesión de prueba: el navegador no conoce ni recibe una contraseña.
    cliente = Client()
    cliente.force_login(empresa_user)
    host = urlparse(live_server.url).hostname
    page.context.add_cookies([{
        'name': 'sessionid', 'value': cliente.cookies['sessionid'].value,
        'domain': host, 'path': '/',
    }])
    errores = []
    page.on('pageerror', lambda error: errores.append(str(error)))
    page.goto(live_server.url + reverse('dashboard_empresa'))
    if page.locator('#modalBienvenidaEmpresa').is_visible():
        page.locator('#chkNoVolverAMostrarBienvenida').check()
        page.locator('button[onclick="cerrarModalBienvenida()"]:visible').click()
    assert page.locator('#modalProyecto').count() == 1
    page.locator('button[onclick="switchTab(\'ofertas\', this)"]').click()
    boton_nueva = page.locator('#ofertas .page-header button[onclick="abrirModal()"]')
    boton_nueva.wait_for(state='visible')
    page.wait_for_timeout(400)
    boton_nueva.click()
    assert page.locator('#modalProyecto').is_visible()
    assert page.locator('#crear_fecha_cumplimiento').get_attribute('required') is not None
    page.locator('#modalProyecto input[name="titulo"]').fill('Convocatoria QA de cumplimiento')
    page.locator('#modalProyecto textarea[name="descripcion"]').fill('Entrega de prueba')
    page.locator('#crear_fecha_limite_display').click()
    page.locator('#datepicker-crear .datepicker-preset-pill').first.click()
    page.locator('#crear_fecha_cumplimiento').fill(
        (timezone.localdate() + timedelta(days=30)).isoformat()
    )
    salida = Path(os.environ.get('TMPDIR', '/tmp')) / 'jobdevs-qa'
    salida.mkdir(parents=True, exist_ok=True)
    page.locator('#modalProyecto').screenshot(path=str(salida / 'creacion-fechas.png'))
    page.locator('#modalProyecto button[type="submit"]').click()
    page.wait_for_url('**' + reverse('dashboard_empresa'))
    proyecto = Proyecto.objects.get(titulo='Convocatoria QA de cumplimiento')
    assert proyecto.fecha_cumplimiento == timezone.localdate() + timedelta(days=30)
    assert page.get_by_text('Convocatoria QA de cumplimiento').count() >= 1

    con_contrato = Proyecto.objects.create(
        empresa=empresa_user, titulo='No retirable', descripcion='D',
        tipo_solucion='sitio_web', estado='publicado',
    )
    Contratacion.objects.create(
        empresa=empresa_user, desarrollador=desarrollador_user,
        proyecto=con_contrato, estado='finalizada',
    )
    proximo = Proyecto.objects.create(
        empresa=empresa_user, titulo='Aviso QA cercano', descripcion='D',
        tipo_solucion='sitio_web', estado='en_desarrollo',
        fecha_cumplimiento=timezone.localdate() + timedelta(days=1),
    )
    assert enviar_avisos_cumplimiento_task() > 0
    assert Notificacion.objects.filter(usuario=empresa_user, proyecto=proximo).exists()
    assert Notificacion.objects.filter(usuario=admin_user, proyecto=proximo).exists()
    page.reload()
    page.locator('button.notif-btn').click()
    assert page.locator('#notifPopover').is_visible()
    assert 'Aviso QA cercano' in page.locator('#notifPopover').inner_text()
    page.locator('#notifPopover').screenshot(path=str(salida / 'aviso-48-horas.png'))
    page.locator('button.notif-btn').click()
    from playwright.sync_api import expect

    page.locator('button[onclick="switchTab(\'ofertas\', this)"]').click()
    assert page.locator(f'form[action="{reverse("desactivar_proyecto", args=[con_contrato.id])}"]').count() == 0
    retiro = page.locator(f'form[action="{reverse("desactivar_proyecto", args=[proyecto.id])}"]')
    expect(retiro).to_be_visible()
    assert '48 horas' in page.content()
    page.wait_for_timeout(700)
    page.screenshot(path=str(salida / 'avisos-y-retiro.png'), full_page=True)
    retiro.locator('button[type="submit"]').click()
    assert page.locator('#modalConfirmarRetiro').is_visible()
    page.locator('#modalConfirmarRetiro').screenshot(path=str(salida / 'confirmacion-retiro.png'))
    page.locator('#modalConfirmarRetiro button[onclick="ejecutarRetiroConfirmado()"]').click()
    page.wait_for_url('**' + reverse('dashboard_empresa'))
    proyecto.refresh_from_db()
    con_contrato.refresh_from_db()
    assert proyecto.estado == 'inactivo'
    assert con_contrato.estado == 'publicado'
    assert not errores, errores
