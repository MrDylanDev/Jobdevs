from django.urls import path

from . import views

app_name = 'disputas'

urlpatterns = [
    path('abrir/<int:proyecto_id>/', views.abrir_disputa_view, name='abrir_disputa'),
    path('<int:disputa_id>/', views.detalle_disputa_view, name='detalle_disputa'),
]
