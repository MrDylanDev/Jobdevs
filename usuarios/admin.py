from django.contrib import admin

from .models import PerfilDesarrollador, PerfilEmpresa


@admin.register(PerfilDesarrollador)
class PerfilDesarrolladorAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'programa_formacion', 'ficha', 'calificacion_promedio', 'num_proyectos_completados')
    search_fields = ('usuario__username', 'usuario__nombre', 'programa_formacion', 'ficha')
    list_filter = ('programa_formacion',)


@admin.register(PerfilEmpresa)
class PerfilEmpresaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'nombre_empresa', 'sector', 'ciudad', 'telefono')
    search_fields = ('usuario__username', 'nombre_empresa', 'sector')
    list_filter = ('sector', 'ciudad')
