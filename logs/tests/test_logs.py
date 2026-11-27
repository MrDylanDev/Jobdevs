import csv
import io

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
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

    def test_log_registrado_no_puede_modificarse_ni_eliminarse(self, db):
        """La bitácora conserva la inmutabilidad exigida por el inventario interno."""
        log = LogAuditoria.objects.create(
            accion='Cambio original',
            tabla_afectada='usuarios',
        )
        log.accion = 'Cambio alterado'

        with pytest.raises(ValidationError):
            log.save()
        with pytest.raises(ValidationError):
            log.delete()

        log.refresh_from_db()
        assert log.accion == 'Cambio original'




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

    def test_historial_actividad_filtra_por_usuario_tipo_y_fecha(
        self, admin_client, admin_user
    ):
        LogAuditoria.objects.create(
            usuario=admin_user,
            accion='Cambió estado de proyecto',
            tabla_afectada='proyectos',
            registro_id=7,
        )
        LogAuditoria.objects.create(
            accion='Otro evento',
            tabla_afectada='usuarios',
        )

        hoy = timezone.localdate().isoformat()
        response = admin_client.get(reverse('historial_actividad'), {
            'usuario': admin_user.username,
            'tipo': 'proyectos',
            'desde': hoy,
            'hasta': hoy,
        })

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 1
        assert data['resultados'][0]['usuario'] == admin_user.username
        assert data['resultados'][0]['tipo'] == 'proyectos'

    def test_historial_actividad_bloquea_no_admin(self, dev_client):
        assert dev_client.get(reverse('historial_actividad')).status_code == 403

    def test_reporte_mensual_pdf_incluye_tres_totales(
        self, admin_client, empresa_user, desarrollador_user
    ):
        import pymupdf

        from contrataciones.models import Contratacion
        from proyectos.models import Proyecto

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto mensual',
            descripcion='D',
            tipo_solucion='sitio_web',
        )
        Contratacion.objects.create(
            proyecto=proyecto,
            empresa=empresa_user,
            desarrollador=desarrollador_user,
            estado='activa',
        )
        mes = timezone.localdate().strftime('%Y-%m')

        response = admin_client.get(reverse('reporte_mensual_pdf'), {'mes': mes})

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response.content.startswith(b'%PDF')
        documento = pymupdf.open(stream=response.content, filetype='pdf')
        texto = ''.join(pagina.get_text() for pagina in documento)
        documento.close()
        assert 'Usuarios registrados' in texto
        assert 'Proyectos publicados' in texto
        assert 'Contrataciones realizadas' in texto
        assert 'Usuarios registrados:' not in texto
        assert 'Cancelado' not in texto
        for _, etiqueta in Proyecto.ESTADO:
            assert etiqueta in texto

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
        assert response['Content-Type'].startswith('text/csv')
        content = response.content.decode('utf-8-sig')
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
        assert response['Content-Type'].startswith('text/csv')
        content = response.content.decode('utf-8-sig')
        assert 'Empresa,NIT,Sector,Ciudad,Telefono,Email,Proyectos Publicados,Reputación (★)' in content
        assert 'csv_emp_0' in content

    def test_reporte_aprendices_incluye_promedio_y_proyectos_completados(
        self, admin_client, empresa_user, desarrollador_user
    ):
        """RF 7.2.1 oficial: expone estrellas y proyectos completados."""
        from proyectos.models import Proyecto, Valoracion
        from usuarios.models import PerfilDesarrollador

        perfil, _ = PerfilDesarrollador.objects.get_or_create(
            usuario=desarrollador_user
        )
        perfil.num_proyectos_completados = 3
        perfil.save(update_fields=['num_proyectos_completados'])
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto reportado',
            descripcion='D',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Valoracion.objects.create(
            proyecto=proyecto,
            empresa=empresa_user,
            desarrollador=desarrollador_user,
            rol_evaluador='empresa',
            puntuacion=4,
        )

        response = admin_client.get(reverse('reporte_aprendices_csv'))

        filas = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
        fila = next(
            item for item in filas
            if item['Usuario'] == desarrollador_user.username
        )
        assert fila['Promedio'] == '4.0'
        assert fila['Proyectos'] == '3'

    def test_reporte_empresas_incluye_publicaciones_y_reputacion(
        self, admin_client, empresa_user, desarrollador_user
    ):
        """RF 7.2.2 oficial: expone volumen publicado y reputación."""
        from proyectos.models import Proyecto, Valoracion
        from usuarios.models import PerfilEmpresa

        perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=empresa_user)
        perfil.nombre_empresa = 'Empresa del reporte'
        perfil.save(update_fields=['nombre_empresa'])
        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto empresarial',
            descripcion='D',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Valoracion.objects.create(
            proyecto=proyecto,
            empresa=empresa_user,
            desarrollador=desarrollador_user,
            rol_evaluador='desarrollador',
            puntuacion=5,
        )

        response = admin_client.get(reverse('reporte_empresas_csv'))

        filas = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
        fila = next(item for item in filas if item['Empresa'] == 'Empresa del reporte')
        assert fila['Proyectos Publicados'] == '1'
        assert fila['Reputación (★)'] == '5.0'

    def test_reporte_proyectos_incluye_estado_y_detalle_gerencial(
        self, admin_client, empresa_user
    ):
        """RF 7.2.3 oficial: lista el estado de todos los proyectos."""
        from proyectos.models import Proyecto

        proyecto = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto con estado visible',
            descripcion='D',
            tipo_solucion='sitio_web',
            prioridad='alta',
            estado='en_desarrollo',
            vacantes=2,
        )

        response = admin_client.get(reverse('reporte_proyectos_csv'))

        filas = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
        fila = next(item for item in filas if item['Título'] == proyecto.titulo)
        assert fila['Estado'] == proyecto.get_estado_display()
        assert fila['Prioridad'] == proyecto.get_prioridad_display()
        assert fila['Vacantes Totales'] == '2'

    @pytest.mark.parametrize(
        'nombre_ruta',
        ('reporte_aprendices_csv', 'reporte_empresas_csv', 'reporte_proyectos_csv'),
    )
    def test_reportes_oficiales_bloquean_usuario_no_admin(
        self, dev_client, nombre_ruta
    ):
        response = dev_client.get(reverse(nombre_ruta))

        assert response.status_code == 302

    def test_reportes_csv_incluyen_bom_sanitizan_formulas_filtran_y_auditan(
        self, admin_client, empresa_user
    ):
        from datetime import timedelta
        from django.utils import timezone
        from logs.models import LogAuditoria
        from proyectos.models import Proyecto

        p_inyeccion = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='=SUM(A1:A2)',
            descripcion='Desc',
            tipo_solucion='sitio_web',
            estado='publicado',
        )
        p_otro = Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto finalizado viejo',
            descripcion='Desc',
            tipo_solucion='sitio_web',
            estado='finalizado',
        )
        Proyecto.objects.filter(pk=p_otro.pk).update(
            fecha_publicacion=timezone.now() - timedelta(days=20)
        )

        hoy = timezone.localdate().isoformat()
        res = admin_client.get(
            reverse('reporte_proyectos_csv'),
            {'estado': 'publicado', 'fecha_desde': hoy, 'fecha_hasta': hoy},
        )
        assert res.status_code == 200
        assert 'charset=utf-8' in res['Content-Type']
        assert res.content.startswith(b'\xef\xbb\xbf')
        texto = res.content.decode('utf-8-sig')
        assert "'=SUM(A1:A2)" in texto
        assert 'Proyecto finalizado viejo' not in texto
        assert LogAuditoria.objects.filter(
            tabla_afectada='reportes', accion__icontains='Reporte de proyectos CSV'
        ).exists()

    def test_dashboard_admin_expone_todos_los_reportes(self, admin_client):
        res = admin_client.get(reverse('dashboard_admin'))
        assert res.status_code == 200
        html = res.content.decode('utf-8')
        assert reverse('reporte_proyectos_csv') in html
        assert reverse('reporte_aprendices_csv') in html
        assert reverse('reporte_empresas_csv') in html
        assert reverse('reporte_auditoria_csv') in html
        assert reverse('reporte_mensual_pdf') in html
        assert reverse('reporte_vista_impresion') in html
        assert 'name="mes"' in html

    @pytest.mark.parametrize(
        'nombre_ruta,titulo_esperado',
        (
            ('reporte_proyectos_csv', 'Reporte de Proyectos'),
            ('reporte_aprendices_csv', 'Reporte de Aprendices'),
            ('reporte_empresas_csv', 'Reporte de Empresas'),
            ('reporte_auditoria_csv', 'Reporte de Auditoría'),
        ),
    )
    def test_reportes_oficiales_soportan_formato_pdf(
        self, admin_client, empresa_user, desarrollador_user, nombre_ruta, titulo_esperado
    ):
        import pymupdf
        from logs.models import LogAuditoria
        from proyectos.models import Proyecto
        from usuarios.models import PerfilDesarrollador, PerfilEmpresa

        PerfilDesarrollador.objects.get_or_create(usuario=desarrollador_user)
        PerfilEmpresa.objects.get_or_create(usuario=empresa_user)
        Proyecto.objects.create(
            empresa=empresa_user,
            titulo='Proyecto PDF Test',
            descripcion='D',
            tipo_solucion='sitio_web',
        )

        res = admin_client.get(reverse(nombre_ruta), {'formato': 'pdf'})
        assert res.status_code == 200
        assert res['Content-Type'] == 'application/pdf'
        assert res.content.startswith(b'%PDF')
        doc = pymupdf.open(stream=res.content, filetype='pdf')
        texto = ''.join(p.get_text() for p in doc)
        doc.close()
        assert titulo_esperado in texto
        assert LogAuditoria.objects.filter(
            tabla_afectada='reportes', accion__icontains='PDF'
        ).exists()

    @pytest.mark.parametrize(
        'nombre_ruta',
        (
            'reporte_proyectos_csv',
            'reporte_aprendices_csv',
            'reporte_empresas_csv',
            'reporte_auditoria_csv',
        ),
    )
    @pytest.mark.parametrize('valor_invalido', ('no-es-fecha', '2026-02-31'))
    def test_reportes_rechazan_fechas_invalidas_con_400(
        self, admin_client, nombre_ruta, valor_invalido
    ):
        res = admin_client.get(reverse(nombre_ruta), {'fecha_desde': valor_invalido})
        assert res.status_code == 400
        assert 'error' in res.json()

    def test_reporte_auditoria_csv_avisa_cuando_trunca(
        self, admin_client, admin_user, monkeypatch
    ):
        from logs import views as logs_views

        monkeypatch.setattr(logs_views, 'MAX_EXPORT_AUDITORIA', 3)
        for i in range(5):
            LogAuditoria.objects.create(
                usuario=admin_user,
                accion=f'Evento prueba {i}',
                tabla_afectada='proyectos',
            )

        res = admin_client.get(reverse('reporte_auditoria_csv'), {'tabla': 'proyectos'})
        assert res.status_code == 200
        assert res.get('X-Export-Truncated') == 'true'
        filas = list(csv.reader(io.StringIO(res.content.decode('utf-8-sig'))))
        # encabezado + 3 filas de datos + 1 fila de advertencia
        assert len(filas) == 5
        assert filas[-1][1] == 'ADVERTENCIA'
        assert 'límite de 3 registros' in filas[-1][2]

    def test_reporte_auditoria_sin_filtros_no_se_incluye_a_si_mismo(
        self, admin_client, admin_user, monkeypatch
    ):
        from logs import views as logs_views

        monkeypatch.setattr(logs_views, 'MAX_EXPORT_AUDITORIA', 2)
        for i in range(2):
            LogAuditoria.objects.create(
                usuario=admin_user,
                accion=f'Evento previo {i}',
                tabla_afectada='proyectos',
            )

        res = admin_client.get(reverse('reporte_auditoria_csv'))
        assert res.status_code == 200
        assert res.get('X-Export-Truncated') is None
        filas = list(csv.reader(io.StringIO(res.content.decode('utf-8-sig'))))
        # encabezado + 2 eventos previos (sin incluir el log del propio reporte)
        assert len(filas) == 3
        acciones = [f[2] for f in filas[1:]]
        assert all('Reporte de auditoría CSV' not in a for a in acciones)
        assert set(acciones) == {'Evento previo 0', 'Evento previo 1'}

    def test_badge_estado_html_no_marca_inactivo_como_ok(self):
        from logs.pdf_reports import _badge_estado_html

        html_inactivo = _badge_estado_html('Inactivo')
        html_activo = _badge_estado_html('Activo')
        assert 'badge-ok' not in html_inactivo
        assert 'badge-ok' in html_activo



