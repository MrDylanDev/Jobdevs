import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from usuarios.models import FichaSena, PerfilDesarrollador

Usuario = get_user_model()


@pytest.fixture
def admin_user(db):
    return Usuario.objects.create_user(
        username='admin_sena',
        email='admin@sena.edu.co',
        password='Password123!',
        rol='administrador',
        identificacion='1000000001',
    )


@pytest.fixture
def dev_user(db):
    user = Usuario.objects.create_user(
        username='aprendiz_juan',
        email='juan@sena.edu.co',
        password='Password123!',
        rol='desarrollador',
        identificacion='1000000002',
    )
    PerfilDesarrollador.objects.get_or_create(usuario=user)
    return user


@pytest.mark.django_db
class TestFichaSenaModel:
    def test_crear_ficha_sena(self, admin_user):
        ficha = FichaSena.objects.create(
            numero_ficha='2670123',
            programa_formacion='Análisis y Desarrollo de Software (ADSO)',
            regional='Distrito Capital',
            centro_formacion='Centro de Servicios Financieros',
            creada_por=admin_user,
        )
        assert ficha.numero_ficha == '2670123'
        assert ficha.programa_formacion == 'Análisis y Desarrollo de Software (ADSO)'
        assert ficha.regional == 'Distrito Capital'
        assert ficha.centro_formacion == 'Centro de Servicios Financieros'
        assert ficha.activa is True
        assert ficha.creada_por == admin_user
        assert str(ficha) == '2670123 - Análisis y Desarrollo de Software (ADSO)'

    def test_numero_ficha_unique(self, admin_user):
        FichaSena.objects.create(
            numero_ficha='2670999',
            programa_formacion='ADSO',
            creada_por=admin_user,
        )
        with pytest.raises(IntegrityError):
            FichaSena.objects.create(
                numero_ficha='2670999',
                programa_formacion='Otro Programa',
                creada_por=admin_user,
            )


@pytest.mark.django_db
class TestPerfilDesarrolladorVerificacionModel:
    def test_defaults_verificacion(self, dev_user):
        perfil = dev_user.perfil_desarrollador
        assert perfil.condicion_sena == 'aprendiz'
        assert perfil.estado_verificacion == 'sin_verificar'
        assert perfil.ficha_sena is None
        assert perfil.documento_soporte.name in (None, '')
        assert perfil.fecha_solicitud_verificacion is None
        assert perfil.fecha_verificacion is None
        assert perfil.verificado_por is None
        assert perfil.notas_auditoria in (None, '')
        assert perfil.es_verificado_sena is False

    @pytest.mark.parametrize('estado,esperado', [
        ('sin_verificar', False),
        ('en_revision', False),
        ('verificado', True),
        ('rechazado', False),
    ])
    def test_es_verificado_sena_property(self, dev_user, estado, esperado):
        perfil = dev_user.perfil_desarrollador
        perfil.estado_verificacion = estado
        perfil.save()
        assert perfil.es_verificado_sena is esperado

    @pytest.mark.parametrize('condicion,estado,label_esperado,css_esperado', [
        ('aprendiz', 'verificado', 'Aprendiz SENA', 'badge-verificada'),
        ('egresado', 'verificado', 'Egresado SENA', 'badge-verificada'),
        ('aprendiz', 'en_revision', 'En Revisión SENA', 'badge-en-revision'),
        ('egresado', 'en_revision', 'En Revisión (Egresado)', 'badge-en-revision'),
        ('aprendiz', 'rechazado', 'Verificación Rechazada', 'badge-rechazada'),
        ('egresado', 'rechazado', 'Verificación Rechazada', 'badge-rechazada'),
        ('aprendiz', 'sin_verificar', 'Sin Verificar', 'badge-sin-verificar'),
        ('egresado', 'sin_verificar', 'Sin Verificar', 'badge-sin-verificar'),
    ])
    def test_badge_info_property_por_condicion(self, dev_user, condicion, estado, label_esperado, css_esperado):
        perfil = dev_user.perfil_desarrollador
        perfil.condicion_sena = condicion
        perfil.estado_verificacion = estado
        perfil.save()
        badge = perfil.badge_info
        assert badge['label'] == label_esperado
        assert badge['css_class'] == css_esperado

    def test_asociacion_ficha_sena_fk(self, dev_user, admin_user):
        ficha = FichaSena.objects.create(
            numero_ficha='2670555',
            programa_formacion='ADSO',
            creada_por=admin_user,
        )
        perfil = dev_user.perfil_desarrollador
        perfil.ficha_sena = ficha
        perfil.estado_verificacion = 'verificado'
        perfil.fecha_verificacion = timezone.now()
        perfil.verificado_por = admin_user
        perfil.save()

        perfil.refresh_from_db()
        assert perfil.ficha_sena == ficha
        assert perfil.verificado_por == admin_user
        assert ficha.aprendices_verificados.filter(id=perfil.id).exists()
