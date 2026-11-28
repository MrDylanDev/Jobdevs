import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from postulaciones.models import Postulacion
from proyectos.models import Proyecto

User = get_user_model()


class TestPostulacionModel:
    """Tests for the Postulacion model."""

    def test_crear_postulacion(self, db):
        """Postulacion links dev to proyecto."""
        empresa = User.objects.create_user(
            username='pe', email='pe@test.jobdevs',
            nombre='PE', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='pd', email='pd@test.jobdevs',
            nombre='PD', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='P', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )
        postulacion = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=dev,
            mensaje='Me interesa', estado='pendiente',
        )
        assert postulacion.id is not None
        assert postulacion.estado == 'pendiente'
        assert postulacion.desarrollador == dev

    def test_unique_postulacion(self, db):
        """Same dev can't apply twice to the same proyecto."""
        empresa = User.objects.create_user(
            username='pe2', email='pe2@test.jobdevs',
            nombre='PE2', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='pd2', email='pd2@test.jobdevs',
            nombre='PD2', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='P2', descripcion='D2',
            tipo_solucion='sitio_web', estado='publicado',
        )
        Postulacion.objects.create(proyecto=proyecto, desarrollador=dev)
        with pytest.raises(IntegrityError):
            Postulacion.objects.create(proyecto=proyecto, desarrollador=dev)

    def test_postulacion_str(self, db):
        """__str__ shows dev and proyecto."""
        empresa = User.objects.create_user(
            username='pe3', email='pe3@test.jobdevs',
            nombre='PE3', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='pd3', email='pd3@test.jobdevs',
            nombre='PD3', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='P3', descripcion='D3',
            tipo_solucion='sitio_web', estado='publicado',
        )
        p = Postulacion.objects.create(proyecto=proyecto, desarrollador=dev)
        assert 'pd3' in str(p)
        assert 'P3' in str(p)


class TestPostularse:
    """Tests for postularse_a_proyecto view."""

    def test_dev_puede_postularse(self, dev_client, desarrollador_user, empresa_user):
        """Dev can apply to a published project."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy Post',
            descripcion='DP', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = dev_client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'Hola', 'experiencia': 'Mucha', 'link': 'http://example.com'}
        )
        assert response.status_code == 302
        assert Postulacion.objects.filter(
            proyecto=proyecto, desarrollador=desarrollador_user
        ).exists()

    def test_empresa_no_puede_postularse(self, auth_client, empresa_user):
        """Empresa cannot apply to projects."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='No Post',
            descripcion='NP', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = auth_client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'X', 'experiencia': 'Y', 'link': 'Z'}
        )
        assert response.status_code == 302
        assert not Postulacion.objects.filter(proyecto=proyecto).exists()

    def test_dev_no_verificado_no_puede_postularse(self, dev_client, desarrollador_user, empresa_user):
        """Dev without SENA verification cannot apply to projects."""
        desarrollador_user.perfil_desarrollador.estado_verificacion = 'sin_verificar'
        desarrollador_user.perfil_desarrollador.save()

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy Guard',
            descripcion='DP', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = dev_client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'Hola', 'experiencia': 'Mucha', 'link': 'http://example.com'}
        )
        assert response.status_code == 302
        assert response.url == reverse('solicitar_verificacion_desarrollador')
        assert not Postulacion.objects.filter(
            proyecto=proyecto, desarrollador=desarrollador_user
        ).exists()

    @pytest.mark.parametrize('estado_invalido', ['en_revision', 'rechazado'])
    def test_dev_estado_no_verificado_bloqueado(self, dev_client, desarrollador_user, empresa_user, estado_invalido):
        """Dev with en_revision or rechazado verification cannot apply."""
        desarrollador_user.perfil_desarrollador.estado_verificacion = estado_invalido
        desarrollador_user.perfil_desarrollador.save()

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy Bloqueado',
            descripcion='DP', tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = dev_client.get(reverse('postularse_a_proyecto', args=[proyecto.id]))
        assert response.status_code == 302
        assert response.url == reverse('solicitar_verificacion_desarrollador')

    def test_no_postularse_proyecto_no_publicado(self, dev_client, empresa_user):
        """Un proyecto en desarrollo sin cupo libre no acepta postulaciones (RF 3.1.1)."""
        from contrataciones.models import Contratacion
        otro_dev = User.objects.create_user(
            username='dev_ocupado', email='dev_ocupado@test.jobdevs',
            nombre='Dev Ocupado', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Cerrado',
            descripcion='C', tipo_solucion='sitio_web',
            estado='en_desarrollo', vacantes=1,
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=otro_dev,
            empresa=empresa_user, estado='activa',
        )
        response = dev_client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'H', 'experiencia': 'E', 'link': 'L'}
        )
        assert response.status_code == 302
        assert not Postulacion.objects.filter(proyecto=proyecto).exists()

    def test_postularse_a_proyecto_en_desarrollo_con_cupo(self, dev_client, empresa_user):
        """Con cupo libre, un proyecto en desarrollo sigue recibiendo postulaciones (RF 3.1.1)."""
        from contrataciones.models import Contratacion
        otro_dev = User.objects.create_user(
            username='dev_activo', email='dev_activo@test.jobdevs',
            nombre='Dev Activo', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Abierto', descripcion='A',
            tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=2,
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=otro_dev,
            empresa=empresa_user, estado='activa',
        )
        response = dev_client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'H', 'experiencia': 'E', 'link': 'L'}
        )
        assert response.status_code == 302
        assert Postulacion.objects.filter(proyecto=proyecto, desarrollador__username='dev_test').exists()

    def test_postularse_notifica_a_la_empresa(self, dev_client, empresa_user):
        """RF 6.2.2: la empresa recibe una Notificacion al recibir la postulación."""
        from notificaciones.models import Notificacion
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Notifica', descripcion='N',
            tipo_solucion='sitio_web', estado='publicado',
        )
        dev_client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'Hola', 'experiencia': 'E', 'link': 'L'}
        )
        assert Notificacion.objects.filter(
            usuario=empresa_user, proyecto=proyecto, tipo='postulacion'
        ).exists()


