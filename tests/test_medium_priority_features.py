from pathlib import Path

import pytest
from django.conf import settings
from django.contrib import admin

from avances.models import Avance
from contrataciones.models import Contratacion, ContratoDigital, SolicitudCancelacion
from favoritos.models import Favorito
from notificaciones.models import AvisoCumplimiento, Notificacion
from postulaciones.models import ConfiguracionNegociacion, Postulacion


@pytest.mark.django_db
def test_scrum_449_modelos_registrados_en_admin():
    """SCRUM-449: Todos los modelos de dominio faltantes están registrados en Django Admin."""
    for model in (
        Avance,
        Favorito,
        Contratacion,
        ContratoDigital,
        SolicitudCancelacion,
        Postulacion,
        ConfiguracionNegociacion,
        Notificacion,
        AvisoCumplimiento,
    ):
        assert admin.site.is_registered(model), f"{model.__name__} no está registrado en admin.site"

    arch_doc = (Path(settings.BASE_DIR) / 'docs/ARQUITECTURA_SERVICIOS.md').read_text(encoding='utf-8')
    assert 'Thin Controller' in arch_doc


def test_scrum_411_drawer_movil_en_los_tres_dashboards():
    """SCRUM-411: Los 3 dashboards incluyen backdrop y botón hamburguesa para el drawer móvil."""
    base = Path(settings.BASE_DIR)
    for tpl in (
        'templates/Desarrollador/Desarrollador.html',
        'templates/empresa/empresa.html',
        'templates/administrador/Administrador.html',
    ):
        content = (base / tpl).read_text(encoding='utf-8')
        assert 'id="sidebarBackdrop"' in content, f"Falta sidebarBackdrop en {tpl}"
        assert 'mobile-menu-toggle' in content, f"Falta mobile-menu-toggle en {tpl}"
        assert 'toggleSidebar()' in content, f"Falta toggleSidebar() en {tpl}"

    css = (base / 'static/dashboard/css/dashboard.css').read_text(encoding='utf-8')
    assert '.sidebar.is-open' in css
    assert '.sidebar-backdrop.is-open' in css
    assert 'width: 260px !important;' in css

    for role_css in (
        'static/administrador/css/admin.css',
        'static/Desarrollador/css/desarrollador.css',
    ):
        role_content = (base / role_css).read_text(encoding='utf-8')
        assert '@media (min-width: 769px) and (max-width: 900px)' in role_content, (
            f"{role_css} no debe colapsar el drawer móvil a 68px por debajo de 768px"
        )


def test_scrum_455_456_457_variables_semanticas_y_tema_claro():
    """SCRUM-455/456/457: Variables semánticas y reglas [data-theme='light'] en CSS y templates."""
    base = Path(settings.BASE_DIR)
    dash_css = (base / 'static/dashboard/css/dashboard.css').read_text(encoding='utf-8')
    for token in ('--bg-app', '--bg-card', '--text-main', '--border-subtle', '[data-theme="light"]'):
        assert token in dash_css

    modals_css = (base / 'static/dashboard/css/dashboard_modals.css').read_text(encoding='utf-8')
    assert '[data-theme="light"]' in modals_css
    assert '.jdm-sub' in modals_css
    assert '.jdm-disputa-chat' in modals_css

    for tpl in (
        'templates/Desarrollador/Desarrollador.html',
        'templates/empresa/empresa.html',
    ):
        content = (base / tpl).read_text(encoding='utf-8')
        assert "localStorage.getItem('jobdevs-theme')" in content


def test_scrum_401_empty_states_accionables_desarrollador():
    """SCRUM-401: Dashboard Desarrollador incluye empty states accionables con enlace a catálogo."""
    content = (Path(settings.BASE_DIR) / 'templates/Desarrollador/Desarrollador.html').read_text(encoding='utf-8')
    assert 'empty-state-actionable' in content
    assert 'Explorar Proyectos Disponibles' in content


def test_scrum_407_408_admin_confirmacion_y_buscador_debounce():
    """SCRUM-407/408: Admin incluye modal de confirmación de toggle y buscadores con debounce."""
    base = Path(settings.BASE_DIR)
    html = (base / 'templates/administrador/Administrador.html').read_text(encoding='utf-8')
    assert 'id="toggleUserConfirmModal"' in html
    assert 'openToggleUserConfirmModal' in html
    assert 'debouncedFilterUsers()' in html
    assert 'debouncedFilterProjects()' in html
    assert 'id="usersResultCount"' in html
    assert 'id="projectsResultCount"' in html

    js = (base / 'static/administrador/script/administrador.js').read_text(encoding='utf-8')
    assert 'function debounce(' in js
    assert 'openToggleUserConfirmModal' in js
    assert "modal.classList.add('open')" in js
