import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from proyectos.models import Proyecto
from usuarios.models import PerfilEmpresa, Usuario


@pytest.fixture(autouse=True)
def tmp_media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path


@pytest.mark.django_db
class TestWorkflowCompletoVerificacionEmpresa:
    """Valida el ciclo de vida completo de verificación de identidad empresarial."""

    def test_ciclo_completo_persona_juridica_solicitud_aprobacion_y_badges(
        self, client, empresa_user, admin_user
    ):
        # 1. Estado inicial: Perfil sin verificar
        perfil, _ = PerfilEmpresa.objects.get_or_create(
            usuario=empresa_user, defaults={"nombre_empresa": "SENA Empresa Demo"}
        )
        assert perfil.estado_verificacion == "sin_verificar"
        assert not perfil.es_verificada

        # 2. Proyecto publicado muestra advertencia de empresa no verificada
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo="Proyecto Test Verificación",
            descripcion="Descripción del proyecto de prueba",
            estado="publicado",
            vacantes=2,
        )

        client.force_login(empresa_user)
        resp_listado = client.get(reverse("listar_proyectos"))
        assert resp_listado.status_code == 200
        assert "Sin Verificar" in resp_listado.content.decode("utf-8")

        # 3. Empresa envía solicitud de verificación con NIT oficial (SENA: 899.999.034)
        pdf_content = b"%PDF-1.4 Fake Camara de Comercio PDF"
        pdf_file = SimpleUploadedFile("camara_comercio.pdf", pdf_content, content_type="application/pdf")

        resp_solicitud = client.post(
            reverse("solicitar_verificacion_empresa"),
            {
                "tipo_persona": "juridica",
                "tipo_documento": "NIT",
                "numero_documento": "899.999.034",
                "razon_social": "Servicio Nacional de Aprendizaje SENA",
                "documento_soporte": pdf_file,
            },
        )
        assert resp_solicitud.status_code == 302

        # 4. Verificar que se procesó el DV automático y pasó a 'en_revision'
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == "en_revision"
        assert perfil.numero_documento == "899999034"
        assert perfil.digito_verificacion == "1"  # DV exacto calculado con Módulo 11 DIAN
        assert perfil.documento_completo == "899999034-1"
        assert perfil.documento_soporte is not None
        assert perfil.fecha_solicitud_verificacion is not None

        # Auditoría y notificación a admins
        assert LogAuditoria.objects.filter(
            tabla_afectada="perfil_empresa", registro_id=perfil.pk
        ).exists()
        assert Notificacion.objects.filter(usuario=admin_user).exists()

        # 5. Administrador ve la empresa pendiente en su dashboard
        client.force_login(admin_user)
        resp_admin_dash = client.get(reverse("dashboard_admin"))
        assert resp_admin_dash.status_code == 200
        assert resp_admin_dash.context["total_empresas_en_revision"] >= 1

        # 6. Administrador aprueba la verificación
        resp_resolver = client.post(
            reverse("admin_resolver_verificacion_empresa", args=[perfil.pk]),
            {"accion": "aprobar", "notas": "Cámara de Comercio vigente y cotejada con éxito."},
        )
        assert resp_resolver.status_code == 302

        perfil.refresh_from_db()
        assert perfil.estado_verificacion == "verificada"
        assert perfil.es_verificada
        assert perfil.verificado_por == admin_user
        assert perfil.fecha_verificacion is not None
        assert "Cámara de Comercio vigente" in perfil.notas_auditoria

        # Notificación enviada a la empresa
        assert Notificacion.objects.filter(
            usuario=empresa_user, mensaje__icontains="fue verificada"
        ).exists()

        # 7. Listado público ahora muestra la insignia de 'Empresa Verificada'
        resp_listado_verificado = client.get(reverse("listar_proyectos"))
        assert resp_listado_verificado.status_code == 200
        contenido_html = resp_listado_verificado.content.decode("utf-8")
        assert "Empresa Verificada" in contenido_html

    def test_ciclo_persona_natural_comerciante_con_cedula(
        self, client, empresa_user, admin_user
    ):
        """Prueba verificación para Persona Natural que usa Cédula + RUT."""
        perfil, _ = PerfilEmpresa.objects.get_or_create(
            usuario=empresa_user, defaults={"nombre_empresa": "Juan Pérez Tech"}
        )

        client.force_login(empresa_user)
        pdf_rut = SimpleUploadedFile("rut_persona_natural.pdf", b"%PDF-1.4 RUT", content_type="application/pdf")

        resp_solicitud = client.post(
            reverse("solicitar_verificacion_empresa"),
            {
                "tipo_persona": "natural",
                "tipo_documento": "CC",
                "numero_documento": "1020304050",
                "razon_social": "Juan Carlos Pérez Gómez",
                "documento_soporte": pdf_rut,
            },
        )
        assert resp_solicitud.status_code == 302

        perfil.refresh_from_db()
        assert perfil.estado_verificacion == "en_revision"
        assert perfil.tipo_persona == "natural"
        assert perfil.tipo_documento == "CC"
        assert perfil.digito_verificacion is None
        assert perfil.documento_completo == "1020304050"

        # Admin aprueba
        client.force_login(admin_user)
        client.post(
            reverse("admin_resolver_verificacion_empresa", args=[perfil.pk]),
            {"accion": "aprobar", "notas": "RUT verificado ante DIAN."},
        )

        perfil.refresh_from_db()
        assert perfil.es_verificada
        assert perfil.badge_info["label"] == "Negocio Verificado"
