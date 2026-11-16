from django.urls import path
from . import views

urlpatterns = [
    path('postularse/<int:proyecto_id>/', views.postularse_a_proyecto, name='postularse_a_proyecto'),
    path('proyecto/<int:proyecto_id>/recibidas/', views.ver_postulaciones_empresa, name='ver_postulaciones_empresa'),
    # Compatibilidad con enlaces antiguos: también deben pasar por la negociación y firma.
    path('aceptar/<int:postulacion_id>/', views.iniciar_negociacion, name='aceptar_postulacion'),
    path('rechazar/<int:postulacion_id>/', views.rechazar_postulacion, name='rechazar_postulacion'),
    path('iniciar-negociacion/<int:postulacion_id>/', views.iniciar_negociacion, name='iniciar_negociacion'),
]
