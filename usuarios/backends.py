from django.contrib.auth.backends import ModelBackend


class UsuarioAuthBackend(ModelBackend):
    """
    Backend de autenticación que valida credenciales permitiendo usuarios con is_active=False.
    Esto permite que `login_view` reciba el usuario tras una única comprobación criptográfica (PBKDF2)
    y gestione el bloqueo/inactividad sin necesidad de re-hashear la contraseña en un segundo paso.
    """
    def user_can_authenticate(self, user):
        return True
