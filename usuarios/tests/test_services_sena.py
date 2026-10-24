import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from logs.models import LogAuditoria
from notificaciones.models import Notificacion
from usuarios.models import FichaSena, PerfilDesarrollador
from usuarios.services_sena import (
    admin_resolver_verificacion_desarrollador,
    normalizar_programa_formacion,
    programa_formacion_es_valido,
    programas_formacion_coinciden,
    solicitar_verificacion_manual_desarrollador,
    validar_ficha_sena_en_lista_blanca,
    verificar_desarrollador_automatico,
)

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
        username='aprendiz_maria',
        email='maria@sena.edu.co',
        password='Password123!',
        rol='desarrollador',
        identificacion='1000000002',
    )
    PerfilDesarrollador.objects.get_or_create(usuario=user)
    return user


@pytest.fixture
def ficha_activa(db, admin_user):
    return FichaSena.objects.create(
        numero_ficha='2670888',
        programa_formacion='Análisis y Desarrollo de Software (ADSO)',
        regional='Antioquia',
        centro_formacion='Centro de Tecnología de la Manufactura Avanzada',
        activa=True,
        creada_por=admin_user,
    )


@pytest.fixture
def ficha_inactiva(db, admin_user):
    return FichaSena.objects.create(
        numero_ficha='2500111',
        programa_formacion='ADSO',
        activa=False,
        creada_por=admin_user,
    )


@pytest.mark.django_db
class TestValidarFichaEnListaBlanca:
    def test_ficha_activa_encontrada(self, ficha_activa):
        ficha, error = validar_ficha_sena_en_lista_blanca('2670888')
        assert error is None
        assert ficha == ficha_activa

    def test_ficha_espacios_guiones_se_normaliza(self, ficha_activa):
        ficha, error = validar_ficha_sena_en_lista_blanca(' 2670-888 ')
        assert error is None
        assert ficha == ficha_activa

    def test_ficha_inactiva_retorna_error(self, ficha_inactiva):
        ficha, error = validar_ficha_sena_en_lista_blanca('2500111')
        assert ficha is None
        assert 'inactiva' in error.lower() or 'no se encuentra' in error.lower()

    def test_ficha_inexistente_retorna_error(self):
        ficha, error = validar_ficha_sena_en_lista_blanca('9999999')
        assert ficha is None
        assert 'no se encuentra registrada' in error.lower()


@pytest.mark.django_db
class TestVerificacionDesarrolladorAutomatica:
    def test_verificacion_automatica_exitosa(self, dev_user, ficha_activa):
        perfil = dev_user.perfil_desarrollador
        ok, msg = verificar_desarrollador_automatico(
            perfil=perfil,
            numero_ficha='2670888',
            programa_formacion=None,
            usuario_solicitante=dev_user,
        )
        assert ok is True
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'verificado'
        assert perfil.es_verificado_sena is True
        assert perfil.ficha_sena == ficha_activa
        assert perfil.ficha == '2670888'
        assert perfil.programa_formacion == ficha_activa.programa_formacion
        assert perfil.fecha_verificacion is not None

        # Auditoria y notificacion
        assert LogAuditoria.objects.filter(registro_id=perfil.id, tabla_afectada='perfil_desarrollador').exists()
        assert Notificacion.objects.filter(usuario=dev_user, tipo='aprobacion').exists()

    def test_verificacion_automatica_falla_si_ficha_no_valida(self, dev_user):
        perfil = dev_user.perfil_desarrollador
        ok, msg = verificar_desarrollador_automatico(
            perfil=perfil,
            numero_ficha='9999999',
            programa_formacion='Inexistente',
            usuario_solicitante=dev_user,
        )
        assert ok is False
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'sin_verificar'
        assert perfil.es_verificado_sena is False


class TestNormalizarProgramaFormacion:
    def test_normaliza_tildes_mayusculas_y_espacios(self):
        assert (
            normalizar_programa_formacion('  Análisis   y Desarrollo DE Software  ')
            == 'analisis y desarrollo de software'
        )

    def test_programa_vacio_retorna_cadena_vacia(self):
        assert normalizar_programa_formacion('') == ''
        assert normalizar_programa_formacion(None) == ''


class TestProgramaFormacionEsValido:
    def test_programa_del_catalogo_es_valido(self):
        assert programa_formacion_es_valido('ADSO') is True
        assert programa_formacion_es_valido('Desarrollo de Videojuegos') is True

    def test_programa_con_tildes_y_minusculas_es_valido(self):
        assert programa_formacion_es_valido('análisis y desarrollo de software') is True

    def test_programa_inventado_no_es_valido(self):
        assert programa_formacion_es_valido('Inventado 123') is False
        assert programa_formacion_es_valido('Cocina') is False
        assert programa_formacion_es_valido('') is False


