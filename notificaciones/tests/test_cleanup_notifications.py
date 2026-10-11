from datetime import timedelta
import pytest
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth import get_user_model
from notificaciones.models import Notificacion

User = get_user_model()


@pytest.fixture
def notif_user(db):
    return User.objects.create_user(
        username='notif_user',
        email='notif@test.teir',
        nombre='Notif User',
        rol='desarrollador',
        password='TestPassword123*',
    )


@pytest.mark.django_db
class TestCleanupNotificationsCommand:
    def test_cleanup_notifications_deletes_old_read_only(self, notif_user):
        """Default run deletes read notifications older than 90 days, preserving unread and recent ones."""
        now = timezone.now()

        # 1. Leída vieja (>90 días) -> Debe eliminarse
        n_old_read = Notificacion.objects.create(
            usuario=notif_user, tipo='alerta', mensaje='Old Read', leida=True,
        )
        Notificacion.objects.filter(id=n_old_read.id).update(fecha=now - timedelta(days=95))

        # 2. No leída vieja (>90 días) -> Debe preservarse
        n_old_unread = Notificacion.objects.create(
            usuario=notif_user, tipo='alerta', mensaje='Old Unread', leida=False,
        )
        Notificacion.objects.filter(id=n_old_unread.id).update(fecha=now - timedelta(days=95))

        # 3. Leída reciente (<90 días) -> Debe preservarse
        n_recent_read = Notificacion.objects.create(
            usuario=notif_user, tipo='alerta', mensaje='Recent Read', leida=True,
        )
        Notificacion.objects.filter(id=n_recent_read.id).update(fecha=now - timedelta(days=10))

        call_command('cleanup_notifications', days=90)

        assert not Notificacion.objects.filter(id=n_old_read.id).exists()
        assert Notificacion.objects.filter(id=n_old_unread.id).exists()
        assert Notificacion.objects.filter(id=n_recent_read.id).exists()

    def test_cleanup_notifications_custom_days(self, notif_user):
        """Custom --days parameter works properly."""
        now = timezone.now()

        n = Notificacion.objects.create(
            usuario=notif_user, tipo='alerta', mensaje='35 days old', leida=True,
        )
        Notificacion.objects.filter(id=n.id).update(fecha=now - timedelta(days=35))

        # Con default 90 días no se borra
        call_command('cleanup_notifications', days=90)
        assert Notificacion.objects.filter(id=n.id).exists()

        # Con 30 días sí se borra
        call_command('cleanup_notifications', days=30)
        assert not Notificacion.objects.filter(id=n.id).exists()

    def test_cleanup_notifications_dry_run(self, notif_user):
        """--dry-run simulates deletion without modifying database."""
        now = timezone.now()
        n = Notificacion.objects.create(
            usuario=notif_user, tipo='alerta', mensaje='Dry run target', leida=True,
        )
        Notificacion.objects.filter(id=n.id).update(fecha=now - timedelta(days=100))

        call_command('cleanup_notifications', days=90, dry_run=True)
        assert Notificacion.objects.filter(id=n.id).exists()

    def test_cleanup_notifications_include_unread_flag(self, notif_user):
        """--all flag removes unread old notifications as well."""
        now = timezone.now()
        n_unread = Notificacion.objects.create(
            usuario=notif_user, tipo='alerta', mensaje='Old unread with all flag', leida=False,
        )
        Notificacion.objects.filter(id=n_unread.id).update(fecha=now - timedelta(days=100))

        call_command('cleanup_notifications', days=90, all=True)
        assert not Notificacion.objects.filter(id=n_unread.id).exists()