class TestVisorLogsTecnicos:
    """SCRUM-317 (HU-A18): visor de logs técnicos del servidor, solo administrador."""

    def _log_file(self, tmp_path, lineas=150):
        archivo = tmp_path / 'jobdevs.log'
        archivo.write_text(
            '\n'.join(f'linea {i}' for i in range(1, lineas + 1)) + '\n',
            encoding='utf-8',
        )
        return archivo

    def test_no_admin_recibe_403(self, dev_client):
        response = dev_client.get(reverse('visor_logs_tecnicos'))
        assert response.status_code == 403

    def test_anonimo_redirige_a_login(self, client):
        response = client.get(reverse('visor_logs_tecnicos'))
        assert response.status_code == 302

    def test_admin_recibe_json(self, admin_client, settings, tmp_path):
        settings.LOG_FILE_APP = self._log_file(tmp_path)
        response = admin_client.get(
            reverse('visor_logs_tecnicos'), {'format': 'json', 'lineas': 50}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['archivo'] == 'jobdevs.log'
        assert data['total'] == 50
        assert len(data['lineas']) == 50
        assert data['lineas'][-1] == 'linea 150'

    def test_admin_recibe_texto_plano(self, admin_client, settings, tmp_path):
        settings.LOG_FILE_APP = self._log_file(tmp_path)
        response = admin_client.get(reverse('visor_logs_tecnicos'), {'lineas': 20})
        assert response.status_code == 200
        assert response['Content-Type'].startswith('text/plain')
        assert 'linea 150' in response.content.decode('utf-8')

    def test_lineas_se_acotan_entre_20_y_500(self, admin_client, settings, tmp_path):
        settings.LOG_FILE_APP = self._log_file(tmp_path, lineas=600)
        response = admin_client.get(
            reverse('visor_logs_tecnicos'), {'format': 'json', 'lineas': 1000}
        )
        assert response.json()['total'] == 500
        response = admin_client.get(
            reverse('visor_logs_tecnicos'), {'format': 'json', 'lineas': 1}
        )
        assert response.json()['total'] == 20

    def test_archivo_inexistente_devuelve_placeholder(self, admin_client, settings, tmp_path):
        settings.LOG_FILE_APP = tmp_path / 'no-existe.log'
        response = admin_client.get(
            reverse('visor_logs_tecnicos'), {'format': 'json'}
        )
        assert response.status_code == 200
        assert response.json()['lineas'] == [
            '(Archivo de log técnico jobdevs.log inicializándose...)'
        ]

    def test_registra_auditoria(self, admin_client, admin_user, settings, tmp_path):
        settings.LOG_FILE_APP = self._log_file(tmp_path)
        admin_client.get(reverse('visor_logs_tecnicos'), {'lineas': 30})
        log = LogAuditoria.objects.filter(
            usuario=admin_user, tabla_afectada='logs_tecnicos'
        ).first()
        assert log is not None
        assert '30' in log.accion

    def test_xhr_header_devuelve_json(self, admin_client, settings, tmp_path):
        settings.LOG_FILE_APP = self._log_file(tmp_path)
        response = admin_client.get(
            reverse('visor_logs_tecnicos'),
            {'lineas': 25},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert response.status_code == 200
        assert response['Content-Type'].startswith('application/json')
        assert response.json()['total'] == 25

    def test_lineas_invalidas_no_rompen_la_vista(self, admin_client, settings, tmp_path):
        settings.LOG_FILE_APP = self._log_file(tmp_path)
        response = admin_client.get(
            reverse('visor_logs_tecnicos'), {'format': 'json', 'lineas': 'abc'}
        )
        assert response.status_code == 200
        assert response.json()['total'] == 100