class TestAceptarPostulacion:
    """Tests for aceptar_postulacion view."""

    def test_ruta_heredada_no_contrata_sin_firmas(self, auth_client, empresa_user, desarrollador_user):
        from contrataciones.models import Contratacion, ContratoDigital

        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Firma requerida', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado', vacantes=1,
        )
        postulacion = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, estado='pendiente',
        )

        response = auth_client.post(reverse('aceptar_postulacion', args=[postulacion.id]))

        assert response.status_code == 302
        postulacion.refresh_from_db()
        proyecto.refresh_from_db()
        assert postulacion.estado == 'en_negociacion'
        assert proyecto.estado == 'publicado'
        assert not Contratacion.objects.filter(proyecto=proyecto).exists()
        contrato = ContratoDigital.objects.get(postulacion=postulacion)
        assert not contrato.firmado_empresa
        assert not contrato.firmado_desarrollador

    def test_empresa_inicia_negociacion_por_url_antigua(self, auth_client, empresa_user, desarrollador_user):
        """La URL antigua reserva cupo pero no contrata sin firmas."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='PA', descripcion='DA',
            tipo_solucion='sitio_web', estado='publicado',
        )
        postulacion = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            estado='pendiente',
        )
        response = auth_client.post(
            reverse('aceptar_postulacion', args=[postulacion.id])
        )
        assert response.status_code == 302
        postulacion.refresh_from_db()
        assert postulacion.estado == 'en_negociacion'
        proyecto.refresh_from_db()
        assert proyecto.estado == 'publicado'
        from contrataciones.models import Contratacion, ContratoDigital
        assert ContratoDigital.objects.filter(postulacion=postulacion).exists()
        assert not Contratacion.objects.filter(proyecto=proyecto).exists()

    def test_dev_no_puede_aceptar(self, dev_client, empresa_user, desarrollador_user):
        """Dev cannot accept postulaciones."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='PAD', descripcion='DAD',
            tipo_solucion='sitio_web', estado='publicado',
        )
        postulacion = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            estado='pendiente',
        )
        response = dev_client.post(
            reverse('aceptar_postulacion', args=[postulacion.id])
        )
        assert response.status_code == 302
        postulacion.refresh_from_db()
        assert postulacion.estado == 'pendiente'

    def test_no_puede_aceptar_si_limite_de_vacantes_alcanzado(self, auth_client, empresa_user, desarrollador_user):
        """RF 3.3.2: No se permite contratar si el proyecto ya cubrió sus vacantes.

        Nota sobre concurrencia (SCRUM-159):
        Esta prueba valida la regla de negocio secuencial del límite de cupos.
        La protección contra carreras concurrentes mediante bloqueo de fila
        (`select_for_update`) y atomicidad se verifica en
        `test_concurrencia_locking_proyecto_select_for_update`.
        """
        from contrataciones.models import Contratacion
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='P Vacantes', descripcion='DV',
            tipo_solucion='sitio_web', estado='publicado', vacantes=1,
        )
        post1 = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, estado='pendiente',
        )
        dev2 = User.objects.create_user(
            username='dev2_cupos', email='dev2_cupos@test.jobdevs',
            nombre='Dev 2 Cupos', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        post2 = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=dev2, estado='pendiente',
        )

        # 1. Iniciar negociación con la primera postulación (reserva la vacante)
        res1 = auth_client.post(reverse('aceptar_postulacion', args=[post1.id]))
        assert res1.status_code == 302
        post1.refresh_from_db()
        assert post1.estado == 'en_negociacion'
        assert Contratacion.objects.filter(proyecto=proyecto, estado='activa').count() == 0

        # 2. Intentar reservar la misma vacante debe ser rechazado
        res2 = auth_client.post(reverse('aceptar_postulacion', args=[post2.id]), follow=True)
        assert res2.status_code == 200
        post2.refresh_from_db()
        assert post2.estado == 'pendiente'
        assert Contratacion.objects.filter(proyecto=proyecto, estado='activa').count() == 0
        messages = list(res2.context['messages'])
        assert any('vacantes' in str(m).lower() for m in messages)

    def test_no_puede_aceptar_si_proyecto_finalizado(self, auth_client, empresa_user, desarrollador_user):
        """No se pueden aceptar postulaciones si el proyecto ya está finalizado."""
        from contrataciones.models import Contratacion
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='P Fin', descripcion='DF',
            tipo_solucion='sitio_web', estado='finalizado', vacantes=2,
        )
        post = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, estado='pendiente',
        )
        res = auth_client.post(reverse('aceptar_postulacion', args=[post.id]), follow=True)
        assert res.status_code == 200
        post.refresh_from_db()
        assert post.estado == 'pendiente'
        assert not Contratacion.objects.filter(proyecto=proyecto).exists()
        messages = list(res.context['messages'])
        assert any('finalizado' in str(m).lower() or 'estado' in str(m).lower() for m in messages)

    def test_concurrencia_locking_proyecto_select_for_update(self, auth_client, empresa_user, desarrollador_user):
        """SCRUM-159: Verificar que la transacción bloquea la fila del proyecto vía select_for_update."""
        from unittest.mock import patch
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='P Lock', descripcion='DL',
            tipo_solucion='sitio_web', estado='publicado', vacantes=1,
        )
        post = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, estado='pendiente',
        )

        with patch.object(Proyecto.objects, 'select_for_update', wraps=Proyecto.objects.select_for_update) as mock_lock:
            res = auth_client.post(reverse('aceptar_postulacion', args=[post.id]))
            assert res.status_code == 302
            assert mock_lock.called, "select_for_update debe ser invocado sobre Proyecto para serializar contrataciones"



