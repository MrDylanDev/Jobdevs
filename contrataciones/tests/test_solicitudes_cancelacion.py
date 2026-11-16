"""RF 3.4.1: una solicitud no libera cupo antes de su aprobación."""

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from contrataciones.models import Contratacion, SolicitudCancelacion
from contrataciones.services import (
    cancelar_contratacion, resolver_solicitud_cancelacion, solicitar_cancelacion,
)
from proyectos.models import Proyecto


@pytest.mark.django_db
def test_desarrollador_propone_y_solo_empresa_confirma(
    empresa_user, desarrollador_user, admin_user, contrato_activo,
):
    from notificaciones.models import Notificacion

    solicitud = solicitar_cancelacion(
        contrato_activo.pk, desarrollador_user, causal='acuerdo_mutuo',
        motivo='Propongo terminar el contrato de común acuerdo.',
    )
    assert solicitud.solicitante == desarrollador_user
    assert solicitud.estado == 'pendiente_acuerdo'
    assert Notificacion.objects.filter(usuario=empresa_user, proyecto=contrato_activo.proyecto).exists()
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'activa'
    assert contrato_activo.proyecto.vacantes_disponibles == 0
    for actor in (desarrollador_user, admin_user):
        with pytest.raises(PermissionDenied):
            resolver_solicitud_cancelacion(solicitud.pk, actor, aprobar=True)
    resolver_solicitud_cancelacion(solicitud.pk, empresa_user, aprobar=True)
    contrato_activo.refresh_from_db()
    solicitud.refresh_from_db()
    assert solicitud.resuelto_por == empresa_user
    assert contrato_activo.estado == 'cancelada'
    assert contrato_activo.proyecto.vacantes_disponibles == 1


@pytest.fixture
def contrato_activo(empresa_user, desarrollador_user):
    proyecto = Proyecto.objects.create(
        empresa=empresa_user, titulo='Contrato bajo revisión', descripcion='D',
        tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=1,
    )
    return Contratacion.objects.create(
        proyecto=proyecto, empresa=empresa_user,
        desarrollador=desarrollador_user, estado='activa',
    )


@pytest.mark.django_db
@pytest.mark.parametrize('inicia_empresa', [True, False])
def test_fuerza_mayor_es_propuesta_bilateral_sin_sanciones(
    empresa_user, desarrollador_user, admin_user, contrato_activo, inicia_empresa,
):
    from disputas.models import Disputa

    proponente, contraparte = (
        (empresa_user, desarrollador_user) if inicia_empresa
        else (desarrollador_user, empresa_user)
    )
    solicitud = solicitar_cancelacion(
        contrato_activo.pk, proponente, causal='fuerza_mayor',
        motivo='Una emergencia impide continuar con el contrato.', evidencia='Referencia de la emergencia.',
    )
    assert solicitud.estado == 'pendiente_acuerdo'
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'activa'
    assert contrato_activo.proyecto.vacantes_disponibles == 0
    assert not Disputa.objects.filter(contratacion=contrato_activo).exists()
    for actor in (proponente, admin_user):
        with pytest.raises(PermissionDenied):
            resolver_solicitud_cancelacion(solicitud.pk, actor, aprobar=True)
    resolver_solicitud_cancelacion(solicitud.pk, contraparte, aprobar=True)
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'cancelada'
    for actor in (empresa_user, desarrollador_user):
        actor.refresh_from_db()
        assert actor.estado == 'activo'
        assert actor.is_active


@pytest.mark.django_db
def test_post_unilateral_no_cancela_ni_libera_cupo(auth_client, contrato_activo):
    respuesta = auth_client.post(reverse('cancelar_contratacion', args=[contrato_activo.id]), {
        'causal': 'incumplimiento',
        'motivo_cancelacion': 'Hito comprometido aún no entregado.',
        'evidencia': 'Hito 1 vencido; avance 4 sin registrar.',
    })
    assert respuesta.status_code == 302
    contrato_activo.refresh_from_db()
    contrato_activo.proyecto.refresh_from_db()
    assert contrato_activo.estado == 'activa'
    assert contrato_activo.proyecto.estado == 'en_desarrollo'
    assert contrato_activo.proyecto.vacantes_disponibles == 0
    assert not SolicitudCancelacion.objects.filter(contratacion=contrato_activo).exists()


