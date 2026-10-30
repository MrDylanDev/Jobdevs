"""
Motor local de verificación documental asistida — JobDevs.

Implementa extracción de texto (PyMuPDF), OCR (Tesseract), preprocesamiento de
imágenes (OpenCV/Pillow), validación cruzada y score de confianza determinístico.

100 % local — sin APIs externas de IA.
"""
from __future__ import annotations

import io
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Umbrales y constantes configurables
# ---------------------------------------------------------------------------
UMBRAL_BORROSIDAD = 100.0           # varianza Laplaciana mínima para imagen nítida
UMBRAL_TEXTO_MINIMO = 50            # caracteres para considerar extracción PDF útil
UMBRAL_SIMILITUD_RAZON_SOCIAL = 0.85
UMBRAL_SIMILITUD_NOMBRE = 0.85
UMBRAL_SIMILITUD_PROGRAMA = 0.75
MAX_PAGINAS_OCR = 10                # límite de páginas a procesar con OCR
VIGENCIA_DOCUMENTO_DIAS = 365       # días de validez por defecto

# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------

@dataclass
class ResultadoExtraccion:
    """Resultado bruto de la extracción de texto de un documento."""
    texto: str = ""
    metodo: str = "ninguno"          # "pdf_nativo", "ocr", "mixto"
    calidad_imagen: str = "desconocida"  # "nitida", "borrosa", "ilegible"
    paginas: int = 0
    advertencias: list[str] = field(default_factory=list)


@dataclass
class DatosEmpresaExtraidos:
    nit: str | None = None
    digito_verificacion: str | None = None
    razon_social: str | None = None
    fecha_expedicion: str | None = None
    matricula_mercantil: str | None = None
    representante_legal: str | None = None
    campos_no_encontrados: list[str] = field(default_factory=list)


@dataclass
class DatosDesarrolladorExtraidos:
    nombre: str | None = None
    numero_ficha: str | None = None
    programa_formacion: str | None = None
    centro_formacion: str | None = None
    estado_formacion: str | None = None
    fechas: list[str] = field(default_factory=list)
    campos_no_encontrados: list[str] = field(default_factory=list)


@dataclass
class Alerta:
    nivel: str   # "critica", "advertencia", "calidad"
    codigo: str
    mensaje: str


@dataclass
class ResultadoTriaje:
    score_confianza: int = 0
    estado_triaje: str = "indeterminado"
    calidad_imagen: str = "desconocida"
    metodo_extraccion: str = "ninguno"
    datos_extraidos: dict[str, Any] = field(default_factory=dict)
    comparacion: dict[str, Any] = field(default_factory=dict)
    alertas: list[dict] = field(default_factory=list)
    coincidencias: list[str] = field(default_factory=list)
    discrepancias: list[str] = field(default_factory=list)
    campos_no_encontrados: list[str] = field(default_factory=list)
    motor: str = "local"
    fecha_analisis: str = field(
        default_factory=lambda: timezone.now().isoformat()
    )
    justificacion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_confianza": self.score_confianza,
            "estado_triaje": self.estado_triaje,
            "calidad_imagen": self.calidad_imagen,
            "metodo_extraccion": self.metodo_extraccion,
            "datos_extraidos": self.datos_extraidos,
            "comparacion": self.comparacion,
            "alertas": self.alertas,
            "coincidencias": self.coincidencias,
            "discrepancias": self.discrepancias,
            "campos_no_encontrados": self.campos_no_encontrados,
            "motor": self.motor,
            "fecha_analisis": self.fecha_analisis,
            "justificacion": self.justificacion,
        }


# ---------------------------------------------------------------------------
# Helpers de importación dinámica (no fallan si la librería no está)
# ---------------------------------------------------------------------------

def _importar_fitz():
    try:
        import fitz  # PyMuPDF
        return fitz
    except ImportError:
        return None


def _importar_cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        return None


def _importar_pytesseract():
    try:
        import pytesseract
        return pytesseract
    except ImportError:
        return None


def _importar_pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Módulo 1: Preprocesamiento de imágenes
# ---------------------------------------------------------------------------

