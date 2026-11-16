import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from logs.models import LogAuditoria
from postulaciones import services
from postulaciones.models import ConfiguracionNegociacion


@pytest.mark.django_db
class TestConfiguracionNegociacion:
    def test_plazo_predeterminado_es_siete_dias(self):
        assert services.obtener_plazo_negociacion_dias() == 7

    @pytest.mark.parametrize('plazo', [0, 31])
    def test_rechaza_plazos_fuera_del_rango(self, plazo):
        configuracion = ConfiguracionNegociacion(pk=1, plazo_dias=plazo)

        with pytest.raises(ValidationError):
            configuracion.full_clean()

    def test_administrador_actualiza_plazo_y_registra_auditoria(self, admin_user):
        configuracion = services.actualizar_plazo_negociacion_dias(15, admin_user)

        assert configuracion.plazo_dias == 15
        log = LogAuditoria.objects.get(
            tabla_afectada='configuracion_negociacion', registro_id=1
        )
        assert log.usuario == admin_user
        assert log.valor_anterior == 'plazo_dias=7'
        assert log.valor_nuevo == 'plazo_dias=15'

    def test_no_administrador_no_puede_actualizar_plazo(self, empresa_user):
        with pytest.raises(PermissionDenied):
            services.actualizar_plazo_negociacion_dias(10, empresa_user)

        assert services.obtener_plazo_negociacion_dias() == 7

    def test_administrador_actualiza_plazo_desde_panel(self, admin_client):
        response = admin_client.post(
            reverse('admin_actualizar_configuracion_negociacion'),
            {'plazo_dias': '12'},
        )

        assert response.status_code == 302
        assert services.obtener_plazo_negociacion_dias() == 12

    def test_panel_muestra_control_con_limites(self, admin_client):
        response = admin_client.get(reverse('dashboard_admin'))

        assert response.status_code == 200
        assert b'name="plazo_dias"' in response.content
        assert b'min="1"' in response.content
        assert b'max="30"' in response.content
