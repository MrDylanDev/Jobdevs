from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

# El admin nativo queda fuera de i18n_patterns: /django-admin/ no lleva prefijo.
urlpatterns = [
    path('django-admin/', admin.site.urls),
]

# Todo el contenido vive detrás del idioma: español en /, inglés en /en/.
urlpatterns += i18n_patterns(
    # Módulos de Aplicación (Modularizados)
    path('', include('usuarios.urls')), 
    path('proyectos/', include('proyectos.urls')),
    path('postulaciones/', include('postulaciones.urls')),
    path('contrataciones/', include('contrataciones.urls')),
    path('avances/', include('avances.urls')),
    path('mensajes/', include('mensajes.urls')),
    path('notificaciones/', include('notificaciones.urls')),
    path('logs/', include('logs.urls')),
    path('favoritos/', include('favoritos.urls')),
    path('disputas/', include('disputas.urls')),
    
    # Admin → redirige al dashboard custom
    path('admin/', RedirectView.as_view(url='/admin/dashboard/', permanent=False)),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if 'django_browser_reload' in settings.INSTALLED_APPS:
        urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]