@pytest.mark.django_db
@pytest.mark.parametrize('inicia_empresa', [True, False])
def test_formulario_bilateral_y_rechazo_sin_cancelacion(
    client, empresa_user, desarrollador_user, contrato_activo, inicia_empresa,
):
    proponente, contraparte = (
        (empresa_user, desarrollador_user) if inicia_empresa
        else (desarrollador_user, empresa_user)
    )
    crear = reverse('cancelar_contratacion', args=[contrato_activo.pk])
    destino = reverse('solicitudes_cancelacion')
    client.force_login(proponente)
    pagina = client.get(destino, follow=True)
    assert crear in pagina.content.decode()
    assert 'value="fuerza_mayor"' in pagina.content.decode()
    respuesta = client.post(crear, {
        'causal': 'fuerza_mayor', 'motivo': 'Emergencia que impide continuar el contrato.',
    })
    assert respuesta.status_code == 302
    solicitud = SolicitudCancelacion.objects.get(contratacion=contrato_activo)
    resolver = reverse('resolver_solicitud_cancelacion', args=[solicitud.pk])
    assert resolver not in client.get(destino, follow=True).content.decode()
    client.force_login(contraparte)
    html = client.get(destino, follow=True).content.decode()
    assert resolver in html
    assert solicitud.motivo in html
    assert 'Solicitar revisión por fuerza mayor' in html
    assert client.post(resolver, {'decision': 'rechazar'}).status_code == 302
    solicitud.refresh_from_db()
    contrato_activo.refresh_from_db()
    assert solicitud.estado == 'rechazada'
    assert contrato_activo.estado == 'activa'
    assert contrato_activo.proyecto.vacantes_disponibles == 0
    assert 'Solicitar revisión por fuerza mayor' in client.get(destino, follow=True).content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize('rol', ['empresa', 'desarrollador'])
def test_tercero_no_propone_ni_confirma_fuerza_mayor(
    client, empresa_user, contrato_activo, rol,
):
    from django.contrib.auth import get_user_model

    tercero = get_user_model().objects.create_user(
        username=f'ajeno_fuerza_{rol}', email=f'ajeno_fuerza_{rol}@example.com',
        rol=rol, estado='activo',
    )
    with pytest.raises(PermissionDenied):
        solicitar_cancelacion(
            contrato_activo.pk, tercero, causal='fuerza_mayor',
            motivo='Intento sobre un contrato que no me pertenece.',
        )
    client.force_login(tercero)
    assert client.post(reverse('cancelar_contratacion', args=[contrato_activo.pk]), {
        'causal': 'fuerza_mayor', 'motivo': 'Intento sobre un contrato que no me pertenece.',
    }).status_code == 404
    solicitud = solicitar_cancelacion(
        contrato_activo.pk, empresa_user, causal='fuerza_mayor',
        motivo='Emergencia que impide continuar el contrato.',
    )
    assert solicitud.motivo not in client.get(reverse('solicitudes_cancelacion'), follow=True).content.decode()
    assert client.post(reverse('resolver_solicitud_cancelacion', args=[solicitud.pk]), {
        'decision': 'aprobar',
    }).status_code == 403
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'activa'