def detectar_borrosidad(datos_imagen: bytes) -> tuple[bool, float]:
    """
    Detecta si una imagen es borrosa usando la varianza del Laplaciano.

    Returns:
        (es_borrosa, varianza)
    """
    cv2 = _importar_cv2()
    Image = _importar_pil()

    if cv2 is None or Image is None:
        logger.warning("OpenCV o Pillow no disponibles; no se puede detectar borrosidad.")
        return False, -1.0

    try:
        imagen = Image.open(io.BytesIO(datos_imagen)).convert("L")
        import numpy as np
        arr = np.array(imagen)
        varianza = float(cv2.Laplacian(arr, cv2.CV_64F).var())
        es_borrosa = varianza < UMBRAL_BORROSIDAD
        return es_borrosa, varianza
    except Exception as exc:
        logger.warning("Error detectando borrosidad: %s", exc)
        return False, -1.0


def preprocesar_imagen_para_ocr(datos_imagen: bytes) -> bytes:
    """
    Aplica pipeline de preprocesamiento a una imagen para mejorar el OCR:
    escala de grises → binarización Otsu → corrección de inclinación.

    Returns bytes de imagen PNG procesada.
    """
    cv2 = _importar_cv2()
    Image = _importar_pil()

    if cv2 is None or Image is None:
        return datos_imagen

    try:
        import numpy as np
        imagen = Image.open(io.BytesIO(datos_imagen)).convert("RGB")
        arr = np.array(imagen)

        # 1. Escala de grises
        gris = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # 2. Binarización Otsu
        _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 3. Corrección de inclinación (deskew)
        coords = np.column_stack(np.where(binaria > 0))
        if len(coords) >= 5:
            angulo = cv2.minAreaRect(coords)[-1]
            if angulo < -45:
                angulo = -(90 + angulo)
            else:
                angulo = -angulo
            if abs(angulo) > 0.5:
                h, w = binaria.shape
                centro = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(centro, angulo, 1.0)
                binaria = cv2.warpAffine(
                    binaria, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )

        # Convertir de vuelta a bytes
        resultado = Image.fromarray(binaria)
        buf = io.BytesIO()
        resultado.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Error en preprocesamiento de imagen: %s", exc)
        return datos_imagen


# ---------------------------------------------------------------------------
# Módulo 2: Extracción de texto
# ---------------------------------------------------------------------------

def extraer_texto_pdf_nativo(ruta_archivo: str) -> ResultadoExtraccion:
    """Extrae texto de un PDF usando PyMuPDF sin OCR."""
    fitz = _importar_fitz()
    resultado = ResultadoExtraccion()

    if fitz is None:
        resultado.advertencias.append("PyMuPDF no disponible.")
        return resultado

    try:
        doc = fitz.open(ruta_archivo)
        resultado.paginas = len(doc)
        partes = []

        for idx, pagina in enumerate(doc):
            if idx >= MAX_PAGINAS_OCR:
                break
            partes.append(pagina.get_text("text"))

        doc.close()
        resultado.texto = "\n".join(partes).strip()
        resultado.metodo = "pdf_nativo"

        if len(resultado.texto) < UMBRAL_TEXTO_MINIMO:
            resultado.advertencias.append(
                f"Texto nativo insuficiente ({len(resultado.texto)} caracteres). "
                "Se intentará OCR."
            )

    except Exception as exc:
        logger.warning("Error extrayendo texto nativo de PDF: %s", exc)
        resultado.advertencias.append(f"Error en extracción nativa: {exc}")

    return resultado


def _ocr_imagen_bytes(datos: bytes, lang: str = "spa") -> str:
    """Aplica Tesseract OCR a bytes de imagen. Retorna texto extraído."""
    pytesseract = _importar_pytesseract()
    Image = _importar_pil()

    if pytesseract is None or Image is None:
        return ""

    try:
        datos_procesados = preprocesar_imagen_para_ocr(datos)
        imagen = Image.open(io.BytesIO(datos_procesados))
        config = r"--oem 3 --psm 6"
        return pytesseract.image_to_string(imagen, lang=lang, config=config)
    except Exception as exc:
        logger.warning("Error en OCR: %s", exc)
        return ""


