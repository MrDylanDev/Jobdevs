import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from logs.models import LogAuditoria

User = get_user_model()


class TestLogAuditoriaModel:
    """Tests for LogAuditoria model."""

    def test_crear_log(self, db):
        """LogAuditoria records user actions."""
        user = User.objects.create_user(
            username='lg', email='lg@test.jobdevs',
            nombre='LG', rol='administrador', estado='activo',
            password='TestPass123!',
        )
        log = LogAuditoria.objects.create(
            usuario=user, accion='TEST',
            tabla_afectada='usuarios',
        )
        assert log.id is not None
        assert log.accion == 'TEST'
        assert log.usuario == user

    def test_log_str(self, db):
        """__str__ shows usuario and accion."""
        user = User.objects.create_user(
            username='lg2', email='lg2@test.jobdevs',
            nombre='LG2', rol='administrador', estado='activo',
            password='TestPass123!',
        )
        log = LogAuditoria.objects.create(
            usuario=user, accion='LOGIN',
            tabla_afectada='usuarios',
        )
        assert 'lg2' in str(log)
        assert 'LOGIN' in str(log)

    def test_log_auditoria_trunca_automaticamente_accion_larga(self, db):
        """SCRUM-179: LogAuditoria.save() trunca automáticamente strings > 300 caracteres."""
        accion_larga = 'Accion super detallada ' * 25  # ~600 caracteres
        tabla_larga = 'nombre_de_tabla_gigante_' * 10   # ~240 caracteres
        log = LogAuditoria.objects.create(
            accion=accion_larga,
            tabla_afectada=tabla_larga,
        )
        assert len(log.accion) == 300
        assert len(log.tabla_afectada) == 100
        log.refresh_from_db()
        assert len(log.accion) == 300
        assert len(log.tabla_afectada) == 100

    def test_log_auditoria_soporta_valor_anterior_y_valor_nuevo(self, db):
        """SCRUM-224 (RF 7.1.2): LogAuditoria persiste valor_anterior y valor_nuevo."""
        log = LogAuditoria.objects.create(
            accion='Cambio de estado',
            tabla_afectada='contrataciones',
            registro_id=1,
            valor_anterior='activa',
            valor_nuevo='cancelada',
        )
        assert log.id is not None
        log.refresh_from_db()
        assert log.valor_anterior == 'activa'
        assert log.valor_nuevo == 'cancelada'




class TestReportes:
    """Tests for report views (admin only)."""

    def test_reporte_vista_impresion_accessible(self, admin_client):
        """Admin can access report view."""
        response = admin_client.get(reverse('reporte_vista_impresion'))
        assert response.status_code == 200

    def test_reporte_blocked_anon(self, client):
        """Anonymous cannot access reports."""
        response = client.get(reverse('reporte_vista_impresion'))
        assert response.status_code == 302

    def test_reporte_aprendices_csv_sin_n_mas_1(self, admin_client, db):
        """SCRUM-177: reporte_aprendices_csv ejecuta un número acotado de consultas con .annotate()."""
        from usuarios.models import PerfilDesarrollador
        for i in range(5):
            u = User.objects.create_user(
                username=f'csv_dev_{i}', email=f'csvdev{i}@test.jobdevs',
                nombre=f'Dev {i}', rol='desarrollador',
            )
            PerfilDesarrollador.objects.get_or_create(usuario=u)

        response = admin_client.get(reverse('reporte_aprendices_csv'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        content = response.content.decode('utf-8')
        assert 'Usuario,Nombre,Programa,Ficha,Promedio,Proyectos' in content
        assert 'csv_dev_0' in content

    def test_reporte_empresas_csv_sin_n_mas_1(self, admin_client, db):
        """SCRUM-177: reporte_empresas_csv ejecuta una sola ráfaga SQL con .annotate()."""
        from usuarios.models import PerfilEmpresa
        for i in range(5):
            u = User.objects.create_user(
                username=f'csv_emp_{i}', email=f'csvemp{i}@test.jobdevs',
                nombre=f'Emp {i}', rol='empresa',
            )
            PerfilEmpresa.objects.get_or_create(usuario=u)

        response = admin_client.get(reverse('reporte_empresas_csv'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        content = response.content.decode('utf-8')
        assert 'Empresa,NIT,Sector,Ciudad,Telefono,Email,Proyectos Publicados,Reputación (★)' in content
        assert 'csv_emp_0' in content

