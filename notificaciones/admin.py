from django.contrib import admin

from .models import AvisoCumplimiento, Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'proyecto', 'tipo', 'leida', 'fecha')
    list_filter = ('tipo', 'leida', 'fecha')
    search_fields = ('usuario__username', 'mensaje', 'proyecto__titulo')


@admin.register(AvisoCumplimiento)
class AvisoCumplimientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'proyecto', 'usuario', 'etapa', 'fecha_cumplimiento')
    list_filter = ('etapa', 'fecha_cumplimiento')
    search_fields = ('proyecto__titulo', 'usuario__username')