def extraer_texto_con_ocr(ruta_archivo: str) -> ResultadoExtraccion:
    """
    Aplica OCR completo a un PDF o imagen.
    Para PDFs convierte cada página a imagen antes de procesar.
    """
    fitz = _importar_fitz()
    Image = _importar_pil()
    resultado = ResultadoExtraccion(metodo="ocr")

    if fitz is None:
        # Intentar OCR directo si es imagen
        if Image is not None:
            try:
                with open(ruta_archivo, "rb") as f:
                    datos = f.read()
                es_borrosa, varianza = detectar_borrosidad(datos)
                resultado.calidad_imagen = "borrosa" if es_borrosa else "nitida"
                if es_borrosa:
                    resultado.advertencias.append(
                        f"Imagen borrosa (varianza Laplaciana={varianza:.1f}). "
                        "Los datos OCR pueden ser poco confiables."
                    )
                resultado.texto = _ocr_imagen_bytes(datos)
                resultado.paginas = 1
            except Exception as exc:
                resultado.advertencias.append(f"Error en OCR directo: {exc}")
        return resultado

    try:
        doc = fitz.open(ruta_archivo)
        resultado.paginas = len(doc)
        partes = []
        calidades = []

        for idx, pagina in enumerate(doc):
            if idx >= MAX_PAGINAS_OCR:
                break
            # Renderizar página como imagen (150 DPI suficiente para OCR)
            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = pagina.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            datos_img = pix.tobytes("png")

            es_borrosa, varianza = detectar_borrosidad(datos_img)
            calidades.append(es_borrosa)

            if es_borrosa:
                resultado.advertencias.append(
                    f"Página {idx + 1}: imagen borrosa (Laplaciana={varianza:.1f})."
                )

            texto_pagina = _ocr_imagen_bytes(datos_img)
            partes.append(texto_pagina)

        doc.close()
        resultado.texto = "\n".join(partes).strip()

        if all(calidades):
            resultado.calidad_imagen = "borrosa"
        elif any(calidades):
            resultado.calidad_imagen = "parcialmente_borrosa"
        else:
            resultado.calidad_imagen = "nitida"

    except Exception as exc:
        logger.error("Error en extracción OCR de PDF: %s", exc)
        resultado.advertencias.append(f"Error en OCR: {exc}")

    return resultado


def extraer_texto_documento(ruta_archivo: str) -> ResultadoExtraccion:
    """
    Punto de entrada principal para extracción de texto.

    1. Intenta extracción nativa (PyMuPDF).
    2. Si el texto es insuficiente, aplica OCR.
    3. Combina resultados si es necesario.
    """
    sufijo = Path(ruta_archivo).suffix.lower()
    es_imagen = sufijo in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

    if es_imagen:
        # Imagen directa: siempre OCR
        with open(ruta_archivo, "rb") as f:
            datos = f.read()
        es_borrosa, varianza = detectar_borrosidad(datos)
        resultado = ResultadoExtraccion(metodo="ocr")
        resultado.calidad_imagen = "borrosa" if es_borrosa else "nitida"
        resultado.paginas = 1
        if es_borrosa:
            resultado.advertencias.append(
                f"Imagen borrosa (Laplaciana={varianza:.1f}). OCR poco confiable."
            )
        resultado.texto = _ocr_imagen_bytes(datos)
        return resultado

    # PDF: primero nativo, luego OCR si es necesario
    nativo = extraer_texto_pdf_nativo(ruta_archivo)

    if len(nativo.texto) >= UMBRAL_TEXTO_MINIMO:
        nativo.calidad_imagen = "nitida"
        return nativo

    # Texto insuficiente → OCR
    ocr = extraer_texto_con_ocr(ruta_archivo)
    ocr.advertencias = nativo.advertencias + ocr.advertencias

    if len(nativo.texto) > 0 and len(ocr.texto) > len(nativo.texto):
        ocr.metodo = "mixto"
        ocr.texto = nativo.texto + "\n" + ocr.texto

    return ocr


# ---------------------------------------------------------------------------
# Módulo 3: Extracción estructurada
# ---------------------------------------------------------------------------

def _normalizar_texto(texto: str) -> str:
    """Elimina tildes, convierte a minúsculas y normaliza espacios."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.lower()).strip()


def _similitud(a: str, b: str) -> float:
    """Similitud de cadenas usando SequenceMatcher (0.0 - 1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalizar_texto(a), _normalizar_texto(b)).ratio()


# --- Patrones regex para empresas ---
_RE_NIT = re.compile(
    r"(?:nit|n\.i\.t\.?|nitde|nit\s+de\s+la\s+empresa)[:\s#]*"
    r"(\d[\d\.\s]{5,14}\d)"
    r"(?:\s*[-–]\s*(\d))?",
    re.IGNORECASE,
)
_RE_NIT_GENERICO = re.compile(
    r"\b(\d{7,10})\s*[-–]\s*(\d)\b"
)
_RE_MATRICULA = re.compile(
    r"(?:matr[ií]cula\s+mercantil|n[úu]mero\s+de\s+matr[ií]cula)[:\s]*(\d[\d\.\-\s]{3,15})",
    re.IGNORECASE,
)
_RE_RAZON_SOCIAL = re.compile(
    r"(?:raz[oó]n\s+social|denominaci[oó]n\s+social|nombre\s+de\s+la\s+empresa)[:\s]+([A-ZÁÉÍÓÚÑ][^\n\r]{3,80})",
    re.IGNORECASE,
)
_RE_REPRESENTANTE = re.compile(
    r"(?:representante\s+legal|firmado\s+por|representado\s+por)[:\s]+([A-ZÁÉÍÓÚÑa-záéíóúñ][^\n\r]{5,60})",
    re.IGNORECASE,
)
_RE_FECHA = re.compile(
    r"\b(\d{1,2})[\/\-\s](\d{1,2})[\/\-\s](\d{2,4})\b"
    r"|\b(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})\b",
    re.IGNORECASE,
)

_MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# --- Patrones regex para desarrolladores SENA ---
_RE_FICHA = re.compile(
    r"(?:ficha|n[uú]mero\s+de\s+ficha|ficha\s+de\s+caracterizaci[oó]n)[:\s]*(\d{5,8})",
    re.IGNORECASE,
)
_RE_FICHA_GENERICA = re.compile(r"\b(\d{7})\b")
_RE_PROGRAMA = re.compile(
    r"(?:programa\s+de\s+formaci[oó]n|programa)[:\s]+([A-ZÁÉÍÓÚÑa-záéíóúñ][^\n\r]{5,120})",
    re.IGNORECASE,
)
_RE_CENTRO = re.compile(
    r"(?:centro\s+de\s+formaci[oó]n|centro)[:\s]+([A-ZÁÉÍÓÚÑa-záéíóúñ][^\n\r]{5,100})",
    re.IGNORECASE,
)
_RE_ESTADO_FORMACION = re.compile(
    r"(?:estado|estado\s+de\s+formaci[oó]n)[:\s]+(en\s+formaci[oó]n|electiva|pr[aá]ctica|graduado|egresado|por\s+certificar)",
    re.IGNORECASE,
)


def _limpiar_numero(texto: str) -> str:
    """Extrae solo dígitos de una cadena."""
    return re.sub(r"\D", "", texto)


def _parsear_fecha(match: re.Match) -> str | None:
    """Convierte un match de fecha a string ISO."""
    try:
        if match.group(4):  # formato "dd de mes de YYYY"
            dia = int(match.group(4))
            mes = _MESES_ES.get(match.group(5).lower(), 0)
            anio = int(match.group(6))
        else:
            dia = int(match.group(1))
            mes = int(match.group(2))
            anio = int(match.group(3))
            if anio < 100:
                anio += 2000

        if 1 <= mes <= 12 and 1 <= dia <= 31 and 1900 <= anio <= 2100:
            return date(anio, mes, dia).isoformat()
    except Exception:
        pass
    return None


def extraer_datos_empresa(texto: str) -> DatosEmpresaExtraidos:
    """Extrae campos estructurados de empresa desde texto de documento."""
    datos = DatosEmpresaExtraidos()
    campos_esperados = ["nit", "razon_social", "fecha_expedicion",
                        "matricula_mercantil", "representante_legal"]

    # NIT con contexto
    m = _RE_NIT.search(texto)
    if m:
        datos.nit = _limpiar_numero(m.group(1))
        datos.digito_verificacion = m.group(2) if m.group(2) else None
    else:
        m = _RE_NIT_GENERICO.search(texto)
        if m:
            datos.nit = _limpiar_numero(m.group(1))
            datos.digito_verificacion = m.group(2)

    # Razón social
    m = _RE_RAZON_SOCIAL.search(texto)
    if m:
        datos.razon_social = m.group(1).strip()

    # Matrícula mercantil
    m = _RE_MATRICULA.search(texto)
    if m:
        datos.matricula_mercantil = _limpiar_numero(m.group(1))

    # Representante legal
    m = _RE_REPRESENTANTE.search(texto)
    if m:
        datos.representante_legal = m.group(1).strip()

    # Fecha (primera encontrada)
    for m in _RE_FECHA.finditer(texto):
        fecha = _parsear_fecha(m)
        if fecha:
            datos.fecha_expedicion = fecha
            break

    # Campos no encontrados
    if not datos.nit:
        datos.campos_no_encontrados.append("nit")
    if not datos.razon_social:
        datos.campos_no_encontrados.append("razon_social")
    if not datos.fecha_expedicion:
        datos.campos_no_encontrados.append("fecha_expedicion")
    if not datos.matricula_mercantil:
        datos.campos_no_encontrados.append("matricula_mercantil")
    if not datos.representante_legal:
        datos.campos_no_encontrados.append("representante_legal")

    return datos


