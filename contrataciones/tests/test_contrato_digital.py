import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from contrataciones.models import ContratoDigital
from postulaciones.models import Postulacion
from proyectos.models import Proyecto

User = get_user_model()


@pytest.fixture
def postulacion(db):
    empresa = User.objects.create_user(
        username='cd_emp', email='cd_emp@test.teir', nombre='CD Emp',
        rol='empresa', estado='activo', password='TestPass123!',
    )
    dev = User.objects.create_user(
        username='cd_dev', email='cd_dev@test.teir', nombre='CD Dev',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    proyecto = Proyecto.objects.create(
        empresa=empresa, titulo='Proy Contrato', descripcion='D',
        tipo_solucion='sitio_web', estado='publicado',
    )
    return Postulacion.objects.create(
        proyecto=proyecto, desarrollador=dev, estado='en_negociacion',
    )


class TestContratoDigitalModel:

    def test_defaults(self, postulacion):
        c = ContratoDigital.objects.create(postulacion=postulacion)
        assert c.estado == 'borrador'
        assert c.moneda == 'COP'
        assert c.forma_pago == 'por_hito'
        assert c.monto == 0
        assert c.comentarios_adicionales == ''
        assert c.clausulas.startswith('1. OBJETO:')
        assert 'CONFIDENCIALIDAD' in c.clausulas
        assert 'no procesa pagos' in c.disclaimer
        assert c.firmado_empresa is False
        assert c.firmado_desarrollador is False
        assert c.hash_contrato is None
        assert c.contratacion is None
        assert c.fecha_creacion is not None
        assert ContratoDigital._meta.db_table == 'contratos_digitales'

    def test_calcular_hash_consistente_sha256(self, postulacion):
        c = ContratoDigital.objects.create(postulacion=postulacion, monto='1500000.00')
        h1 = c.calcular_hash()
        h2 = c.calcular_hash()
        assert h1 == h2
        assert len(h1) == 64
        assert int(h1, 16) >= 0

    def test_calcular_hash_cambia_con_datos_clave(self, postulacion):
        c = ContratoDigital.objects.create(postulacion=postulacion, monto='100.00')
        base = c.calcular_hash()

        c.monto = '200.00'
        assert c.calcular_hash() != base
        c.monto = '100.00'
        assert c.calcular_hash() == base

        c.moneda = 'USD'
        assert c.calcular_hash() != base
        c.moneda = 'COP'

        c.fecha_firma_empresa = timezone.now()
        assert c.calcular_hash() != base

    @pytest.mark.parametrize('empresa,dev,esperado', [
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (True, True, True),
    ])
    def test_esta_firmado(self, postulacion, empresa, dev, esperado):
        c = ContratoDigital.objects.create(
            postulacion=postulacion,
            firmado_empresa=empresa, firmado_desarrollador=dev,
        )
        assert c.esta_firmado is esperado

    def test_un_contrato_por_postulacion(self, postulacion):
        ContratoDigital.objects.create(postulacion=postulacion)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ContratoDigital.objects.create(postulacion=postulacion)
        assert ContratoDigital.objects.filter(postulacion=postulacion).count() == 1
        assert postulacion.contrato_digital is not None
