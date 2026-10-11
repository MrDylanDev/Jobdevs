from django.urls import path
from . import views

urlpatterns = [
    # Chat en tiempo real
    path('chat/<int:receptor_id>/<int:proyecto_id>/', views.sala_chat, name='sala_chat'),
    path('chat/<int:receptor_id>/', views.sala_chat, name='sala_chat_general'),
    path('espacio-trabajo/<int:proyecto_id>/', views.sala_chat_grupal, name='sala_chat_grupal'),

    # Mensajería directa
    path('bandeja/', views.mensajeria_inbox, name='mensajeria_inbox'),
    path('enviados/', views.mensajeria_sent, name='mensajeria_sent'),
    path('redactar/', views.mensajeria_redactar, name='mensajeria_redactar'),
    path('ver/<int:mensaje_id>/', views.ver_mensaje, name='ver_mensaje'),

    # Auditoría de chats (administrador)
    path('auditoria/', views.admin_auditar_mensajes, name='admin_auditar_mensajes'),
]
