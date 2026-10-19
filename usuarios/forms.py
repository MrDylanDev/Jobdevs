from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario, PerfilEmpresa, PerfilDesarrollador, FichaSena
from datetime import date
from .services_sena import verificar_desarrollador_automatico

class RegistroUsuarioForm(UserCreationForm):
    nombre = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Completo'}),
        label="Nombre Completo"
    )
    tipo_documento = forms.ChoiceField(
        choices=[
            ('cedula', 'Cédula de Ciudadanía'),
            ('nit', 'NIT (Número de Identificación Tributaria)'),
        ],
        required=True,
        initial='cedula',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_tipo_documento'})
    )
    identificacion = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de documento'}),
        label="Número de Identificación"
    )
    email = forms.EmailField(required=True)
    fecha_nacimiento = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Fecha de Nacimiento"
    )
    rol = forms.ChoiceField(
        choices=[
            ('desarrollador', 'Desarrollador'),
            ('empresa', 'Empresa'),
        ],
        required=True
    )
    ficha = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de Ficha SENA (ej: 2670123)'}),
        label="Ficha SENA (Opcional)"
    )
    programa_formacion = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Programa de formación (ADSO, etc)'}),
        label="Programa de Formación (Opcional)"
    )
    sector = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sector (ej: Tecnología, Salud)'}),
        label="Sector Empresarial (Opcional)"
    )
    ciudad = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad (ej: Bogotá, Medellín)'}),
        label="Ciudad de Operación (Opcional)"
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.HiddenInput(),
        label="Nombre de Usuario (Opcional)"
    )
    
    class Meta:
        model = Usuario
        fields = ('nombre', 'identificacion', 'email', 'fecha_nacimiento', 'rol')
    
    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get('rol')
        tipo_doc = cleaned_data.get('tipo_documento')

        if rol == 'desarrollador' and tipo_doc == 'nit':
            self.add_error('tipo_documento', "Un desarrollador solo puede registrarse con Cédula.")

        email = cleaned_data.get('email')
        username = (cleaned_data.get('username') or '').strip()
        if not username and email:
            cleaned_data['username'] = email.strip().lower()
        
        return cleaned_data

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email and Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo electrónico ya se encuentra registrado.")
        return email

    def clean_identificacion(self):
        identificacion = (self.cleaned_data.get('identificacion') or '').strip()
        if identificacion and Usuario.objects.filter(identificacion=identificacion).exists():
            raise forms.ValidationError("Este número de identificación/NIT ya se encuentra registrado.")
        return identificacion

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha:
            today = date.today()
            edad = today.year - fecha.year - ((today.month, today.day) < (fecha.month, fecha.day))
            if edad < 18:
                raise forms.ValidationError("Debes ser mayor de edad (18 años) para registrarte en la plataforma.")
        return fecha

    def save(self, commit=True):
        user = super().save(commit=False)
        email = (self.cleaned_data.get('email') or '').strip().lower()
        username = (self.cleaned_data.get('username') or '').strip()
        user.email = email
        user.username = username if username else email
        user.nombre = self.cleaned_data['nombre']
        user.identificacion = self.cleaned_data['identificacion']
        user.rol = self.cleaned_data['rol']
        user.fecha_nacimiento = self.cleaned_data['fecha_nacimiento']
        
        if commit:
            user.save()
            
            # Crear perfil según el rol seleccionado
            if user.rol == 'empresa':
                perfil, _ = PerfilEmpresa.objects.get_or_create(usuario=user)
                sector = (self.cleaned_data.get('sector') or '').strip()
                ciudad = (self.cleaned_data.get('ciudad') or '').strip()
                if sector:
                    perfil.sector = sector
                if ciudad:
                    perfil.ciudad = ciudad
                if not perfil.nombre_empresa:
                    perfil.nombre_empresa = user.nombre
                perfil.save()
            elif user.rol == 'desarrollador':
                perfil, _ = PerfilDesarrollador.objects.get_or_create(usuario=user)
                ficha = (self.cleaned_data.get('ficha') or '').strip()
                programa = (self.cleaned_data.get('programa_formacion') or '').strip()
                if ficha:
                    perfil.ficha = ficha
                    if programa:
                        perfil.programa_formacion = programa
                    perfil.save()
                    verificar_desarrollador_automatico(
                        perfil=perfil,
                        numero_ficha=ficha,
                        programa_formacion=programa,
                        usuario_solicitante=user,
                    )
        
        return user

class PerfilEmpresaForm(forms.ModelForm):
    class Meta:
        model = PerfilEmpresa
        fields = ['nombre_empresa', 'logo', 'sector', 'telefono', 'ciudad', 'descripcion']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la empresa'}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'sector': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sector (ej: Tecnología)'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Breve descripción...'}),
        }

class PerfilDesarrolladorForm(forms.ModelForm):
    class Meta:
        model = PerfilDesarrollador
        fields = ['foto_perfil', 'telefono', 'programa_formacion', 'ficha', 'habilidades', 'portafolio_url']
        widgets = {
            'foto_perfil': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono de contacto (ej: 3001234567)'}),
            'portafolio_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://github.com/tu-usuario'}),
            'programa_formacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Programa de formación (ADSO, etc)'}),
            'ficha': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de Ficha'}),
            'habilidades': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Lista tus habilidades (ej: Python, Java, SQL...)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # SCRUM-171: Si el desarrollador ya está verificado o en revisión, bloquear ficha y programa de formación
        if self.instance and self.instance.pk and self.instance.estado_verificacion in ('verificado', 'en_revision'):
            self.fields['ficha'].disabled = True
            self.fields['programa_formacion'].disabled = True

    def clean_ficha(self):
        if self.instance and self.instance.pk and self.instance.estado_verificacion in ('verificado', 'en_revision'):
            return self.instance.ficha
        return (self.cleaned_data.get('ficha') or '').strip()

    def clean_programa_formacion(self):
        if self.instance and self.instance.pk and self.instance.estado_verificacion in ('verificado', 'en_revision'):
            return self.instance.programa_formacion
        return (self.cleaned_data.get('programa_formacion') or '').strip()

    def save(self, commit=True):
        # Concurrencia segura: preservar ficha y programa si el registro en DB está protegido
        if self.instance and self.instance.pk:
            from django.db import transaction
            with transaction.atomic():
                actual = PerfilDesarrollador.objects.select_for_update().get(pk=self.instance.pk)
                if actual.estado_verificacion in ('verificado', 'en_revision'):
                    self.instance.ficha = actual.ficha
                    self.instance.programa_formacion = actual.programa_formacion
                    self.instance.estado_verificacion = actual.estado_verificacion
        return super().save(commit=commit)

