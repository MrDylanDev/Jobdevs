# usuarios/views/__init__.py
# Re-exporta todas las vistas para mantener compatibilidad con urls.py

from .auth_views import (
    login_view,
    logout_view,
    recuperar_view,
    restablecer_view,
)

from .registration_views import (
    registro_view,
)

from .profile_views import (
    editar_perfil,
)

from .dashboard_views import (
    inicio,
)

from .empresa_dashboard import (
    dashboard_empresa,
    detalle_empresa,
)

from .dev_dashboard import (
    dashboard_desarrollador,
)

from .admin_dashboard import (
    dashboard_admin,
    marcar_notificaciones_leidas,
    admin_toggle_usuario,
    admin_reactivar_proyecto,
    admin_crear_ficha_sena,
    admin_toggle_ficha_sena,
)

from .admin_api import (
    api_usuarios,
    api_usuario_detalle,
    api_crear_usuario,
    api_actualizar_usuario,
    api_eliminar_usuario,
    api_bulk_toggle,
)

from .verificacion_views import (
    solicitar_verificacion_empresa,
    admin_resolver_verificacion_empresa,
    descargar_documento_soporte_empresa,
    solicitar_verificacion_desarrollador,
    descargar_documento_soporte_desarrollador,
    admin_resolver_verificacion_desarrollador,
)
