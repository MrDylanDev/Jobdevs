from django.contrib import admin

from .models import ConfiguracionNegociacion, Postulacion


@admin.register(Postulacion)
class PostulacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'proyecto', 'desarrollador', 'estado', 'fecha', 'fecha_limite_negociacion')
    list_filter = ('estado', 'fecha')
    search_fields = ('proyecto__titulo', 'desarrollador__username')


@admin.register(ConfiguracionNegociacion)
class ConfiguracionNegociacionAdmin(admin.ModelAdmin):
    list_display = ('id',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
