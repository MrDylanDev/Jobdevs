from django.contrib import admin

from .models import Favorito


@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ('id', 'desarrollador', 'proyecto', 'fecha')
    list_filter = ('fecha',)
    search_fields = ('desarrollador__username', 'proyecto__titulo')
