"""
Pruebas automatizadas para el sistema de verificación documental asistida (JobDevs).
Cubre Fase 10: heurísticas, extracción, OCR, tareas Celery y control administrativo.
"""

import io
import json
import sys
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from usuarios.models import PerfilEmpresa, PerfilDesarrollador, FichaSena
from usuarios.services_ia_docs import (
    extraer_datos_empresa,
    extraer_datos_desarrollador,
    analizar_empresa,
    analizar_desarrollador,
    detectar_borrosidad,
    _validar_dv_nit,
    _similitud,
    ResultadoTriaje,
)
from usuarios.tasks import analizar_documento_soporte_task
from logs.models import LogAuditoria
from notificaciones.models import Notificacion

Usuario = get_user_model()


class TriajeHeuristicasTestCase(TestCase):
    """Pruebas unitarias para extracción, matching difuso y validación Módulo 11."""

    def test_01_extraccion_empresa_nit_correcto(self):
        texto = """
        CAMARA DE COMERCIO DE BOGOTA
        NIT: 900.123.456-7
        RAZON SOCIAL: INVERSIONES TECNOLOGICAS SAS
        MATRICULA MERCANTIL: 12345678
        REPRESENTANTE LEGAL: JUAN PEREZ
        FECHA: 15 de marzo de 2024
        """
        datos = extraer_datos_empresa(texto)
        self.assertEqual(datos.nit, "900123456")
        self.assertEqual(datos.digito_verificacion, "7")
        self.assertEqual(datos.razon_social, "INVERSIONES TECNOLOGICAS SAS")
        self.assertEqual(datos.matricula_mercantil, "12345678")

    def test_02_analisis_empresa_nit_coincidente(self):
        texto = "NIT: 900123456-7\nRAZON SOCIAL: SOLUCIONES DIGITALES SAS"
        perfil_datos = {
            "numero_documento": "900123456",
            "digito_verificacion": "7",
            "razon_social": "Soluciones Digitales S.A.S.",
        }
        res = analizar_empresa(perfil_datos, texto)
        self.assertGreaterEqual(res.score_confianza, 70)
        self.assertIn("NIT coincide: 900123456", res.coincidencias[0])

    def test_03_analisis_empresa_nit_discrepante_limita_score(self):
        texto = "NIT: 800999888-1\nRAZON SOCIAL: OTRA EMPRESA DISTINTA"
        perfil_datos = {
            "numero_documento": "900123456",
            "digito_verificacion": "7",
            "razon_social": "Mi Empresa SAS",
        }
        res = analizar_empresa(perfil_datos, texto)
        # Una discrepancia crítica limita el score a menos de 40
        self.assertLessEqual(res.score_confianza, 39)
        self.assertEqual(res.estado_triaje, "discrepancias_criticas")
        self.assertTrue(any(a["codigo"] == "NIT_NO_COINCIDE" for a in res.alertas))

    def test_04_extraccion_desarrollador_ficha_y_programa(self):
        texto = """
        SERVICIO NACIONAL DE APRENDIZAJE - SENA
        CERTIFICA QUE:
        CARLOS ANDRES RAMIREZ
        IDENTIFICADO CON CC 1020304050
        ESTA MATRICULADO EN LA FICHA: 2670123
        PROGRAMA: Tecnologo en Analisis y Desarrollo de Software
        CENTRO: Centro de Servicios Financieros
        ESTADO: En formacion
        FECHA: 20/01/2024
        """
        datos = extraer_datos_desarrollador(texto)
        self.assertEqual(datos.numero_ficha, "2670123")
        self.assertIn("Analisis y Desarrollo", datos.programa_formacion)
        self.assertIn("Centro de Servicios", datos.centro_formacion)

    def test_05_analisis_desarrollador_ficha_coincidente(self):
        texto = "FICHA: 2670123\nPROGRAMA: ADSO\nCARLOS RAMIREZ"
        perfil_datos = {
            "ficha": "2670123",
            "programa_formacion": "Análisis y Desarrollo de Software",
            "nombre_usuario": "Carlos Ramirez",
        }
        res = analizar_desarrollador(perfil_datos, texto)
        self.assertGreaterEqual(res.score_confianza, 70)
        self.assertTrue(any("Ficha" in c or "ficha" in c for c in res.coincidencias))

    def test_06_analisis_desarrollador_ficha_discrepante_limita_score(self):
        texto = "FICHA: 9999999\nPROGRAMA: Gastronomia"
        perfil_datos = {
            "ficha": "2670123",
            "programa_formacion": "ADSO",
            "nombre_usuario": "Pedro",
        }
        res = analizar_desarrollador(perfil_datos, texto)
        self.assertLessEqual(res.score_confianza, 39)
        self.assertTrue(any(a["codigo"] == "FICHA_NO_COINCIDE" for a in res.alertas))

    def test_07_coincidencia_difusa_razon_social(self):
        # 85% de similitud para variaciones menores
        s1 = "Inversiones y Soluciones Tecnológicas S.A.S."
        s2 = "Inversiones y Soluciones Tecnologicas SAS"
        ratio = _similitud(s1, s2)
        self.assertGreaterEqual(ratio, 0.85)

    def test_08_validacion_digito_verificacion_modulo_11(self):
        # NIT SENA: 899999034 -> DV calculado es 1
        valido = _validar_dv_nit("899999034", "1")
        self.assertTrue(valido)
        invalido = _validar_dv_nit("899999034", "9")
        self.assertFalse(invalido)

    def test_09_documento_con_campos_faltantes(self):
        texto = "Documento sin datos reconocibles solo saludos cordiales."
        datos = extraer_datos_empresa(texto)
        self.assertIn("nit", datos.campos_no_encontrados)
        self.assertIn("razon_social", datos.campos_no_encontrados)

    def test_10_detector_borrosidad_sintetico(self):
        # Mock de imagen plana para probar el algoritmo con numpy simulado
        mock_numpy = MagicMock()
        mock_numpy.array.return_value = MagicMock()
        with patch.dict(sys.modules, {"numpy": mock_numpy}), \
             patch("usuarios.services_ia_docs._importar_cv2") as mock_cv2, \
             patch("usuarios.services_ia_docs._importar_pil") as mock_pil:
            cv2_inst = MagicMock()
            cv2_inst.Laplacian.return_value.var.return_value = 45.0  # Menor a 100.0 (borrosa)
            mock_cv2.return_value = cv2_inst
            mock_pil.return_value = MagicMock()

            es_borrosa, var = detectar_borrosidad(b"fake_image_bytes")
            self.assertTrue(es_borrosa)
            self.assertEqual(var, 45.0)


