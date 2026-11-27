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
        content = response.content.decode()
        assert 'id="inicio"' in content
        assert 'dashboard-layout-corp' in content
        assert 'modalBienvenidaEmpresa' in content
        assert 'Convocatorias' in content
        assert 'Candidatos' in content
        assert 'Contratos / Firmas' in content

    def test_ledger_suma_historia_y_desglosa_solo_seis_meses(
        self, auth_client, empresa_user, desarrollador_user
    ):
        from datetime import timedelta
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from contrataciones.models import ContratoDigital
        from postulaciones.models import Postulacion
        from proyectos.models import Proyecto

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Cierre contable', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado', vacantes=2,
        )
        otro = get_user_model().objects.create_user(
            username='dev_ledger', email='dev_ledger@test.jobdevs',
            rol='desarrollador', estado='activo', password='TestPass123!',
        )
        anterior = ContratoDigital.objects.create(
            postulacion=Postulacion.objects.create(
                proyecto=proyecto, desarrollador=desarrollador_user),
            monto='75.00',
        )
        ContratoDigital.objects.filter(pk=anterior.pk).update(
            fecha_creacion=timezone.now() - timedelta(days=220),
        )
        ContratoDigital.objects.create(
            postulacion=Postulacion.objects.create(proyecto=proyecto, desarrollador=otro),
            monto='25.00',
        )

        respuesta = auth_client.get(reverse('dashboard_empresa'))
        assert respuesta.status_code == 200
        assert respuesta.context['capital_ejecutado'] == 100
        meses = respuesta.context['meses_ledger']
        assert len(meses) == 6
        assert meses[-1]['monto'] == 25.0
        assert sum(fila['monto'] for fila in meses) == 25.0
        assert respuesta.context['breakdown_stack'][0]['total'] == 100.0

    def test_empresa_dashboard_renders_mini_roadmap_and_deliverable_alert(
        self, auth_client, empresa_user, desarrollador_user
    ):
        from proyectos.models import Proyecto, Entregable
        from contrataciones.models import Contratacion
        from avances.models import Avance

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto con Hitos y Avance',
            descripcion='Desc', tipo_solucion='sitio_web', estado='en_desarrollo',
        )
        Contratacion.objects.create(
            proyecto=proyecto, empresa=empresa_user, desarrollador=desarrollador_user,
            estado='activa',
        )
        h1 = Entregable.objects.create(
            proyecto=proyecto, titulo='Hito 1 Setup', estado='completado'
        )
        h2 = Entregable.objects.create(
            proyecto=proyecto, titulo='Hito 2 API', estado='en_revision'
        )
        Avance.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, entregable=h2,
            descripcion='Entrega de API completada', estado='pendiente'
        )

        response = auth_client.get(reverse('dashboard_empresa'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'alerta-avance-pendiente-empresa' in content
        assert 'Roadmap de Hitos del Proyecto' in content
        assert 'Hito 1 Setup' in content
        assert 'Hito 2 API' in content
        assert 'Entrega de API completada' in content

    def test_empresa_ve_alerta_de_cumplimiento_sin_confundirla_con_cierre(self, auth_client, empresa_user):
        from datetime import timedelta
        from django.utils import timezone
        from proyectos.models import Proyecto

        hoy = timezone.localdate()
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Entrega atrasada', descripcion='D',
            tipo_solucion='sitio_web', estado='en_desarrollo',
            fecha_limite=hoy + timedelta(days=10),
            fecha_cumplimiento=hoy - timedelta(days=1),
        )
        response = auth_client.get(reverse('dashboard_empresa'))
        fila = next(p for p in response.context['en_desarrollo_v'] if p['proyecto_id'] == proyecto.id)
        assert fila['fecha_fin'] == proyecto.fecha_cumplimiento
        assert fila['cumplimiento_vencido'] is True
        assert 'Cumplimiento vencido' in response.content.decode()

    def test_oferta_con_contrato_historico_no_ofrece_retiro(self, auth_client, empresa_user, desarrollador_user):
        from proyectos.models import Proyecto
        from contrataciones.models import Contratacion

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Oferta con historial contractual',
            descripcion='D', tipo_solucion='sitio_web', estado='publicado',
        )
        Contratacion.objects.create(
            proyecto=proyecto, empresa=empresa_user,
            desarrollador=desarrollador_user, estado='finalizada',
        )
        response = auth_client.get(reverse('dashboard_empresa'))
        assert f'action="{reverse("desactivar_proyecto", args=[proyecto.id])}"' not in response.content.decode()

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

    def test_explorar_no_muestra_publicado_sin_cupo(
        self, dev_client, empresa_user,
    ):
        from django.contrib.auth import get_user_model
        from contrataciones.models import Contratacion
        from proyectos.models import Proyecto

        otro_dev = get_user_model().objects.create_user(
            username='ocupante_explorar', email='ocupante@test.jobdevs',
            rol='desarrollador', estado='activo', password='TestPass123!',
        )
        agotado = Proyecto.objects.create(
            empresa=empresa_user, titulo='Sin cupo', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado', vacantes=1,
        )
        disponible = Proyecto.objects.create(
            empresa=empresa_user, titulo='Con cupo', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado', vacantes=1,
        )
        Contratacion.objects.create(
            empresa=empresa_user, proyecto=agotado,
            desarrollador=otro_dev, estado='activa',
        )
        response = dev_client.get(reverse('dashboard_desarrollador'))
        ids = {p.id for p in response.context['proyectos_explorar']}
        assert disponible.id in ids
        assert agotado.id not in ids

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

    def test_editar_perfil_empresa_actualiza_stack_interes_opcional(self, auth_client, empresa_user):
        """Empresa puede actualizar su stack tecnológico de interés de manera opcional."""
        response = auth_client.post(reverse('editar_perfil'), {
            'nombre_empresa': 'Tech Innovators SAS',
            'sector': 'Fintech',
            'ciudad': 'Medellín',
            'telefono': '3109876543',
            'descripcion': 'Empresa líder en finanzas digitales.',
            'stack_interes': 'Python, Django, React, AWS, Docker',
        }, follow=True)
        assert response.status_code == 200
        empresa_user.perfil_empresa.refresh_from_db()
        assert empresa_user.perfil_empresa.stack_interes == 'Python, Django, React, AWS, Docker'
        assert empresa_user.perfil_empresa.lista_stack_interes == ['Python', 'Django', 'React', 'AWS', 'Docker']
        # El campo es opcional: puede guardarse vacío sin fallar
        response_vacio = auth_client.post(reverse('editar_perfil'), {
            'nombre_empresa': 'Tech Innovators SAS',
            'sector': 'Fintech',
            'ciudad': 'Medellín',
            'telefono': '3109876543',
            'descripcion': 'Empresa líder en finanzas digitales.',
            'stack_interes': '',
        }, follow=True)
        assert response_vacio.status_code == 200
        empresa_user.perfil_empresa.refresh_from_db()
        assert empresa_user.perfil_empresa.stack_interes in ('', None)
        assert empresa_user.perfil_empresa.lista_stack_interes == []

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

    # El chat se abre embebido: hay disparador inline y no un enlace a otra página
    chat_url = reverse('sala_chat', kwargs={'receptor_id': empresa.id, 'proyecto_id': proyecto.id})
    assert chat_url not in content
    assert "data-chat-open" in content
    assert f'data-receptor="{empresa.id}"' in content
    assert f'data-proyecto="{proyecto.id}"' in content
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