def extraer_datos_desarrollador(texto: str) -> DatosDesarrolladorExtraidos:
    """Extrae campos estructurados de aprendiz/egresado SENA desde texto."""
    datos = DatosDesarrolladorExtraidos()

    # Número de ficha
    m = _RE_FICHA.search(texto)
    if m:
        datos.numero_ficha = m.group(1).strip()
    else:
        m = _RE_FICHA_GENERICA.search(texto)
        if m:
            datos.numero_ficha = m.group(1)

    # Programa de formación
    m = _RE_PROGRAMA.search(texto)
    if m:
        datos.programa_formacion = m.group(1).strip().rstrip(",;.")

    # Centro de formación
    m = _RE_CENTRO.search(texto)
    if m:
        datos.centro_formacion = m.group(1).strip().rstrip(",;.")

    # Estado de formación
    m = _RE_ESTADO_FORMACION.search(texto)
    if m:
        datos.estado_formacion = m.group(1).strip()

    # Nombre del aprendiz (primera línea con nombre propio)
    lineas = texto.split("\n")
    for linea in lineas[:20]:
        linea = linea.strip()
        if 8 < len(linea) < 60 and re.match(r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]", linea):
            if not re.search(r"sena|servicio|nacional|formaci", linea, re.I):
                datos.nombre = linea
                break

    # Fechas
    datos.fechas = []
    for m in _RE_FECHA.finditer(texto):
        fecha = _parsear_fecha(m)
        if fecha and fecha not in datos.fechas:
            datos.fechas.append(fecha)

    # Campos no encontrados
    if not datos.numero_ficha:
        datos.campos_no_encontrados.append("numero_ficha")
    if not datos.programa_formacion:
        datos.campos_no_encontrados.append("programa_formacion")
    if not datos.centro_formacion:
        datos.campos_no_encontrados.append("centro_formacion")
    if not datos.nombre:
        datos.campos_no_encontrados.append("nombre")

    return datos


# ---------------------------------------------------------------------------
# Módulo 4: Validación cruzada y score
# ---------------------------------------------------------------------------

def _validar_dv_nit(nit: str, dv: str | None) -> bool:
    """Valida el dígito de verificación usando el módulo DIAN existente."""
    try:
        from .utils_dian import calcular_dv_dian
        dv_calculado = calcular_dv_dian(nit)
        if dv is not None:
            return str(dv_calculado) == str(dv)
    except Exception:
        pass
    return True  # Si no hay DV disponible no se puede invalidar


def _similitud_programa_sena(programa_extraido: str, programa_registrado: str) -> float:
    """
    Compara programas SENA usando el catálogo de equivalentes y similitud difusa.
    """
    from .services_sena import normalizar_programa_formacion, _grupo_programa

    norm_extraido = normalizar_programa_formacion(programa_extraido)
    norm_registrado = normalizar_programa_formacion(programa_registrado)

    if not norm_extraido or not norm_registrado:
        return 0.0

    # Mismo grupo de equivalentes
    grupo_ext = _grupo_programa(norm_extraido)
    grupo_reg = _grupo_programa(norm_registrado)
    if grupo_ext and grupo_ext == grupo_reg:
        return 1.0

    return SequenceMatcher(None, norm_extraido, norm_registrado).ratio()


def _verificar_vigencia_documento(fecha_iso: str | None, dias: int = VIGENCIA_DOCUMENTO_DIAS) -> bool:
    """Retorna True si el documento está dentro del período de vigencia."""
    if not fecha_iso:
        return True  # Sin fecha no se puede determinar vencimiento
    try:
        fecha = date.fromisoformat(fecha_iso)
        hoy = date.today()
        return (hoy - fecha).days <= dias
    except Exception:
        return True


