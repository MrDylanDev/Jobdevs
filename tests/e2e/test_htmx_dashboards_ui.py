"""Playwright E2E tests for HTMX dashboards, semantic light-theme tokens, and declarative action delegation."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestHtmxDashboardsE2E:
    """Real-browser verification of HTMX swaps, ES modules, semantic tokens, and action_delegate.js."""

    def test_admin_htmx_users_filter_and_modal_delegation(self, page, live_server, login_user, test_dev):
        """Admin dashboard loads without JS errors, filters users via HTMX without reload, and closes modal via data-action."""
        admin = User.objects.filter(rol='administrador').first()
        assert admin is not None
        login_user(admin)

        page_errors = []
        page.on('pageerror', lambda err: page_errors.append(str(err)))

        page.goto(live_server.url + reverse('dashboard_admin'), wait_until='domcontentloaded')
        page.wait_for_function('() => typeof window.showSection === "function" && window.__jobdevsActionDelegateBound === true')
        page.evaluate('() => { window.__e2eNoReload = true; }')

        # Switch to Users section and trigger HTMX search
        page.evaluate('() => window.showSection("usersSection")')
        search = page.locator('#userSearch')
        search.wait_for(state='visible', timeout=5000)

        api_url = reverse('api_usuarios')
        with page.expect_response(lambda r: api_url in r.url and r.status == 200, timeout=5000):
            search.fill(test_dev.username)

        page.wait_for_function(
            '(uname) => (document.getElementById("usersTableBody")?.innerText || "").includes(uname)',
            arg=test_dev.username,
            timeout=5000,
        )
        assert page.evaluate('() => window.__e2eNoReload') is True

        # Open Create User modal and close it via declarative data-action="close-modal"
        page.locator('button[onclick="openCreateUserModal()"]').click()
        modal = page.locator('#createUserModal')
        modal.wait_for(state='visible', timeout=5000)

        modal.locator('button[data-action="close-modal"][data-target="createUserModal"]').first.click()
        page.wait_for_function(
            '() => !document.getElementById("createUserModal").classList.contains("active")',
            timeout=5000,
        )
        assert page_errors == [], f'Unexpected JS pageerrors in admin dashboard: {page_errors}'

    def test_dev_dashboard_delegation_light_theme_tokens_and_notif_popover(self, page, live_server, login_user, test_dev):
        """Developer dashboard loads ES modules cleanly, delegates tab clicks, resolves light-theme tokens, and opens notif popover."""
        login_user(test_dev)

        page_errors = []
        page.on('pageerror', lambda err: page_errors.append(str(err)))

        page.goto(live_server.url + reverse('dashboard_desarrollador'), wait_until='domcontentloaded')
        page.wait_for_function('() => typeof window.verSeccion === "function" && window.__jobdevsActionDelegateBound === true')
        page.evaluate('() => { window.__e2eNoReload = true; }')

        # Click declarative data-action="ver-seccion" card/button to open 'explorar' without full reload
        page.locator('[data-action="ver-seccion"][data-target="explorar"]').first.click()
        page.wait_for_function(
            '() => document.getElementById("explorar")?.classList.contains("activa")',
            timeout=5000,
        )
        assert page.evaluate('() => window.__e2eNoReload') is True

        # Toggle theme and verify semantic light-theme CSS token resolves
        initial_theme = page.evaluate('() => document.documentElement.getAttribute("data-theme")')
        page.evaluate('() => window.toggleDevTheme()')
        toggled_theme = page.evaluate('() => document.documentElement.getAttribute("data-theme")')
        assert toggled_theme != initial_theme

        if toggled_theme != 'light':
            page.evaluate('() => window.toggleDevTheme()')
        theme = page.evaluate('() => document.documentElement.getAttribute("data-theme")')
        surface_elevated = page.evaluate(
            '() => getComputedStyle(document.documentElement).getPropertyValue("--surface-elevated").trim()'
        )
        assert theme == 'light'
        assert surface_elevated.lower() == '#ffffff'

        # Open notifications popover (loaded as ES module)
        page.locator('[data-notif-toggle]').click()
        page.wait_for_function(
            '() => document.getElementById("notifPopover")?.getAttribute("aria-hidden") === "false"',
            timeout=5000,
        )
        assert page_errors == [], f'Unexpected JS pageerrors in dev dashboard: {page_errors}'

    def test_empresa_dashboard_delegation_and_create_project_modal(self, page, live_server, login_user, test_empresa):
        """Empresa dashboard loads cleanly, delegates KPI card tab switch, and opens create-project modal via data-action."""
        login_user(test_empresa)

        page_errors = []
        page.on('pageerror', lambda err: page_errors.append(str(err)))

        page.add_init_script("localStorage.setItem('jobdevs_bienvenida_no_mostrar', '1');")
        page.goto(live_server.url + reverse('dashboard_empresa'), wait_until='domcontentloaded')
        page.wait_for_function('() => typeof window.switchTab === "function" && window.__jobdevsActionDelegateBound === true')
        page.evaluate('() => { window.cerrarModalBienvenida?.(); window.__e2eNoReload = true; }')

        # Open create-project modal via declarative data-action="abrir-modal"
        page.locator('button[data-action="abrir-modal"]').first.click()
        modal = page.locator('#modalProyecto')
        modal.wait_for(state='visible', timeout=5000)
        page.keyboard.press('Escape')
        page.wait_for_timeout(200)

        # Click KPI card with data-action="switch-tab" data-target="ofertas"
        page.locator('[data-action="switch-tab"][data-target="ofertas"]').first.click()
        page.wait_for_function(
            '() => document.getElementById("ofertas")?.classList.contains("activa")',
            timeout=5000,
        )
        assert page.evaluate('() => window.__e2eNoReload') is True
        assert page_errors == [], f'Unexpected JS pageerrors in empresa dashboard: {page_errors}'
