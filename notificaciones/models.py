from django.db import models
from usuarios.models import Usuario

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('postulacion', 'Postulación'),
        ('avance', 'Avance'),
        ('aprobacion', 'Aprobación'),
        ('mensaje', 'Mensaje'),
        ('alerta', 'Alerta'),
        ('otro', 'Otro'),
    ]
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mis_notificaciones')
    proyecto = models.ForeignKey('proyectos.Proyecto', on_delete=models.CASCADE, null=True, blank=True, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='otro')
    mensaje = models.TextField()
    leida = models.BooleanField(default=False) 
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificaciones'
        verbose_name_plural = "Notificaciones"
        indexes = [
            models.Index(fields=['usuario', 'leida'], name='idx_notif_usr_leida'),
            models.Index(fields=['usuario', '-fecha'], name='idx_notif_usr_fecha'),
        ]


    def __str__(self):
        return f"{self.tipo} - {self.usuario.username}"