def test_dev_dashboard_muestra_esperando_contrato_si_no_hay_contrato_digital(dev_client, desarrollador_user, db):
    """Muestra 'Esperando contrato' en la postulación cuando la empresa aún no ha emitido el contrato digital."""
    from django.urls import reverse
    from usuarios.models import Usuario
    from proyectos.models import Proyecto
    from postulaciones.models import Postulacion

    empresa = Usuario.objects.create_user(
        username="emp_sin_contrato", email="emp_sin_c@test.local", rol="empresa", estado="activo"
    )
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo="Proyecto Esperando Contrato Test", estado="publicado"
    )
    Postulacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, estado="pendiente"
    )

    response = dev_client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200
    content = response.content.decode()

    assert "Esperando contrato" in content

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


def test_postulacion_de_proyecto_finalizado_no_aparece_en_vigentes(dev_client, desarrollador_user, empresa_user, db):
    """Las postulaciones de proyectos que ya finalizaron no deben figurar como activas/vigentes."""
    from django.urls import reverse
    from postulaciones.models import Postulacion

    proyecto_finalizado = _crear_proyecto(empresa_user, 'Proyecto Ya Concluido', estado='finalizado')
    post = Postulacion.objects.create(
        proyecto=proyecto_finalizado, desarrollador=desarrollador_user, estado='en_negociacion'
    )

    response = dev_client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200

    vigentes_ids = {p.id for p in response.context['postulaciones_vigentes']}
    historial_ids = {p.id for p in response.context['postulaciones_historial']}

    assert post.id not in vigentes_ids
    assert post.id not in historial_ids


