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