@pytest.mark.django_db
def test_fuerza_mayor_heredada_conserva_revision_administrativa(
    empresa_user, desarrollador_user, admin_user, contrato_activo,
):
    solicitud = SolicitudCancelacion.objects.create(
        contratacion=contrato_activo, solicitante=empresa_user, causal='fuerza_mayor',
        motivo='Expediente de emergencia radicado con la política anterior.',
        estado='pendiente_revision',
    )
    with pytest.raises(PermissionDenied):
        resolver_solicitud_cancelacion(solicitud.pk, desarrollador_user, aprobar=True)
    resolver_solicitud_cancelacion(
        solicitud.pk, admin_user, aprobar=True, dictamen='Emergencia acreditada en el expediente anterior.',
    )
    solicitud.refresh_from_db()
    contrato_activo.refresh_from_db()
    assert solicitud.resuelto_por == admin_user
    assert contrato_activo.estado == 'cancelada'


@pytest.mark.django_db
def test_servicio_directo_no_puede_omitir_revision(empresa_user, contrato_activo):
    with pytest.raises(ValidationError, match='solicitud aprobada'):
        cancelar_contratacion(contrato_activo.pk, empresa_user, motivo='Motivo cualquiera')
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'activa'


@pytest.mark.django_db
def test_admin_aprueba_causa_y_solo_entonces_libera_cupo(
    auth_client, admin_user, empresa_user, contrato_activo,
):
    # Los expedientes unilaterales ya radicados antes del cambio se conservan.
    solicitud = SolicitudCancelacion.objects.create(
        contratacion=contrato_activo, solicitante=empresa_user,
        causal='incumplimiento', motivo='No entregó el hito pactado.',
        evidencia='Hito 1 vencido sin entregable.', estado='pendiente_revision',
    )
    resolver_solicitud_cancelacion(solicitud.pk, admin_user, aprobar=True,
                                  dictamen='Hito y avances verificados.')
    solicitud.refresh_from_db()
    contrato_activo.refresh_from_db()
    contrato_activo.proyecto.refresh_from_db()
    assert solicitud.estado == 'aprobada'
    assert solicitud.resuelto_por == admin_user
    assert contrato_activo.estado == 'cancelada'
    assert contrato_activo.proyecto.estado == 'publicado'
    assert contrato_activo.proyecto.vacantes_disponibles == 1


@pytest.mark.django_db
def test_acuerdo_mutuo_requiere_confirmacion_del_desarrollador(
    empresa_user, desarrollador_user, contrato_activo,
):
    solicitud = solicitar_cancelacion(
        contrato_activo.pk, empresa_user, causal='acuerdo_mutuo',
        motivo='Las dos partes desean terminar el contrato.',
    )
    assert solicitud.estado == 'pendiente_acuerdo'
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'activa'
    with pytest.raises(PermissionDenied):
        resolver_solicitud_cancelacion(solicitud.pk, empresa_user, aprobar=True)
    resolver_solicitud_cancelacion(solicitud.pk, desarrollador_user, aprobar=True)
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'cancelada'
    with pytest.raises(ValidationError, match='ya no está pendiente'):
        resolver_solicitud_cancelacion(solicitud.pk, desarrollador_user, aprobar=True)


@pytest.mark.django_db
def test_rechazo_administrativo_mantiene_contrato_y_cupo(
    empresa_user, admin_user, desarrollador_user, contrato_activo,
):
    solicitud = SolicitudCancelacion.objects.create(
        contratacion=contrato_activo, solicitante=empresa_user, causal='inactividad',
        motivo='No presentó actividad durante el plazo pactado.',
        evidencia='Historial del hito 3 y avisos de seguimiento.', estado='pendiente_revision',
    )
    with pytest.raises(PermissionDenied):
        resolver_solicitud_cancelacion(solicitud.pk, desarrollador_user, aprobar=True,
                                      dictamen='No corresponde.')
    with pytest.raises(ValidationError, match='dictamen'):
        resolver_solicitud_cancelacion(solicitud.pk, admin_user, aprobar=True)
    resolver_solicitud_cancelacion(solicitud.pk, admin_user, aprobar=False,
                                  dictamen='La evidencia no demuestra incumplimiento.')
    contrato_activo.refresh_from_db()
    solicitud.refresh_from_db()
    assert solicitud.estado == 'rechazada'
    assert contrato_activo.estado == 'activa'
    assert contrato_activo.proyecto.vacantes_disponibles == 0