def test_dev_dashboard_detecta_y_alerta_calificacion_pendiente_empresa(dev_client, desarrollador_user, empresa_user, db):
    """El dashboard del desarrollador detecta proyectos finalizados sin calificar a la empresa."""
    from django.urls import reverse
    from contrataciones.models import Contratacion
    from proyectos.models import Valoracion

    proyecto_fin = _crear_proyecto(empresa_user, 'Proyecto Pendiente Calificar Empresa', estado='finalizado')
    contratacion = Contratacion.objects.create(
        proyecto=proyecto_fin, desarrollador=desarrollador_user, empresa=empresa_user, estado='finalizada'
    )

    response = dev_client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200
    assert response.context['pendientes_calificar_empresa_count'] == 1
    assert contratacion.id in {c.id for c in response.context['contrataciones_pendientes_calificar']}
    assert 'abrirCalificacionObligatoria' in response.content.decode()
    assert reverse('calificar_empresa', args=[proyecto_fin.id]) in response.content.decode()

    # Tras calificar, ya no debe quedar pendiente
    Valoracion.objects.create(
        proyecto=proyecto_fin, empresa=empresa_user, desarrollador=desarrollador_user,
        rol_evaluador='desarrollador', puntuacion=5, comentario='Excelente empresa para colaborar'
    )
    response_despues = dev_client.get(reverse('dashboard_desarrollador'))
    assert response_despues.context['pendientes_calificar_empresa_count'] == 0


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


def test_dev_dashboard_incluye_seccion_explorar_integrada(client, desarrollador_user, empresa_user, db):
    """Verifica que el dashboard de desarrollador incluye la sección integrada de explorar sin redirección."""
    from proyectos.models import Proyecto

    proyecto = Proyecto.objects.create(
        empresa=empresa_user,
        titulo='Proyecto Cyber Test',
        descripcion='Descripción de prueba para explorador integrado',
        tipo_solucion='sitio_web',
        estado='publicado',
        vacantes=2,
    )

    client.force_login(desarrollador_user)
    response = client.get(reverse('dashboard_desarrollador'))
    assert response.status_code == 200
    assert 'proyectos_explorar' in response.context
    assert 'categorias_solucion' in response.context
    assert any(p.id == proyecto.id for p in response.context['proyectos_explorar'])

    content = response.content.decode()
    # Verifica que el botón de navegación llama a verSeccion y no redirige a /proyectos/
    assert "verSeccion('explorar', this)" in content
    assert 'id="explorar"' in content
    assert 'id="devExploreSearch"' in content
    assert 'id="devExploreCategory"' in content
    assert 'id="devExplorePriority"' in content
    assert 'lucide.min.js' in content
    assert 'Proyecto Cyber Test' in content
    # El botón Postularme abre un modal flotante en vez de navegar a otra página.
    assert 'data-abrir-postulacion' in content
    assert 'id="modalPostulacion"' in content
    assert 'data-postulacion-form' in content


