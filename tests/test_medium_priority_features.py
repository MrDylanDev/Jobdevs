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
        'templates/desarrollador/Desarrollador.html',
        'templates/empresa/empresa.html',
        'templates/administrador/Administrador.html',
    ):
        content = (base / tpl).read_text(encoding='utf-8')
        assert 'id="sidebarBackdrop"' in content, f"Falta sidebarBackdrop en {tpl}"
        assert 'mobile-menu-toggle' in content, f"Falta mobile-menu-toggle en {tpl}"
        assert 'data-call="toggleSidebar"' in content, f"Falta toggleSidebar en {tpl}"

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


def test_scrum_411_badge_cero_no_se_revela_en_drawer_movil():
    """SCRUM-411: la regla móvil restaura las etiquetas sin forzar visible el badge `hidden`."""
    base = Path(settings.BASE_DIR)
    css = (base / 'static/dashboard/css/dashboard.css').read_text(encoding='utf-8')

    # Sigue restaurando las etiquetas de texto del drawer por debajo de 768px.
    assert 'display: initial !important;' in css

    # ...pero no debe alcanzar a los badges, que el template oculta con el atributo `hidden`
    # cuando el contador es 0: con `!important` la regla le ganaba al `display: none` del UA.
    label_rule = next(
        line.strip()
        for line in css.splitlines()
        if line.strip().startswith('.app-layout > .sidebar .nav-item span')
    )
    assert '.nav-badge' in label_rule, 'la regla móvil no debe forzar visible el badge de notificaciones'
    assert 'hidden' in label_rule, 'la regla móvil no debe pisar el atributo hidden del badge'

    for tpl in (
        'templates/desarrollador/Desarrollador.html',
        'templates/empresa/empresa.html',
        'templates/administrador/Administrador.html',
    ):
        content = (base / tpl).read_text(encoding='utf-8')
        assert 'data-notif-badge{% if notificaciones_pendientes_count == 0 %} hidden{% endif %}' in content, (
            f'{tpl} debe ocultar el badge con el atributo hidden cuando el contador es 0'
        )


@pytest.mark.django_db
def test_scrum_449_criterio_admin_documentado_coincide_con_el_codigo():
    """SCRUM-449: el criterio de registro en admin.py describe el alcance real del estándar."""
    arch_doc = (Path(settings.BASE_DIR) / 'docs/ARQUITECTURA_SERVICIOS.md').read_text(encoding='utf-8')
    seccion = arch_doc.split('### 2. Criterio de Registro en `admin.py`', 1)[1]

    # El estándar nombra las apps cubiertas y deja explícito qué queda como legado.
    for app in ('avances', 'favoritos', 'contrataciones', 'postulaciones', 'notificaciones'):
        assert app in seccion, f'el criterio debe nombrar la app {app}'
    assert 'legado' in seccion, 'las apps fuera del estándar deben declararse como legado pendiente'
    assert 'no están obligadas a este criterio hasta que se incorporen' in seccion, (
        'el criterio debe acotar la obligación a las apps del estándar'
    )
    assert 'solo lectura' in seccion, 'el criterio debe declarar la excepción de los modelos de solo lectura'

    # La excepción documentada existe en el código: la configuración se publica como solo lectura.
    config_admin = admin.site._registry[ConfiguracionNegociacion]
    assert not config_admin.has_change_permission(None)
    assert not config_admin.has_add_permission(None)

    # Y todo modelo registrado del estándar expone al menos list_display.
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
        list_display = admin.site._registry[model].list_display
        assert list_display != admin.ModelAdmin.list_display, (
            f'{model.__name__} no declara list_display propio (usa el default __str__)'
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
        'templates/desarrollador/Desarrollador.html',
        'templates/empresa/empresa.html',
    ):
        content = (base / tpl).read_text(encoding='utf-8')
        assert "localStorage.getItem('jobdevs-theme')" in content


def test_scrum_401_empty_states_accionables_desarrollador():
    """SCRUM-401: Dashboard Desarrollador incluye empty states accionables con enlace a catálogo."""
    dev_dir = Path(settings.BASE_DIR) / 'templates/desarrollador'
    partials = sorted((dev_dir / 'partials').glob('*.html'))
    assert partials, 'Se esperaban parciales en templates/desarrollador/partials/'
    content = '\n'.join(
        p.read_text(encoding='utf-8') for p in [dev_dir / 'Desarrollador.html', *partials]
    )
    assert 'empty-state-actionable' in content
    assert 'Explorar Proyectos Disponibles' in content


def test_scrum_407_408_admin_confirmacion_y_buscador_debounce():
    """SCRUM-407/408: Admin incluye modal de confirmación de toggle y buscadores con debounce."""
    base = Path(settings.BASE_DIR)
    admin_tpl_dir = base / 'templates/administrador'
    partials = sorted((admin_tpl_dir / 'partials').glob('*.html'))
    assert partials, 'Se esperaban parciales en templates/administrador/partials/'
    html = '\n'.join(
        p.read_text(encoding='utf-8') for p in [admin_tpl_dir / 'Administrador.html', *partials]
    )
    assert 'id="toggleUserConfirmModal"' in html
    assert 'openToggleUserConfirmModal' in html
    assert 'data-input-call="debouncedFilterUsers"' in html
    assert 'data-input-call="debouncedFilterProjects"' in html
    assert 'id="usersResultCount"' in html
    assert 'id="projectsResultCount"' in html

    admin_script_dir = base / 'static/administrador/script'
    js = '\n'.join(
        p.read_text(encoding='utf-8')
        for p in [admin_script_dir / 'administrador.js', *sorted((admin_script_dir / 'modules').glob('*.js'))]
    )
    assert 'function debounce(' in js
    assert 'openToggleUserConfirmModal' in js
    assert "modal.classList.add('open')" in js