@pytest.mark.django_db
def test_no_se_duplican_solicitudes_ni_se_admiten_causas_unilaterales(
    empresa_user, contrato_activo,
):
    with pytest.raises(ValidationError, match='disputa'):
        solicitar_cancelacion(contrato_activo.pk, empresa_user,
                             causal='incumplimiento', motivo='No entregó el hito pactado.')
    with pytest.raises(ValidationError, match='causal válida'):
        solicitar_cancelacion(contrato_activo.pk, empresa_user,
                             causal='otro', motivo='No entregó el hito pactado.')
    solicitar_cancelacion(contrato_activo.pk, empresa_user,
                         causal='acuerdo_mutuo', motivo='Las partes acordaron terminar.')
    with pytest.raises(ValidationError, match='solicitud.*pendiente'):
        solicitar_cancelacion(contrato_activo.pk, empresa_user,
                             causal='acuerdo_mutuo', motivo='Las partes acordaron terminar.')


@pytest.mark.django_db
def test_empresa_gestiona_cancelaciones_dentro_del_panel(auth_client, contrato_activo):
    """La pestaña conserva el shell del panel: sidebar, navegación y diseño corp."""
    pagina = auth_client.get(reverse('dashboard_empresa'), {'section': 'cancelaciones'})
    contenido = pagina.content.decode()
    assert pagina.status_code == 200
    assert 'id="cancelaciones"' in contenido
    assert "switchTab('cancelaciones'" in contenido
    assert reverse('cancelar_contratacion', args=[contrato_activo.pk]) in contenido
    assert 'Abrir una disputa formal para este contrato' in contenido


@pytest.mark.django_db
def test_pagina_suelta_redirige_a_la_empresa_a_su_pestana(auth_client):
    """La URL histórica sigue viva, pero la empresa aterriza en su pestaña."""
    respuesta = auth_client.get(reverse('solicitudes_cancelacion'))
    assert respuesta.status_code == 302
    assert respuesta.url == f"{reverse('dashboard_empresa')}?section=cancelaciones"


@pytest.mark.django_db
def test_empresa_tiene_formulario_y_revisa_solicitud_pendiente(auth_client, contrato_activo):
    pagina = auth_client.get(reverse('dashboard_empresa'), {'section': 'cancelaciones'})
    assert pagina.status_code == 200
    assert reverse('cancelar_contratacion', args=[contrato_activo.pk]) in pagina.content.decode()
    assert 'name="causal"' in pagina.content.decode()
    assert 'value="acuerdo_mutuo"' in pagina.content.decode()

    respuesta = auth_client.post(reverse('cancelar_contratacion', args=[contrato_activo.pk]), {
        'causal': 'acuerdo_mutuo', 'motivo': 'Ambas partes quieren terminar el contrato.',
    }, follow=True)
    assert respuesta.status_code == 200
    assert 'Pendiente de confirmación de la contraparte' in respuesta.content.decode()
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'activa'


@pytest.mark.django_db
def test_admin_revisa_por_post_y_empresa_no_puede_autoaprobar(
    auth_client, admin_client, admin_user, empresa_user, contrato_activo,
):
    solicitud = SolicitudCancelacion.objects.create(
        contratacion=contrato_activo, solicitante=empresa_user, causal='incumplimiento',
        motivo='Entregable 1 no completado en fecha.',
        evidencia='Avance del hito 1 sin entrega registrada.',
        estado='pendiente_revision',
    )
    url = reverse('resolver_solicitud_cancelacion', args=[solicitud.pk])
    auth_client.force_login(empresa_user)
    assert auth_client.post(url, {'decision': 'aprobar', 'dictamen': 'Revisado.'}).status_code == 403
    admin_client.force_login(admin_user)
    pagina = admin_client.get(reverse('solicitudes_cancelacion'))
    assert pagina.status_code == 200
    assert solicitud.motivo in pagina.content.decode()
    assert solicitud.evidencia in pagina.content.decode()
    assert url in pagina.content.decode()
    respuesta = admin_client.post(url, {
        'decision': 'aprobar', 'dictamen': 'Evidencia revisada y suficiente.',
    })
    assert respuesta.status_code == 302
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'cancelada'


