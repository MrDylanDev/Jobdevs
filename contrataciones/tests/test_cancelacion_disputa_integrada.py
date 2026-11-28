"""Terminación por conflicto usa mediación; acuerdo mutuo usa confirmación bilateral."""

import pytest
from django.urls import reverse

from contrataciones.models import Contratacion, SolicitudCancelacion
from contrataciones.services import (
    resolver_solicitud_cancelacion,
    solicitar_cancelacion,
)
from disputas.services import abrir_disputa, resolver_disputa
from proyectos.models import Proyecto


@pytest.fixture
def contrato(empresa_user, desarrollador_user):
    proyecto = Proyecto.objects.create(
        empresa=empresa_user, titulo='Contrato con conflicto', descripcion='D',
        tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=1,
    )
    return Contratacion.objects.create(
        empresa=empresa_user, desarrollador=desarrollador_user,
        proyecto=proyecto, estado='activa',
    )


@pytest.mark.django_db
def test_disputa_reserva_cupo_y_lo_libera_solo_tras_fallo(
    contrato, empresa_user, admin_user,
):
    disputa = abrir_disputa(
        proyecto=contrato.proyecto, usuario=empresa_user, contratacion=contrato,
        categoria='incumplimiento_contractual',
        motivo='El hito contractual venció sin entrega; intentamos acordar un nuevo plazo y no hubo respuesta.',
        evidencia_url='https://evidencia.test/hito',
    )
    contrato.refresh_from_db()
    contrato.proyecto.refresh_from_db()
    assert contrato.estado == 'en_disputa'
    assert contrato.proyecto.estado == 'en_disputa'
    assert contrato.proyecto.vacantes_disponibles == 0
    resolver_disputa(disputa, admin_user, 'cancelar_contrato', 'Incumplimiento acreditado.')
    contrato.refresh_from_db()
    contrato.proyecto.refresh_from_db()
    assert contrato.estado == 'cancelada'
    assert contrato.proyecto.estado == 'publicado'
    assert contrato.proyecto.vacantes_disponibles == 1
    from notificaciones.models import Notificacion

    assert Notificacion.objects.filter(
        usuario=empresa_user, mensaje__contains='proyecto quedó publicado',
    ).exists()


@pytest.mark.django_db
def test_disputa_desplaza_solicitud_pendiente_sin_borrar_historial(
    contrato, empresa_user,
):
    solicitud = solicitar_cancelacion(
        contrato.pk, empresa_user, causal='acuerdo_mutuo',
        motivo='Propuesta inicial que no llegó a confirmarse.',
    )
    disputa = abrir_disputa(
        proyecto=contrato.proyecto, usuario=empresa_user, contratacion=contrato,
        categoria='incumplimiento_contractual',
        motivo='El hito contractual venció sin entrega; intentamos acordar un nuevo plazo y no hubo respuesta.',
        evidencia_url='https://evidencia.test/hito',
    )
    solicitud.refresh_from_db()
    assert solicitud.estado == 'rechazada'
    assert str(disputa.pk) in solicitud.dictamen
    assert solicitud.fecha_resolucion is not None
    from notificaciones.models import Notificacion

    assert Notificacion.objects.filter(
        usuario=contrato.desarrollador, mensaje__contains=f'Solicitud de cancelación #{solicitud.pk} sustituida',
    ).exists()
    contrato.refresh_from_db()
    assert contrato.estado == 'en_disputa'


@pytest.mark.django_db
def test_nueva_causa_unilateral_no_crea_una_segunda_revision(
    contrato, empresa_user,
):
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match='disputa'):
        solicitar_cancelacion(
            contrato.pk, empresa_user, causal='incumplimiento',
            motivo='No entregó el hito pactado.', evidencia='Hito 1 vencido.',
        )
    assert not SolicitudCancelacion.objects.exists()
    contrato.refresh_from_db()
    assert contrato.estado == 'activa'


@pytest.mark.django_db
def test_formulario_de_empresa_ofrece_acuerdo_y_enlace_a_disputa(
    auth_client, contrato,
):
    # La empresa ya no usa la página suelta: el formulario vive en su pestaña.
    pagina = auth_client.get(reverse('dashboard_empresa'), {'section': 'cancelaciones'})
    html = pagina.content.decode()
    assert 'value="acuerdo_mutuo"' in html
    assert 'value="incumplimiento"' not in html
    assert reverse('disputas:abrir_disputa', args=[contrato.proyecto_id]) in html


@pytest.mark.django_db
def test_post_heredado_de_causa_unilateral_no_crea_solicitud(
    auth_client, contrato,
):
    respuesta = auth_client.post(reverse('cancelar_contratacion', args=[contrato.pk]), {
        'causal': 'incumplimiento', 'motivo': 'No entregó el hito pactado.',
        'evidencia': 'Hito 1 vencido.',
    })
    assert respuesta.status_code == 302
    assert respuesta.url == (
        reverse('disputas:abrir_disputa', args=[contrato.proyecto_id])
        + f'?contratacion_id={contrato.pk}'
    )
    assert not SolicitudCancelacion.objects.exists()
    contrato.refresh_from_db()
    assert contrato.estado == 'activa'


