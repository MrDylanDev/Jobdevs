import pytest
from django.urls import reverse


class TestDashboardAccess:
    """Tests for role-based dashboard access control."""

    # --- Landing page (public) ---

    def test_inicio_accessible_anonymous(self, client):
        """Landing page accessible without login."""
        response = client.get(reverse('inicio'))
        assert response.status_code == 200

    # --- Dashboard: empresa ---

    def test_empresa_dashboard_accessible(self, auth_client):
        """Empresa user can access their dashboard."""
        response = auth_client.get(reverse('dashboard_empresa'))
        assert response.status_code == 200

    def test_empresa_dashboard_incluye_postulaciones_y_vacantes_en_desarrollo(self, auth_client, empresa_user, desarrollador_user):
        """Dashboard de empresa debe contabilizar postulaciones de proyectos en desarrollo y reportar vacantes disponibles."""
        from proyectos.models import Proyecto
        from postulaciones.models import Postulacion
        from contrataciones.models import Contratacion
        from usuarios.models import Usuario

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy MultiVacantes', descripcion='DM',
            tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=3,
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, empresa=empresa_user, estado='activa'
        )
        dev2 = Usuario.objects.create_user(
            username='dev_cand_2', email='dev_cand_2@test.jobdevs',
            nombre='Dev Cand 2', rol='desarrollador', estado='activo', password='Password123*'
        )
        Postulacion.objects.create(
            proyecto=proyecto, desarrollador=dev2, estado='pendiente'
        )

        response = auth_client.get(reverse('dashboard_empresa'))
        assert response.status_code == 200
        assert response.context['total_postulaciones'] >= 1
        proy_en_desarrollo = next((p for p in response.context['en_desarrollo_v'] if p['proyecto_id'] == proyecto.id), None)
        assert proy_en_desarrollo is not None
        assert proy_en_desarrollo['vacantes_disponibles'] == 2
        assert proy_en_desarrollo['vacantes_totales'] == 3
        content = response.content.decode()
        exact_url = reverse('ver_postulaciones_empresa', args=[proyecto.id])
        assert f'href="{exact_url}"' in content

    def test_empresa_dashboard_en_revision_no_expone_vacantes_disponibles(self, auth_client, empresa_user, desarrollador_user):
        """Proyectos en estado 'en_revision' no deben reportar vacantes disponibles ni enlace de contratación."""
        from proyectos.models import Proyecto

        proyecto_rev = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy En Revision', descripcion='DR',
            tipo_solucion='sitio_web', estado='en_revision', vacantes=3,
        )
        response = auth_client.get(reverse('dashboard_empresa'))
        assert response.status_code == 200
        p_rev = next((p for p in response.context['en_desarrollo_v'] if p['proyecto_id'] == proyecto_rev.id), None)
        assert p_rev is not None
        assert p_rev['vacantes_disponibles'] == 0
        content = response.content.decode()
        exact_url = reverse('ver_postulaciones_empresa', args=[proyecto_rev.id])
        assert f'href="{exact_url}"' not in content

    def test_empresa_dashboard_blocked_for_anon(self, client):
        """Anonymous users cannot access empresa dashboard."""
        response = client.get(reverse('dashboard_empresa'))
        assert response.status_code == 302

    def test_empresa_dashboard_blocked_for_dev(self, dev_client):
        """Dev users cannot access empresa dashboard."""
        response = dev_client.get(reverse('dashboard_empresa'))
        # Redirects to inicio because role check fails
        assert response.status_code == 302

    # --- Dashboard: desarrollador ---

    def test_dev_dashboard_accessible(self, dev_client):
        """Dev user can access their dashboard."""
        response = dev_client.get(reverse('dashboard_desarrollador'))
        assert response.status_code == 200

    def test_dev_dashboard_blocked_for_anon(self, client):
        """Anonymous users cannot access dev dashboard."""
        response = client.get(reverse('dashboard_desarrollador'))
        assert response.status_code == 302

    def test_dev_dashboard_blocked_for_empresa(self, auth_client):
        """Empresa users cannot access dev dashboard."""
        response = auth_client.get(reverse('dashboard_desarrollador'))
        assert response.status_code == 302

    # --- Dashboard: admin ---

    def test_admin_dashboard_accessible(self, admin_client):
        """Admin user can access their dashboard."""
        response = admin_client.get(reverse('dashboard_admin'))
        assert response.status_code == 200

    def test_admin_dashboard_blocked_for_anon(self, client):
        """Anonymous users cannot access admin dashboard."""
        response = client.get(reverse('dashboard_admin'))
        assert response.status_code == 302

    def test_admin_dashboard_blocked_for_empresa(self, auth_client):
        """Empresa users cannot access admin dashboard."""
        response = auth_client.get(reverse('dashboard_admin'))
        assert response.status_code == 302

    # --- Profile editing ---

    def test_editar_perfil_accessible(self, auth_client):
        """Authenticated user can access profile edit."""
        response = auth_client.get(reverse('editar_perfil'))
        assert response.status_code == 200

    def test_editar_perfil_blocked_for_anon(self, client):
        """Anonymous cannot access profile edit."""
        response = client.get(reverse('editar_perfil'))
        assert response.status_code == 302

    def test_editar_perfil_desarrollador_actualiza_telefono(self, dev_client, desarrollador_user):
        """RF 1.2.2 (SCRUM-41): Desarrollador puede actualizar su teléfono de contacto."""
        response = dev_client.post(reverse('editar_perfil'), {
            'telefono': '3001234567',
            'programa_formacion': 'ADSO',
            'ficha': '2670123',
            'habilidades': 'Python, Django',
            'portafolio_url': 'https://github.com/devtest',
        }, follow=True)
        assert response.status_code == 200
        desarrollador_user.perfil_desarrollador.refresh_from_db()
        assert desarrollador_user.perfil_desarrollador.telefono == '3001234567'