class TestPostulacionEnNegociacion:
    """SCRUM-150/151: el estado en_negociacion reserva cupo de vacantes."""

    def _escenario(self, empresa_user, desarrollador_user, vacantes=2):
        from contrataciones.models import Contratacion
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='P Negociacion', descripcion='DN',
            tipo_solucion='sitio_web', estado='en_desarrollo', vacantes=vacantes,
        )
        dev_activo = User.objects.create_user(
            username='dev_activo_neg', email='dev_activo_neg@test.jobdevs',
            nombre='Dev Activo', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=dev_activo,
            empresa=empresa_user, estado='activa',
        )
        return proyecto

    def test_crear_postulacion_en_negociacion(self, empresa_user, desarrollador_user):
        from django.utils import timezone
        proyecto = self._escenario(empresa_user, desarrollador_user)
        limite = timezone.now() + timezone.timedelta(days=3)
        post = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            estado='en_negociacion', fecha_limite_negociacion=limite,
        )
        post.refresh_from_db()
        assert post.estado == 'en_negociacion'
        assert post.fecha_limite_negociacion == limite
        assert post.get_estado_display() == 'En Negociación'

    def test_en_negociacion_descuenta_vacantes_disponibles_en_dashboard(
            self, auth_client, empresa_user, desarrollador_user):
        proyecto = self._escenario(empresa_user, desarrollador_user, vacantes=3)

        res = auth_client.get(reverse('dashboard_empresa'))
        item = next(i for i in res.context['en_desarrollo_v'] if i['proyecto_id'] == proyecto.id)
        assert item['vacantes_disponibles'] == 2  # 3 - 1 contratación activa

        Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, estado='en_negociacion',
        )
        res = auth_client.get(reverse('dashboard_empresa'))
        item = next(i for i in res.context['en_desarrollo_v'] if i['proyecto_id'] == proyecto.id)
        assert item['vacantes_disponibles'] == 1  # 3 - 1 activa - 1 en negociación

    def test_en_negociacion_bloquea_aceptar_otra_postulacion_sin_cupo(
            self, auth_client, empresa_user, desarrollador_user):
        from contrataciones.models import Contratacion
        proyecto = self._escenario(empresa_user, desarrollador_user, vacantes=2)
        Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, estado='en_negociacion',
        )
        dev2 = User.objects.create_user(
            username='dev2_neg', email='dev2_neg@test.jobdevs',
            nombre='Dev 2 Neg', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        post2 = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=dev2, estado='pendiente',
        )

        res = auth_client.post(reverse('aceptar_postulacion', args=[post2.id]), follow=True)
        assert res.status_code == 200
        post2.refresh_from_db()
        assert post2.estado == 'pendiente'
        assert Contratacion.objects.filter(proyecto=proyecto, estado='activa').count() == 1
        assert any('vacantes' in str(m).lower() for m in res.context['messages'])


