"""
Tareas Celery asíncronas para verificación documental asistida (JobDevs).

Procesamiento 100% local sin bloqueo de la interfaz web.
"""

import logging
import os
from celery import shared_task
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='usuarios.analizar_documento_soporte',
    max_retries=2,
    default_retry_delay=10,
)
def analizar_documento_soporte_task(self, perfil_id: int, tipo_perfil: str) -> dict:
    """
    Tarea Celery asíncrona que ejecuta el análisis heurístico y OCR local
    del documento de soporte de una empresa o talento SENA.
    """
    from .models import PerfilEmpresa, PerfilDesarrollador, Usuario
    from .services_ia_docs import analizar_documento_soporte
    from .utils import get_admin_ids
    from notificaciones.models import Notificacion

    logger.info("Iniciando análisis documental para perfil_id=%s, tipo=%s", perfil_id, tipo_perfil)

    perfil = None
    datos_perfil = {}

    try:
        if tipo_perfil == 'empresa':
            perfil = PerfilEmpresa.objects.select_related('usuario').filter(id=perfil_id).first()
            if not perfil:
                logger.error("PerfilEmpresa id=%s no encontrado.", perfil_id)
                return {'error': 'perfil_no_encontrado'}

            datos_perfil = {
                'numero_documento': perfil.numero_documento or '',
                'digito_verificacion': perfil.digito_verificacion or '',
                'razon_social': perfil.razon_social or perfil.nombre_empresa or '',
            }

        elif tipo_perfil == 'desarrollador':
            perfil = PerfilDesarrollador.objects.select_related('usuario').filter(id=perfil_id).first()
            if not perfil:
                logger.error("PerfilDesarrollador id=%s no encontrado.", perfil_id)
                return {'error': 'perfil_no_encontrado'}

            datos_perfil = {
                'ficha': perfil.ficha or '',
                'programa_formacion': perfil.programa_formacion or '',
                'nombre_usuario': perfil.usuario.nombre or perfil.usuario.username,
            }
        else:
            logger.error("Tipo de perfil desconocido: %s", tipo_perfil)
            return {'error': 'tipo_perfil_invalido'}

        # Validar existencia física del documento
        if not perfil.documento_soporte or not bool(perfil.documento_soporte.name):
            logger.warning("Perfil id=%s no tiene documento_soporte adjunto.", perfil_id)
            dictamen_vacio = {
                'score_confianza': 0,
                'estado_triaje': 'sin_documento',
                'calidad_imagen': 'desconocida',
                'alertas': [{'nivel': 'critica', 'codigo': 'SIN_DOCUMENTO', 'mensaje': 'No se encontró documento adjunto.'}],
                'justificacion': 'El perfil no tiene un archivo de soporte cargado.',
            }
            perfil.dictamen_ia = dictamen_vacio
            perfil.save(update_fields=['dictamen_ia'])
            return dictamen_vacio

        # Marcar estado transitorio en dictamen_ia
        perfil.dictamen_ia = {'estado_triaje': 'procesando', 'score_confianza': None}
        perfil.save(update_fields=['dictamen_ia'])

        ruta_archivo = perfil.documento_soporte.path
        if not os.path.exists(ruta_archivo):
            logger.error("Archivo físico no encontrado en ruta: %s", ruta_archivo)
            dictamen_error = {
                'score_confianza': 0,
                'estado_triaje': 'error_archivo_no_encontrado',
                'calidad_imagen': 'desconocida',
                'alertas': [{'nivel': 'critica', 'codigo': 'ARCHIVO_INEXISTENTE', 'mensaje': 'El archivo físico no existe en el almacenamiento.'}],
                'justificacion': 'Ruta del archivo inaccesible en el servidor.',
            }
            perfil.dictamen_ia = dictamen_error
            perfil.save(update_fields=['dictamen_ia'])
            return dictamen_error

        # Ejecutar motor heurístico local
        resultado = analizar_documento_soporte(
            ruta_archivo=ruta_archivo,
            tipo_perfil=tipo_perfil,
            datos_perfil=datos_perfil,
        )

        dictamen_final = resultado.to_dict()

        with transaction.atomic():
            perfil.dictamen_ia = dictamen_final
            perfil.save(update_fields=['dictamen_ia'])

            # Notificar al administrador que el triaje asistido está listo
            admin_ids = get_admin_ids()
            if admin_ids:
                nombre_sujeto = perfil.usuario.nombre or perfil.usuario.username
                tipo_humano = "Empresa" if tipo_perfil == "empresa" else "Talento SENA"
                mensaje_notif = (
                    f"Análisis documental completado para {tipo_humano} '{nombre_sujeto}'. "
                    f"Score: {resultado.score_confianza}/100 ({resultado.estado_triaje})."
                )
                notificaciones = [
                    Notificacion(
                        usuario_id=admin_id,
                        tipo='alerta',
                        mensaje=mensaje_notif,
                    )
                    for admin_id in admin_ids
                ]
                Notificacion.objects.bulk_create(notificaciones)

        logger.info(
            "Análisis documental completado exitosamente para perfil_id=%s. Score=%s",
            perfil_id, resultado.score_confianza
        )
        return dictamen_final

    except Exception as exc:
        logger.error("Error procesando documento para perfil_id=%s: %s", perfil_id, exc, exc_info=True)
        if perfil:
            perfil.dictamen_ia = {
                'score_confianza': 0,
                'estado_triaje': 'error',
                'calidad_imagen': 'desconocida',
                'alertas': [{'nivel': 'critica', 'codigo': 'ERROR_CELERY', 'mensaje': str(exc)}],
                'justificacion': f'Fallo en la tarea de análisis: {exc}',
            }
            perfil.save(update_fields=['dictamen_ia'])

        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.critical("Se agotaron los reintentos de análisis documental para perfil_id=%s", perfil_id)
            raise