def test_dev_dashboard_muestra_chat_de_postulacion_en_negociacion(dev_client, desarrollador_user, db):
    from django.urls import reverse
    from usuarios.models import Usuario
    from proyectos.models import Proyecto
    from postulaciones.models import Postulacion

    empresa = Usuario.objects.create_user(
        username="emp_nego", email="emp_nego@test.local", rol="empresa", estado="activo"
    )
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo="Proyecto Negociacion Test", estado="publicado"
    )
    Postulacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, estado="en_negociacion"
    )

    response = dev_client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200
    content = response.content.decode()

    # Debe figurar en la tabla de postulaciones con su botón de Chatear
    chat_url = reverse('sala_chat', kwargs={'receptor_id': empresa.id, 'proyecto_id': proyecto.id})
    assert chat_url in content
    assert "En Negociación" in content

def test_dev_dashboard_muestra_boton_firmar_contrato_digital_en_negociacion(dev_client, desarrollador_user, db):
    """SCRUM-203: El dashboard del desarrollador muestra el botón y enlace para firmar el contrato digital."""
    from django.urls import reverse
    from usuarios.models import Usuario
    from proyectos.models import Proyecto
    from postulaciones.models import Postulacion
    from contrataciones.models import ContratoDigital

    empresa = Usuario.objects.create_user(
        username="emp_contrato", email="emp_contrato@test.local", rol="empresa", estado="activo"
    )
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo="Proyecto Contrato Digital Test", estado="publicado"
    )
    post = Postulacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, estado="en_negociacion"
    )
    contrato = ContratoDigital.objects.create(
        postulacion=post, monto=2000000, moneda="COP"
    )

    response = dev_client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200
    content = response.content.decode()

    contrato_url = reverse('ver_contrato_digital', args=[contrato.id])
    assert contrato_url in content
    assert "Firmar Contrato" in content

def test_dev_dashboard_incluye_seccion_contratos_digitales(dev_client, desarrollador_user, db):
    """SCRUM-204: El dashboard incluye la sección dedicada #contratos y el ítem de menú en sidebar."""
    from django.urls import reverse
    from usuarios.models import Usuario
    from proyectos.models import Proyecto
    from postulaciones.models import Postulacion
    from contrataciones.models import ContratoDigital

    empresa = Usuario.objects.create_user(
        username="emp_contratos_sec", email="emp_sec@test.local", rol="empresa", estado="activo"
    )
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo="Proyecto Seccion Contratos", estado="publicado"
    )
    post = Postulacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, estado="en_negociacion"
    )
    contrato = ContratoDigital.objects.create(
        postulacion=post, monto=3500000, moneda="COP"
    )

    response = dev_client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200
    assert 'mis_contratos_digitales' in response.context
    assert 'contratos_pendientes_firma_count' in response.context
    assert response.context['contratos_pendientes_firma_count'] == 1

    content = response.content.decode()
    assert 'verSeccion(\'contratos\'' in content or 'verSeccion("contratos"' in content
    assert 'id="contratos"' in content
    assert 'Proyecto Seccion Contratos' in content
    assert '$ 3.500.000 COP' in content


def _crear_proyecto(empresa, titulo, estado='publicado'):
    from proyectos.models import Proyecto
    return Proyecto.objects.create(
        empresa=empresa, titulo=titulo, descripcion='Descripcion de prueba',
        tipo_solucion='sitio_web', estado=estado,
    )