class TriajeCeleryYAdminTestCase(TestCase):
    """Pruebas de tareas Celery, permisos y registro de auditoría."""

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            username="admin_test",
            email="admin@jobdevs.edu.co",
            password="Password123!",
            rol="administrador",
        )
        self.empresa_user = Usuario.objects.create_user(
            username="empresa_demo",
            email="empresa@demo.com",
            password="Password123!",
            rol="empresa",
        )
        self.perfil_empresa = PerfilEmpresa.objects.create(
            usuario=self.empresa_user,
            nombre_empresa="Demo Tech",
            numero_documento="900123456",
            digito_verificacion="7",
            razon_social="Demo Tech SAS",
            estado_verificacion="en_revision",
            documento_soporte=SimpleUploadedFile("soporte.pdf", b"%PDF-1.4 Fake PDF Content", content_type="application/pdf"),
        )

    def test_11_tarea_celery_analisis_empresa_exitosa(self):
        with patch("usuarios.services_ia_docs.analizar_documento_soporte") as mock_analizar, \
             patch("os.path.exists", return_value=True):
            resultado_mock = ResultadoTriaje(
                score_confianza=95,
                estado_triaje="recomendado_aprobar",
                calidad_imagen="nitida",
                coincidencias=["NIT coincide: 900123456"],
            )
            mock_analizar.return_value = resultado_mock

            dictamen = analizar_documento_soporte_task(self.perfil_empresa.id, "empresa")

            self.perfil_empresa.refresh_from_db()
            self.assertIsNotNone(self.perfil_empresa.dictamen_ia)
            self.assertEqual(self.perfil_empresa.dictamen_ia["score_confianza"], 95)
            self.assertEqual(self.perfil_empresa.dictamen_ia["estado_triaje"], "recomendado_aprobar")

            # Verifica notificación a administradores
            notif = Notificacion.objects.filter(usuario=self.admin).last()
            self.assertIsNotNone(notif)
            self.assertIn("95/100", notif.mensaje)

    def test_12_tarea_celery_perfil_inexistente_manejo_defensivo(self):
        res = analizar_documento_soporte_task(999999, "empresa")
        self.assertEqual(res.get("error"), "perfil_no_encontrado")

    def test_13_administrador_aprueba_verificacion_con_auditoria(self):
        self.client.force_login(self.admin)
        from django.urls import reverse
        url = reverse("admin_resolver_verificacion_empresa", args=[self.perfil_empresa.id])

        resp = self.client.post(url, {"accion": "aprobar"})
        self.assertEqual(resp.status_code, 302)

        self.perfil_empresa.refresh_from_db()
        self.assertEqual(self.perfil_empresa.estado_verificacion, "verificada")
        self.assertEqual(self.perfil_empresa.verificado_por, self.admin)

        # LogAuditoria verificado
        log = LogAuditoria.objects.filter(tabla_afectada="perfil_empresa", registro_id=self.perfil_empresa.id).last()
        self.assertIsNotNone(log)
        self.assertIn("Aprobó", log.accion)

    def test_14_administrador_solicita_correccion_con_motivo(self):
        self.client.force_login(self.admin)
        from django.urls import reverse
        url = reverse("admin_resolver_verificacion_empresa", args=[self.perfil_empresa.id])

        motivo = "El PDF es ilegible. Por favor adjunta un documento nítido."
        resp = self.client.post(url, {"accion": "rechazar", "notas": motivo})
        self.assertEqual(resp.status_code, 302)

        self.perfil_empresa.refresh_from_db()
        self.assertEqual(self.perfil_empresa.estado_verificacion, "rechazada")
        self.assertEqual(self.perfil_empresa.notas_auditoria, motivo)

        # Notificación al usuario de la empresa
        notif = Notificacion.objects.filter(usuario=self.empresa_user).last()
        self.assertIsNotNone(notif)
        self.assertIn(motivo, notif.mensaje)

    def test_15_usuario_sin_permisos_no_puede_aprobar(self):
        # Intentar aprobar como usuario empresa sin rol administrador
        self.client.force_login(self.empresa_user)
        from django.urls import reverse
        url = reverse("admin_resolver_verificacion_empresa", args=[self.perfil_empresa.id])

        resp = self.client.post(url, {"accion": "aprobar"})
        self.assertEqual(resp.status_code, 403)
