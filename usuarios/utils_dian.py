"""Utilidades DIAN: cálculo y validación del Dígito de Verificación (DV).

Implementa el algoritmo oficial Módulo 11 de la DIAN para NIT y cédulas
en Colombia.

Marco normativo y fuentes técnicas:
- Estatuto Tributario Nacional, Arts. 555-1 y 555-2.
- Decreto 2460 de 2013 (art. 19), compilado en el Decreto Único
  Reglamentario 1625 de 2016 (art. 1.6.1.2.21).
  https://normograma.dian.gov.co/dian/compilacion/docs/decreto_2460_2013.htm
- Concepto Tributario DIAN 35986 de 1997 (Naturaleza del DV).
  https://normograma.dian.gov.co/dian/compilacion/docs/concepto_tributario_dian_0035986_1997.htm
- Especificación algorítmica: factores primos ponderados Módulo 11:
  https://www.consultorcontable.com/digito-de-verificacion-de-nit/
  https://www.gerencie.com/digito-de-verificacion-del-nit.html
"""

# Factores oficiales DIAN; se aplican de derecha a izquierda sobre el número.
PRIME_FACTORS = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]

_SEPARADORES = " \t\r\n.,-"


def limpiar_documento(documento: str) -> str:
    """Elimina espacios, puntos, comas y guiones de un documento."""
    return "".join(c for c in str(documento) if c not in _SEPARADORES)


def _solo_digitos(documento: str | int) -> str:
    limpio = limpiar_documento(str(documento))
    if not limpio:
        raise ValueError("El documento no puede estar vacío.")
    if not (limpio.isascii() and limpio.isdigit()):
        raise ValueError("El documento solo puede contener dígitos.")
    return limpio


def calcular_dv_dian(numero_documento: str | int) -> int:
    """Calcula el dígito de verificación DIAN (Módulo 11) de un NIT/cédula."""
    digitos = _solo_digitos(numero_documento)
    if len(digitos) > len(PRIME_FACTORS):
        raise ValueError(f"El documento no puede tener más de {len(PRIME_FACTORS)} dígitos.")
    total = sum(int(d) * f for d, f in zip(reversed(digitos), reversed(PRIME_FACTORS)))
    resto = total % 11
    return resto if resto < 2 else 11 - resto


def validar_nit_con_dv(nit_con_dv: str) -> bool:
    """Valida un NIT con DV (p. ej. ``899.999.034-1``).

    El último dígito es el DV. Lanza ``ValueError`` si hay caracteres no
    numéricos (distintos de separadores), está vacío o le falta base o DV.
    """
    digitos = _solo_digitos(nit_con_dv)
    if len(digitos) < 2:
        raise ValueError("El NIT debe incluir número base y dígito de verificación.")
    base, dv = digitos[:-1], int(digitos[-1])
    return calcular_dv_dian(base) == dv


def formatear_nit(numero: str | int, dv: int | str | None = None) -> str:
    """Formatea un NIT como ``900.123.456-7``; calcula el DV si no se da."""
    digitos = _solo_digitos(numero)
    if dv is None:
        dv = calcular_dv_dian(digitos)
    return f"{int(digitos):,}".replace(",", ".") + f"-{dv}"
