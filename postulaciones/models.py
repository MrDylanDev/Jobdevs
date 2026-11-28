from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from proyectos.models import Proyecto
from usuarios.models import Usuario


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


class ConfiguracionNegociacion(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    plazo_dias = models.PositiveSmallIntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_negociacion'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(id=1),
                name='configuracion_negociacion_singleton',
            ),
            models.CheckConstraint(
                condition=models.Q(plazo_dias__gte=1, plazo_dias__lte=30),
                name='configuracion_negociacion_plazo_1_30',
            ),
        ]
