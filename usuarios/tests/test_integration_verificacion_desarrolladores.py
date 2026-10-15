import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from postulaciones.models import Postulacion
from proyectos.models import Proyecto
from usuarios.models import FichaSena, PerfilDesarrollador

Usuario = get_user_model()


@pytest.fixture
def admin_user(db):
    return Usuario.objects.create_user(
        username='admin_sena_e2e',
        email='admin_e2e@sena.edu.co',
        nombre='Admin Principal SENA',
        password='TestPassword123!',
        rol='administrador',
        identificacion='1000000099',
    )


@pytest.fixture
def empresa_user(db):
    user = Usuario.objects.create_user(
        username='empresa_colombia_tech',
        email='contacto@colombiatech.co',
        nombre='Colombia Tech S.A.S.',
        password='TestPassword123!',
        rol='empresa',
        identificacion='900888777-1',
    )
    return user


@pytest.fixture
def proyecto_abierto(empresa_user):
    return Proyecto.objects.create(
        empresa=empresa_user,
        titulo='Plataforma IoT de Monitoreo',
        descripcion='Desarrollo de backend distribuido y dashboards en tiempo real.',
        tipo_solucion='sitio_web',
        estado='publicado',
        vacantes=2,
    )


@pytest.mark.django_db
class TestWorkflowCompletoVerificacionDesarrolladorSena:
    """Valida los flujos de punta a punta del Módulo 9 - Etapa 2 (SCRUM-154)."""

    def test_ciclo_1_registro_con_ficha_en_lista_blanca_verificacion_automatica_y_postulacion(
        self, client, admin_user, empresa_user, proyecto_abierto
    ):
        # 1. Admin crea ficha en lista blanca
        client.force_login(admin_user)
        res_crear_ficha = client.post(reverse('admin_crear_ficha_sena'), {
            'numero_ficha': '2670999',
            'programa_formacion': 'Análisis y Desarrollo de Software (ADSO)',
            'regional': 'Cundinamarca',
            'centro_formacion': 'CBA Mosquera',
        }, follow=True)
        assert res_crear_ficha.status_code == 200
        assert FichaSena.objects.filter(numero_ficha='2670999', activa=True).exists()

        # 2. Aprendiz se registra indicando la ficha de la lista blanca
        client.logout()
        res_reg = client.post(reverse('registro'), {
            'username': 'aprendiz_auto',
            'nombre': 'Santiago Montoya',
            'tipo_documento': 'cedula',
            'identificacion': '1017999888',
            'email': 'santiago@sena.edu.co',
            'fecha_nacimiento': '2001-04-10',
            'rol': 'desarrollador',
            'ficha': '2670999',
            'programa_formacion': 'ADSO',
            'password1': 'SantiagoPass123!',
            'password2': 'SantiagoPass123!',
        }, follow=True)
        assert res_reg.status_code == 200
        assert res_reg.redirect_chain[-1][0] == reverse('dashboard_desarrollador')

        dev = Usuario.objects.get(username='aprendiz_auto')
        perfil = dev.perfil_desarrollador
        assert perfil.estado_verificacion == 'verificado'
        assert perfil.es_verificado_sena is True
        assert perfil.ficha_sena.numero_ficha == '2670999'

        # 3. Visita su dashboard: badge visible y sin alertas de bloqueo
        res_dash = client.get(reverse('dashboard_desarrollador'))
        dash_content = res_dash.content.decode('utf-8')
        assert 'Aprendiz SENA' in dash_content
        assert 'alerta-verificacion-sena' not in dash_content

        # 4. Se postula exitosamente al proyecto publicado
        res_postular = client.post(
            reverse('postularse_a_proyecto', args=[proyecto_abierto.id]),
            {
                'carta': 'Cuento con certificación en Python y Django.',
                'experiencia': '6 meses en etapa productiva.',
                'link': 'https://github.com/smontoya',
            },
            follow=True,
        )
        assert res_postular.status_code == 200
        assert Postulacion.objects.filter(proyecto=proyecto_abierto, desarrollador=dev).exists()

        # 5. Empresa ve al candidato postulado con su badge "Aprendiz SENA"
        client.force_login(empresa_user)
        res_empresa = client.get(reverse('ver_postulaciones_empresa', args=[proyecto_abierto.id]))
        assert res_empresa.status_code == 200
        empresa_content = res_empresa.content.decode('utf-8')
        assert 'Santiago Montoya' in empresa_content
        assert 'Aprendiz SENA' in empresa_content
        assert 'data-testid="badge-sena-postulante"' in empresa_content

    def test_ciclo_2_registro_sin_ficha_bloqueo_solicitud_manual_y_resolucion_admin(
        self, client, admin_user, empresa_user, proyecto_abierto
    ):
        # 1. Aprendiz se registra sin ficha SENA
        res_reg = client.post(reverse('registro'), {
            'username': 'aprendiz_manual',
            'nombre': 'Valentina Gómez',
            'tipo_documento': 'cedula',
            'identificacion': '1020304055',
            'email': 'valentina@sena.edu.co',
            'fecha_nacimiento': '2002-09-15',
            'rol': 'desarrollador',
            'password1': 'ValentinaPass123!',
            'password2': 'ValentinaPass123!',
        }, follow=True)
        assert res_reg.status_code == 200
        dev = Usuario.objects.get(username='aprendiz_manual')
        perfil = dev.perfil_desarrollador
        assert perfil.estado_verificacion == 'sin_verificar'
        assert perfil.es_verificado_sena is False

        # 2. Intenta postularse y es bloqueado
        res_bloqueo = client.post(
            reverse('postularse_a_proyecto', args=[proyecto_abierto.id]),
            {'carta': 'Deseo postularme', 'experiencia': 'Junior', 'link': ''},
            follow=True,
        )
        assert res_bloqueo.status_code == 200
        # Redirigido a verificación
        assert not Postulacion.objects.filter(proyecto=proyecto_abierto, desarrollador=dev).exists()

        # 3. Envía solicitud manual con archivo PDF válido
        pdf_file = SimpleUploadedFile(
            'matricula_sena.pdf',
            b'%PDF-1.4 certificado oficial de matricula sofia plus',
            content_type='application/pdf',
        )
        res_solicitud = client.post(
            reverse('solicitar_verificacion_desarrollador'),
            {
                'metodo': 'manual',
                'ficha': '2900888',
                'programa_formacion': 'ADSO',
                'documento_soporte': pdf_file,
            },
            follow=True,
        )
        assert res_solicitud.status_code == 200
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'en_revision'

        # 4. Admin ingresa a su dashboard y ve la solicitud pendiente
        client.force_login(admin_user)
        res_admin_dash = client.get(reverse('dashboard_admin'))
        assert res_admin_dash.status_code == 200
        assert perfil in res_admin_dash.context['desarrolladores_en_revision']

        # 5. Admin aprueba la verificación con observaciones
        res_aprobar = client.post(
            reverse('admin_resolver_verificacion_desarrollador', args=[perfil.id]),
            {'accion': 'aprobar', 'notas': 'Documento contrastado y aprobado con éxito'},
            follow=True,
        )
        assert res_aprobar.status_code == 200
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'verificado'
        assert perfil.es_verificado_sena is True
        assert perfil.verificado_por == admin_user
        assert LogAuditoria.objects.filter(tabla_afectada='perfil_desarrollador', registro_id=perfil.id).exists()
        assert Notificacion.objects.filter(usuario=dev, tipo='aprobacion').exists()

        # 6. Aprendiz ya verificado ahora se postula con éxito
        client.force_login(dev)
        res_postular_ok = client.post(
            reverse('postularse_a_proyecto', args=[proyecto_abierto.id]),
            {'carta': 'Ahora que estoy verificado envío mi postulación.', 'experiencia': 'SENA', 'link': ''},
            follow=True,
        )
        assert res_postular_ok.status_code == 200
        assert Postulacion.objects.filter(proyecto=proyecto_abierto, desarrollador=dev).exists()

    def test_ciclo_3_rechazo_con_motivo_y_reintento_exitoso(
        self, client, admin_user, desarrollador_user
    ):
        perfil = desarrollador_user.perfil_desarrollador
        perfil.estado_verificacion = 'sin_verificar'
        perfil.save()

        pdf_file = SimpleUploadedFile('soporte.pdf', b'%PDF-1.4 sena', content_type='application/pdf')

        client.force_login(desarrollador_user)
        client.post(reverse('solicitar_verificacion_desarrollador'), {
            'metodo': 'manual',
            'ficha': '2700111',
            'programa_formacion': 'ADSO',
            'documento_soporte': pdf_file,
        })
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'en_revision'

        # Admin rechaza por documento borroso
        client.force_login(admin_user)
        client.post(
            reverse('admin_resolver_verificacion_desarrollador', args=[perfil.id]),
            {'accion': 'rechazar', 'notas': 'Documento ilegible. Vuelve a subirlo en alta calidad.'},
        )
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'rechazado'
        assert perfil.es_verificado_sena is False

        # Aprendiz ve el motivo del rechazo en su vista de verificación
        client.force_login(desarrollador_user)
        res_verif = client.get(reverse('solicitar_verificacion_desarrollador'))
        assert res_verif.status_code == 200
        assert 'Documento ilegible' in res_verif.content.decode('utf-8')

        # Reenvía con nuevo documento
        pdf_nuevo = SimpleUploadedFile('soporte_hd.pdf', b'%PDF-1.4 sena hd', content_type='application/pdf')
        client.post(reverse('solicitar_verificacion_desarrollador'), {
            'metodo': 'manual',
            'ficha': '2700111',
            'programa_formacion': 'ADSO',
            'documento_soporte': pdf_nuevo,
        })
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'en_revision'

        # Admin aprueba
        client.force_login(admin_user)
        client.post(
            reverse('admin_resolver_verificacion_desarrollador', args=[perfil.id]),
            {'accion': 'aprobar', 'notas': 'Documento HD recibido y aprobado'},
        )
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'verificado'
        assert perfil.es_verificado_sena is True
