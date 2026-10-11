import pytest

from usuarios.utils_dian import (
    PRIME_FACTORS,
    calcular_dv_dian,
    formatear_nit,
    limpiar_documento,
    validar_nit_con_dv,
)

# (numero, dv) — NITs oficiales conocidos y cédulas (7, 8 y 10 dígitos).
CASOS_DV = [
    ("899999034", 1),  # SENA
    ("899999068", 1),  # Ecopetrol
    ("890903938", 8),  # Bancolombia
    ("860001024", 1),  # Módulo 11 DIAN (suma 593 % 11 = 10 -> 1)
    ("900123456", 8),
    ("1234567", 2),  # cédula 7 dígitos
    ("12345678", 8),  # cédula 8 dígitos
    ("1020304050", 8),  # cédula 10 dígitos
]


def test_prime_factors_oficiales():
    assert PRIME_FACTORS == [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]


@pytest.mark.parametrize("numero,dv", CASOS_DV)
def test_calcular_dv_conocidos(numero, dv):
    assert calcular_dv_dian(numero) == dv


def test_calcular_dv_acepta_int_y_formato():
    assert calcular_dv_dian(899999034) == 1
    assert calcular_dv_dian("899.999.034") == 1
    assert calcular_dv_dian(" 899 999 034 ") == 1


@pytest.mark.parametrize(
    "numero,dv",
    [
        ("15", 0),  # resto 0 -> 0
        ("4", 1),  # resto 1 -> 1
        ("1", 8),  # resto 3 -> 11 - 3
    ],
)
def test_calcular_dv_ramas_del_resto(numero, dv):
    assert calcular_dv_dian(numero) == dv


@pytest.mark.parametrize("valor", ["", "   ", "abc", "12a45", "-", "..."])
def test_calcular_dv_invalido(valor):
    with pytest.raises(ValueError):
        calcular_dv_dian(valor)


def test_calcular_dv_demasiado_largo():
    with pytest.raises(ValueError):
        calcular_dv_dian("1" * 16)


@pytest.mark.parametrize(
    "crudo,esperado",
    [
        ("899.999.034-1", "8999990341"),
        ("899 999 034", "899999034"),
        (" 899,999,034 - 1 ", "8999990341"),
        ("899999034", "899999034"),
        ("", ""),
    ],
)
def test_limpiar_documento(crudo, esperado):
    assert limpiar_documento(crudo) == esperado


def test_limpiar_documento_conserva_caracteres_invalidos():
    assert limpiar_documento("12-ab") == "12ab"


@pytest.mark.parametrize(
    "numero,dv,esperado",
    [
        ("899999034", 1, "899.999.034-1"),
        (899999034, "1", "899.999.034-1"),
        ("900123456", 8, "900.123.456-8"),
        ("1234567", 2, "1.234.567-2"),
        ("899.999.034", 1, "899.999.034-1"),
        ("899999034", None, "899.999.034-1"),  # DV calculado
        ("899999034", 0, "899.999.034-0"),  # dv=0 explícito se respeta
    ],
)
def test_formatear_nit(numero, dv, esperado):
    assert formatear_nit(numero, dv) == esperado


def test_formatear_nit_sin_dv_argumento():
    assert formatear_nit("899999034") == "899.999.034-1"


@pytest.mark.parametrize("numero,dv", CASOS_DV)
def test_validar_nit_con_dv_correcto(numero, dv):
    assert validar_nit_con_dv(f"{numero}-{dv}") is True


@pytest.mark.parametrize(
    "nit",
    ["899.999.034-1", "899 999 034 1", "8999990341", "899999034-1"],
)
def test_validar_nit_con_dv_formatos(nit):
    assert validar_nit_con_dv(nit) is True


@pytest.mark.parametrize("nit", ["899999034-2", "899.999.034-0", "890903938-9"])
def test_validar_nit_con_dv_incorrecto(nit):
    assert validar_nit_con_dv(nit) is False


@pytest.mark.parametrize("nit", ["", "   ", "abc-1", "899999034-x", "89a999034-1", "-", "1"])
def test_validar_nit_con_dv_invalido_lanza(nit):
    with pytest.raises(ValueError):
        validar_nit_con_dv(nit)
