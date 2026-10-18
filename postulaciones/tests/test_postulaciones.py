import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from proyectos.models import Proyecto
from postulaciones.models import Postulacion

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
        with pytest.raises(Exception):
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
        """Cannot apply to non-published projects."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Cerrado',
            descripcion='C', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        response = dev_client.post(
            reverse('postularse_a_proyecto', args=[proyecto.id]),
            {'carta': 'H', 'experiencia': 'E', 'link': 'L'}
        )
        assert response.status_code == 302
        assert not Postulacion.objects.filter(proyecto=proyecto).exists()


class TestAceptarPostulacion:
    """Tests for aceptar_postulacion view."""

    def test_empresa_acepta_postulacion(self, auth_client, empresa_user, desarrollador_user):
        """Empresa can accept a pending postulacion."""
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
        assert postulacion.estado == 'aceptada'

        # Verificar preservación exacta de estado_anterior en HistorialEstadoProyecto
        from proyectos.models import HistorialEstadoProyecto
        historial = HistorialEstadoProyecto.objects.filter(proyecto=proyecto).first()
        assert historial is not None
        assert historial.estado_anterior == 'publicado'
        assert historial.estado_nuevo == 'en_desarrollo'
        assert historial.cambiado_por == empresa_user

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

        # 1. Aceptar la primera postulación (ocupa la única vacante disponible)
        res1 = auth_client.post(reverse('aceptar_postulacion', args=[post1.id]))
        assert res1.status_code == 302
        post1.refresh_from_db()
        assert post1.estado == 'aceptada'
        assert Contratacion.objects.filter(proyecto=proyecto, estado='activa').count() == 1

        # 2. Intentar aceptar la segunda postulación debe ser rechazado
        res2 = auth_client.post(reverse('aceptar_postulacion', args=[post2.id]), follow=True)
        assert res2.status_code == 200
        post2.refresh_from_db()
        assert post2.estado == 'pendiente'
        assert Contratacion.objects.filter(proyecto=proyecto, estado='activa').count() == 1
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

    def test_requiere_post(self, auth_client, escenario):
        _, post = escenario
        assert auth_client.get(reverse('iniciar_negociacion', args=[post.id])).status_code == 405

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
        assert reverse('aceptar_postulacion', args=[post.id]) in html

        auth_client.post(reverse('iniciar_negociacion', args=[post.id]))
        contrato = ContratoDigital.objects.get(postulacion=post)
        html = auth_client.get(url).content.decode()
        assert 'En Negociación' in html
        assert reverse('ver_contrato_digital', args=[contrato.id]) in html
        assert reverse('sala_chat', args=[desarrollador_user.id, proyecto.id]) in html
        assert reverse('iniciar_negociacion', args=[post.id]) not in html
