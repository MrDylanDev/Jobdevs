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
