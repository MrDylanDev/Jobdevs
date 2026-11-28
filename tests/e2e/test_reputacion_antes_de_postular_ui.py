"""RF 3.1.2 oficial: consultar reputación desde una oferta filtrada antes de postular."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from playwright.sync_api import expect

from postulaciones.models import Postulacion
from proyectos.models import Proyecto, Valoracion
from usuarios.models import PerfilDesarrollador, PerfilEmpresa

User = get_user_model()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_reputacion_desde_catalogo_filtrado_antes_de_postular(
    page, live_server, login_user
):
    empresa = User.objects.create_user(
        username='reput_emp', email='reput_emp@test.jobdevs', nombre='Empresa Reputada',
        rol='empresa', estado='activo', password='TestPass123!',
    )
    PerfilEmpresa.objects.update_or_create(
        usuario=empresa, defaults={'descripcion': 'Desarrollamos tecnología responsable.'},
    )
    dev = User.objects.create_user(
        username='reput_dev', email='reput_dev@test.jobdevs', nombre='Candidato',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    PerfilDesarrollador.objects.update_or_create(
        usuario=dev, defaults={'estado_verificacion': 'verificado'},
    )
    oferta = Proyecto.objects.create(
        empresa=empresa, titulo='Oferta de reputación', descripcion='Oferta de prueba',
        tipo_solucion='sitio_web', estado='publicado',
    )
    anterior = Proyecto.objects.create(
        empresa=empresa, titulo='Trabajo previo', descripcion='Historial',
        tipo_solucion='sitio_web', estado='finalizado',
    )
    Valoracion.objects.create(
        proyecto=anterior, empresa=empresa, desarrollador=dev,
        rol_evaluador='desarrollador', puntuacion=5,
        comentario='Pagos puntuales y comunicación clara.',
    )

    errores = []
    page.on('pageerror', lambda error: errores.append(str(error)))
    login_user(dev)
    page.goto(live_server.url + reverse('listar_proyectos'))
    with page.expect_response(lambda response: '/proyectos/?' in response.url and response.status == 200):
        page.fill('input[name="q"]', 'Oferta de reputación')
    tarjeta = page.locator('.cards-grid .project-card').filter(has_text='Oferta de reputación')
    expect(tarjeta).to_have_count(1)
    expect(page).to_have_url(live_server.url + reverse('listar_proyectos') + '?q=Oferta+de+reputaci%C3%B3n')
    perfil_url = reverse('detalle_empresa', args=[empresa.id])
    enlace_empresa = tarjeta.get_by_role('link', name='Empresa Reputada')
    expect(enlace_empresa).to_have_attribute('href', perfil_url)
    enlace_empresa.click()
    expect(page).to_have_url(live_server.url + perfil_url)
    expect(page.get_by_text('Desarrollamos tecnología responsable.')).to_be_visible()
    page.wait_for_function('() => window.__jobdevsActionDelegateBound === true')
    page.get_by_role('button', name='Opiniones & Reputación (1)').click()
    expect(page.get_by_text('Pagos puntuales y comunicación clara.')).to_be_visible()
    expect(page.locator('.rep-score-value')).to_have_text('5.0')
    assert not Postulacion.objects.filter(proyecto=oferta, desarrollador=dev).exists()

    page.go_back()
    page.fill('input[name="q"]', '')
    with page.expect_response(lambda response: '/proyectos/?' in response.url and response.status == 200):
        page.fill('input[name="q"]', 'Oferta de reputación')
    expect(tarjeta).to_have_count(1)
    postular_url = reverse('postularse_a_proyecto', args=[oferta.id])
    enlace_postular = tarjeta.get_by_role('link', name='Postularme')
    expect(enlace_postular).to_have_attribute('href', postular_url)
    enlace_postular.click()
    expect(page).to_have_url(live_server.url + postular_url)
    page.fill('textarea[name="carta"]', 'Consulté la reputación y deseo participar.')
    page.locator('form:has(textarea[name="carta"]) button[type="submit"]').click()
    expect(page).to_have_url(live_server.url + reverse('dashboard_desarrollador'))
    assert Postulacion.objects.filter(proyecto=oferta, desarrollador=dev).count() == 1
    assert not errores