class TestProgramasFormacionCoinciden:
    def test_alias_adso_coincide_con_nombre_oficial(self):
        assert programas_formacion_coinciden('ADSO', 'Análisis y Desarrollo de Software') is True

    def test_mismo_programa_con_tildes_y_mayusculas_coincide(self):
        assert programas_formacion_coinciden(
            'programacion de software', 'Programación de Software'
        ) is True

    def test_programa_distinto_no_coincide(self):
        assert programas_formacion_coinciden('Cocina', 'ADSO') is False
        assert programas_formacion_coinciden('ADSO', 'Gestión de Redes de Datos') is False

    def test_cadenas_vacias_no_coinciden(self):
        assert programas_formacion_coinciden('', 'ADSO') is False
        assert programas_formacion_coinciden('ADSO', None) is False


@pytest.mark.django_db
class TestVerificacionManualDesarrollador:
    def test_solicitud_manual_exitosa_pasa_a_en_revision(self, dev_user, admin_user):
        perfil = dev_user.perfil_desarrollador
        pdf_content = b"%PDF-1.4 valid test pdf content for sena certification"
        archivo = SimpleUploadedFile("certificado_sena.pdf", pdf_content, content_type="application/pdf")

        ok, msg, errores = solicitar_verificacion_manual_desarrollador(
            perfil=perfil,
            numero_ficha='2800123',
            programa_formacion='Programación de Software',
            documento_soporte=archivo,
            usuario_solicitante=dev_user,
        )
        assert ok is True
        assert not errores
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'en_revision'
        assert perfil.ficha == '2800123'
        assert perfil.programa_formacion == 'Programación de Software'
        assert bool(perfil.documento_soporte) is True
        assert perfil.fecha_solicitud_verificacion is not None

        # Notificacion al admin
        assert Notificacion.objects.filter(usuario=admin_user, tipo='alerta').exists()
        assert LogAuditoria.objects.filter(registro_id=perfil.id, tabla_afectada='perfil_desarrollador').exists()

    def test_rechazo_archivo_no_pdf(self, dev_user):
        perfil = dev_user.perfil_desarrollador
        archivo = SimpleUploadedFile("carnet.png", b"fake png image", content_type="image/png")

        ok, msg, errores = solicitar_verificacion_manual_desarrollador(
            perfil=perfil,
            numero_ficha='2800123',
            programa_formacion='ADSO',
            documento_soporte=archivo,
            usuario_solicitante=dev_user,
        )
        assert ok is False
        assert 'documento_soporte' in errores
        assert 'PDF' in errores['documento_soporte']

    def test_rechazo_archivo_pdf_falso(self, dev_user):
        perfil = dev_user.perfil_desarrollador
        archivo = SimpleUploadedFile("virus.pdf", b"MZexecutable fake", content_type="application/pdf")

        ok, msg, errores = solicitar_verificacion_manual_desarrollador(
            perfil=perfil,
            numero_ficha='2800123',
            programa_formacion='ADSO',
            documento_soporte=archivo,
            usuario_solicitante=dev_user,
        )
        assert ok is False
        assert 'documento_soporte' in errores
        assert 'válido' in errores['documento_soporte']

    def test_solicitud_manual_egresado_sin_ficha_requiere_programa_y_soporte(self, dev_user, admin_user):
        perfil = dev_user.perfil_desarrollador
        pdf_content = b"%PDF-1.4 diploma de graduacion sena"
        archivo = SimpleUploadedFile("diploma.pdf", pdf_content, content_type="application/pdf")

        ok, msg, errores = solicitar_verificacion_manual_desarrollador(
            perfil=perfil,
            numero_ficha='',
            programa_formacion='Tecnólogo en ADSO',
            documento_soporte=archivo,
            usuario_solicitante=dev_user,
            condicion_sena='egresado',
        )
        assert ok is True
        assert not errores
        perfil.refresh_from_db()
        assert perfil.condicion_sena == 'egresado'
        assert perfil.estado_verificacion == 'en_revision'
        assert perfil.programa_formacion == 'Tecnólogo en ADSO'
        assert bool(perfil.documento_soporte) is True


