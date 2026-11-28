from django.urls import path

from . import views

urlpatterns = [
    path('toggle/<int:proyecto_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('mis-favoritos/', views.listar_favoritos, name='listar_favoritos'),
]
