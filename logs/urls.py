from django.urls import path
from . import views

urlpatterns = [
    path('reporte/proyectos/csv/', views.reporte_proyectos_csv, name='reporte_proyectos_csv'),
    path('reporte/empresas/csv/', views.reporte_empresas_csv, name='reporte_empresas_csv'),
    path('reporte/aprendices/csv/', views.reporte_aprendices_csv, name='reporte_aprendices_csv'),
    path('reporte/imprimir/', views.reporte_vista_impresion, name='reporte_vista_impresion'),
    path('tecnico/', views.visor_logs_tecnicos, name='visor_logs_tecnicos'),
]