@pytest.mark.django_db
class TestAdminResolucionDesarrollador:
    def test_admin_aprobar_solicitud(self, dev_user, admin_user):
        perfil = dev_user.perfil_desarrollador
        perfil.estado_verificacion = 'en_revision'
        perfil.ficha = '2800123'
        perfil.save()

        ok, msg = admin_resolver_verificacion_desarrollador(
            perfil_id=perfil.id,
            admin_user=admin_user,
            accion='aprobar',
            notas='Certificado verificado contra SofíaPlus',
        )
        assert ok is True
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'verificado'
        assert perfil.verificado_por == admin_user
        assert perfil.notas_auditoria == 'Certificado verificado contra SofíaPlus'
        assert Notificacion.objects.filter(usuario=dev_user, tipo='aprobacion').exists()

    def test_admin_rechazar_exige_motivo(self, dev_user, admin_user):
        perfil = dev_user.perfil_desarrollador
        perfil.estado_verificacion = 'en_revision'
        perfil.save()

        ok, msg = admin_resolver_verificacion_desarrollador(
            perfil_id=perfil.id,
            admin_user=admin_user,
            accion='rechazar',
            notas='',
        )
        assert ok is False
        assert 'motivo' in msg.lower()
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'en_revision'

    def test_admin_rechazar_con_motivo_actualiza_estado(self, dev_user, admin_user):
        perfil = dev_user.perfil_desarrollador
        perfil.estado_verificacion = 'en_revision'
        perfil.save()

        ok, msg = admin_resolver_verificacion_desarrollador(
            perfil_id=perfil.id,
            admin_user=admin_user,
            accion='rechazar',
            notas='El documento no es legible.',
        )
        assert ok is True
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'rechazado'
        assert perfil.verificado_por == admin_user
        assert perfil.notas_auditoria == 'El documento no es legible.'
        assert Notificacion.objects.filter(usuario=dev_user, tipo='alerta').exists()

    def test_admin_aprobar_solicitud_egresado(self, dev_user, admin_user):
        perfil = dev_user.perfil_desarrollador
        perfil.condicion_sena = 'egresado'
        perfil.estado_verificacion = 'en_revision'
        perfil.programa_formacion = 'ADSO'
        perfil.save()

        ok, msg = admin_resolver_verificacion_desarrollador(
            perfil_id=perfil.id,
            admin_user=admin_user,
            accion='aprobar',
            notas='Diploma verificado',
        )
        assert ok is True
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'verificado'
        assert perfil.condicion_sena == 'egresado'
        assert perfil.es_verificado_sena is True
        notif = Notificacion.objects.filter(usuario=dev_user, tipo='aprobacion').first()
        assert notif is not None
        assert 'Egresado SENA' in notif.mensaje


@pytest.fixture
def excepcion_activa(db, dev_user, admin_user):
    from usuarios.models import ExcepcionFichaSena
    return ExcepcionFichaSena.objects.create(
        desarrollador=dev_user.perfil_desarrollador,
        numero_ficha='3000123',
        justificacion='Ficha pendiente de cargue en SOFIA Plus, avalada por coordinación.',
        autorizado_por=admin_user,
        activa=True,
    )


@pytest.mark.django_db
class TestBuscarExcepcionFichaActiva:
    def test_excepcion_activa_sin_expiracion(self, dev_user, excepcion_activa):
        from usuarios.services_sena import buscar_excepcion_ficha_activa

        encontrada = buscar_excepcion_ficha_activa(
            ' 3000-123 ', dev_user.perfil_desarrollador
        )
        assert encontrada == excepcion_activa

    def test_excepcion_inactiva_no_se_encuentra(self, dev_user, admin_user):
        from usuarios.models import ExcepcionFichaSena
        from usuarios.services_sena import buscar_excepcion_ficha_activa

        ExcepcionFichaSena.objects.create(
            desarrollador=dev_user.perfil_desarrollador,
            numero_ficha='3000999',
            justificacion='Revocada por el comité.',
            autorizado_por=admin_user,
            activa=False,
        )
        assert buscar_excepcion_ficha_activa('3000999', dev_user.perfil_desarrollador) is None

    def test_excepcion_expirada_no_se_encuentra(self, dev_user, admin_user):
        from usuarios.models import ExcepcionFichaSena
        from usuarios.services_sena import buscar_excepcion_ficha_activa

        ExcepcionFichaSena.objects.create(
            desarrollador=dev_user.perfil_desarrollador,
            numero_ficha='3000888',
            justificacion='Vigencia vencida.',
            autorizado_por=admin_user,
            activa=True,
            fecha_expiracion=timezone.now() - timedelta(days=1),
        )
        assert buscar_excepcion_ficha_activa('3000888', dev_user.perfil_desarrollador) is None

    def test_excepcion_vigente_futura_se_encuentra(self, dev_user, admin_user):
        from usuarios.models import ExcepcionFichaSena
        from usuarios.services_sena import buscar_excepcion_ficha_activa

        excepcion = ExcepcionFichaSena.objects.create(
            desarrollador=dev_user.perfil_desarrollador,
            numero_ficha='3000777',
            justificacion='Vigencia futura.',
            autorizado_por=admin_user,
            activa=True,
            fecha_expiracion=timezone.now() + timedelta(days=15),
        )
        assert buscar_excepcion_ficha_activa('3000777', dev_user.perfil_desarrollador) == excepcion

    def test_sin_perfil_retorna_none(self, excepcion_activa):
        from usuarios.services_sena import buscar_excepcion_ficha_activa

        assert buscar_excepcion_ficha_activa('3000123', None) is None

    def test_sin_numero_ficha_retorna_none(self, dev_user, excepcion_activa):
        from usuarios.services_sena import buscar_excepcion_ficha_activa

        assert buscar_excepcion_ficha_activa('', dev_user.perfil_desarrollador) is None

    def test_excepcion_de_otro_desarrollador_no_se_encuentra(self, dev_user, admin_user,
                                                            excepcion_activa):
        from usuarios.services_sena import buscar_excepcion_ficha_activa

        otro = Usuario.objects.create_user(
            username='aprendiz_otro',
            email='otro@sena.edu.co',
            password='Password123!',
            rol='desarrollador',
            identificacion='1000000009',
        )
        PerfilDesarrollador.objects.get_or_create(usuario=otro)
        assert buscar_excepcion_ficha_activa('3000123', otro.perfil_desarrollador) is None


