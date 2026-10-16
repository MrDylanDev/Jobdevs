from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

UserModel = get_user_model()


class UsuarioAuthBackend(ModelBackend):
    """
    Backend de autenticación que valida credenciales en un único cómputo hash.
    En authenticate(), acepta correo electrónico (insensible a mayúsculas) o nombre de usuario.
    Retorna el objeto Usuario si la contraseña es correcta, incluso si is_active=False,
    permitiendo que `login_view` verifique el estado sin re-hashear.
    En get_user() (restauración de sesión), rechaza usuarios inactivos o suspendidos
    para que pierdan acceso inmediato a vistas protegidas.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        identificador = username or kwargs.get('email') or kwargs.get(UserModel.USERNAME_FIELD)
        if not identificador or not password:
            return None

        identificador = str(identificador).strip()
        user = None

        # 1. Búsqueda por correo electrónico (insensible a mayúsculas)
        if '@' in identificador:
            user = UserModel.objects.filter(email__iexact=identificador).first()

        # 2. Fallback a username o email
        if not user:
            user = UserModel.objects.filter(
                Q(username__iexact=identificador) | Q(email__iexact=identificador)
            ).first()

        if user is None:
            # Dummy hasher para evitar timing side-channels si no existe el usuario
            UserModel().set_password(password)
            return None

        if user.check_password(password):
            return user
        return None

    def user_can_authenticate(self, user):
        """
        Rechaza usuarios inactivos o suspendidos al restaurar sesiones existentes.
        """
        is_active = getattr(user, 'is_active', True)
        estado = getattr(user, 'estado', 'activo')
        return is_active and (estado not in ('suspendido', 'inactivo'))
