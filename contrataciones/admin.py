from django.contrib import admin

from .models import Contratacion, ContratoDigital, SolicitudCancelacion


@admin.register(Contratacion)
class ContratacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'proyecto', 'empresa', 'desarrollador', 'estado', 'fecha_inicio')
    list_filter = ('estado', 'fecha_inicio')
    search_fields = ('proyecto__titulo', 'empresa__username', 'desarrollador__username')


@admin.register(ContratoDigital)
class ContratoDigitalAdmin(admin.ModelAdmin):
    list_display = ('id', 'postulacion', 'monto', 'moneda', 'estado', 'firmado_empresa', 'firmado_desarrollador', 'fecha_creacion')
    list_filter = ('estado', 'moneda', 'firmado_empresa', 'firmado_desarrollador')
    search_fields = ('postulacion__proyecto__titulo', 'postulacion__desarrollador__username', 'hash_contrato')

    @staticmethod
    def _esta_firmado(obj):
        return bool(obj and (obj.firmado_empresa or obj.firmado_desarrollador or obj.estado == 'firmado'))

    def get_readonly_fields(self, request, obj=None):
        if self._esta_firmado(obj):
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        if self._esta_firmado(obj):
            return False
        return super().has_delete_permission(request, obj)


@admin.register(SolicitudCancelacion)
class SolicitudCancelacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'contratacion', 'solicitante', 'causal', 'estado', 'fecha_creacion')
    list_filter = ('causal', 'estado', 'fecha_creacion')
    search_fields = ('contratacion__proyecto__titulo', 'solicitante__username', 'motivo')