class TestVerPostulacionesEmpresaFiltros:
    """SCRUM-146 (HU-E08): filtros por habilidades, programa y ficha."""

    @staticmethod
    def _crear_candidato(proyecto, username, programa, ficha, habilidades):
        from usuarios.models import PerfilDesarrollador
        dev = User.objects.create_user(
            username=username, email=f'{username}@test.jobdevs',
            nombre=username.upper(), rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        PerfilDesarrollador.objects.update_or_create(
            usuario=dev,
            defaults={
                'programa_formacion': programa,
                'ficha': ficha,
                'habilidades': habilidades,
            },
        )
        Postulacion.objects.create(proyecto=proyecto, desarrollador=dev, estado='pendiente')
        return dev

    @pytest.fixture
    def escenario(self, empresa_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='P Filtros', descripcion='DF',
            tipo_solucion='sitio_web', estado='publicado', vacantes=3,
        )
        self._crear_candidato(proyecto, 'ana', 'ADSO', '2558104', 'Python, Django, SQL')
        self._crear_candidato(proyecto, 'beto', 'Multimedia', '2600001', 'React, JavaScript')
        self._crear_candidato(proyecto, 'carla', 'ADSO', '2700002', 'React, SQL')
        return proyecto

    @staticmethod
    def _nombres(response):
        return sorted(p['desarrollador']['nombre'] for p in response.context['postulaciones'])

    def test_filtrar_por_programa_formacion(self, auth_client, escenario):
        res = auth_client.get(
            reverse('ver_postulaciones_empresa', args=[escenario.id]),
            {'programa': 'Multimedia'},
        )
        assert res.status_code == 200
        assert self._nombres(res) == ['BETO']
        assert res.context['filtros']['programa'] == 'Multimedia'
        assert res.context['programas_disponibles'] == ['ADSO', 'Multimedia']

    def test_filtrar_por_ficha(self, auth_client, escenario):
        res = auth_client.get(
            reverse('ver_postulaciones_empresa', args=[escenario.id]),
            {'ficha': '2558104'},
        )
        assert res.status_code == 200
        assert self._nombres(res) == ['ANA']

    def test_filtrar_por_estado_funnel(self, auth_client, escenario):
        # Mover un candidato a 'en_negociacion'
        p_beto = Postulacion.objects.get(proyecto=escenario, desarrollador__username='beto')
        p_beto.estado = 'en_negociacion'
        p_beto.save()

        # Consulta general: muestra pendientes y en negociación, y conteos de embudo
        res = auth_client.get(reverse('ver_postulaciones_empresa', args=[escenario.id]))
        assert res.status_code == 200
        assert res.context['conteos_funnel']['total'] == 3
        assert res.context['conteos_funnel']['pendientes'] == 2
        assert res.context['conteos_funnel']['en_negociacion'] == 1
        content = res.content.decode()
        assert 'funnel-tabs-grid' in content
        assert 'candidatos-split-layout' in content

        # Filtrar por 'en_negociacion'
        res_neg = auth_client.get(
            reverse('ver_postulaciones_empresa', args=[escenario.id]),
            {'estado': 'en_negociacion'},
        )
        assert res_neg.status_code == 200
        assert self._nombres(res_neg) == ['BETO']
        assert res_neg.context['filtros']['estado'] == 'en_negociacion'

    def test_filtrar_por_habilidades(self, auth_client, escenario):
        url = reverse('ver_postulaciones_empresa', args=[escenario.id])
        res = auth_client.get(url, {'habilidad': 'react'})
        assert self._nombres(res) == ['BETO', 'CARLA']

        # Varios términos separados por comas: el candidato debe cumplir todos
        res = auth_client.get(url, {'habilidad': 'REACT, sql'})
        assert self._nombres(res) == ['CARLA']

        # Sin coincidencias: lista vacía y mensaje para restablecer filtros
        res = auth_client.get(url, {'habilidad': 'cobol'})
        assert res.context['postulaciones'] == []
        assert 'Restablecer filtros' in res.content.decode()

    def test_filtros_combinados(self, auth_client, escenario):
        res = auth_client.get(
            reverse('ver_postulaciones_empresa', args=[escenario.id]),
            {'programa': 'ADSO', 'habilidad': 'react'},
        )
        assert res.status_code == 200
        assert self._nombres(res) == ['CARLA']

    def test_otra_empresa_no_puede_ver_postulaciones(self, client, escenario):
        User.objects.create_user(
            username='otra_empresa', email='otra@test.jobdevs',
            nombre='Otra', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        client.login(username='otra_empresa', password='TestPass123!')
        res = client.get(
            reverse('ver_postulaciones_empresa', args=[escenario.id]),
            {'programa': 'ADSO'},
        )
        assert res.status_code == 404


class TestIniciarNegociacion:
    """SCRUM-149: la empresa inicia negociación y se crea el contrato digital borrador."""

    @pytest.fixture
    def escenario(self, empresa_user, desarrollador_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='P Negociar', descripcion='DN',
            tipo_solucion='sitio_web', estado='publicado', vacantes=1,
        )
        post = Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, estado='pendiente',
        )
        return proyecto, post

    def test_inicia_negociacion_crea_contrato_notifica_y_redirige_al_chat(
            self, auth_client, escenario, desarrollador_user):
        from django.utils import timezone

        from contrataciones.models import ContratoDigital
        from logs.models import LogAuditoria
        from notificaciones.models import Notificacion
        proyecto, post = escenario

        antes = timezone.now()
        res = auth_client.post(reverse('iniciar_negociacion', args=[post.id]))

        assert res.status_code == 302
        assert res.url == reverse('sala_chat', args=[desarrollador_user.id, proyecto.id])
        post.refresh_from_db()
        assert post.estado == 'en_negociacion'
        delta = post.fecha_limite_negociacion - antes
        assert 6 < delta.days + delta.seconds / 86400 <= 7.01
        contrato = ContratoDigital.objects.get(postulacion=post)
        assert contrato.estado == 'borrador'
        assert Notificacion.objects.filter(usuario=desarrollador_user, proyecto=proyecto).exists()
        assert LogAuditoria.objects.filter(
            tabla_afectada='postulaciones', registro_id=post.id,
            accion__contains='negociación').exists()

    def test_usa_plazo_configurado_y_lo_congela_en_la_negociacion(
            self, auth_client, escenario, admin_user, desarrollador_user):
        from notificaciones.models import Notificacion
        from postulaciones import services

        proyecto, post = escenario
        services.actualizar_plazo_negociacion_dias(15, admin_user)
        antes = timezone.now()

        auth_client.post(reverse('iniciar_negociacion', args=[post.id]))

        post.refresh_from_db()
        limite_congelado = post.fecha_limite_negociacion
        assert 14.99 <= (limite_congelado - antes).total_seconds() / 86400 <= 15.01
        aviso = Notificacion.objects.get(
            usuario=desarrollador_user, proyecto=proyecto, tipo='postulacion'
        )
        assert '15 días' in aviso.mensaje

        services.actualizar_plazo_negociacion_dias(2, admin_user)
        post.refresh_from_db()
        assert post.fecha_limite_negociacion == limite_congelado

    def test_requiere_post(self, auth_client, escenario):
        _, post = escenario
        assert auth_client.get(reverse('iniciar_negociacion', args=[post.id])).status_code == 405

    def test_notifica_a_la_empresa_que_el_contrato_espera_su_firma(
            self, auth_client, escenario, empresa_user):
        """El aviso dejó de ocupar el dashboard: ahora vive en la campana."""
        from notificaciones.models import Notificacion

        proyecto, post = escenario
        auth_client.post(reverse('iniciar_negociacion', args=[post.id]))

        aviso = Notificacion.objects.get(
            usuario=empresa_user, proyecto=proyecto, tipo='alerta',
        )
        assert 'firma' in aviso.mensaje.lower()
        assert proyecto.titulo in aviso.mensaje
        assert aviso.leida is False

    def test_dev_no_puede_iniciar_negociacion(self, dev_client, escenario):
        _, post = escenario
        dev_client.post(reverse('iniciar_negociacion', args=[post.id]))
        post.refresh_from_db()
        assert post.estado == 'pendiente'

    def test_otra_empresa_recibe_404(self, client, escenario):
        _, post = escenario
        User.objects.create_user(
            username='otra_emp', email='otra_emp@test.jobdevs', nombre='Otra',
            rol='empresa', estado='activo', password='TestPass123!',
        )
        client.login(username='otra_emp', password='TestPass123!')
        res = client.post(reverse('iniciar_negociacion', args=[post.id]))
        assert res.status_code == 404
        post.refresh_from_db()
        assert post.estado == 'pendiente'

    def test_solo_desde_pendiente(self, auth_client, escenario):
        from contrataciones.models import ContratoDigital
        _, post = escenario
        post.estado = 'rechazada'
        post.save()
        auth_client.post(reverse('iniciar_negociacion', args=[post.id]))
        post.refresh_from_db()
        assert post.estado == 'rechazada'
        assert not ContratoDigital.objects.filter(postulacion=post).exists()

    def test_bloquea_si_no_hay_cupo(self, auth_client, escenario):
        from contrataciones.models import ContratoDigital
        proyecto, post = escenario
        dev2 = User.objects.create_user(
            username='dev_neg2', email='dev_neg2@test.jobdevs', nombre='Dev N2',
            rol='desarrollador', estado='activo', password='TestPass123!',
        )
        Postulacion.objects.create(proyecto=proyecto, desarrollador=dev2, estado='en_negociacion')

        res = auth_client.post(reverse('iniciar_negociacion', args=[post.id]), follow=True)
        post.refresh_from_db()
        assert post.estado == 'pendiente'
        assert not ContratoDigital.objects.filter(postulacion=post).exists()
        assert any('vacantes' in str(m).lower() for m in res.context['messages'])

    def test_lista_recibidas_muestra_acciones_segun_estado(self, auth_client, escenario, desarrollador_user):
        from contrataciones.models import ContratoDigital
        proyecto, post = escenario
        url = reverse('ver_postulaciones_empresa', args=[proyecto.id])

        html = auth_client.get(url).content.decode()
        assert reverse('iniciar_negociacion', args=[post.id]) in html
        assert reverse('aceptar_postulacion', args=[post.id]) not in html
        assert reverse('rechazar_postulacion', args=[post.id]) in html

        auth_client.post(reverse('iniciar_negociacion', args=[post.id]))
        contrato = ContratoDigital.objects.get(postulacion=post)
        html = auth_client.get(url).content.decode()
        assert 'En Negociación' in html
        assert reverse('ver_contrato_digital', args=[contrato.id]) in html
        assert 'Continuar en el Chat' not in html
        assert reverse('iniciar_negociacion', args=[post.id]) not in html

    def test_vista_rechazar_postulacion_exito(self, auth_client, escenario):
        _, post = escenario
        url = reverse('rechazar_postulacion', args=[post.id])
        res = auth_client.post(url, follow=True)
        assert res.status_code == 200
        post.refresh_from_db()
        assert post.estado == 'rechazada'
        assert any('ha sido rechazada' in str(m) for m in res.context['messages'])

    def test_vista_rechazar_postulacion_no_empresa_denegado(self, dev_client, escenario):
        _, post = escenario
        url = reverse('rechazar_postulacion', args=[post.id])
        res = dev_client.post(url, follow=True)
        assert res.status_code == 200
        post.refresh_from_db()
        assert post.estado == 'pendiente'

    def test_lista_recibidas_muestra_badge_verificado_con_fecha(self, auth_client, escenario, desarrollador_user):
        """SCRUM-231 (RF 9.2.2): La lista de postulaciones muestra el badge de verificación y su fecha."""
        proyecto, post = escenario
        perfil = desarrollador_user.perfil_desarrollador
        perfil.estado_verificacion = 'verificado'
        perfil.condicion_sena = 'egresado'
        perfil.fecha_verificacion = timezone.now()
        perfil.save()

        url = reverse('ver_postulaciones_empresa', args=[proyecto.id])
        res = auth_client.get(url)
        assert res.status_code == 200
        html = res.content.decode()

        assert 'badge-sena-postulante' in html
        assert 'Egresado SENA' in html
        assert 'Verificado el' in html


@pytest.mark.django_db
class TestDrawerCandidatosHTMX:
    """Pruebas S4: Drawer de Candidatos de Empresa vía HTMX (`HX-Request: true`)."""

    @pytest.fixture
    def escenario(self, empresa_user, desarrollador_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo="Plataforma HTMX",
            descripcion="Descripción",
            tipo_solucion="app_web",
            estado="publicado",
            vacantes=2,
        )
        post = Postulacion.objects.create(
            proyecto=proyecto,
            desarrollador=desarrollador_user,
            mensaje="Quiero aportar al proyecto.",
            estado="pendiente",
        )
        return proyecto, post

    def test_ver_postulaciones_htmx_retorna_partial_drawer(self, auth_client, escenario):
        proyecto, post = escenario
        url = reverse('ver_postulaciones_empresa', args=[proyecto.id])
        res = auth_client.get(url, HTTP_HX_REQUEST='true')

        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in html
        assert 'drawer-funnel-tabs' in html
        assert 'hx-target="#drawerContent"' in html
        assert 'drawer-candidates-list' in html
        assert 'drawer-candidate-card' in html
        assert f'hx-post="{reverse("iniciar_negociacion", args=[post.id])}"' in html
        assert f'hx-post="{reverse("rechazar_postulacion", args=[post.id])}"' in html

    def test_ver_postulaciones_htmx_estado_vacio(self, auth_client, escenario):
        proyecto, _ = escenario
        url = f"{reverse('ver_postulaciones_empresa', args=[proyecto.id])}?estado=aceptada"
        res = auth_client.get(url, HTTP_HX_REQUEST='true')

        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'drawer-funnel-tabs' in html
        assert 'activity-empty' in html

    def test_ver_postulaciones_htmx_escapa_xss(self, auth_client, escenario, desarrollador_user):
        proyecto, post = escenario
        desarrollador_user.nombre = '<script>alert("dev")</script>'
        desarrollador_user.save(update_fields=['nombre'])
        post.mensaje = '<img src=x onerror=alert(1)>'
        post.save(update_fields=['mensaje'])

        url = reverse('ver_postulaciones_empresa', args=[proyecto.id])
        res = auth_client.get(url, HTTP_HX_REQUEST='true')
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert '<script>alert("dev")</script>' not in html
        assert '&lt;script&gt;alert(&quot;dev&quot;)&lt;/script&gt;' in html
        assert '<img src=x onerror=alert(1)>' not in html
        assert '&lt;img src=x onerror=alert(1)&gt;' in html

    def test_iniciar_negociacion_htmx_re_renderiza_drawer_y_emite_toast(self, auth_client, escenario):
        import json
        _, post = escenario
        url = reverse('iniciar_negociacion', args=[post.id])
        res = auth_client.post(url, {'estado_filtro': ''}, HTTP_HX_REQUEST='true')

        assert res.status_code == 200
        post.refresh_from_db()
        assert post.estado == 'en_negociacion'
        html = res.content.decode('utf-8')
        assert 'drawer-funnel-tabs' in html
        assert 'Ver Contrato Digital' in html
        hx_trigger = json.loads(res['HX-Trigger'])
        assert hx_trigger['jobdevs:toast']['tipo'] == 'success'
        assert 'Negociación iniciada' in hx_trigger['jobdevs:toast']['mensaje']

    def test_rechazar_postulacion_htmx_re_renderiza_drawer_y_emite_toast(self, auth_client, escenario):
        import json
        _, post = escenario
        url = reverse('rechazar_postulacion', args=[post.id])
        res = auth_client.post(url, {'estado_filtro': 'pendiente'}, HTTP_HX_REQUEST='true')

        assert res.status_code == 200
        post.refresh_from_db()
        assert post.estado == 'rechazada'
        html = res.content.decode('utf-8')
        assert 'drawer-funnel-tabs' in html
        hx_trigger = json.loads(res['HX-Trigger'])
        assert hx_trigger['jobdevs:toast']['tipo'] == 'success'
        assert 'ha sido rechazada' in hx_trigger['jobdevs:toast']['mensaje']

    def test_rechazar_preserva_json_con_accept_json(self, auth_client, escenario):
        _, post = escenario
        url = reverse('rechazar_postulacion', args=[post.id])
        res = auth_client.post(
            url,
            HTTP_HX_REQUEST='true',
            HTTP_ACCEPT='application/json',
        )
        assert res.status_code == 200
        data = res.json()
        assert data['status'] == 'ok'




class TestPostularseAjax:
    """El modal del dashboard envía la postulación por fetch y espera JSON."""

    def test_cuenta_suspendida_no_puede_postularse(self, dev_client, desarrollador_user, empresa_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Oferta protegida', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )
        desarrollador_user.estado = 'suspendido'
        desarrollador_user.save(update_fields=['estado'])

        respuesta = self._post_ajax(dev_client, proyecto)
        assert respuesta.status_code == 302
        assert respuesta.url == reverse('login')
        assert not Postulacion.objects.filter(
            proyecto=proyecto, desarrollador=desarrollador_user,
        ).exists()

    def _post_ajax(self, client, proyecto, **extra):
        data = {'carta': 'Me interesa este proyecto.', 'experiencia': 'Django', 'link': '', 'origen': 'dashboard'}
        data.update(extra)
        return client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

    def test_ajax_postulacion_exitosa(self, dev_client, desarrollador_user, empresa_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy Modal', descripcion='DM',
            tipo_solucion='sitio_web', estado='publicado',
        )
        response = self._post_ajax(dev_client, proyecto)

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['proyecto_id'] == proyecto.id
        assert Postulacion.objects.filter(
            proyecto=proyecto, desarrollador=desarrollador_user
        ).exists()

    def test_ajax_carta_obligatoria(self, dev_client, empresa_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy Sin Carta', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )
        response = self._post_ajax(dev_client, proyecto, carta='   ')

        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False
        assert 'carta' in data['mensaje'].lower()
        assert not Postulacion.objects.filter(proyecto=proyecto).exists()

    def test_ajax_no_verificado_pide_verificacion(self, dev_client, desarrollador_user, empresa_user):
        desarrollador_user.perfil_desarrollador.estado_verificacion = 'sin_verificar'
        desarrollador_user.perfil_desarrollador.save()
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy Verif', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )
        response = self._post_ajax(dev_client, proyecto)

        assert response.status_code == 403
        data = response.json()
        assert data['ok'] is False
        assert data['requiere_verificacion'] is True
        assert not Postulacion.objects.filter(proyecto=proyecto).exists()

    def test_ajax_duplicado_devuelve_409(self, dev_client, desarrollador_user, empresa_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy Dup', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )
        Postulacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            mensaje='Primera', estado='pendiente',
        )
        response = self._post_ajax(dev_client, proyecto)

        assert response.status_code == 409
        data = response.json()
        assert data['ok'] is False
        assert Postulacion.objects.filter(proyecto=proyecto).count() == 1

    def test_ajax_empresa_no_puede_postularse(self, auth_client, empresa_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy Empresa', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )
        response = self._post_ajax(auth_client, proyecto)

        assert response.status_code == 403
        assert response.json()['ok'] is False
        assert not Postulacion.objects.filter(proyecto=proyecto).exists()

    def test_ajax_error_inesperado_no_filtra_str_e(self, dev_client, desarrollador_user, empresa_user, monkeypatch):
        """SCRUM-445: Errores inesperados en postulación no deben filtrar detalles internos str(e)."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proy Leak Test', descripcion='D',
            tipo_solucion='sitio_web', estado='publicado',
        )

        def mock_create(*args, **kwargs):
            raise RuntimeError("DB_SECRET_INTERNAL_ERROR_XYZ")

        monkeypatch.setattr(Postulacion.objects, 'create', mock_create)
        response = self._post_ajax(dev_client, proyecto)

        assert response.status_code == 500
        data = response.json()
        assert data['ok'] is False
        assert 'DB_SECRET_INTERNAL_ERROR_XYZ' not in data['mensaje']
        assert 'error inesperado' in data['mensaje'].lower()


@pytest.mark.django_db
class TestPostularseHTMX:
    """Pruebas S2: Postulación de Desarrollador vía HTMX (`HX-Request: true`)."""

    def _post_htmx(self, client, proyecto, extra_data=None, **headers):
        data = {
            'carta': 'Me interesa aportar al proyecto.',
            'experiencia': 'Django y HTMX',
            'link': '',
            'origen': 'dashboard',
        }
        if extra_data:
            data.update(extra_data)
        req_headers = {'HTTP_HX_REQUEST': 'true'}
        req_headers.update(headers)
        return client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            data,
            **req_headers,
        )

    def test_htmx_postulacion_exitosa_retorna_card_y_hx_trigger(
        self, dev_client, desarrollador_user, empresa_user
    ):
        import json

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Plataforma HTMX Dev',
            descripcion='Desc',
            tipo_solucion='app_web',
            modalidad='remoto',
            estado='publicado',
        )
        response = self._post_htmx(dev_client, proyecto)

        assert response.status_code == 200
        assert Postulacion.objects.filter(
            proyecto=proyecto, desarrollador=desarrollador_user
        ).exists()

        html = response.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in html
        assert 'post-row-compact' in html
        assert 'Plataforma HTMX Dev' in html
        assert 'data-ver-proyecto' in html
        assert 'data-abrir-empresa' in html

        hx_trigger = json.loads(response['HX-Trigger'])
        assert hx_trigger['jobdevs:toast']['tipo'] == 'success'
        assert 'Plataforma HTMX Dev' in hx_trigger['jobdevs:toast']['mensaje']
        assert hx_trigger['jobdevs:postulacion-creada'] == {
            'proyecto_id': proyecto.id,
            'requiere_verificacion': False,
        }

    def test_htmx_postulacion_escapa_xss(self, dev_client, empresa_user):
        empresa_user.nombre = '<img src=x onerror=alert(1)>'
        empresa_user.save(update_fields=['nombre'])
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='<script>alert("xss")</script>',
            descripcion='Desc',
            tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = self._post_htmx(dev_client, proyecto)

        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert '<script>alert("xss")</script>' not in html
        assert '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;' in html
        assert '<img src=x onerror=alert(1)>' not in html
        assert '&lt;img src=x onerror=alert(1)&gt;' in html

    def test_htmx_carta_obligatoria_retorna_error_y_toast(self, dev_client, empresa_user):
        import json

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proy Carta HTMX',
            descripcion='D',
            tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = self._post_htmx(dev_client, proyecto, extra_data={'carta': '   '})

        assert response.status_code == 400
        assert response['HX-Reswap'] == 'none'
        assert not Postulacion.objects.filter(proyecto=proyecto).exists()
        hx_trigger = json.loads(response['HX-Trigger'])
        assert hx_trigger['jobdevs:toast']['tipo'] == 'error'
        assert 'carta' in hx_trigger['jobdevs:toast']['mensaje'].lower()

    def test_htmx_duplicado_retorna_409_y_toast(
        self, dev_client, desarrollador_user, empresa_user
    ):
        import json

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proy Dup HTMX',
            descripcion='D',
            tipo_solucion='sitio_web',
            estado='publicado',
        )
        Postulacion.objects.create(
            proyecto=proyecto,
            desarrollador=desarrollador_user,
            mensaje='Primera',
            estado='pendiente',
        )
        response = self._post_htmx(dev_client, proyecto)

        assert response.status_code == 409
        assert response['HX-Reswap'] == 'none'
        assert Postulacion.objects.filter(proyecto=proyecto).count() == 1
        hx_trigger = json.loads(response['HX-Trigger'])
        assert hx_trigger['jobdevs:toast']['tipo'] in ('warning', 'error')
        assert 'anteriormente' in hx_trigger['jobdevs:toast']['mensaje'].lower()

    def test_htmx_no_verificado_retorna_403_requiere_verificacion(
        self, dev_client, desarrollador_user, empresa_user
    ):
        import json

        desarrollador_user.perfil_desarrollador.estado_verificacion = 'sin_verificar'
        desarrollador_user.perfil_desarrollador.save()
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proy Verif HTMX',
            descripcion='D',
            tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = self._post_htmx(dev_client, proyecto)

        assert response.status_code == 403
        assert response['HX-Reswap'] == 'none'
        assert not Postulacion.objects.filter(proyecto=proyecto).exists()
        hx_trigger = json.loads(response['HX-Trigger'])
        assert hx_trigger['jobdevs:toast']['tipo'] == 'error'
        assert hx_trigger['jobdevs:postulacion-error']['requiere_verificacion'] is True

    def test_htmx_con_accept_json_preserva_respuesta_json(self, dev_client, empresa_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proy JSON Accept',
            descripcion='D',
            tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = self._post_htmx(
            dev_client, proyecto, HTTP_ACCEPT='application/json'
        )
        assert response.status_code == 200
        assert response.json()['ok'] is True

    def test_htmx_con_xhr_preserva_respuesta_json(self, dev_client, empresa_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proy JSON XHR',
            descripcion='D',
            tipo_solucion='sitio_web',
            estado='publicado',
        )
        response = self._post_htmx(
            dev_client, proyecto, HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 200
        assert response.json()['ok'] is True


@pytest.mark.django_db
class TestListaRecibidasStandaloneHTMX:
    """Pruebas S2 (Phase 4): Postulaciones Recibidas standalone vía HTMX (`HX-Target: postulacionesSplitWrap`)."""

    @pytest.fixture
    def escenario(self, empresa_user, desarrollador_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo="Convocatoria Split HTMX",
            descripcion="Descripción",
            tipo_solucion="app_web",
            estado="publicado",
            vacantes=1,
        )
        post = Postulacion.objects.create(
            proyecto=proyecto,
            desarrollador=desarrollador_user,
            mensaje="Carta de prueba.",
            estado="pendiente",
        )
        return proyecto, post

    def test_lista_recibidas_carga_htmx_y_forms_split(self, auth_client, escenario):
        proyecto, post = escenario
        res = auth_client.get(reverse('ver_postulaciones_empresa', args=[proyecto.id]))
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'htmx.min.js' in html
        assert 'htmx_bridge.js' in html
        assert 'id="postulacionesSplitWrap"' in html
        assert f'hx-post="{reverse("iniciar_negociacion", args=[post.id])}"' in html
        assert f'hx-post="{reverse("rechazar_postulacion", args=[post.id])}"' in html
        assert 'hx-target="#postulacionesSplitWrap"' in html
        assert 'hx-swap="outerHTML"' in html

    def test_iniciar_negociacion_htmx_split_retorna_partial_y_toast(self, auth_client, escenario):
        import json

        _, post = escenario
        url = reverse('iniciar_negociacion', args=[post.id])
        res = auth_client.post(
            url,
            {'estado_filtro': ''},
            HTTP_HX_REQUEST='true',
            HTTP_HX_TARGET='postulacionesSplitWrap',
        )
        assert res.status_code == 200
        post.refresh_from_db()
        assert post.estado == 'en_negociacion'

        html = res.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in html
        assert 'id="postulacionesSplitWrap"' in html
        assert 'candidatos-split-layout' in html
        assert 'drawer-funnel-tabs' not in html
        assert 'Ver Contrato Digital' in html

        hx_trigger = json.loads(res['HX-Trigger'])
        assert hx_trigger['jobdevs:toast']['tipo'] == 'success'
        assert 'Negociación iniciada' in hx_trigger['jobdevs:toast']['mensaje']

    def test_rechazar_postulacion_htmx_split_retorna_partial_y_toast(self, auth_client, escenario):
        import json

        _, post = escenario
        url = reverse('rechazar_postulacion', args=[post.id])
        res = auth_client.post(
            url,
            {'estado_filtro': 'pendiente'},
            HTTP_HX_REQUEST='true',
            HTTP_HX_TARGET='postulacionesSplitWrap',
        )
        assert res.status_code == 200
        post.refresh_from_db()
        assert post.estado == 'rechazada'

        html = res.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in html
        assert 'id="postulacionesSplitWrap"' in html
        assert 'drawer-funnel-tabs' not in html

        hx_trigger = json.loads(res['HX-Trigger'])
        assert hx_trigger['jobdevs:toast']['tipo'] == 'success'
        assert 'ha sido rechazada' in hx_trigger['jobdevs:toast']['mensaje']

    def test_iniciar_negociacion_htmx_split_error_cupo_retorna_partial_y_toast_error(
        self, auth_client, escenario
    ):
        import json

        proyecto, post = escenario
        dev2 = User.objects.create_user(
            username='dev_cupo_split', email='dev_cupo_split@test.jobdevs',
            nombre='Dev Cupo', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        Postulacion.objects.create(proyecto=proyecto, desarrollador=dev2, estado='en_negociacion')

        res = auth_client.post(
            reverse('iniciar_negociacion', args=[post.id]),
            {'estado_filtro': ''},
            HTTP_HX_REQUEST='true',
            HTTP_HX_TARGET='postulacionesSplitWrap',
        )
        assert res.status_code == 200
        post.refresh_from_db()
        assert post.estado == 'pendiente'

        html = res.content.decode('utf-8')
        assert '<!DOCTYPE html>' not in html
        assert 'id="postulacionesSplitWrap"' in html
        assert 'drawer-funnel-tabs' not in html

        hx_trigger = json.loads(res['HX-Trigger'])
        assert hx_trigger['jobdevs:toast']['tipo'] == 'error'
        assert 'vacantes' in hx_trigger['jobdevs:toast']['mensaje'].lower()

    def test_iniciar_negociacion_preserva_json_con_accept_json(self, auth_client, escenario):
        _, post = escenario
        res = auth_client.post(
            reverse('iniciar_negociacion', args=[post.id]),
            HTTP_HX_REQUEST='true',
            HTTP_HX_TARGET='postulacionesSplitWrap',
            HTTP_ACCEPT='application/json',
        )
        assert res.status_code == 200
        data = res.json()
        assert data['status'] == 'ok'

    def test_iniciar_negociacion_drawer_target_preserva_drawer_partial(self, auth_client, escenario):
        _, post = escenario
        res = auth_client.post(
            reverse('iniciar_negociacion', args=[post.id]),
            {'estado_filtro': ''},
            HTTP_HX_REQUEST='true',
            HTTP_HX_TARGET='drawerContent',
        )
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert 'drawer-funnel-tabs' in html
        assert 'id="postulacionesSplitWrap"' not in html


