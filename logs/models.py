from django.db import models
from usuarios.models import Usuario

class LogAuditoria(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=300)
    tabla_afectada = models.CharField(max_length=100, blank=True, null=True)
    registro_id = models.BigIntegerField(blank=True, null=True) 
    valor_anterior = models.TextField(blank=True, null=True)
    valor_nuevo = models.TextField(blank=True, null=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'logs_auditoria'
        verbose_name_plural = "Logs de Auditoría"

    def save(self, *args, **kwargs):
        # SCRUM-179: Truncado defensivo automático para evitar DataError en PostgreSQL
        if self.accion and len(self.accion) > 300:
            self.accion = self.accion[:300]
        if self.tabla_afectada and len(self.tabla_afectada) > 100:
            self.tabla_afectada = self.tabla_afectada[:100]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fecha_hora} - {self.usuario.username if self.usuario else 'Sistema'}: {self.accion}"

class CopiaSeguridad(models.Model):
    ESTADO = [
        ('exitoso', 'Exitoso'),
        ('fallido', 'Fallido'),
        ('pendiente', 'Pendiente'),
    ]
    ejecutado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, db_column='ejecutado_por')
    archivo_url = models.CharField(max_length=500)
    tamano_mb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADO, default='pendiente')

    class Meta:
        db_table = 'copias_seguridad'
        verbose_name_plural = "Copias de Seguridad"

    def __str__(self):
        return f"Backup {self.fecha} - {self.estado}"