def test_dev_dashboard_explorar_paginacion_15_por_pagina(client, desarrollador_user, empresa_user, db):
    """El catálogo de explorar pagina a 15 proyectos y expone controles numéricos."""
    from proyectos.models import Proyecto

    # Crear 17 proyectos disponibles
    for i in range(1, 18):
        Proyecto.objects.create(
            empresa=empresa_user,
            titulo=f'Proyecto Paginado {i}',
            descripcion='Desc',
            tipo_solucion='sitio_web',
            estado='publicado',
            vacantes=2,
        )

    client.force_login(desarrollador_user)
    response = client.get(reverse('dashboard_desarrollador'), {'seccion': 'explorar', 'page': 1})
    assert response.status_code == 200
    assert len(response.context['proyectos_explorar']) == 15
    assert response.context['proyectos_explorar_page'].paginator.num_pages == 2
    assert response.context['proyectos_explorar_total'] >= 17

    content = response.content.decode()
    assert 'dev-pagination-wrap' in content
    assert 'Página 1 de 2' in content
    assert '?seccion=explorar&amp;page=2#explorar' in content

    # Página 2 contiene los restantes
    response_p2 = client.get(reverse('dashboard_desarrollador'), {'seccion': 'explorar', 'page': 2})
    assert len(response_p2.context['proyectos_explorar']) >= 2
    assert response_p2.context['proyectos_explorar_page'].number == 2


def test_empresa_dashboard_historial_reorganizado_y_disputas_sin_cerradas(auth_client, empresa_user, desarrollador_user, db):
    """
    Verifica la arquitectura Dirección 01 (Centro de Mediación Integral sin duplicación en Historial):
    1. La sección Disputas centraliza todo el ciclo: banner de protocolo SENA/JobDevs, 4 KPIs,
       switcher dual ('Casos Activos & En Mediación' y 'Expedientes Resueltos') y los expedientes resueltos.
    2. La sección Historial queda enfocada en Proyectos Archivados y Libro Mayor Financiero,
       sin la subpestaña/panel duplicado de disputas ('btn-historial-disputas', 'pane-historial-disputas').
    """
    from django.utils import timezone
    from proyectos.models import Proyecto
    from contrataciones.models import Contratacion
    from disputas.models import Disputa

    proyecto = Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto Con Disputa Resuelta', descripcion='D',
        tipo_solucion='sitio_web', estado='finalizado',
    )
    contratacion = Contratacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, empresa=empresa_user, estado='finalizada',
    )
    disputa = Disputa.objects.create(
        proyecto=proyecto, contratacion=contratacion, iniciado_por=desarrollador_user,
        motivo='Conflicto de prueba', estado='resuelta', resolucion='reanudar_proyecto',
        notas_resolucion='Acuerdo alcanzado satisfactoriamente', fecha_resolucion=timezone.now(),
    )

    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200
    content = response.content.decode()

    # 1. Separar las secciones por id
    disputas_idx = content.find('id="disputas"')
    historial_idx = content.find('id="historial"')
    perfil_idx = content.find('id="perfil"')

    assert disputas_idx != -1 and historial_idx != -1 and perfil_idx != -1
    bloque_disputas = content[disputas_idx:historial_idx]
    bloque_historial = content[historial_idx:perfil_idx]

    # En la sección Disputas debe estar el Centro de Mediación Integral con ambas vistas
    assert 'protocolo-arbitraje-banner' in bloque_disputas
    assert 'disputas-kpis' in bloque_disputas
    # La etiqueta {% trans %} es contenido seguro y Django conserva el '&'
    # literal. Ambas serializaciones producen el mismo texto en el DOM; la
    # aserción valida el contenido visible sin exigir una codificación HTML.
    from html import unescape
    assert 'Casos Activos & En Mediación' in unescape(bloque_disputas)
    assert 'Expedientes Resueltos' in bloque_disputas
    assert 'pane-disputas-activas' in bloque_disputas
    assert 'pane-disputas-resueltas' in bloque_disputas
    assert 'Proyecto Con Disputa Resuelta' in bloque_disputas
    assert f'#{disputa.pk}' in bloque_disputas
    assert 'Acuerdo alcanzado satisfactoriamente' in bloque_disputas

    # En la sección Historial NO debe duplicarse la subpestaña/panel de disputas
    assert 'history-toolbar-corp' in bloque_historial
    assert 'Proyectos Archivados' in bloque_historial
    assert 'pane-historial-proyectos' in bloque_historial
    assert 'btn-historial-disputas' not in bloque_historial
    assert 'pane-historial-disputas' not in bloque_historial
    assert 'Expedientes de Disputas' not in bloque_historial
    assert f'#{disputa.pk}' not in bloque_historial
    assert 'Acuerdo alcanzado satisfactoriamente' not in bloque_historial


