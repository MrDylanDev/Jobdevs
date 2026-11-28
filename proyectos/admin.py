from django.contrib import admin

from .models import HistorialEstadoProyecto, Valoracion


@admin.register(Valoracion)
class ValoracionAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'empresa', 'desarrollador', 'puntuacion', 'rol_evaluador', 'fecha')
    list_filter = ('puntuacion', 'rol_evaluador')
    search_fields = ('proyecto__titulo', 'comentario')


@admin.register(HistorialEstadoProyecto)
class HistorialEstadoProyectoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'estado_anterior', 'estado_nuevo', 'cambiado_por', 'fecha')
    list_filter = ('estado_nuevo', 'fecha')
    search_fields = ('proyecto__titulo',)
