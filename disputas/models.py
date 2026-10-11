from django.db import models

from contrataciones.models import Contratacion
from proyectos.models import Proyecto
from usuarios.models import Usuario


class Disputa(models.Model):
    ESTADO = [
        ('abierta', 'Abierta'),
        ('en_mediacion', 'En Mediación'),
        ('resuelta', 'Resuelta'),
        ('cancelada', 'Cancelada'),
    ]
    RESOLUCION = [
        ('reanudar_proyecto', 'Reanudar Proyecto'),
        ('cancelar_contrato', 'Cancelar Contrato'),
        ('sancionar_empresa', 'Sancionar Empresa'),
        ('sancionar_desarrollador', 'Sancionar Desarrollador'),
    ]

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='disputas')
    contratacion = models.ForeignKey(
        Contratacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='disputas'
    )
    iniciado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='disputas_iniciadas')
    mediador = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='disputas_mediadas'
    )
    motivo = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO, default='abierta')
    resolucion = models.CharField(max_length=30, choices=RESOLUCION, null=True, blank=True)
    notas_resolucion = models.TextField(blank=True, default='')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'disputas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Disputa #{self.pk} - {self.proyecto_id} ({self.get_estado_display()})"


class MensajeDisputa(models.Model):
    disputa = models.ForeignKey(Disputa, on_delete=models.CASCADE, related_name='mensajes')
    emisor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensajes_disputa')
    contenido = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mensajes_disputa'
        ordering = ['fecha_envio']

    def __str__(self):
        return f"Mensaje de {self.emisor_id} en disputa {self.disputa_id}"
