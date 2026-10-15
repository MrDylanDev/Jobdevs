from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager

class UsuarioQuerySet(models.QuerySet):
    def update(self, **kwargs):
        """Sincroniza is_superuser cuando se cambia el rol via update().

        QuerySet.update() bypasea save(), por lo que sin esto un cambio de rol
        via .update(rol='empresa') dejaría is_superuser en True.
        """
        if 'rol' in kwargs:
            kwargs['is_superuser'] = (kwargs['rol'] == 'administrador')
        return super().update(**kwargs)


class UsuarioManager(UserManager):
    def get_queryset(self):
        return UsuarioQuerySet(self.model, using=self._db)


class Usuario(AbstractUser):
    # Campos heredados de AbstractUser que desactivamos para limpiar la DB
    first_name = None
    last_name = None

    # Campos base de MySQL
    nombre = models.CharField(max_length=150)
    identificacion = models.CharField(max_length=20, unique=True, null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    email = models.EmailField(max_length=150, unique=True)
    
    rol = models.CharField(
        max_length=20,
        choices=[
            ('empresa', 'Empresa'),
            ('desarrollador', 'Desarrollador'),
            ('administrador', 'Administrador'),
        ],
        default='desarrollador'
    )
    estado = models.CharField(
        max_length=20,
        choices=[
            ('activo', 'Activo'),
            ('inactivo', 'Inactivo'),
            ('suspendido', 'Suspendido'),
        ],
        default='activo'
    )
    
    # Campos técnicos para recuperación y seguridad
    token_recuperacion = models.CharField(max_length=255, null=True, blank=True)
    token_expiracion = models.DateTimeField(null=True, blank=True)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_por_intentos = models.BooleanField(default=False)

    objects = UsuarioManager()

    def save(self, *args, **kwargs):
        # Sincronizar is_superuser con el rol: True solo si es administrador,
        # False en cualquier otro caso (evita que ex-admins conserven acceso elevado)
        self.is_superuser = (self.rol == 'administrador')
        super().save(*args, **kwargs)

    @property
    def is_staff(self):
        """Django Admin requiere is_staff=True. Lo mapeamos al is_superuser existente."""
        return self.is_superuser

    @is_staff.setter
    def is_staff(self, value):
        """Permite que create_user() y el ORM seteen is_staff."""
        self.is_superuser = value

    REQUIRED_FIELDS = ['email', 'nombre', 'rol']

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"

    class Meta:
        db_table = 'usuarios'

class PerfilEmpresa(models.Model):
    TIPO_PERSONA_CHOICES = [
        ('juridica', 'Persona Jurídica (Empresa)'),
        ('natural', 'Persona Natural / Negocio'),
    ]
    TIPO_DOCUMENTO_CHOICES = [
        ('NIT', 'NIT'),
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
    ]
    ESTADO_VERIFICACION_CHOICES = [
        ('sin_verificar', 'Sin Verificar'),
        ('en_revision', 'En Revisión'),
        ('verificada', 'Verificada'),
        ('rechazada', 'Rechazada'),
    ]

    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil_empresa', db_column='usuario_id')
    nombre_empresa = models.CharField(max_length=200, blank=True, null=True)
    sector = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to='perfiles/empresas/', blank=True, null=True)
    calificacion_promedio = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    # Verificación de identidad
    tipo_persona = models.CharField(max_length=20, choices=TIPO_PERSONA_CHOICES, default='juridica')
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES, default='NIT')
    numero_documento = models.CharField(max_length=30, blank=True, null=True)
    digito_verificacion = models.CharField(max_length=2, blank=True, null=True)
    razon_social = models.CharField(max_length=255, blank=True, null=True)
    documento_soporte = models.FileField(upload_to='verificaciones/empresas/', blank=True, null=True)
    estado_verificacion = models.CharField(
        max_length=20, choices=ESTADO_VERIFICACION_CHOICES, default='sin_verificar'
    )
    fecha_solicitud_verificacion = models.DateTimeField(null=True, blank=True)
    fecha_verificacion = models.DateTimeField(null=True, blank=True)
    verificado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='empresas_verificadas',
    )
    notas_auditoria = models.TextField(blank=True, null=True)

    @property
    def es_verificada(self):
        return self.estado_verificacion == 'verificada'

    @property
    def documento_completo(self):
        """Documento con dígito de verificación, p. ej. '900123456-7'."""
        if not self.numero_documento:
            return ''
        if self.digito_verificacion not in (None, ''):
            return f"{self.numero_documento}-{self.digito_verificacion}"
        return self.numero_documento

    @property
    def badge_info(self):
        """Etiqueta y clase CSS de la insignia según estado y tipo de persona."""
        if self.estado_verificacion == 'verificada':
            if self.tipo_persona == 'natural':
                return {'label': 'Negocio Verificado', 'css_class': 'badge-verificada'}
            return {'label': 'Empresa Verificada', 'css_class': 'badge-verificada'}
        if self.estado_verificacion == 'en_revision':
            return {'label': 'En Revisión', 'css_class': 'badge-en-revision'}
        if self.estado_verificacion == 'rechazada':
            return {'label': 'Verificación Rechazada', 'css_class': 'badge-rechazada'}
        return {'label': 'Sin Verificar', 'css_class': 'badge-sin-verificar'}

    def __str__(self):
        return self.nombre_empresa or f"Empresa {self.usuario.username}"

    class Meta:
        db_table = 'perfil_empresa'