def test_dev_dashboard_separa_postulaciones_vigentes_e_historial(dev_client, desarrollador_user, empresa_user, db):
    """SCRUM-227 (RF 1.2.3): postulaciones vigentes vs historial de rechazadas."""
    from django.urls import reverse
    from postulaciones.models import Postulacion

    proyecto_vigente = _crear_proyecto(empresa_user, 'Proyecto Postulacion Vigente')
    proyecto_negociacion = _crear_proyecto(empresa_user, 'Proyecto Postulacion Negociacion')
    proyecto_rechazada = _crear_proyecto(empresa_user, 'Proyecto Postulacion Rechazada')

    post_vigente = Postulacion.objects.create(
        proyecto=proyecto_vigente, desarrollador=desarrollador_user, estado='pendiente'
    )
    post_negociacion = Postulacion.objects.create(
        proyecto=proyecto_negociacion, desarrollador=desarrollador_user, estado='en_negociacion'
    )
    post_rechazada = Postulacion.objects.create(
        proyecto=proyecto_rechazada, desarrollador=desarrollador_user, estado='rechazada'
    )

    response = dev_client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200

    vigentes_ids = {p.id for p in response.context['postulaciones_vigentes']}
    historial_ids = {p.id for p in response.context['postulaciones_historial']}

    assert post_vigente.id in vigentes_ids
    assert post_negociacion.id in vigentes_ids
    assert post_rechazada.id in historial_ids
    assert post_rechazada.id not in vigentes_ids

    assert response.context['postulaciones_vigentes_count'] == 2
    assert response.context['postulaciones_historial_count'] == 1

    # Claves preexistentes se mantienen (compatibilidad estricta)
    assert 'mis_postulaciones' in response.context
    assert 'mis_proyectos_activos_v' in response.context
    assert 'mis_proyectos_finalizados' in response.context
    assert post_rechazada.id in {p.id for p in response.context['mis_postulaciones']}


def test_dev_dashboard_ui_muestra_bloques_vigente_e_historial_postulaciones(dev_client, desarrollador_user, empresa_user, db):
    """SCRUM-227 (RF 1.2.3): la UI expone un bloque vigente y un historial de rechazadas."""
    from django.urls import reverse
    from postulaciones.models import Postulacion

    proyecto_vigente = _crear_proyecto(empresa_user, 'Proyecto UI Vigente')
    proyecto_rechazada = _crear_proyecto(empresa_user, 'Proyecto UI Rechazada')
    Postulacion.objects.create(
        proyecto=proyecto_vigente, desarrollador=desarrollador_user, estado='pendiente'
    )
    Postulacion.objects.create(
        proyecto=proyecto_rechazada, desarrollador=desarrollador_user, estado='rechazada'
    )

    response = dev_client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200
    content = response.content.decode()

    assert 'data-testid="postulaciones-vigentes"' in content
    assert 'data-testid="postulaciones-historial"' in content

    bloque_vigente = content.split('data-testid="postulaciones-vigentes"', 1)[1]
    bloque_vigente = bloque_vigente.split('data-testid="postulaciones-historial"', 1)[0]
    bloque_historial = content.split('data-testid="postulaciones-historial"', 1)[1]

    assert 'Proyecto UI Vigente' in bloque_vigente
    assert 'Proyecto UI Rechazada' not in bloque_vigente
    assert 'Proyecto UI Rechazada' in bloque_historial


def test_dev_dashboard_separa_contratos_vigentes_e_historial(dev_client, desarrollador_user, empresa_user, db):
    """SCRUM-227 (RF 1.2.3): contratos vigentes vs historial (finalizada/cancelada)."""
    from django.urls import reverse
    from contrataciones.models import Contratacion

    proyecto_activa = _crear_proyecto(empresa_user, 'Contrato Activa', estado='en_desarrollo')
    proyecto_disputa = _crear_proyecto(empresa_user, 'Contrato Disputa', estado='en_disputa')
    proyecto_finalizada = _crear_proyecto(empresa_user, 'Contrato Finalizada', estado='finalizado')
    proyecto_cancelada = _crear_proyecto(empresa_user, 'Contrato Cancelada', estado='en_desarrollo')

    contrato_activa = Contratacion.objects.create(
        proyecto=proyecto_activa, desarrollador=desarrollador_user, empresa=empresa_user, estado='activa'
    )
    contrato_disputa = Contratacion.objects.create(
        proyecto=proyecto_disputa, desarrollador=desarrollador_user, empresa=empresa_user, estado='en_disputa'
    )
    contrato_finalizada = Contratacion.objects.create(
        proyecto=proyecto_finalizada, desarrollador=desarrollador_user, empresa=empresa_user, estado='finalizada'
    )
    contrato_cancelada = Contratacion.objects.create(
        proyecto=proyecto_cancelada, desarrollador=desarrollador_user, empresa=empresa_user, estado='cancelada'
    )

    response = dev_client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200

    vigentes_ids = {c.id for c in response.context['contratos_vigentes']}
    historial_ids = {c.id for c in response.context['contratos_historial']}

    assert contrato_activa.id in vigentes_ids
    assert contrato_disputa.id in vigentes_ids
    assert contrato_finalizada.id in historial_ids
    assert contrato_cancelada.id in historial_ids
    assert not ({contrato_finalizada.id, contrato_cancelada.id} & vigentes_ids)




