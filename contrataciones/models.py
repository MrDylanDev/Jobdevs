import hashlib
from decimal import Decimal

from django.db import models
from usuarios.models import Usuario
from proyectos.models import Proyecto

class ContratacionManager(models.Manager):
    def desarrolladores_activos(self, proyecto):
        """Retorna queryset de Usuarios con contratación activa en el proyecto."""
        from usuarios.models import Usuario
        return Usuario.objects.filter(
            id__in=self.filter(proyecto=proyecto, estado='activa').values_list('desarrollador_id', flat=True)
        )


class Contratacion(models.Model):
    ESTADO = [
        ('activa', 'Activa'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
        ('en_disputa', 'En Disputa'),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name='contrataciones')
    desarrollador = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='contrataciones_dev')
    empresa = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='contrataciones_emp')
    fecha_inicio = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=25, choices=ESTADO, default='activa')

    objects = ContratacionManager()

    class Meta:
        db_table = 'contrataciones'
        unique_together = ('proyecto', 'desarrollador')
        indexes = [
            models.Index(fields=['proyecto', 'desarrollador', 'estado'], name='idx_proy_dev_est'),
            models.Index(fields=['empresa'], name='idx_empresa_contratos'),
            # RNF-10: dashboards por empresa filtrando contratos activos
            models.Index(fields=['empresa', 'estado'], name='idx_contratos_empresa_estado'),
        ]

    def __str__(self):
        return f"Contrato: {self.proyecto.titulo}"



class ContratoDigital(models.Model):
    ESTADO_CONTRATO = [
        ('borrador', 'Borrador'),
        ('pendiente_firma', 'Pendiente de Firma'),
        ('firmado', 'Firmado'),
        ('rechazado', 'Rechazado'),
        ('expirado', 'Expirado'),
    ]
    MONEDAS = [('COP', 'COP'), ('USD', 'USD')]
    FORMAS_PAGO = [
        ('unico_finalizar', 'Pago único al finalizar'),
        ('por_hito', 'Pago por hito completado'),
        ('mensual', 'Pago mensual'),
    ]

    postulacion = models.OneToOneField(
        'postulaciones.Postulacion', on_delete=models.CASCADE, related_name='contrato_digital')
    contratacion = models.OneToOneField(
        'contrataciones.Contratacion', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contrato_digital')

    # Términos y condiciones
    monto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    moneda = models.CharField(max_length=5, choices=MONEDAS, default='COP')
    forma_pago = models.CharField(max_length=30, choices=FORMAS_PAGO, default='por_hito')
    clausulas = models.TextField(default=(
        "1. OBJETO: El desarrollador se compromete a realizar las actividades acordadas para el proyecto. "
        "2. ENTREGABLES: Los avances deberán registrarse con evidencias verificables. "
        "3. PAGO: La empresa se compromete a liquidar el monto acordado según la forma de pago establecida. "
        "4. CONFIDENCIALIDAD: La información compartida es de carácter privado."
    ))
    comentarios_adicionales = models.TextField(blank=True, default='')
    disclaimer = models.TextField(default=(
        "Este contrato digital es un acuerdo de voluntades. "
        "La plataforma no procesa pagos ni reemplaza un contrato laboral formal."
    ))

    estado = models.CharField(max_length=30, choices=ESTADO_CONTRATO, default='borrador')

    # Firmas digitales y hash
    firmado_empresa = models.BooleanField(default=False)
    fecha_firma_empresa = models.DateTimeField(null=True, blank=True)
    firmado_desarrollador = models.BooleanField(default=False)
    fecha_firma_desarrollador = models.DateTimeField(null=True, blank=True)
    hash_contrato = models.CharField(max_length=64, blank=True, null=True, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contratos_digitales'

    def __str__(self):
        return f"Contrato digital #{self.pk} - postulación {self.postulacion_id} ({self.estado})"

    def calcular_hash(self) -> str:
        """SHA-256 determinista de los datos clave del contrato."""
        postulacion = self.postulacion
        partes = [
            str(postulacion.pk),
            str(postulacion.proyecto_id),
            str(postulacion.proyecto.empresa_id),
            str(postulacion.desarrollador_id),
            f"{Decimal(str(self.monto)):.2f}" if self.monto is not None else '',
            self.moneda,
            self.forma_pago,
            self.clausulas,
            self.fecha_firma_empresa.isoformat() if self.fecha_firma_empresa else '',
            self.fecha_firma_desarrollador.isoformat() if self.fecha_firma_desarrollador else '',
        ]
        return hashlib.sha256('|'.join(partes).encode('utf-8')).hexdigest()

    @property
    def esta_firmado(self) -> bool:
        return self.firmado_empresa and self.firmado_desarrollador

    @property
    def monto_formateado(self) -> str:
        """Formatea el monto según la moneda seleccionada (COP o USD) respetando las convenciones financieras (SCRUM-202)."""
        if self.monto is None:
            return "$ 0 COP" if self.moneda == 'COP' else "$ 0.00 USD"
        m = Decimal(str(self.monto))
        if self.moneda == 'COP':
            if m % 1 == 0:
                entero = int(m)
                return f"$ {entero:,} COP".replace(",", ".")
            else:
                partes = f"{m:,.2f}".split(".")
                entero = partes[0].replace(",", ".")
                decimal = partes[1]
                return f"$ {entero},{decimal} COP"
        elif self.moneda == 'USD':
            return f"$ {m:,.2f} USD"
        return f"$ {m:,.2f} {self.moneda}"
