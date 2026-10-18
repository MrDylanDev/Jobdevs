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
        username='cd_emp', email='cd_emp@test.jobdevs', nombre='CD Emp',
        rol='empresa', estado='activo', password='TestPass123!',
    )
    dev = User.objects.create_user(
        username='cd_dev', email='cd_dev@test.jobdevs', nombre='CD Dev',
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


# ---------------------------------------------------------------------------
# Vistas: ver / editar / firmar contrato digital
# ---------------------------------------------------------------------------

from django.test import Client
from django.urls import reverse

from contrataciones.models import Contratacion
from logs.models import LogAuditoria
from notificaciones.models import Notificacion


def _login(username):
    c = Client()
    assert c.login(username=username, password='TestPass123!')
    return c


@pytest.fixture
def contrato(postulacion):
    return ContratoDigital.objects.create(postulacion=postulacion)


@pytest.fixture
def empresa_c(contrato):
    return _login('cd_emp')


@pytest.fixture
def dev_c(contrato):
    return _login('cd_dev')


@pytest.fixture
def tercero_c(db):
    User.objects.create_user(
        username='cd_ext', email='cd_ext@test.jobdevs', nombre='Externo',
        rol='desarrollador', estado='activo', password='TestPass123!',
    )
    return _login('cd_ext')


class TestVerContratoDigital:

    def test_empresa_ve_contrato_y_formulario_editable(self, empresa_c, contrato):
        res = empresa_c.get(reverse('ver_contrato_digital', args=[contrato.id]))
        assert res.status_code == 200
        assert res.context['puede_editar'] is True
        assert res.context['puede_firmar'] is True
        html = res.content.decode()
        assert 'name="monto"' in html
        assert 'no procesa pagos' in html  # disclaimer legal visible
        assert 'name="acepta_terminos"' in html

    def test_desarrollador_ve_contrato_sin_edicion(self, dev_c, contrato):
        res = dev_c.get(reverse('ver_contrato_digital', args=[contrato.id]))
        assert res.status_code == 200
        assert res.context['puede_editar'] is False
        assert 'name="monto"' not in res.content.decode()

    def test_tercero_no_participante_recibe_403(self, tercero_c, contrato):
        url = reverse('ver_contrato_digital', args=[contrato.id])
        assert tercero_c.get(url).status_code == 403
        assert tercero_c.post(url, {'monto': '1'}).status_code == 403
        firmar = reverse('firmar_contrato_digital', args=[contrato.id])
        assert tercero_c.post(firmar, {'acepta_terminos': 'on'}).status_code == 403
        contrato.refresh_from_db()
        assert contrato.monto == 0 and not contrato.firmado_empresa

    def test_anonimo_redirige_a_login(self, client, contrato):
        res = client.get(reverse('ver_contrato_digital', args=[contrato.id]))
        assert res.status_code == 302

    def test_empresa_edita_terminos(self, empresa_c, contrato):
        res = empresa_c.post(reverse('ver_contrato_digital', args=[contrato.id]), {
            'monto': '2500000.50', 'moneda': 'USD', 'forma_pago': 'mensual',
            'comentarios_adicionales': 'Entrega en 2 meses',
        })
        assert res.status_code == 302
        contrato.refresh_from_db()
        assert str(contrato.monto) == '2500000.50'
        assert contrato.moneda == 'USD'
        assert contrato.forma_pago == 'mensual'
        assert contrato.comentarios_adicionales == 'Entrega en 2 meses'
        assert LogAuditoria.objects.filter(
            tabla_afectada='contratos_digitales', registro_id=contrato.id).exists()

    def test_desarrollador_no_puede_editar_terminos(self, dev_c, contrato):
        res = dev_c.post(reverse('ver_contrato_digital', args=[contrato.id]), {
            'monto': '999', 'moneda': 'COP', 'forma_pago': 'mensual',
        })
        assert res.status_code == 403
        contrato.refresh_from_db()
        assert contrato.monto == 0

    @pytest.mark.parametrize('payload', [
        {'monto': 'abc', 'moneda': 'COP', 'forma_pago': 'mensual'},
        {'monto': '-5', 'moneda': 'COP', 'forma_pago': 'mensual'},
        {'monto': '10', 'moneda': 'EUR', 'forma_pago': 'mensual'},
        {'monto': '10', 'moneda': 'COP', 'forma_pago': 'inventada'},
    ])
    def test_edicion_invalida_no_modifica(self, empresa_c, contrato, payload):
        res = empresa_c.post(reverse('ver_contrato_digital', args=[contrato.id]), payload)
        assert res.status_code == 302
        contrato.refresh_from_db()
        assert contrato.monto == 0 and contrato.moneda == 'COP' and contrato.forma_pago == 'por_hito'

    def test_no_se_edita_tras_una_firma(self, empresa_c, dev_c, contrato):
        dev_c.post(reverse('firmar_contrato_digital', args=[contrato.id]), {'acepta_terminos': 'on'})
        empresa_c.post(reverse('ver_contrato_digital', args=[contrato.id]), {
            'monto': '777', 'moneda': 'COP', 'forma_pago': 'mensual',
        })
        contrato.refresh_from_db()
        assert contrato.monto == 0


class TestFirmarContratoDigital:

    def test_requiere_post(self, empresa_c, contrato):
        res = empresa_c.get(reverse('firmar_contrato_digital', args=[contrato.id]))
        assert res.status_code == 405

    def test_firma_sin_aceptar_terminos_no_firma(self, empresa_c, contrato):
        res = empresa_c.post(reverse('firmar_contrato_digital', args=[contrato.id]))
        assert res.status_code == 302
        contrato.refresh_from_db()
        assert contrato.firmado_empresa is False
        assert contrato.hash_contrato is None

    def test_primera_firma_pendiente_firma_y_hash(self, empresa_c, contrato):
        res = empresa_c.post(
            reverse('firmar_contrato_digital', args=[contrato.id]), {'acepta_terminos': 'on'})
        assert res.status_code == 302
        contrato.refresh_from_db()
        assert contrato.firmado_empresa is True
        assert contrato.fecha_firma_empresa is not None
        assert contrato.firmado_desarrollador is False
        assert contrato.estado == 'pendiente_firma'
        assert contrato.hash_contrato == contrato.calcular_hash()
        assert len(contrato.hash_contrato) == 64
        # No se formaliza aún
        assert not Contratacion.objects.filter(proyecto=contrato.postulacion.proyecto).exists()
        contrato.postulacion.refresh_from_db()
        assert contrato.postulacion.estado == 'en_negociacion'
        # Se notifica a la otra parte
        assert Notificacion.objects.filter(
            usuario=contrato.postulacion.desarrollador, tipo='alerta').exists()

    def test_no_se_puede_firmar_dos_veces(self, empresa_c, contrato):
        url = reverse('firmar_contrato_digital', args=[contrato.id])
        empresa_c.post(url, {'acepta_terminos': 'on'})
        contrato.refresh_from_db()
        fecha, h = contrato.fecha_firma_empresa, contrato.hash_contrato
        empresa_c.post(url, {'acepta_terminos': 'on'})
        contrato.refresh_from_db()
        assert contrato.fecha_firma_empresa == fecha
        assert contrato.hash_contrato == h

    def test_segunda_firma_activa_contratacion_formal(self, empresa_c, dev_c, contrato):
        url = reverse('firmar_contrato_digital', args=[contrato.id])
        dev_c.post(url, {'acepta_terminos': 'on'})
        hash_parcial = ContratoDigital.objects.get(id=contrato.id).hash_contrato
        res = empresa_c.post(url, {'acepta_terminos': 'on'})
        assert res.status_code == 302

        contrato.refresh_from_db()
        postulacion = contrato.postulacion
        postulacion.refresh_from_db()
        proyecto = postulacion.proyecto
        proyecto.refresh_from_db()

        assert contrato.esta_firmado
        assert contrato.estado == 'firmado'
        assert contrato.hash_contrato == contrato.calcular_hash()
        assert contrato.hash_contrato != hash_parcial

        assert postulacion.estado == 'aceptada'
        assert proyecto.estado == 'en_desarrollo'

        contratacion = Contratacion.objects.get(
            proyecto=proyecto, desarrollador=postulacion.desarrollador)
        assert contratacion.estado == 'activa'
        assert contratacion.empresa == proyecto.empresa
        assert contrato.contratacion == contratacion

        assert proyecto.equipos.first().miembros.filter(id=postulacion.desarrollador_id).exists()
        assert Notificacion.objects.filter(usuario=proyecto.empresa, tipo='aprobacion').exists()
        assert Notificacion.objects.filter(usuario=postulacion.desarrollador, tipo='aprobacion').exists()
        assert LogAuditoria.objects.filter(
            tabla_afectada='contratos_digitales', registro_id=contrato.id,
            accion__contains='formalizada').exists()
        assert proyecto.historial_estados.filter(estado_nuevo='en_desarrollo').exists()

    def test_activacion_rechaza_pendientes_si_se_llena_cupo(self, empresa_c, dev_c, contrato):
        proyecto = contrato.postulacion.proyecto  # vacantes por defecto = 1
        otro = User.objects.create_user(
            username='cd_otro', email='cd_otro@test.jobdevs', nombre='Otro',
            rol='desarrollador', estado='activo', password='TestPass123!',
        )
        pendiente = Postulacion.objects.create(proyecto=proyecto, desarrollador=otro, estado='pendiente')
        url = reverse('firmar_contrato_digital', args=[contrato.id])
        dev_c.post(url, {'acepta_terminos': 'on'})
        empresa_c.post(url, {'acepta_terminos': 'on'})
        pendiente.refresh_from_db()
        assert proyecto.vacantes == 1
        assert pendiente.estado == 'rechazada'

    def test_no_se_firma_contrato_ya_firmado(self, empresa_c, dev_c, contrato):
        url = reverse('firmar_contrato_digital', args=[contrato.id])
        dev_c.post(url, {'acepta_terminos': 'on'})
        empresa_c.post(url, {'acepta_terminos': 'on'})
        empresa_c.post(url, {'acepta_terminos': 'on'})
        assert Contratacion.objects.filter(proyecto=contrato.postulacion.proyecto).count() == 1
