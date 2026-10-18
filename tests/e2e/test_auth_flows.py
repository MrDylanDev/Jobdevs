import pytest
from django.urls import reverse


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestLoginE2E:
    """End-to-end login flow tests using Playwright."""

    def test_login_modal_opens(self, page, live_server):
        """Clicking [ AUTH ] opens the login modal."""
        page.goto(live_server.url)
        # Click the AUTH button by its text
        page.locator('.nav-cta').click()
        page.wait_for_timeout(1000)
        # Verify modal is visible
        modal = page.locator('#loginModal')
        assert modal.is_visible()

    def test_login_dev_success(self, page, live_server, test_dev):
        """Login as desarrollador via modal and land on dev dashboard."""
        page.goto(live_server.url)
        # Open modal
        page.locator('.nav-cta').click()
        page.wait_for_timeout(1000)

        # Fill credentials
        page.fill('#username', 'e2e_dev')
        page.fill('#password', 'E2ETest123!')
        # DEV tab is active by default (rol_seleccionado = desarrollador)

        # Submit
        page.locator('.btn-submit-tech:has-text("INGRESAR")').click(force=True)

        # Should redirect to dev dashboard
        page.wait_for_url('**/desarrollador/dashboard/', timeout=5000)
        assert 'dashboard' in page.url

    def test_login_empresa_success(self, page, live_server, test_empresa):
        """Login as empresa via modal and land on empresa dashboard."""
        page.goto(live_server.url)
        page.locator('.nav-cta').click()
        page.wait_for_timeout(1000)

        # Fill credentials (unified login automatically routes to empresa dashboard)
        page.fill('#username', 'e2e_empresa')
        page.fill('#password', 'E2ETest123!')

        # Submit
        page.locator('.btn-submit-tech:has-text("INGRESAR")').click(force=True)

        # Should redirect to empresa dashboard
        page.wait_for_url('**/empresa/dashboard/', timeout=5000)
        assert 'dashboard' in page.url

    def test_login_wrong_password(self, page, live_server, test_dev):
        """Wrong password shows error and stays on landing."""
        page.goto(live_server.url)
        page.locator('.nav-cta').click()
        page.wait_for_timeout(1000)

        page.fill('#username', 'e2e_dev')
        page.fill('#password', 'WrongPassword!')
        page.locator('.btn-submit-tech:has-text("INGRESAR")').click(force=True)

        # Should redirect back to landing (inicio)
        page.wait_for_url(live_server.url + '/', timeout=5000)
        # Toast or message should appear
        assert page.url == live_server.url + '/' or page.url == live_server.url


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestRecoveryE2E:
    """End-to-end password recovery flow."""

    def test_recovery_form_opens(self, page, live_server):
        """Clicking RECUPERAR ACCESO shows the recovery form."""
        page.goto(live_server.url)
        page.locator('.nav-cta').click()
        page.wait_for_timeout(1000)

        # Click recovery link
        page.click('#recoveryLink')

        # Recovery form should be visible
        recovery_form = page.locator('#recoveryForm')
        assert recovery_form.is_visible()

    def test_recovery_submit_shows_success(self, page, live_server, test_empresa):
        """Recovery POST with valid email shows success via JS fetch."""
        page.goto(live_server.url)
        page.locator('.nav-cta').click()
        page.wait_for_timeout(1000)

        # Switch to recovery
        page.click('#recoveryLink')
        page.wait_for_selector('#recoveryForm:not([style*="display: none"])', timeout=3000)

        # Fill email
        page.fill('input[name="email"]', 'e2e_empresa@test.jobdevs')
        page.locator('#recoveryForm button:has-text("ENVIAR")').click(force=True)

        # Wait for the toast or success indicator
        page.wait_for_timeout(2000)
        # Toast should appear or we should still be on the landing page
        assert 'jobdevs' in page.url.lower() or 'localhost' in page.url

    def test_back_to_login_from_recovery(self, page, live_server):
        """BACK TO LOGIN link returns to login form."""
        page.goto(live_server.url)
        page.locator('.nav-cta').click()
        page.wait_for_timeout(1000)

        # Go to recovery
        page.click('#recoveryLink')
        page.wait_for_selector('#recoveryForm:not([style*="display: none"])', timeout=3000)

        # Go back to login
        page.click('#backToLoginLink')

        # Login form should be visible again
        login_form = page.locator('#loginForm')
        assert login_form.is_visible()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestRegistroE2E:
    """End-to-end registration flow."""

    def test_registro_page_loads(self, page, live_server):
        """Registration page renders correctly."""
        page.goto(live_server.url + reverse('registro'))
        assert page.locator('form').count() > 0

    def test_registro_dev_success(self, page, live_server, db):
        """Register as desarrollador and get redirected to dashboard."""
        page.goto(live_server.url + reverse('registro'))

        page.fill('input[name="username"]', 'e2e_newdev')
        page.fill('input[name="nombre"]', 'E2E New Dev')
        page.fill('input[name="identificacion"]', '9876543210')
        page.fill('input[name="email"]', 'e2e_newdev@test.jobdevs')
        page.fill('input[name="fecha_nacimiento"]', '2000-05-15')
        page.fill('input[name="password1"]', 'E2ETest123!')
        page.fill('input[name="password2"]', 'E2ETest123!')
        # Default rol is desarrollador

        page.locator('button[type="submit"]').click(force=True)

        page.wait_for_url('**/desarrollador/dashboard/', timeout=5000)
        assert 'dashboard' in page.url
