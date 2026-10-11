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
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil_empresa', db_column='usuario_id')
    nombre_empresa = models.CharField(max_length=200, blank=True, null=True)
    sector = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to='perfiles/empresas/', blank=True, null=True)
    calificacion_promedio = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    def __str__(self):
        return self.nombre_empresa or f"Empresa {self.usuario.username}"

    class Meta:
        db_table = 'perfil_empresa'

class PerfilDesarrollador(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil_desarrollador', db_column='usuario_id')
    programa_formacion = models.CharField(max_length=200, blank=True, null=True)
    ficha = models.CharField(max_length=50, blank=True, null=True)
    habilidades = models.TextField(blank=True, null=True)
    foto_perfil = models.ImageField(upload_to='perfiles/devs/', blank=True, null=True)
    portafolio_url = models.URLField(max_length=500, blank=True, null=True)
    calificacion_promedio = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    num_proyectos_completados = models.IntegerField(default=0)

    def __str__(self):
        return f"Desarrollador {self.usuario.username}"

    class Meta:
        db_table = 'perfil_desarrollador'
