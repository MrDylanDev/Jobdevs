import pytest

from usuarios.models import PerfilEmpresa, Usuario


@pytest.fixture
def perfil(db):
    user = Usuario.objects.create_user(
        username='empresa_verif', email='e@example.com', password='x', nombre='Emp', rol='empresa'
    )
    return PerfilEmpresa.objects.create(usuario=user)


def _values(choices):
    return [c[0] for c in choices]


def test_estado_verificacion_default(perfil):
    assert perfil.estado_verificacion == 'sin_verificar'


def test_defaults_tipo_persona_y_documento(perfil):
    assert perfil.tipo_persona == 'juridica'
    assert perfil.tipo_documento == 'NIT'


def test_choices_tipo_persona():
    field = PerfilEmpresa._meta.get_field('tipo_persona')
    assert _values(field.choices) == ['juridica', 'natural']


def test_choices_tipo_documento():
    field = PerfilEmpresa._meta.get_field('tipo_documento')
    assert _values(field.choices) == ['NIT', 'CC', 'CE']


def test_choices_estado_verificacion():
    field = PerfilEmpresa._meta.get_field('estado_verificacion')
    assert _values(field.choices) == ['sin_verificar', 'en_revision', 'verificada', 'rechazada']


@pytest.mark.parametrize('name', [
    'numero_documento', 'digito_verificacion', 'razon_social', 'documento_soporte',
    'fecha_solicitud_verificacion', 'fecha_verificacion', 'verificado_por', 'notas_auditoria',
])
def test_campos_existen_y_son_opcionales(name):
    field = PerfilEmpresa._meta.get_field(name)
    assert field.null is True
    assert field.blank is True


def test_verificado_por_fk(perfil):
    admin = Usuario.objects.create_user(
        username='adm', email='a@example.com', password='x', nombre='Adm', rol='administrador'
    )
    perfil.verificado_por = admin
    perfil.save()
    assert list(admin.empresas_verificadas.all()) == [perfil]
    admin.delete()
    perfil.refresh_from_db()
    assert perfil.verificado_por is None


@pytest.mark.parametrize('estado,esperado', [
    ('sin_verificar', False), ('en_revision', False), ('verificada', True), ('rechazada', False),
])
def test_es_verificada(estado, esperado):
    assert PerfilEmpresa(estado_verificacion=estado).es_verificada is esperado


def test_documento_completo_con_dv():
    p = PerfilEmpresa(numero_documento='900123456', digito_verificacion='7')
    assert p.documento_completo == '900123456-7'


def test_documento_completo_sin_dv():
    assert PerfilEmpresa(numero_documento='1020304050').documento_completo == '1020304050'
    assert PerfilEmpresa(numero_documento='1020304050', digito_verificacion='').documento_completo == '1020304050'


def test_documento_completo_sin_numero():
    assert PerfilEmpresa().documento_completo == ''


@pytest.mark.parametrize('estado,tipo,label,css', [
    ('verificada', 'juridica', 'Empresa Verificada', 'badge-verificada'),
    ('verificada', 'natural', 'Negocio Verificado', 'badge-verificada'),
    ('en_revision', 'juridica', 'En Revisión', 'badge-en-revision'),
    ('rechazada', 'natural', 'Verificación Rechazada', 'badge-rechazada'),
    ('sin_verificar', 'juridica', 'Sin Verificar', 'badge-sin-verificar'),
])
def test_badge_info(estado, tipo, label, css):
    info = PerfilEmpresa(estado_verificacion=estado, tipo_persona=tipo).badge_info
    assert info == {'label': label, 'css_class': css}