@pytest.mark.django_db
def test_empresa_dashboard_renders_donut_chart_with_offsets_and_tooltips(auth_client, empresa_user):
    """Verifica que el dashboard de la empresa renderice el gráfico de torta/dona con cálculo de dash_offset y tooltip."""
    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200
    content = response.content.decode()

    # Contexto contiene breakdown_stack con dash_offset
    breakdown = response.context['breakdown_stack']
    assert len(breakdown) > 0
    for item in breakdown:
        assert 'dash_offset' in item
        assert 'dash_length' in item
        assert 'porcentaje' in item
        assert 'label' in item

    # La dona redundante ya no se renderiza en Inicio (vive en Historial)
    assert 'command-donut-card' not in content
    assert 'id="donutHomeTooltip"' not in content


@pytest.mark.django_db
def test_empresa_dashboard_renders_pending_deliverables_queue(auth_client, empresa_user, desarrollador_user):
    """Verifica que dashboard_empresa entregue avances_pendientes_revision y renderice la bandeja de aprobación."""
    from django.urls import reverse
    from proyectos.models import Proyecto, Entregable
    from contrataciones.models import Contratacion
    from avances.models import Avance

    proyecto = Proyecto.objects.create(
        empresa=empresa_user,
        titulo='Plataforma Analítica B2B',
        descripcion='Desarrollo de dashboard analítico',
        tipo_solucion='sitio_web',
        estado='en_desarrollo',
    )
    Contratacion.objects.create(
        proyecto=proyecto,
        empresa=empresa_user,
        desarrollador=desarrollador_user,
        estado='activa',
    )
    hito = Entregable.objects.create(
        proyecto=proyecto,
        titulo='Hito 1: Módulo de Reportes',
        estado='en_revision',
    )
    avance = Avance.objects.create(
        proyecto=proyecto,
        desarrollador=desarrollador_user,
        entregable=hito,
        descripcion='Implementación completa de exportación CSV y filtros.',
        archivo_url='https://github.com/jobdevs/demo-pr/pull/42',
        estado='pendiente',
    )

    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200

    assert 'avances_pendientes_revision' in response.context
    assert 'total_avances_pendientes' in response.context
    assert response.context['total_avances_pendientes'] == 1

    avances_ctx = response.context['avances_pendientes_revision']
    assert len(avances_ctx) == 1
    assert avances_ctx[0]['id'] == avance.id
    assert avances_ctx[0]['proyecto_id'] == proyecto.id
    assert avances_ctx[0]['proyecto_titulo'] == 'Plataforma Analítica B2B'
    assert avances_ctx[0]['entregable_id'] == hito.id
    assert avances_ctx[0]['entregable_titulo'] == 'Hito 1: Módulo de Reportes'
    assert avances_ctx[0]['descripcion'] == 'Implementación completa de exportación CSV y filtros.'
    assert avances_ctx[0]['archivo_url'] == 'https://github.com/jobdevs/demo-pr/pull/42'

    content = response.content.decode()
    assert 'Entregables Pendientes de Aprobación' in content
    assert 'Plataforma Analítica B2B' in content
    assert 'Hito 1: Módulo de Reportes' in content
    assert 'Implementación completa de exportación CSV y filtros.' in content
    assert 'https://github.com/jobdevs/demo-pr/pull/42' in content

    revisar_url = reverse('revisar_avance', args=[avance.id])
    assert f'action="{revisar_url}"' in content
    assert 'name="comentario"' in content
    assert 'value="aceptar"' in content
    assert 'value="rechazar"' in content
    assert 'Aprobar y Liberar Hito' in content
    assert 'Solicitar Ajustes' in content
    assert 'Revisar Entregables' in content