@pytest.mark.django_db
class TestVerificacionPorExcepcionFichaSena:
    def test_verificacion_automatica_por_excepcion_activa(self, dev_user, admin_user,
                                                         excepcion_activa):
        perfil = dev_user.perfil_desarrollador
        ok, msg = verificar_desarrollador_automatico(
            perfil=perfil,
            numero_ficha=' 3000-123 ',
            programa_formacion='Programación de Software',
            usuario_solicitante=dev_user,
        )

        assert ok is True
        assert 'excepción autorizada' in msg.lower()
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'verificado'
        assert perfil.es_verificado_sena is True
        assert perfil.ficha == '3000123'
        assert perfil.programa_formacion == 'Programación de Software'
        assert perfil.ficha_sena is None
        assert perfil.fecha_verificacion is not None

        assert LogAuditoria.objects.filter(
            tabla_afectada='excepciones_ficha_sena', registro_id=excepcion_activa.id
        ).exists()
        assert Notificacion.objects.filter(usuario=dev_user, tipo='aprobacion').exists()

    def test_rechazo_con_excepcion_inactiva(self, dev_user, admin_user):
        from usuarios.models import ExcepcionFichaSena

        perfil = dev_user.perfil_desarrollador
        ExcepcionFichaSena.objects.create(
            desarrollador=perfil,
            numero_ficha='3000555',
            justificacion='Excepción revocada.',
            autorizado_por=admin_user,
            activa=False,
        )

        ok, msg = verificar_desarrollador_automatico(
            perfil=perfil, numero_ficha='3000555', usuario_solicitante=dev_user,
        )

        assert ok is False
        assert 'no se encuentra registrada' in msg.lower()
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'sin_verificar'

    def test_rechazo_con_excepcion_expirada(self, dev_user, admin_user):
        from usuarios.models import ExcepcionFichaSena

        perfil = dev_user.perfil_desarrollador
        ExcepcionFichaSena.objects.create(
            desarrollador=perfil,
            numero_ficha='3000666',
            justificacion='Excepción vencida.',
            autorizado_por=admin_user,
            activa=True,
            fecha_expiracion=timezone.now() - timedelta(days=2),
        )

        ok, msg = verificar_desarrollador_automatico(
            perfil=perfil, numero_ficha='3000666', usuario_solicitante=dev_user,
        )

        assert ok is False
        perfil.refresh_from_db()
        assert perfil.estado_verificacion == 'sin_verificar'

    def test_ficha_en_lista_blanca_tiene_prioridad_sobre_excepcion(self, dev_user, ficha_activa,
                                                                   excepcion_activa):
        perfil = dev_user.perfil_desarrollador
        ok, msg = verificar_desarrollador_automatico(
            perfil=perfil, numero_ficha='2670888', usuario_solicitante=dev_user,
        )

        assert ok is True
        perfil.refresh_from_db()
        assert perfil.ficha_sena == ficha_activa
        assert not LogAuditoria.objects.filter(
            tabla_afectada='excepciones_ficha_sena'
        ).exists()
