from django.urls import path
from . import views

urlpatterns = [
    path('postularse/<int:proyecto_id>/', views.postularse_a_proyecto, name='postularse_a_proyecto'),
    path('proyecto/<int:proyecto_id>/recibidas/', views.ver_postulaciones_empresa, name='ver_postulaciones_empresa'),
    path('aceptar/<int:postulacion_id>/', views.aceptar_postulacion, name='aceptar_postulacion'),
    path('iniciar-negociacion/<int:postulacion_id>/', views.iniciar_negociacion, name='iniciar_negociacion'),
]
