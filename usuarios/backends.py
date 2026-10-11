from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class UsuarioAuthBackend(ModelBackend):
    """
    Backend de autenticación que valida credenciales en un único cómputo hash.
    En authenticate(), retorna el objeto Usuario si la contraseña es correcta, incluso si
    is_active=False, permitiendo que `login_view` verifique el estado sin re-hashear.
    En get_user() (restauración de sesión), rechaza usuarios inactivos o suspendidos
    para que pierdan acceso inmediato a vistas protegidas.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
            return None
        else:
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
