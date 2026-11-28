from django.db import models

from proyectos.models import Proyecto
from usuarios.models import Usuario


class Favorito(models.Model):
    desarrollador = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'desarrollador'}, related_name='favoritos')
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='favoritos')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'favoritos'
        unique_together = ('desarrollador', 'proyecto')

    def __str__(self):
        return f"{self.desarrollador.username} -> {self.proyecto.titulo}"
