import io
import zipfile
import pytest
from PIL import Image
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from proyectos.models import Proyecto, Entregable
from contrataciones.models import Contratacion
from avances.models import Avance
from notificaciones.models import Notificacion

User = get_user_model()


def _crear_zip_valido():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('evidencia.txt', 'codigo fuente verificado')
    return buf.getvalue()


def _crear_png_valido():
    buf = io.BytesIO()
    img = Image.new('RGB', (10, 10), color='blue')
    img.save(buf, format='PNG')
    return buf.getvalue()



class TestAvanceModel:
    """Tests for Avance model."""

    def test_crear_avance(self, db):
        """Avance links to proyecto and entregable."""
        empresa = User.objects.create_user(
            username='ae', email='ae@test.jobdevs',
            nombre='AE', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        dev = User.objects.create_user(
            username='ad', email='ad@test.jobdevs',
            nombre='AD', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='AP',
            descripcion='D', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        entregable = Entregable.objects.create(
            proyecto=proyecto, titulo='Hito 1',
            descripcion='H1',
        )
        avance = Avance.objects.create(
            proyecto=proyecto, entregable=entregable,
            desarrollador=dev, descripcion='Avance test',
        )
        assert avance.id is not None

    def test_avance_str(self, db):
        """__str__ includes proyecto and entregable."""
        empresa = User.objects.create_user(
            username='ae2', email='ae2@test.jobdevs',
            nombre='AE2', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        proyecto = Proyecto.objects.create(
            empresa=empresa, titulo='AP2',
            descripcion='D', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        entregable = Entregable.objects.create(
            proyecto=proyecto, titulo='H2', descripcion='H2',
        )
        dev = User.objects.create_user(
            username='ad2', email='ad2@test.jobdevs',
            nombre='AD2', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        avance = Avance.objects.create(
            proyecto=proyecto, entregable=entregable,
            desarrollador=dev, descripcion='Test',
        )
        assert 'AP2' in str(avance)


class TestVerAvances:
    """Tests for ver_avances view."""

    def test_ver_avances_accessible(self, auth_client, empresa_user):
        """Authenticated user can view avances for a project."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='VA',
            descripcion='D', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        response = auth_client.get(
            reverse('ver_avances', args=[proyecto.id])
        )
        assert response.status_code == 200

    def test_ver_avances_muestra_boton_descargar_archivo(self, auth_client, empresa_user, desarrollador_user):
        """RF 4.2.1 (SCRUM-64): Ver avances muestra enlace para descargar archivo adjunto."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='VA Evidencias',
            descripcion='D', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        entregable = Entregable.objects.create(
            proyecto=proyecto, titulo='Hito Evidencia', descripcion='H',
        )
        archivo = SimpleUploadedFile("evidencia_doc.pdf", b"%PDF-1.4 contenido", content_type="application/pdf")
        avance = Avance.objects.create(
            proyecto=proyecto, entregable=entregable,
            desarrollador=desarrollador_user, descripcion='Avance con archivo',
            archivo_adjunto=archivo,
        )
        response = auth_client.get(reverse('ver_avances', args=[proyecto.id]))
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Descargar Archivo' in content or 'evidencia_doc' in content


class TestRegistrarAvance:
    """Tests for registrar_avance view."""

    @pytest.fixture
    def escenario_avance(self, empresa_user, desarrollador_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto Avances',
            descripcion='D', tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        entregable = Entregable.objects.create(
            proyecto=proyecto, titulo='Hito Test',
            descripcion='Desc', estado='pendiente',
        )
        contratacion = Contratacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user,
            empresa=empresa_user, estado='activa',
        )
        return proyecto, entregable, contratacion

    def test_registrar_avance_con_archivo_adjunto_sin_url(self, dev_client, desarrollador_user, escenario_avance):
        """RF 4.2.1 (SCRUM-64): Desarrollador puede subir archivo real de evidencia sin URL."""
        proyecto, entregable, _ = escenario_avance
        archivo = SimpleUploadedFile("codigo.zip", _crear_zip_valido(), content_type="application/zip")

        response = dev_client.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': entregable.id,
            'descripcion': 'Subida de código fuente en ZIP',
            'archivo_url': '',
            'archivo_adjunto': archivo,
        }, follow=True)
        assert response.status_code == 200
        assert Avance.objects.filter(proyecto=proyecto, entregable=entregable).exists()
        avance = Avance.objects.get(proyecto=proyecto, entregable=entregable)
        assert bool(avance.archivo_adjunto) is True
        assert avance.archivo_url in (None, '')

    def test_registrar_avance_con_url_sin_archivo(self, dev_client, desarrollador_user, escenario_avance):
        """Desarrollador puede registrar avance solo con URL de repositorio."""
        proyecto, entregable, _ = escenario_avance
        response = dev_client.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': entregable.id,
            'descripcion': 'Enlace al repo',
            'archivo_url': 'https://github.com/mrdylan/jobdevs',
        }, follow=True)
        assert response.status_code == 200
        assert Avance.objects.filter(proyecto=proyecto, entregable=entregable).exists()
        avance = Avance.objects.get(proyecto=proyecto, entregable=entregable)
        assert avance.archivo_url == 'https://github.com/mrdylan/jobdevs'

    def test_registrar_avance_sin_url_ni_archivo_muestra_error(self, dev_client, desarrollador_user, escenario_avance):
        """Si no se ingresa ni URL ni archivo adjunto, se rechaza la solicitud."""
        proyecto, entregable, _ = escenario_avance
        response = dev_client.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': entregable.id,
            'descripcion': 'Sin evidencia alguna',
            'archivo_url': '',
        }, follow=True)
        assert response.status_code == 200
        assert not Avance.objects.filter(proyecto=proyecto, entregable=entregable).exists()
        content = response.content.decode('utf-8')
        assert 'Debes proporcionar una URL o adjuntar un archivo de evidencia' in content

    def test_registrar_avance_rechaza_extension_no_permitida(self, dev_client, desarrollador_user, escenario_avance):
        """SCRUM-168: Se rechazan archivos con extensiones no permitidas (.html, .sh, .exe)."""
        proyecto, entregable, _ = escenario_avance
        archivo = SimpleUploadedFile("script.html", b"<script>alert(1)</script>", content_type="text/html")
        response = dev_client.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': entregable.id,
            'descripcion': 'Intento de XSS',
            'archivo_adjunto': archivo,
        }, follow=True)
        assert response.status_code == 200
        assert not Avance.objects.filter(proyecto=proyecto, entregable=entregable).exists()
        content = response.content.decode('utf-8')
        assert 'Tipo de archivo no permitido' in content

    def test_registrar_avance_rechaza_magic_bytes_inconsistentes(self, dev_client, desarrollador_user, escenario_avance):
        """SCRUM-168: Se rechaza un archivo con extensión .pdf cuyos magic bytes no coincidan."""
        proyecto, entregable, _ = escenario_avance
        archivo = SimpleUploadedFile("falso.pdf", b"MZ fake executable header", content_type="application/pdf")
        response = dev_client.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': entregable.id,
            'descripcion': 'PDF corrupto o ejecutable disfrazado',
            'archivo_adjunto': archivo,
        }, follow=True)
        assert response.status_code == 200
        assert not Avance.objects.filter(proyecto=proyecto, entregable=entregable).exists()
        content = response.content.decode('utf-8')
        assert 'El archivo no es un documento PDF válido' in content

    def test_registrar_avance_acepta_png_con_magic_bytes_validos(self, dev_client, desarrollador_user, escenario_avance):
        """SCRUM-168: Se aceptan imágenes PNG válidas con su cabecera mágica y estructura verificada."""
        proyecto, entregable, _ = escenario_avance
        archivo = SimpleUploadedFile("captura.png", _crear_png_valido(), content_type="image/png")
        response = dev_client.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': entregable.id,
            'descripcion': 'Captura de pantalla como evidencia',
            'archivo_adjunto': archivo,
        }, follow=True)
        assert response.status_code == 200
        assert Avance.objects.filter(proyecto=proyecto, entregable=entregable).exists()

    def test_registrar_avance_bloquea_si_proyecto_no_tiene_hitos(self, dev_client, empresa_user, desarrollador_user):
        """SCRUM-205: Si un proyecto no tiene hitos definidos, registrar_avance redirige con advertencia."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto Sin Hitos',
            descripcion='D', tipo_solucion='sitio_web', estado='en_desarrollo',
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, empresa=empresa_user, estado='activa',
        )
        response = dev_client.get(reverse('registrar_avance', args=[proyecto.id]))
        assert response.status_code == 302
        assert reverse('dashboard_desarrollador') in response.url
        res_follow = dev_client.get(reverse('registrar_avance', args=[proyecto.id]), follow=True)
        content = res_follow.content.decode('utf-8')
        assert 'aún no tiene hitos definidos' in content

    def test_registrar_avance_bloquea_si_todos_los_hitos_entregados_o_en_revision(self, dev_client, empresa_user, desarrollador_user):
        """SCRUM-205: Si todos los hitos ya fueron entregados, registrar_avance redirige con aviso."""
        proyecto = Proyecto.objects.create(
            empresa=empresa_user, titulo='Proyecto Hitos Completos',
            descripcion='D', tipo_solucion='sitio_web', estado='en_desarrollo',
        )
        Entregable.objects.create(
            proyecto=proyecto, titulo='Hito 1', descripcion='D', estado='en_revision'
        )
        Contratacion.objects.create(
            proyecto=proyecto, desarrollador=desarrollador_user, empresa=empresa_user, estado='activa',
        )
        response = dev_client.get(reverse('registrar_avance', args=[proyecto.id]))
        assert response.status_code == 302
        res_follow = dev_client.get(reverse('registrar_avance', args=[proyecto.id]), follow=True)
        content = res_follow.content.decode('utf-8')
        assert 'ya han sido entregados o están en revisión' in content

    def test_registrar_avance_post_rechaza_hito_no_pendiente(self, dev_client, empresa_user, desarrollador_user, escenario_avance):
        """SCRUM-205: POST rechazado si el hito seleccionado no se encuentra en estado pendiente."""
        proyecto, entregable, _ = escenario_avance
        entregable.estado = 'completado'
        entregable.save()

        response = dev_client.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': entregable.id,
            'descripcion': 'Intento de avance sobre hito completado',
            'archivo_url': 'https://github.com/mrdylan/jobdevs',
        }, follow=True)
        assert response.status_code == 200
        assert not Avance.objects.filter(proyecto=proyecto, entregable=entregable).exists()
        content = response.content.decode('utf-8')
        assert 'no admite nuevos avances' in content or 'ya han sido entregados' in content

    def test_registrar_avance_preserva_datos_en_error_sin_redireccion(self, dev_client, desarrollador_user, escenario_avance):
        """SCRUM-206: Al fallar validación (sin URL ni archivo), no redirige (200) y preserva la descripción y el hito."""
        proyecto, entregable, _ = escenario_avance
        texto_largo = "Implementé toda la capa de autenticación JWT y pruebas de integración completas."

        response = dev_client.post(reverse('registrar_avance', args=[proyecto.id]), {
            'entregable_id': str(entregable.id),
            'descripcion': texto_largo,
            'archivo_url': '',
        })
        assert response.status_code == 200  # Render directo, NO redirect 302
        content = response.content.decode('utf-8')
        assert texto_largo in content
        assert 'Debes proporcionar una URL o adjuntar un archivo de evidencia' in content
        assert response.context['form_data']['descripcion'] == texto_largo
        assert response.context['form_data']['entregable_id'] == str(entregable.id)

    def test_registrar_avance_ajax_retorna_json_error_sin_recarga(self, dev_client, desarrollador_user, escenario_avance):
        """SCRUM-206: Petición AJAX/Fetch sin URL ni archivo retorna JSON 400 con detalle del error."""
        proyecto, entregable, _ = escenario_avance
        response = dev_client.post(
            reverse('registrar_avance', args=[proyecto.id]),
            {
                'entregable_id': entregable.id,
                'descripcion': 'Avance por Fetch',
                'archivo_url': '',
            },
            headers={'Accept': 'application/json'}
        )
        assert response.status_code == 400
        assert response.headers['Content-Type'] == 'application/json'
        data = response.json()
        assert data['status'] == 'error'
        assert 'Debes proporcionar una URL o adjuntar un archivo de evidencia' in data['error']

    def test_registrar_avance_ajax_exitoso_retorna_json_redirect(self, dev_client, desarrollador_user, escenario_avance):
        """SCRUM-206: Petición AJAX/Fetch válida crea el avance y retorna JSON 200 con redirect_url."""
        proyecto, entregable, _ = escenario_avance
        response = dev_client.post(
            reverse('registrar_avance', args=[proyecto.id]),
            {
                'entregable_id': entregable.id,
                'descripcion': 'Avance exitoso vía Fetch',
                'archivo_url': 'https://github.com/mrdylan/jobdevs/pull/1',
            },
            headers={'Accept': 'application/json'}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'redirect_url' in data
        assert Avance.objects.filter(proyecto=proyecto, entregable=entregable).exists()


class TestRevisarAvance:
    """Tests for revisar_avance view (SCRUM-308)."""

    @pytest.fixture
    def escenario_revision(self, empresa_user, desarrollador_user):
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto Revisión',
            descripcion='Desc',
            tipo_solucion='sitio_web',
            estado='en_desarrollo',
        )
        entregable = Entregable.objects.create(
            proyecto=proyecto,
            titulo='Hito Entrega',
            descripcion='Desc',
            estado='en_revision',
        )
        avance = Avance.objects.create(
            proyecto=proyecto,
            entregable=entregable,
            desarrollador=desarrollador_user,
            descripcion='Avance para revisar',
            archivo_url='https://github.com/mrdylan/jobdevs',
            estado='pendiente',
        )
        return proyecto, entregable, avance

    def test_empresa_acepta_avance_pendiente_exitosamente(self, auth_client, escenario_revision):
        """Empresa puede aceptar un avance en estado pendiente."""
        proyecto, entregable, avance = escenario_revision
        response = auth_client.post(
            reverse('revisar_avance', args=[avance.id]),
            {'accion': 'aceptar', 'comentario': 'Excelente trabajo'},
            follow=True,
        )
        assert response.status_code == 200
        avance.refresh_from_db()
        entregable.refresh_from_db()
        assert avance.estado == 'aceptado'
        assert avance.comentario_revision == 'Excelente trabajo'
        assert entregable.estado == 'completado'

    def test_empresa_rechaza_avance_pendiente_con_comentario(self, auth_client, escenario_revision):
        """Empresa puede rechazar un avance pendiente proporcionando justificación."""
        proyecto, entregable, avance = escenario_revision
        response = auth_client.post(
            reverse('revisar_avance', args=[avance.id]),
            {'accion': 'rechazar', 'comentario': 'Falta documentación de la API'},
            follow=True,
        )
        assert response.status_code == 200
        avance.refresh_from_db()
        entregable.refresh_from_db()
        assert avance.estado == 'rechazado'
        assert avance.comentario_revision == 'Falta documentación de la API'
        assert entregable.estado == 'pendiente'

    def test_revisar_avance_bloquea_si_avance_ya_fue_aceptado(self, auth_client, escenario_revision):
        """SCRUM-308: Un avance ya aceptado no puede ser modificado ni rechazado posteriormente."""
        proyecto, entregable, avance = escenario_revision
        avance.estado = 'aceptado'
        avance.comentario_revision = 'Aprobado originalmente'
        avance.save()
        entregable.estado = 'completado'
        entregable.save()

        notificaciones_previas = Notificacion.objects.count()

        response = auth_client.post(
            reverse('revisar_avance', args=[avance.id]),
            {'accion': 'rechazar', 'comentario': 'Intento de revertir aprobación previa'},
            follow=True,
        )
        assert response.status_code == 200
        avance.refresh_from_db()
        entregable.refresh_from_db()
        # El estado no debe haber mutado
        assert avance.estado == 'aceptado'
        assert avance.comentario_revision == 'Aprobado originalmente'
        assert entregable.estado == 'completado'
        # No deben generarse notificaciones espurias
        assert Notificacion.objects.count() == notificaciones_previas
        content = response.content.decode('utf-8')
        assert 'ya fue' in content.lower() or 'ya se encuentra' in content.lower() or 'no puede' in content.lower()

    def test_revisar_avance_bloquea_si_avance_ya_fue_rechazado(self, auth_client, escenario_revision):
        """SCRUM-308: Un avance ya rechazado no puede ser aceptado nuevamente de forma extemporánea."""
        proyecto, entregable, avance = escenario_revision
        avance.estado = 'rechazado'
        avance.comentario_revision = 'Rechazado originalmente'
        avance.save()
        entregable.estado = 'pendiente'
        entregable.save()

        notificaciones_previas = Notificacion.objects.count()

        response = auth_client.post(
            reverse('revisar_avance', args=[avance.id]),
            {'accion': 'aceptar', 'comentario': 'Intento de aceptar avance previamente rechazado'},
            follow=True,
        )
        assert response.status_code == 200
        avance.refresh_from_db()
        entregable.refresh_from_db()
        assert avance.estado == 'rechazado'
        assert entregable.estado == 'pendiente'
        assert Notificacion.objects.count() == notificaciones_previas
        content = response.content.decode('utf-8')
        assert 'ya fue' in content.lower() or 'ya se encuentra' in content.lower() or 'no puede' in content.lower()

    def test_desarrollador_no_puede_revisar_avance(self, dev_client, escenario_revision):
        """Solo las empresas pueden revisar avances; desarrollador es redirigido con error."""
        _, _, avance = escenario_revision
        response = dev_client.post(
            reverse('revisar_avance', args=[avance.id]),
            {'accion': 'aceptar'},
            follow=True,
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Solo las empresas pueden revisar avances' in content

    def test_otra_empresa_no_puede_revisar_avance_ajeno(self, client, escenario_revision):
        """Una empresa no puede revisar avances de proyectos que no le pertenecen (404)."""
        _, _, avance = escenario_revision
        otra_empresa = User.objects.create_user(
            username='otra_empresa',
            email='otra@test.jobdevs',
            nombre='Otra Empresa',
            rol='empresa',
            estado='activo',
            password='TestPass123!',
        )
        client.login(username='otra_empresa', password='TestPass123!')
        response = client.post(
            reverse('revisar_avance', args=[avance.id]),
            {'accion': 'aceptar'},
        )
        assert response.status_code == 404




