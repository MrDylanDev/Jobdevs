import pytest
from django.core.management import call_command
from usuarios.models import Usuario, PerfilEmpresa, PerfilDesarrollador


@pytest.mark.django_db
class TestSeedDemoDataCommand:
    def test_seed_demo_data_creates_accounts(self):
        call_command('seed_demo_data', password='PasswordSegura2026*')

        # Verificar admin
        admin = Usuario.objects.get(username='admin_demo')
        assert admin.rol == 'administrador'
        assert admin.is_superuser is True
        assert admin.check_password('PasswordSegura2026*')

        # Verificar empresa
        empresa = Usuario.objects.get(username='empresa_demo')
        assert empresa.rol == 'empresa'
        assert PerfilEmpresa.objects.filter(usuario=empresa).exists()

        # Verificar desarrollador
        dev = Usuario.objects.get(username='dev_demo')
        assert dev.rol == 'desarrollador'
        assert PerfilDesarrollador.objects.filter(usuario=dev).exists()

    def test_seed_demo_data_is_idempotent(self):
        call_command('seed_demo_data', password='PasswordSegura2026*')
        # Segunda ejecución no debe fallar ni duplicar registros
        call_command('seed_demo_data', password='PasswordSegura2026*')

        assert Usuario.objects.filter(username='admin_demo').count() == 1
        assert Usuario.objects.filter(username='empresa_demo').count() == 1
        assert Usuario.objects.filter(username='dev_demo').count() == 1