@pytest.mark.django_db
def test_desarrollador_confirma_acuerdo_en_su_panel(
    dev_client, empresa_user, desarrollador_user, contrato_activo,
):
    solicitud = solicitar_cancelacion(
        contrato_activo.pk, empresa_user, causal='acuerdo_mutuo',
        motivo='Terminación de mutuo acuerdo de ambas partes.',
    )
    pagina = dev_client.get(reverse('solicitudes_cancelacion'))
    assert pagina.status_code == 200
    url = reverse('resolver_solicitud_cancelacion', args=[solicitud.pk])
    assert url in pagina.content.decode()
    respuesta = dev_client.post(url, {'decision': 'aprobar'})
    assert respuesta.status_code == 302
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'cancelada'


@pytest.mark.django_db
def test_los_tres_paneles_enlazan_el_flujo_de_cancelacion(
    auth_client, admin_user, empresa_user, desarrollador_user,
):
    destino = reverse('solicitudes_cancelacion')
    # La empresa lo gestiona dentro de su panel; dev y admin mantienen la página.
    assert "switchTab('cancelaciones'" in auth_client.get(
        reverse('dashboard_empresa')
    ).content.decode()
    auth_client.force_login(desarrollador_user)
    assert destino in auth_client.get(reverse('dashboard_desarrollador')).content.decode()
    auth_client.force_login(admin_user)
    assert destino in auth_client.get(reverse('dashboard_admin')).content.decode()


@pytest.mark.django_db
def test_csrf_bloquea_creacion_y_resolucion_sin_token(
    empresa_user, admin_user, contrato_activo,
):
    from django.test import Client

    cliente = Client(enforce_csrf_checks=True)
    cliente.force_login(empresa_user)
    assert cliente.post(reverse('cancelar_contratacion', args=[contrato_activo.pk]), {
        'causal': 'acuerdo_mutuo', 'motivo_cancelacion': 'Acuerdo de finalización.',
    }).status_code == 403
    assert not SolicitudCancelacion.objects.exists()
    solicitud = SolicitudCancelacion.objects.create(
        contratacion=contrato_activo, solicitante=empresa_user,
        causal='incumplimiento', motivo='Incumplimiento registrado.',
        evidencia='Hito sin entregar.', estado='pendiente_revision',
    )
    cliente.force_login(admin_user)
    assert cliente.post(reverse('resolver_solicitud_cancelacion', args=[solicitud.pk]), {
        'decision': 'aprobar', 'dictamen': 'Se verificó la evidencia.',
    }).status_code == 403
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'activa'


@pytest.mark.django_db
def test_desarrollador_no_ve_ni_resuelve_causa_de_otro_contrato(
    dev_client, empresa_user, contrato_activo,
):
    from django.contrib.auth import get_user_model

    otro = get_user_model().objects.create_user(
        username='otro_dev_cancel', email='otro_dev_cancel@example.com',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    solicitud = solicitar_cancelacion(
        contrato_activo.pk, empresa_user, causal='acuerdo_mutuo',
        motivo='Acuerdo de terminación de ambas partes.',
    )
    dev_client.force_login(otro)
    assert 'Acuerdo de terminación de ambas partes.' not in dev_client.get(
        reverse('solicitudes_cancelacion')
    ).content.decode()
    assert dev_client.post(
        reverse('resolver_solicitud_cancelacion', args=[solicitud.pk]),
        {'decision': 'aprobar'},
    ).status_code == 403
    contrato_activo.refresh_from_db()
    assert contrato_activo.estado == 'activa'