@pytest.mark.django_db
def test_empresa_dashboard_pending_deliverables_queue_empty_state(auth_client):
    """Verifica el estado vacío de la bandeja cuando no hay avances pendientes."""
    from django.urls import reverse

    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200
    assert response.context['total_avances_pendientes'] == 0
    assert response.context['avances_pendientes_revision'] == []

    content = response.content.decode()
    assert 'Entregables Pendientes de Aprobación' in content
    assert 'Todos los entregables técnicos están al día.' in content


@pytest.mark.django_db
def test_empresa_dashboard_no_usa_espacio_con_firma_pendiente(
    auth_client, empresa_user, desarrollador_user,
):
    """El aviso de contrato por firmar vive en la campana, no en el cuerpo del panel."""
    from django.urls import reverse
    from proyectos.models import Proyecto
    from postulaciones.models import Postulacion
    from contrataciones.models import ContratoDigital

    proyecto = Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto pendiente de firma', descripcion='D',
        tipo_solucion='sitio_web', estado='en_desarrollo',
    )
    postulacion = Postulacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, estado='en_negociacion',
    )
    ContratoDigital.objects.create(postulacion=postulacion, estado='borrador')

    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200
    # El dato sigue disponible para la campana y el badge del sidebar.
    assert response.context['contratos_pendientes_firma_count'] == 1

    content = response.content.decode()
    assert 'Firmar Contratos' not in content
    assert 'pendiente de firma digital' not in content


