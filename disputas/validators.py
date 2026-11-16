import os
import zipfile

from django.core.exceptions import ValidationError
from PIL import Image

EXTENSIONES_EVIDENCIA = {'.pdf', '.zip', '.png', '.jpg', '.jpeg'}
MAX_EVIDENCIA_BYTES = 10 * 1024 * 1024


def validar_evidencia_archivo(archivo):
    if not archivo:
        return
    if archivo.size > MAX_EVIDENCIA_BYTES:
        raise ValidationError('La evidencia no puede superar los 10 MB.')

    _, extension = os.path.splitext(archivo.name.lower())
    if extension not in EXTENSIONES_EVIDENCIA:
        raise ValidationError('Solo se admiten evidencias PDF, ZIP, PNG y JPG.')

    cabecera = archivo.read(16)
    archivo.seek(0)
    if extension == '.pdf' and not cabecera.startswith(b'%PDF-'):
        raise ValidationError('El archivo no es un PDF válido.')
    if extension == '.zip':
        if not cabecera.startswith((b'PK\x03\x04', b'PK\x05\x06')):
            raise ValidationError('El archivo no es un ZIP válido.')
        if not zipfile.is_zipfile(archivo):
            archivo.seek(0)
            raise ValidationError('El archivo ZIP está dañado.')
        archivo.seek(0)
    if extension in ('.png', '.jpg', '.jpeg'):
        firma_valida = (
            extension == '.png' and cabecera.startswith(b'\x89PNG\r\n\x1a\n')
        ) or (
            extension in ('.jpg', '.jpeg') and cabecera.startswith(b'\xff\xd8\xff')
        )
        if not firma_valida:
            raise ValidationError('La imagen de evidencia no es válida.')
        try:
            with Image.open(archivo) as imagen:
                imagen.verify()
        except Exception as exc:
            raise ValidationError('La imagen de evidencia está dañada.') from exc
        finally:
            archivo.seek(0)