def analizar_empresa(
    datos_perfil: dict[str, Any],
    texto_documento: str,
) -> ResultadoTriaje:
    """
    Validación cruzada completa para PerfilEmpresa.

    datos_perfil debe contener:
        numero_documento, digito_verificacion, razon_social
    """
    resultado = ResultadoTriaje()
    alertas: list[Alerta] = []

    # 1. Extraer datos del documento
    extraidos = extraer_datos_empresa(texto_documento)
    resultado.datos_extraidos = {
        "nit": extraidos.nit,
        "digito_verificacion": extraidos.digito_verificacion,
        "razon_social": extraidos.razon_social,
        "fecha_expedicion": extraidos.fecha_expedicion,
        "matricula_mercantil": extraidos.matricula_mercantil,
        "representante_legal": extraidos.representante_legal,
    }
    resultado.campos_no_encontrados = extraidos.campos_no_encontrados

    # 2. Datos registrados
    nit_registrado = str(datos_perfil.get("numero_documento") or "").strip()
    dv_registrado = str(datos_perfil.get("digito_verificacion") or "").strip()
    razon_registrada = str(datos_perfil.get("razon_social") or "").strip()

    puntos = 0
    puntos_posibles = 0
    discrepancia_critica = False

    # --- Validar NIT ---
    if nit_registrado:
        puntos_posibles += 50
        if extraidos.nit:
            nit_doc = re.sub(r"\D", "", extraidos.nit)
            nit_reg = re.sub(r"\D", "", nit_registrado)
            if nit_doc == nit_reg:
                puntos += 40
                resultado.coincidencias.append(
                    f"NIT coincide: {nit_reg}"
                )
                # Validar DV
                dv_doc = extraidos.digito_verificacion or dv_registrado
                if dv_doc and _validar_dv_nit(nit_reg, dv_doc):
                    puntos += 10
                    resultado.coincidencias.append("Dígito de verificación válido")
                else:
                    alertas.append(Alerta(
                        "advertencia", "DV_INVALIDO",
                        f"El dígito de verificación del NIT no coincide o es inválido."
                    ))
            else:
                discrepancia_critica = True
                alertas.append(Alerta(
                    "critica", "NIT_NO_COINCIDE",
                    f"El NIT del documento ({nit_doc}) no coincide con el registrado ({nit_reg})."
                ))
                resultado.discrepancias.append(
                    f"NIT: registrado={nit_reg}, documento={nit_doc}"
                )
        else:
            alertas.append(Alerta(
                "advertencia", "NIT_NO_ENCONTRADO",
                "No se encontró el NIT en el documento."
            ))

    resultado.comparacion["nit"] = {
        "registrado": nit_registrado,
        "extraido": extraidos.nit,
    }

    # --- Validar razón social ---
    if razon_registrada:
        puntos_posibles += 30
        if extraidos.razon_social:
            sim = _similitud(razon_registrada, extraidos.razon_social)
            resultado.comparacion["razon_social"] = {
                "registrado": razon_registrada,
                "extraido": extraidos.razon_social,
                "similitud": round(sim, 3),
            }
            if sim >= UMBRAL_SIMILITUD_RAZON_SOCIAL:
                puntos += 30
                resultado.coincidencias.append(
                    f"Razón social coincide ({sim:.0%}): {extraidos.razon_social}"
                )
            else:
                alertas.append(Alerta(
                    "advertencia", "RAZON_SOCIAL_DIFERENTE",
                    f"La razón social presenta diferencias ({sim:.0%} similitud)."
                ))
                resultado.discrepancias.append(
                    f"Razón social: registrada='{razon_registrada}', documento='{extraidos.razon_social}'"
                )
                if sim >= 0.6:
                    puntos += 15
        else:
            alertas.append(Alerta(
                "advertencia", "RAZON_SOCIAL_NO_ENCONTRADA",
                "No se encontró la razón social en el documento."
            ))

    # --- Vigencia del documento ---
    if extraidos.fecha_expedicion:
        puntos_posibles += 10
        if _verificar_vigencia_documento(extraidos.fecha_expedicion):
            puntos += 10
            resultado.coincidencias.append(
                f"Documento dentro del período de vigencia (expedición: {extraidos.fecha_expedicion})"
            )
        else:
            alertas.append(Alerta(
                "advertencia", "DOCUMENTO_VENCIDO",
                f"El documento podría estar fuera del período de vigencia "
                f"(expedición: {extraidos.fecha_expedicion})."
            ))

    # --- Calcular score ---
    resultado = _calcular_score_final(
        resultado, alertas, puntos, puntos_posibles, discrepancia_critica
    )
    return resultado