@pytest.mark.django_db
def test_empresa_dashboard_financial_escrow_widget(auth_client, empresa_user, desarrollador_user):
    """Valida el cálculo en context y renderizado del widget Presupuesto de Contratos Vigentes (Opción A)."""
    from decimal import Decimal
    from django.contrib.auth import get_user_model
    from django.urls import reverse
    from proyectos.models import Proyecto, Entregable
    from postulaciones.models import Postulacion
    from contrataciones.models import Contratacion, ContratoDigital

    # 1. Estado inicial sin compromisos activos
    empty_resp = auth_client.get(reverse('dashboard_empresa'))
    assert empty_resp.status_code == 200
    assert empty_resp.context['presupuesto_total_comprometido'] == Decimal('0')
    assert empty_resp.context['fondos_liberados'] == Decimal('0')
    assert empty_resp.context['fondos_en_custodia'] == Decimal('0')
    assert empty_resp.context['porcentaje_fondos_liberados'] == 0
    empty_html = empty_resp.content.decode()
    assert 'command-financial-card' in empty_html
    assert 'Presupuesto de Contratos' in empty_html
    assert 'Sin compromisos activos' in empty_html
    assert 'SHA-256' in empty_html

    # 2. Con contratos formalizados (firmados y/o con contratación activa) y borrador excluido
    dev2 = get_user_model().objects.create_user(
        username='dev_escrow_2', email='dev_escrow_2@test.jobdevs',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    dev3 = get_user_model().objects.create_user(
        username='dev_escrow_3', email='dev_escrow_3@test.jobdevs',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )

    # Proyecto 1: en_desarrollo con 3 hitos (1 completado -> 1/3 de 3.000.000 = 1.000.000 liberado)
    proy1 = Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto Escrow Hitos',
        descripcion='D1', tipo_solucion='sitio_web', estado='en_desarrollo',
    )
    c1 = Contratacion.objects.create(
        proyecto=proy1, empresa=empresa_user, desarrollador=desarrollador_user, estado='activa',
    )
    p1 = Postulacion.objects.create(proyecto=proy1, desarrollador=desarrollador_user, estado='aceptada')
    ContratoDigital.objects.create(
        postulacion=p1, contratacion=c1, monto=Decimal('3000000.00'), moneda='COP',
        estado='firmado', firmado_empresa=True, firmado_desarrollador=True,
    )
    Entregable.objects.create(proyecto=proy1, titulo='H1', estado='completado')
    Entregable.objects.create(proyecto=proy1, titulo='H2', estado='en_revision')
    Entregable.objects.create(proyecto=proy1, titulo='H3', estado='pendiente')

    # Proyecto 2: finalizado (100% liberado = 2.000.000)
    proy2 = Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto Escrow Finalizado',
        descripcion='D2', tipo_solucion='aplicacion_movil', estado='finalizado',
    )
    c2 = Contratacion.objects.create(
        proyecto=proy2, empresa=empresa_user, desarrollador=dev2, estado='finalizada',
    )
    p2 = Postulacion.objects.create(proyecto=proy2, desarrollador=dev2, estado='aceptada')
    ContratoDigital.objects.create(
        postulacion=p2, contratacion=c2, monto=Decimal('2000000.00'), moneda='COP',
        estado='firmado', firmado_empresa=True, firmado_desarrollador=True,
    )

    # Contrato 3: borrador sin formalizar (NO debe sumarse)
    proy3 = Proyecto.objects.create(
        empresa=empresa_user, titulo='Proyecto Borrador Excluido',
        descripcion='D3', tipo_solucion='automatizacion', estado='publicado',
    )
    p3 = Postulacion.objects.create(proyecto=proy3, desarrollador=dev3, estado='en_negociacion')
    ContratoDigital.objects.create(
        postulacion=p3, monto=Decimal('5000000.00'), moneda='COP',
        estado='pendiente_firma', firmado_empresa=True, firmado_desarrollador=False,
    )

    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200
    assert response.context['presupuesto_total_comprometido'] == Decimal('5000000.00')
    assert response.context['fondos_liberados'] == Decimal('3000000')
    assert response.context['fondos_en_custodia'] == Decimal('2000000.00')
    assert response.context['porcentaje_fondos_liberados'] == 60

    content = response.content.decode()
    assert 'command-financial-card' in content
    assert 'Contratos Vigentes' in content
    assert '60%' in content
    assert 'Presupuesto Total Acordado' in content
    assert 'Hitos Cumplidos' in content
    assert 'Pendiente de Ejecución' in content
    assert '2000000' in content
    assert '5000000' in content
    assert '3000000' in content
    # Asegurar que NO contenga términos erróneos de custodia o retención
    assert 'Custodia Activa' not in content
    assert 'Fondos en Custodia / Garantía' not in content
    assert 'Los fondos se retienen de forma segura' not in content