class FichaSena(models.Model):
    numero_ficha = models.CharField(max_length=50, unique=True, db_index=True)
    programa_formacion = models.CharField(max_length=200)
    regional = models.CharField(max_length=100, blank=True, null=True)
    centro_formacion = models.CharField(max_length=200, blank=True, null=True)
    activa = models.BooleanField(default=True, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creada_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fichas_creadas'
    )

    def __str__(self):
        return f"{self.numero_ficha} - {self.programa_formacion}"

    class Meta:
        db_table = 'fichas_sena'
        verbose_name = 'Ficha SENA'
        verbose_name_plural = 'Fichas SENA'
        ordering = ['numero_ficha']


class PerfilDesarrollador(models.Model):
    CONDICION_SENA_CHOICES = [
        ('aprendiz', 'Aprendiz en Formación'),
        ('egresado', 'Egresado SENA'),
    ]
    ESTADO_VERIFICACION_CHOICES = [
        ('sin_verificar', 'Sin Verificar'),
        ('en_revision', 'En Revisión'),
        ('verificado', 'Verificado SENA'),
        ('rechazado', 'Rechazado'),
    ]

    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil_desarrollador', db_column='usuario_id')
    condicion_sena = models.CharField(
        max_length=20, choices=CONDICION_SENA_CHOICES, default='aprendiz'
    )
    programa_formacion = models.CharField(max_length=200, blank=True, null=True)
    ficha = models.CharField(max_length=50, blank=True, null=True)
    habilidades = models.TextField(blank=True, null=True)
    foto_perfil = models.ImageField(upload_to='perfiles/devs/', blank=True, null=True)
    portafolio_url = models.URLField(max_length=500, blank=True, null=True)
    calificacion_promedio = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    num_proyectos_completados = models.IntegerField(default=0)

    # Verificación de identidad SENA
    estado_verificacion = models.CharField(
        max_length=20, choices=ESTADO_VERIFICACION_CHOICES, default='sin_verificar'
    )
    ficha_sena = models.ForeignKey(
        FichaSena, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='aprendices_verificados'
    )
    documento_soporte = models.FileField(upload_to='verificaciones/desarrolladores/', blank=True, null=True)
    fecha_solicitud_verificacion = models.DateTimeField(null=True, blank=True)
    fecha_verificacion = models.DateTimeField(null=True, blank=True)
    verificado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='desarrolladores_verificados'
    )
    notas_auditoria = models.TextField(blank=True, null=True)

    @property
    def es_verificado_sena(self):
        return self.estado_verificacion == 'verificado'

    @property
    def badge_info(self):
        """Etiqueta y clase CSS de la insignia según estado y condición SENA."""
        if self.estado_verificacion == 'verificado':
            if self.condicion_sena == 'egresado':
                return {'label': 'Egresado SENA', 'css_class': 'badge-verificada'}
            return {'label': 'Aprendiz SENA', 'css_class': 'badge-verificada'}
        if self.estado_verificacion == 'en_revision':
            if self.condicion_sena == 'egresado':
                return {'label': 'En Revisión (Egresado)', 'css_class': 'badge-en-revision'}
            return {'label': 'En Revisión SENA', 'css_class': 'badge-en-revision'}
        if self.estado_verificacion == 'rechazado':
            return {'label': 'Verificación Rechazada', 'css_class': 'badge-rechazada'}
        return {'label': 'Sin Verificar', 'css_class': 'badge-sin-verificar'}

    def __str__(self):
        return f"Desarrollador {self.usuario.username}"

    class Meta:
        db_table = 'perfil_desarrollador'
