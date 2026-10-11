from django.db import models
from usuarios.models import Usuario
from proyectos.models import Proyecto

class Contratacion(models.Model):
    ESTADO = [
        ('activa', 'Activa'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='contrataciones')
    desarrollador = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='contrataciones_dev')
    empresa = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='contrataciones_emp')
    fecha_inicio = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=25, choices=ESTADO, default='activa')

    class Meta:
        db_table = 'contrataciones'
        unique_together = ('proyecto', 'desarrollador')
        indexes = [
            models.Index(fields=['proyecto', 'desarrollador', 'estado'], name='idx_proy_dev_est'),
            models.Index(fields=['empresa'], name='idx_empresa_contratos'),
        ]

    def __str__(self):
        return f"Contrato: {self.proyecto.titulo}"
