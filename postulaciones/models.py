from django.db import models
from usuarios.models import Usuario
from proyectos.models import Proyecto

class Postulacion(models.Model):
    ESTADO = [
        ('pendiente', 'Pendiente'),
        ('en_negociacion', 'En Negociación'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name='postulaciones')
    desarrollador = models.ForeignKey(Usuario, on_delete=models.PROTECT, limit_choices_to={'rol': 'desarrollador'}, related_name='mis_postulaciones')
    mensaje = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=25, choices=ESTADO, default='pendiente')
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_limite_negociacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'postulaciones'
        unique_together = ('proyecto', 'desarrollador')

    def __str__(self):
        return f"{self.desarrollador.username} - {self.proyecto.titulo}"