def analizar_desarrollador(
    datos_perfil: dict[str, Any],
    texto_documento: str,
) -> ResultadoTriaje:
    """
    Validación cruzada completa para PerfilDesarrollador.

    datos_perfil debe contener:
        nombre_usuario, ficha, programa_formacion
    """
    resultado = ResultadoTriaje()
    alertas: list[Alerta] = []

    extraidos = extraer_datos_desarrollador(texto_documento)
    resultado.datos_extraidos = {
        "nombre": extraidos.nombre,
        "numero_ficha": extraidos.numero_ficha,
        "programa_formacion": extraidos.programa_formacion,
        "centro_formacion": extraidos.centro_formacion,
        "estado_formacion": extraidos.estado_formacion,
        "fechas": extraidos.fechas,
    }
    resultado.campos_no_encontrados = extraidos.campos_no_encontrados

    ficha_registrada = str(datos_perfil.get("ficha") or "").strip()
    programa_registrado = str(datos_perfil.get("programa_formacion") or "").strip()
    nombre_registrado = str(datos_perfil.get("nombre_usuario") or "").strip()

    puntos = 0
    puntos_posibles = 0
    discrepancia_critica = False

    # --- Validar número de ficha ---
    if ficha_registrada:
        puntos_posibles += 50
        if extraidos.numero_ficha:
            ficha_doc = re.sub(r"\D", "", extraidos.numero_ficha)
            ficha_reg = re.sub(r"\D", "", ficha_registrada)
            resultado.comparacion["ficha"] = {
                "registrada": ficha_reg,
                "extraida": ficha_doc,
            }
            if ficha_doc == ficha_reg:
                puntos += 50
                resultado.coincidencias.append(f"Número de ficha coincide: {ficha_reg}")
            else:
                discrepancia_critica = True
                alertas.append(Alerta(
                    "critica", "FICHA_NO_COINCIDE",
                    f"El número de ficha del documento ({ficha_doc}) no coincide "
                    f"con el registrado ({ficha_reg})."
                ))
                resultado.discrepancias.append(
                    f"Ficha: registrada={ficha_reg}, documento={ficha_doc}"
                )
        else:
            alertas.append(Alerta(
                "advertencia", "FICHA_NO_ENCONTRADA",
                "No se encontró el número de ficha en el documento."
            ))

    # --- Validar nombre ---
    if nombre_registrado and extraidos.nombre:
        puntos_posibles += 25
        sim = _similitud(nombre_registrado, extraidos.nombre)
        resultado.comparacion["nombre"] = {
            "registrado": nombre_registrado,
            "extraido": extraidos.nombre,
            "similitud": round(sim, 3),
        }
        if sim >= UMBRAL_SIMILITUD_NOMBRE:
            puntos += 25
            resultado.coincidencias.append(
                f"Nombre coincide ({sim:.0%}): {extraidos.nombre}"
            )
        else:
            alertas.append(Alerta(
                "advertencia", "NOMBRE_DIFERENTE",
                f"El nombre presenta diferencias ({sim:.0%} similitud)."
            ))
            resultado.discrepancias.append(
                f"Nombre: registrado='{nombre_registrado}', documento='{extraidos.nombre}'"
            )
            if sim >= 0.6:
                puntos += 12

    # --- Validar programa de formación ---
    if programa_registrado and extraidos.programa_formacion:
        puntos_posibles += 20
        sim_prog = _similitud_programa_sena(
            extraidos.programa_formacion, programa_registrado
        )
        resultado.comparacion["programa_formacion"] = {
            "registrado": programa_registrado,
            "extraido": extraidos.programa_formacion,
            "similitud": round(sim_prog, 3),
        }
        if sim_prog >= UMBRAL_SIMILITUD_PROGRAMA:
            puntos += 20
            resultado.coincidencias.append(
                f"Programa de formación coincide ({sim_prog:.0%})"
            )
        else:
            alertas.append(Alerta(
                "advertencia", "PROGRAMA_DIFERENTE",
                f"El programa de formación presenta diferencias ({sim_prog:.0%} similitud)."
            ))
            resultado.discrepancias.append(
                f"Programa: registrado='{programa_registrado}', "
                f"documento='{extraidos.programa_formacion}'"
            )

    # --- Vigencia ---
    if extraidos.fechas:
        puntos_posibles += 5
        fecha_mas_reciente = max(extraidos.fechas)
        if _verificar_vigencia_documento(fecha_mas_reciente):
            puntos += 5
            resultado.coincidencias.append(
                f"Documento dentro del período de vigencia ({fecha_mas_reciente})"
            )
        else:
            alertas.append(Alerta(
                "advertencia", "DOCUMENTO_VENCIDO",
                f"El documento podría estar fuera de vigencia (fecha: {fecha_mas_reciente})."
            ))

    resultado = _calcular_score_final(
        resultado, alertas, puntos, puntos_posibles, discrepancia_critica
    )
    return resultado


