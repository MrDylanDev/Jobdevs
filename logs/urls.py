from django.urls import path
from . import views

urlpatterns = [
    path('actividad/', views.historial_actividad, name='historial_actividad'),
    path('reporte/mensual/pdf/', views.reporte_mensual_pdf, name='reporte_mensual_pdf'),
    path('reporte/proyectos/csv/', views.reporte_proyectos_csv, name='reporte_proyectos_csv'),
    path('reporte/empresas/csv/', views.reporte_empresas_csv, name='reporte_empresas_csv'),
    path('reporte/aprendices/csv/', views.reporte_aprendices_csv, name='reporte_aprendices_csv'),
    path('reporte/auditoria/csv/', views.reporte_auditoria_csv, name='reporte_auditoria_csv'),
    path('reporte/imprimir/', views.reporte_vista_impresion, name='reporte_vista_impresion'),
    path('tecnico/', views.visor_logs_tecnicos, name='visor_logs_tecnicos'),
]