def test_empresa_dashboard_historial_chart_datasets_and_controls(auth_client, empresa_user, desarrollador_user, db):
    """El historial financiero expone datasets JSON (6m/12m) para las 3 métricas y controles interactivos en el HTML."""
    import json
    from datetime import timedelta
    from decimal import Decimal
    from django.urls import reverse
    from django.utils import timezone
    from proyectos.models import Proyecto, Entregable
    from postulaciones.models import Postulacion
    from contrataciones.models import ContratoDigital

    proyecto = Proyecto.objects.create(
        empresa=empresa_user,
        titulo='Proyecto Analítica Historial',
        descripcion='Desc',
        tipo_solucion='sitio_web',
        estado='en_desarrollo',
    )
    post = Postulacion.objects.create(
        proyecto=proyecto, desarrollador=desarrollador_user, estado='aceptada'
    )
    contrato = ContratoDigital.objects.create(
        postulacion=post, monto=Decimal('4000000.00'), moneda='COP'
    )
    # Contrato de hace ~8 meses (visible en 12m, fuera de 6m)
    ContratoDigital.objects.filter(pk=contrato.pk).update(
        fecha_creacion=timezone.now() - timedelta(days=240)
    )

    # 2 hitos totales: 1 completado este mes, 1 pendiente -> liquidado proporcional = 2,000,000
    Entregable.objects.create(proyecto=proyecto, titulo='Hito Aprobado 1', estado='completado')
    Entregable.objects.create(proyecto=proyecto, titulo='Hito Pendiente 2', estado='pendiente')

    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200
    assert 'chart_datasets_json' in response.context

    datasets = json.loads(response.context['chart_datasets_json'])
    assert set(datasets.keys()) == {'contratado', 'liquidado', 'hitos_qty'}

    for key in ('contratado', 'liquidado', 'hitos_qty'):
        serie = datasets[key]
        assert len(serie['puntos_6m']) == 6
        assert len(serie['puntos_12m']) == 12
        assert 'total_6m' in serie
        assert 'total_12m' in serie
        assert 'label' in serie
        assert all('mes' in p and 'valor' in p for p in serie['puntos_6m'])
        assert all('mes' in p and 'valor' in p for p in serie['puntos_12m'])

    assert datasets['contratado']['label'] == 'Presupuesto Contratado (COP)'
    assert datasets['contratado']['total_6m'] == 0.0
    assert datasets['contratado']['total_12m'] == 4000000.0

    assert datasets['liquidado']['label'] == 'Liquidaciones por Hitos Aprobados (COP)'
    assert datasets['liquidado']['total_6m'] == 2000000.0
    assert datasets['liquidado']['total_12m'] == 2000000.0

    assert datasets['hitos_qty']['label'] == 'Volumen de Hitos Aprobados (Cant.)'
    assert datasets['hitos_qty']['total_6m'] == 1
    assert datasets['hitos_qty']['total_12m'] == 1

    content = response.content.decode()
    assert 'ledger-filter-pill' in content
    assert 'Presupuesto Contratado' in content
    assert 'Hitos Aprobados (COP)' in content
    assert 'Volumen de Hitos' in content
    assert '6 Meses' in content
    assert '12 Meses' in content
    assert 'id="ledgerChartTitle"' in content
    assert 'id="ledgerChartSub"' in content
    assert 'id="ledgerChartTotal"' in content
    assert 'id="empresa-ledger-datasets"' in content
    assert 'empresa/script/empresa.js' in content
    from pathlib import Path
    from django.conf import settings
    ledger_js = Path(settings.BASE_DIR) / 'static/empresa/script/modules/ledger_chart.js'
    assert ledger_js.exists()
    assert 'actualizarGraficaLedger' in ledger_js.read_text(encoding='utf-8')


def test_empresa_dashboard_user_dropdown_menu(auth_client, empresa_user):
    """El topbar de empresa incluye el menú desplegable de usuario y el sidebar omite el grupo Cuenta."""
    response = auth_client.get(reverse('dashboard_empresa'))
    assert response.status_code == 200
    content = response.content.decode()

    # Estructura del dropdown en el topbar
    assert 'user-dropdown-wrapper' in content
    assert 'id="userMenuBtn"' in content
    assert 'onclick="toggleUserMenu(event)"' in content
    assert 'id="userDropdownMenu"' in content
    assert 'user-dropdown-menu' in content

    # Opciones del menú desplegable
    assert 'Perfil de Empresa' in content
    assert "switchTab('perfil')" in content
    assert 'Vista Pública para Talentos' not in content
    assert 'Verificación NIT / Legal' in content
    assert 'abrirModalVerificacion(event)' in content
    assert 'user-dropdown-divider' in content
    assert 'Cerrar Sesión' in content
    assert reverse('logout') in content
    assert 'is-danger' in content

    # El sidebar no debe contener el grupo Cuenta ni el enlace de logout redundante
    sidebar_html = content.split('<aside class="sidebar">')[1].split('</aside>')[0]
    assert 'Cuenta' not in sidebar_html
    assert 'Perfil Empresa' not in sidebar_html
    assert reverse('logout') not in sidebar_html

