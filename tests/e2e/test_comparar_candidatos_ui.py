"""RF 3.2.2 oficial: recorrido de perfiles y filtros desde la empresa."""

import os
import tempfile

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from playwright.sync_api import expect

from postulaciones.models import Postulacion
from proyectos.models import Proyecto
from usuarios.models import PerfilDesarrollador

User = get_user_model()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_empresa_inspecciona_formacion_y_habilidades_de_dos_candidatos(
    page, live_server, login_user
):
    empresa = User.objects.create_user(
        username='cmp_emp', email='cmp_emp@test.jobdevs', nombre='Empresa QA',
        rol='empresa', estado='activo', password='TestPass123!',
    )
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo='Comparar perfiles QA', descripcion='Prueba RF 3.2.2',
        tipo_solucion='sitio_web', estado='publicado', vacantes=2,
    )
    candidatos = []
    for username, programa, ficha, habilidades in (
        ('cmp_ana', 'ADSO', '2558104', 'Python y Django'),
        ('cmp_beto', 'Multimedia', '2600001', 'React y JavaScript'),
    ):
        dev = User.objects.create_user(
            username=username, email=f'{username}@test.jobdevs', nombre=username.upper(),
            rol='desarrollador', estado='activo', password='TestPass123!',
        )
        PerfilDesarrollador.objects.update_or_create(
            usuario=dev, defaults={
                'programa_formacion': programa, 'ficha': ficha, 'habilidades': habilidades,
            },
        )
        candidatos.append(Postulacion.objects.create(
            proyecto=proyecto, desarrollador=dev, estado='pendiente',
            mensaje=f'Carta de {username}',
        ))

    errores = []
    page.on('pageerror', lambda error: errores.append(str(error)))
    login_user(empresa)

    url = live_server.url + reverse('ver_postulaciones_empresa', args=[proyecto.id])
    page.goto(url)
    assert page.locator('.candidate-row-corp').count() == 2
    expect(page.locator('.funnel-tab-card').first.locator('.funnel-tab-count')).to_have_text('2')
    ana, beto = candidatos
    page.locator(f'[data-comparar-id="{ana.id}"]').check()
    page.locator(f'[data-comparar-id="{beto.id}"]').check()
    page.get_by_role('button', name='Comparar seleccionados (2)').click()
    comparador = page.locator('[data-testid="comparador-candidatos"]')
    expect(comparador).to_be_visible()
    expect(comparador.locator('[data-comparacion-candidato]')).to_have_count(2)
    expect(comparador).to_contain_text('CMP_ANA')
    expect(comparador).to_contain_text('CMP_BETO')
    expect(comparador).to_contain_text('Python y Django')
    expect(comparador).to_contain_text('React y JavaScript')
    page.locator(f'#cand-card-{ana.id}').click()
    inspector = page.locator('.inspector-detail:visible')
    assert inspector.count() == 1
    assert 'ADSO' in inspector.inner_text()
    assert '2558104' in inspector.inner_text()
    assert 'Python y Django' in inspector.inner_text()
    page.locator(f'#cand-card-{beto.id}').click()
    assert inspector.count() == 1
    assert 'Multimedia' in inspector.inner_text()
    assert '2600001' in inspector.inner_text()
    assert 'React y JavaScript' in inspector.inner_text()
    assert 'Python y Django' not in inspector.inner_text()
    page.locator(f'#cand-card-{ana.id}').focus()
    page.keyboard.press('Enter')
    expect(page.locator(f'#inspector-{ana.id}')).to_be_visible()
    page.locator(f'#cand-card-{beto.id}').click()
    contraste = page.locator('.inspector-detail:visible .btn-secondary').first.evaluate(
        '(el) => ({fondo: getComputedStyle(el).backgroundColor, texto: getComputedStyle(el).color})')
    assert contraste['fondo'] != contraste['texto']

    page.screenshot(path=os.path.join(tempfile.gettempdir(), 'jobdevs_rf322_inspector.png'),
                    full_page=True)
    page.select_option('#filtro-programa', 'ADSO')
    page.fill('#filtro-habilidad', 'Python')
    page.get_by_role('button', name='Filtrar').click()
    expect(page.locator('.candidate-row-corp')).to_have_count(1)
    expect(page.locator(f'#cand-card-{ana.id}')).to_have_count(1)
    assert 'Python y Django' in page.locator('.inspector-detail:visible').inner_text()
    assert not errores
