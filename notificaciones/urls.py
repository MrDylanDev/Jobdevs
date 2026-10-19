from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_notificaciones, name='notificaciones_lista'),
    path('stream/', views.notificaciones_stream, name='notificaciones_stream'),
    path('marcar-leida/<int:notificacion_id>/', views.marcar_leida, name='notificacion_marcar_leida'),
    path('marcar-todas-leidas/', views.marcar_todas_leidas, name='notificaciones_marcar_todas_leidas'),
]
