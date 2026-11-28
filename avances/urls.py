from django.urls import path

from . import views

urlpatterns = [
    path('registrar/<int:proyecto_id>/', views.registrar_avance, name='registrar_avance'),
    path('proyecto/<int:proyecto_id>/', views.ver_avances, name='ver_avances'),
    path('revisar/<int:avance_id>/', views.revisar_avance, name='revisar_avance'),
]