@pytest.mark.django_db
def test_disputa_en_proyecto_multi_dev_se_asocia_al_contrato_seleccionado(
    auth_client, contrato, empresa_user,
):
    from django.contrib.auth import get_user_model

    from disputas.models import Disputa

    otro = get_user_model().objects.create_user(
        username='otro_dev_mediacion', email='otro_dev_mediacion@example.com',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    contrato.proyecto.vacantes = 2
    contrato.proyecto.save(update_fields=['vacantes'])
    segundo = Contratacion.objects.create(
        empresa=empresa_user, desarrollador=otro,
        proyecto=contrato.proyecto, estado='activa',
    )
    url = reverse('disputas:abrir_disputa', args=[contrato.proyecto_id])
    url += f'?contratacion_id={segundo.pk}'
    assert auth_client.get(url).context['contratacion'].pk == segundo.pk
    respuesta = auth_client.post(url, {
        'categoria': 'incumplimiento_contractual',
        'motivo': 'El segundo desarrollador no entregó su hito a pesar de las conversaciones y del plazo prorrogado.',
        'evidencia_url': 'https://evidencia.test/hito',
        'confirma_intento_previo': '1', 'confirma_gravedad': '1',
        'acepta_sanciones': '1',
    })
    assert respuesta.status_code == 302
    assert Disputa.objects.get(proyecto=contrato.proyecto).contratacion_id == segundo.pk
    segundo.refresh_from_db()
    contrato.refresh_from_db()
    assert segundo.estado == 'en_disputa'
    assert contrato.estado == 'activa'


@pytest.mark.django_db
def test_disputa_rechaza_identificador_de_contrato_invalido_o_ajeno(
    auth_client, contrato, desarrollador_user,
):
    from django.contrib.auth import get_user_model

    otra_empresa = get_user_model().objects.create_user(
        username='empresa_ajena_disputa', email='empresa_ajena_disputa@example.com',
        rol='empresa', estado='activo', password='TestPass123!',
    )
    otro_proyecto = Proyecto.objects.create(
        empresa=otra_empresa, titulo='Otro proyecto', descripcion='D',
        tipo_solucion='sitio_web', estado='en_desarrollo',
    )
    ajeno = Contratacion.objects.create(
        empresa=otra_empresa, desarrollador=desarrollador_user,
        proyecto=otro_proyecto, estado='activa',
    )
    url = reverse('disputas:abrir_disputa', args=[contrato.proyecto_id])
    assert auth_client.get(url + '?contratacion_id=abc').status_code == 404
    assert auth_client.get(url + f'?contratacion_id={ajeno.pk}').status_code == 404


@pytest.mark.django_db
def test_proyecto_congelado_no_acepta_nuevo_acuerdo_en_otro_contrato(
    contrato, empresa_user,
):
    from django.contrib.auth import get_user_model
    from django.core.exceptions import ValidationError

    otro = get_user_model().objects.create_user(
        username='otro_dev_congelado', email='otro_dev_congelado@example.com',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    contrato.proyecto.vacantes = 2
    contrato.proyecto.save(update_fields=['vacantes'])
    segundo = Contratacion.objects.create(
        empresa=empresa_user, desarrollador=otro,
        proyecto=contrato.proyecto, estado='activa',
    )
    abrir_disputa(
        proyecto=contrato.proyecto, usuario=empresa_user, contratacion=contrato,
        motivo='El hito contractual venció sin entrega; intentamos acordar un nuevo plazo y no hubo respuesta.',
        evidencia_url='https://evidencia.test/hito',
    )
    with pytest.raises(ValidationError, match='disputa'):
        solicitar_cancelacion(
            segundo.pk, empresa_user, causal='acuerdo_mutuo',
            motivo='Ambas partes acordaron la terminación.',
        )
    assert not SolicitudCancelacion.objects.filter(contratacion=segundo).exists()


@pytest.mark.django_db
def test_acuerdo_ya_pendiente_de_otro_contrato_espera_fin_de_disputa(
    contrato, empresa_user,
):
    from django.contrib.auth import get_user_model
    from django.core.exceptions import ValidationError

    otro = get_user_model().objects.create_user(
        username='dev_acuerdo_congelado', email='dev_acuerdo_congelado@example.com',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    segundo = Contratacion.objects.create(
        empresa=empresa_user, desarrollador=otro,
        proyecto=contrato.proyecto, estado='activa',
    )
    solicitud = solicitar_cancelacion(
        segundo.pk, empresa_user, causal='acuerdo_mutuo',
        motivo='Las partes acordaron finalizar este contrato.',
    )
    abrir_disputa(
        proyecto=contrato.proyecto, usuario=empresa_user, contratacion=contrato,
        motivo='El hito contractual venció sin entrega; intentamos acordar un nuevo plazo y no hubo respuesta.',
        evidencia_url='https://evidencia.test/hito',
    )
    with pytest.raises(ValidationError, match='disputa'):
        resolver_solicitud_cancelacion(solicitud.pk, otro, aprobar=True)
    from django.test import Client

    cliente_dev = Client()
    cliente_dev.force_login(otro)
    assert reverse('resolver_solicitud_cancelacion', args=[solicitud.pk]) not in (
        cliente_dev.get(reverse('solicitudes_cancelacion')).content.decode()
    )
    solicitud.refresh_from_db()
    segundo.refresh_from_db()
    assert solicitud.estado == 'pendiente_acuerdo'
    assert segundo.estado == 'activa'
