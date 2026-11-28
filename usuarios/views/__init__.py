# usuarios/views/__init__.py
# Re-exporta todas las vistas para mantener compatibilidad con urls.py

from .admin_api import (
    api_actualizar_usuario,
    api_auditoria,
    api_bulk_toggle,
    api_crear_usuario,
    api_eliminar_usuario,
    api_usuario_detalle,
    api_usuarios,
)
from .admin_dashboard import (
    admin_actualizar_configuracion_negociacion,
    admin_crear_excepcion_ficha_sena,
    admin_crear_ficha_sena,
    admin_depurar_notificaciones,
    admin_reactivar_proyecto,
    admin_regularizar_cierre_proyecto,
    admin_revocar_excepcion_ficha_sena,
    admin_toggle_ficha_sena,
    admin_toggle_usuario,
    dashboard_admin,
)
from .auth_views import (
    api_sesion,
    login_view,
    logout_view,
    recuperar_view,
    restablecer_view,
)
from .dashboard_views import (
    inicio,
)
from .dev_dashboard import (
    dashboard_desarrollador,
    detalle_desarrollador,
)
from .empresa_dashboard import (
    api_inicio_actividad_empresa,
    dashboard_empresa,
    detalle_empresa,
)
from .profile_views import (
    editar_perfil,
)
from .public_views import (
    legal_condiciones_view,
    legal_cookies_view,
    legal_privacidad_view,
)
from .registration_views import (
    registro_view,
)
from .verificacion_views import (
    admin_resolver_verificacion_desarrollador,
    admin_resolver_verificacion_empresa,
    api_generar_url_subida_prefirmada,
    descargar_documento_soporte_desarrollador,
    descargar_documento_soporte_empresa,
    solicitar_verificacion_desarrollador,
    solicitar_verificacion_empresa,
)

__all__ = [
    'admin_actualizar_configuracion_negociacion',
    'admin_crear_excepcion_ficha_sena',
    'admin_crear_ficha_sena',
    'admin_depurar_notificaciones',
    'admin_reactivar_proyecto',
    'admin_regularizar_cierre_proyecto',
    'admin_resolver_verificacion_desarrollador',
    'admin_resolver_verificacion_empresa',
    'admin_revocar_excepcion_ficha_sena',
    'admin_toggle_ficha_sena',
    'admin_toggle_usuario',
    'api_actualizar_usuario',
    'api_auditoria',
    'api_bulk_toggle',
    'api_crear_usuario',
    'api_eliminar_usuario',
    'api_generar_url_subida_prefirmada',
    'api_inicio_actividad_empresa',
    'api_sesion',
    'api_usuario_detalle',
    'api_usuarios',
    'dashboard_admin',
    'dashboard_desarrollador',
    'dashboard_empresa',
    'descargar_documento_soporte_desarrollador',
    'descargar_documento_soporte_empresa',
    'detalle_desarrollador',
    'detalle_empresa',
    'editar_perfil',
    'inicio',
    'legal_condiciones_view',
    'legal_cookies_view',
    'legal_privacidad_view',
    'login_view',
    'logout_view',
    'recuperar_view',
    'registro_view',
    'restablecer_view',
    'solicitar_verificacion_desarrollador',
    'solicitar_verificacion_empresa',
]
