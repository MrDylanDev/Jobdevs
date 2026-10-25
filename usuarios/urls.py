from django.urls import path
from . import views

urlpatterns = [
    # Inicio Global
    path('', views.inicio, name='inicio'),

    # Dashboards y Acciones Administrativas
    path('admin/dashboard/', views.dashboard_admin, name='dashboard_admin'),
    path('admin/usuario/toggle/<int:usuario_id>/', views.admin_toggle_usuario, name='admin_toggle_usuario'),
    path('admin/proyecto/reactivar/<int:proyecto_id>/', views.admin_reactivar_proyecto, name='admin_reactivar_proyecto'),
    path('empresa/dashboard/', views.dashboard_empresa, name='dashboard_empresa'),
    path('empresa/<int:empresa_id>/detalle/', views.detalle_empresa, name='detalle_empresa'),
    path('admin/empresa/<int:perfil_id>/verificar/', views.admin_resolver_verificacion_empresa, name='admin_resolver_verificacion_empresa'),
    path('admin/desarrollador/<int:perfil_id>/verificar/', views.admin_resolver_verificacion_desarrollador, name='admin_resolver_verificacion_desarrollador'),
    path('admin/fichas-sena/crear/', views.admin_crear_ficha_sena, name='admin_crear_ficha_sena'),
    path('admin/fichas-sena/<int:ficha_id>/toggle/', views.admin_toggle_ficha_sena, name='admin_toggle_ficha_sena'),
    path('admin/fichas-sena/excepciones/crear/', views.admin_crear_excepcion_ficha_sena, name='admin_crear_excepcion_ficha_sena'),
    path('admin/fichas-sena/excepciones/<int:excepcion_id>/revocar/', views.admin_revocar_excepcion_ficha_sena, name='admin_revocar_excepcion_ficha_sena'),
    path('admin/notificaciones/depurar/', views.admin_depurar_notificaciones, name='admin_depurar_notificaciones'),
    path('empresa/<int:perfil_id>/documento/', views.descargar_documento_soporte_empresa, name='descargar_documento_soporte_empresa'),
    path('empresa/verificacion/', views.solicitar_verificacion_empresa, name='solicitar_verificacion_empresa'),
    path('desarrollador/dashboard/', views.dashboard_desarrollador, name='dashboard_desarrollador'),
    path('desarrollador/<int:desarrollador_id>/detalle/', views.detalle_desarrollador, name='detalle_desarrollador'),
    path('desarrollador/verificacion/', views.solicitar_verificacion_desarrollador, name='solicitar_verificacion_desarrollador'),
    path('desarrollador/<int:perfil_id>/documento/', views.descargar_documento_soporte_desarrollador, name='descargar_documento_soporte_desarrollador'),
    
    # Gestión de Perfil
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    
    # Autenticación y Registro
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('recuperar/', views.recuperar_view, name='recuperar'),
    path('restablecer/<str:token>/', views.restablecer_view, name='restablecer'),

    # APIs de Usuarios
    path('api/', views.api_usuarios, name='api_usuarios'),
    path('api/<int:usuario_id>/', views.api_usuario_detalle, name='api_usuario_detalle'),
    path('api/crear/', views.api_crear_usuario, name='api_crear_usuario'),
    path('api/<int:usuario_id>/actualizar/', views.api_actualizar_usuario, name='api_actualizar_usuario'),
    path('api/<int:usuario_id>/eliminar/', views.api_eliminar_usuario, name='api_eliminar_usuario'),
    path('api/bulk-toggle/', views.api_bulk_toggle, name='api_bulk_toggle'),

    # Almacenamiento privado (Cloudflare R2)
    path('api/storage/presigned-upload/', views.api_generar_url_subida_prefirmada, name='api_presigned_upload'),
]
