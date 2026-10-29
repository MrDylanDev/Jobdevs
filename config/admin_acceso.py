"""Acceso al admin nativo de Django.

El panel custom (`/admin/dashboard/`) es la cara visible de la administración y
se entra por el login de la página. El admin nativo queda como herramienta de
operación y reparación de datos, restringido a **superusuarios**: `is_staff`
solo ya no alcanza, porque la administración de negocio vive en el panel custom.
"""

from types import MethodType

from django.contrib import admin


def _solo_superusuarios(self, request):
    return bool(request.user.is_active and request.user.is_superuser)


def restringir_admin_a_superusuarios():
    """Idempotente: la llama `config/urls.py` al montar las rutas."""
    if getattr(admin.site, '_solo_superusuarios', False):
        return
    admin.site.has_permission = MethodType(_solo_superusuarios, admin.site)
    admin.site._solo_superusuarios = True