# ---------------------------------------------------------------------------
# SCRUM-228 (RF 2.2.1): historial de proyectos de empresa por estado
# ---------------------------------------------------------------------------

def _crear_proyectos_historial(empresa_user):
    from proyectos.models import Proyecto
    estados = ('finalizado', 'rechazado', 'inactivo', 'en_disputa', 'publicado')
    return {
        estado: Proyecto.objects.create(
            empresa=empresa_user,
            titulo=f'Proyecto Historial {estado}',
            descripcion='DH',
            tipo_solucion='sitio_web',
            estado=estado,
        )
        for estado in estados
    }


def test_empresa_dashboard_historial_incluye_estados_inactivos(auth_client, empresa_user, db):
    """SCRUM-228: el historial de empresa incluye finalizado, rechazado, inactivo y en_disputa."""
    proyectos = _crear_proyectos_historial(empresa_user)

    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200

    historial_ids = {p.id for p in response.context['historial_inactivos']}
    for estado in ('finalizado', 'rechazado', 'inactivo', 'en_disputa'):
        assert proyectos[estado].id in historial_ids
    assert proyectos['publicado'].id not in historial_ids
    assert response.context['historial_inactivos_count'] == 4

    # La clave preexistente 'historial' se conserva y sigue siendo solo finalizados.
    historial_solo_finalizados = {p.id for p in response.context['historial']}
    assert historial_solo_finalizados == {proyectos['finalizado'].id}

    por_estado = response.context['historial_por_estado']
    assert por_estado['finalizado'] == 1
    assert por_estado['rechazado'] == 1
    assert por_estado['inactivo'] == 1
    assert por_estado['en_disputa'] == 1


def test_empresa_dashboard_historial_filtra_por_estado(auth_client, empresa_user, db):
    """SCRUM-228: ?historial_estado filtra el historial por estado válido."""
    proyectos = _crear_proyectos_historial(empresa_user)

    response = auth_client.get(reverse('dashboard_empresa'), {'historial_estado': 'rechazado'})
    assert response.status_code == 200
    ids_rechazado = {p.id for p in response.context['historial_inactivos']}
    assert ids_rechazado == {proyectos['rechazado'].id}
    assert response.context['historial_inactivos_count'] == 1
    assert response.context['historial_estado_actual'] == 'rechazado'

    response = auth_client.get(reverse('dashboard_empresa'), {'historial_estado': 'inactivo'})
    assert response.status_code == 200
    ids_inactivo = {p.id for p in response.context['historial_inactivos']}
    assert ids_inactivo == {proyectos['inactivo'].id}
    assert response.context['historial_estado_actual'] == 'inactivo'

    # Un estado inválido no debe romper la vista ni filtrar el queryset.
    response = auth_client.get(reverse('dashboard_empresa'), {'historial_estado': 'inexistente'})
    assert response.status_code == 200
    assert response.context['historial_inactivos_count'] == 4


def test_empresa_dashboard_historial_ui_muestra_badges_dinamicos(auth_client, empresa_user, db):
    """SCRUM-228: la UI expone filtros por estado, badges dinámicos y data-testid."""
    _crear_proyectos_historial(empresa_user)

    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200
    content = response.content.decode()

    assert 'data-testid="historial-inactivos"' in content
    for estado in ('finalizado', 'rechazado', 'inactivo', 'en_disputa'):
        assert f'data-testid="card-historial-{estado}"' in content

    # Badges dinámicos según get_estado_display()
    assert 'Finalizado' in content
    assert 'Rechazado' in content
    assert 'Inactivo' in content
    assert 'En Disputa' in content

    # Enlaces de filtro conservan la sección de historial
    assert 'historial_estado=rechazado' in content
    assert 'historial_estado=inactivo' in content
    assert 'historial_estado=en_disputa' in content


def test_empresa_dashboard_historial_empty_state_por_filtro(auth_client, empresa_user, db):
    """SCRUM-228: un filtro sin resultados muestra el empty state, no el historial completo."""
    from proyectos.models import Proyecto

    finalizado = Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto Solo Finalizado', descripcion='DH',
        tipo_solucion='sitio_web', estado='finalizado',
    )

    response = auth_client.get(reverse('dashboard_empresa'), {'historial_estado': 'rechazado'})
    assert response.status_code == 200
    assert response.context['historial_inactivos_count'] == 0
    content = response.content.decode()
    assert 'No hay proyectos en este estado del historial.' in content
    assert finalizado.titulo not in content
