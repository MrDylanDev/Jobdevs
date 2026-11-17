from django.contrib import admin

from .models import Avance


@admin.register(Avance)
class AvanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'proyecto', 'desarrollador', 'entregable', 'estado', 'fecha_hora')
    list_filter = ('estado', 'fecha_hora')
    search_fields = ('proyecto__titulo', 'desarrollador__username', 'descripcion')