def _calcular_score_final(
    resultado: ResultadoTriaje,
    alertas: list[Alerta],
    puntos: int,
    puntos_posibles: int,
    discrepancia_critica: bool,
) -> ResultadoTriaje:
    """Calcula el score final y determina el estado de triaje."""
    # Convertir alertas a dicts
    resultado.alertas = [
        {"nivel": a.nivel, "codigo": a.codigo, "mensaje": a.mensaje}
        for a in alertas
    ]

    # Penalizar por campos no encontrados
    penalizacion_campos = min(len(resultado.campos_no_encontrados) * 5, 20)

    if puntos_posibles > 0:
        score_base = int((puntos / puntos_posibles) * 100)
    else:
        # Sin datos registrados para comparar: score neutro pero informativo
        score_base = 50

    score = max(0, score_base - penalizacion_campos)

    # Una discrepancia crítica limita el score a menos de 40
    if discrepancia_critica:
        score = min(score, 39)

    # Imagen ilegible: no puede recibir score alto
    if resultado.calidad_imagen in ("borrosa", "ilegible"):
        score = min(score, 55)

    resultado.score_confianza = score

    # Estado de triaje
    if score >= 90:
        resultado.estado_triaje = "recomendado_aprobar"
    elif score >= 70:
        resultado.estado_triaje = "revision_recomendada"
    elif score >= 40:
        resultado.estado_triaje = "revision_detallada"
    else:
        resultado.estado_triaje = "discrepancias_criticas"

    # Justificación
    partes_just = []
    if resultado.coincidencias:
        partes_just.append(f"Coincidencias: {', '.join(resultado.coincidencias[:3])}.")
    if resultado.discrepancias:
        partes_just.append(f"Discrepancias: {', '.join(resultado.discrepancias[:3])}.")
    if resultado.campos_no_encontrados:
        partes_just.append(
            f"Campos no encontrados: {', '.join(resultado.campos_no_encontrados)}."
        )
    if discrepancia_critica:
        partes_just.append(
            "Discrepancia crítica detectada en identificador principal: "
            "score limitado a < 40."
        )
    resultado.justificacion = " ".join(partes_just) or "Análisis sin datos suficientes."

    return resultado


# ---------------------------------------------------------------------------
# Punto de entrada principal del motor
# ---------------------------------------------------------------------------

def analizar_documento_soporte(
    ruta_archivo: str,
    tipo_perfil: str,
    datos_perfil: dict[str, Any],
) -> ResultadoTriaje:
    """
    Función principal del motor documental.

    Args:
        ruta_archivo: Ruta absoluta al archivo en el servidor.
        tipo_perfil: "empresa" o "desarrollador".
        datos_perfil: Datos del perfil registrado en JobDevs.

    Returns:
        ResultadoTriaje con score, alertas, comparación y dictamen.
    """
    try:
        extraccion = extraer_texto_documento(ruta_archivo)
    except Exception as exc:
        logger.error("Error crítico en extracción de documento: %s", exc)
        return ResultadoTriaje(
            score_confianza=0,
            estado_triaje="error_procesamiento",
            calidad_imagen="ilegible",
            alertas=[{
                "nivel": "critica",
                "codigo": "ERROR_EXTRACCION",
                "mensaje": f"Error al procesar el documento: {exc}",
            }],
            justificacion=f"Error irrecuperable durante el análisis: {exc}",
        )

    # Alertas de calidad del documento
    alertas_previas: list[dict] = []
    for advertencia in extraccion.advertencias:
        alertas_previas.append({
            "nivel": "calidad",
            "codigo": "CALIDAD_DOCUMENTO",
            "mensaje": advertencia,
        })

    if len(extraccion.texto) < UMBRAL_TEXTO_MINIMO:
        return ResultadoTriaje(
            score_confianza=0,
            estado_triaje="documento_ilegible",
            calidad_imagen="ilegible",
            metodo_extraccion=extraccion.metodo,
            alertas=alertas_previas + [{
                "nivel": "critica",
                "codigo": "TEXTO_INSUFICIENTE",
                "mensaje": "No se pudo extraer texto suficiente del documento.",
            }],
            justificacion="El documento no contiene texto extraíble con los métodos disponibles.",
        )

    # Análisis según tipo de perfil
    if tipo_perfil == "empresa":
        resultado = analizar_empresa(datos_perfil, extraccion.texto)
    elif tipo_perfil == "desarrollador":
        resultado = analizar_desarrollador(datos_perfil, extraccion.texto)
    else:
        raise ValueError(f"Tipo de perfil desconocido: {tipo_perfil!r}")

    resultado.calidad_imagen = extraccion.calidad_imagen
    resultado.metodo_extraccion = extraccion.metodo
    resultado.alertas = alertas_previas + resultado.alertas
    return resultado

