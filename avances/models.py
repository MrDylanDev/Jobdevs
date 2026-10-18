from django.db import models
from django.core.validators import URLValidator
from usuarios.models import Usuario
from proyectos.models import Proyecto

class Avance(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente de Revisión'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='avances')
    desarrollador = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'desarrollador'}, related_name='avances_realizados')
    entregable = models.ForeignKey('proyectos.Entregable', on_delete=models.CASCADE, db_column='entregable_id')
    descripcion = models.TextField()
    archivo_url = models.URLField(max_length=500, blank=True, null=True, validators=[URLValidator(schemes=['http', 'https'])])
    archivo_adjunto = models.FileField(upload_to='avances/archivos/', blank=True, null=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    comentario_revision = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'avances'

    def __str__(self):
        return f"Avance: {self.entregable.titulo} - {self.proyecto.titulo}"
