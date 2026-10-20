import os
import zipfile
from PIL import Image
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from .models import Avance
from proyectos.models import Proyecto, Entregable
from contrataciones.models import Contratacion
from notificaciones.models import Notificacion

EXTENSIONES_PERMITIDAS = {'.pdf', '.zip', '.png', '.jpg', '.jpeg'}
MAX_AVANCE_BYTES = 10 * 1024 * 1024  # 10 MB


def _validar_archivo_adjunto(archivo):
    """Valida tamaño, extensión, cabecera mágica y consistencia estructural (SCRUM-168)."""
    if not archivo:
        return None
    if archivo.size > MAX_AVANCE_BYTES:
        return "El archivo adjunto no puede superar los 10 MB."

    _, ext = os.path.splitext(archivo.name.lower())
    if ext not in EXTENSIONES_PERMITIDAS:
        return f"Tipo de archivo no permitido ({ext}). Solo se admiten archivos PDF, ZIP, PNG y JPG."

    cabecera = archivo.read(16)
    archivo.seek(0)

    if ext == '.pdf':
        if not cabecera.startswith(b'%PDF-'):
            return "El archivo no es un documento PDF válido."
    elif ext == '.zip':
        if not (cabecera.startswith(b'PK\x03\x04') or cabecera.startswith(b'PK\x05\x06')):
            return "El archivo no es un archivo ZIP válido."
        if not zipfile.is_zipfile(archivo):
            return "El archivo no es un archivo ZIP válido o está dañado."
        archivo.seek(0)
    elif ext in ('.png', '.jpg', '.jpeg'):
        if ext == '.png' and not cabecera.startswith(b'\x89PNG\r\n\x1a\n'):
            return "El archivo no es una imagen PNG válida."
        if ext in ('.jpg', '.jpeg') and not cabecera.startswith(b'\xff\xd8\xff'):
            return "El archivo no es una imagen JPG válida."
        try:
            with Image.open(archivo) as img:
                img.verify()
        except Exception:
            return f"El archivo no es una imagen {ext[1:].upper()} válida o está dañada."
        finally:
            archivo.seek(0)

    return None

@login_required
def registrar_avance(request, proyecto_id):
    if request.user.rol != 'desarrollador':
        messages.error(request, "Solo los desarrolladores pueden registrar avances.")
        return redirect('inicio')
    
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    
    # 1. Verificar el estado del proyecto: 
    # Solo se permiten avances en proyectos 'en_desarrollo' o 'en_revision' (si hay hitos pendientes)
    hitos_pendientes_count = Entregable.objects.filter(proyecto=proyecto, estado='pendiente').count()

    if proyecto.estado == 'en_revision' and hitos_pendientes_count > 0:
        # Corrección automática: El proyecto está en revisión pero tiene trabajo pendiente
        estado_anterior = proyecto.estado
        proyecto.estado = 'en_desarrollo'
        proyecto.save()
        proyecto.registrar_cambio_estado('en_desarrollo', request.user, estado_anterior=estado_anterior)
    elif proyecto.estado != 'en_desarrollo':
        messages.warning(request, f"Ya no puedes subir más avances para el proyecto '{proyecto.titulo}', pues ya no se encuentra en estado de desarrollo.")
        return redirect(reverse('dashboard_desarrollador') + '?section=activos')

    # 2. Verificar que el desarrollador está contratado para este proyecto
    contratado = Contratacion.objects.filter(proyecto=proyecto, desarrollador=request.user, estado='activa').exists()
    if not contratado:
        messages.error(request, "No tienes un contrato activo para este proyecto.")
        return redirect(reverse('dashboard_desarrollador') + '?section=activos')

    # 3. SCRUM-205: Verificar si hay hitos pendientes disponibles para el desarrollador
    hitos_pendientes = Entregable.objects.filter(
        Q(proyecto=proyecto) & 
        Q(estado='pendiente') & 
        (Q(equipo__miembros=request.user) | Q(equipo__isnull=True))
    ).distinct()

    if not hitos_pendientes.exists():
        total_hitos = Entregable.objects.filter(proyecto=proyecto).count()
        if total_hitos == 0:
            messages.warning(request, f"El proyecto '{proyecto.titulo}' aún no tiene hitos definidos por la empresa.")
        else:
            messages.info(request, f"Todos los hitos del proyecto '{proyecto.titulo}' ya han sido entregados o están en revisión.")
        return redirect(reverse('dashboard_desarrollador') + '?section=activos')

    if request.method == 'POST':
        try:
            descripcion = request.POST.get('descripcion')
            archivo_url = (request.POST.get('archivo_url') or '').strip()
            archivo_adjunto = request.FILES.get('archivo_adjunto')
            entregable_id = request.POST.get('entregable_id')
            
            if not archivo_url and not archivo_adjunto:
                messages.error(request, "Debes proporcionar una URL o adjuntar un archivo de evidencia.")
                return redirect('registrar_avance', proyecto_id=proyecto.id)

            if archivo_url:
                from django.core.validators import URLValidator
                from django.core.exceptions import ValidationError
                url_val = URLValidator(schemes=['http', 'https'])
                try:
                    url_val(archivo_url)
                except ValidationError:
                    messages.error(request, "La URL de evidencia debe ser una dirección web válida (iniciando con http:// o https://).")
                    return redirect('registrar_avance', proyecto_id=proyecto.id)

            if archivo_adjunto:
                error_adjunto = _validar_archivo_adjunto(archivo_adjunto)
                if error_adjunto:
                    messages.error(request, error_adjunto)
                    return redirect('registrar_avance', proyecto_id=proyecto.id)

            if not entregable_id:
                messages.error(request, "Debes seleccionar un hito para registrar el avance.")
                return redirect('registrar_avance', proyecto_id=proyecto.id)

            entregable = get_object_or_404(Entregable, id=entregable_id, proyecto=proyecto)

            if entregable.estado != 'pendiente':
                messages.error(request, f"El hito '{entregable.titulo}' ya no se encuentra pendiente y no admite nuevos avances.")
                return redirect('registrar_avance', proyecto_id=proyecto.id)

            with transaction.atomic():
                # Bloquear el proyecto para evitar condiciones de carrera
                proyecto = Proyecto.objects.select_for_update().get(id=proyecto_id)

                # Re-verificar estado dentro de la transacción
                hitos_pendientes_count = Entregable.objects.filter(proyecto=proyecto, estado='pendiente').count()

                if proyecto.estado == 'en_revision' and hitos_pendientes_count > 0:
                    estado_anterior = proyecto.estado
                    proyecto.estado = 'en_desarrollo'
                    proyecto.save()
                    proyecto.registrar_cambio_estado('en_desarrollo', request.user, estado_anterior=estado_anterior)
                elif proyecto.estado != 'en_desarrollo':
                    raise Exception(f"El proyecto '{proyecto.titulo}' ya no se encuentra en estado de desarrollo.")

                # 1. Crear el Avance
                avance = Avance.objects.create(
                    proyecto=proyecto,
                    desarrollador=request.user,
                    entregable=entregable,
                    descripcion=descripcion,
                    archivo_url=archivo_url or None,
                    archivo_adjunto=archivo_adjunto,
                    estado='pendiente'
                )

                # 2. Actualizar el Hito
                entregable.estado = 'en_revision'
                entregable.save()

                # 3. Notificar a la Empresa
                Notificacion.objects.create(
                    usuario=proyecto.empresa,
                    proyecto=proyecto,
                    tipo='avance',
                    mensaje=f"{request.user.nombre or request.user.username} completó el hito '{entregable.titulo}' en el proyecto: {proyecto.titulo}"
                )

                # 4. Verificar si quedan hitos pendientes para cierre automático del proyecto
                hitos_restantes = Entregable.objects.filter(proyecto=proyecto, estado='pendiente').count()
                
                if hitos_restantes == 0:
                    estado_anterior = proyecto.estado
                    proyecto.estado = 'en_revision'
                    proyecto.save()
                    # Auditoría de estado
                    proyecto.registrar_cambio_estado('en_revision', request.user, estado_anterior=estado_anterior)
                    messages.info(request, "¡Felicidades! Has enviado el último hito. El proyecto ha pasado a Revisión Final.")

            messages.success(request, "¡Hito completado y avance registrado exitosamente!")
            return redirect(reverse('dashboard_desarrollador') + '?section=activos')
        except Exception as e:
            messages.error(request, f"Error al registrar avance: {str(e)}")

    # Obtener hitos pendientes filtrados por equipo o generales
    hitos_pendientes = Entregable.objects.filter(
        Q(proyecto=proyecto) & 
        Q(estado='pendiente') & 
        (Q(equipo__miembros=request.user) | Q(equipo__isnull=True))
    ).distinct()

    return render(request, 'avances/registrar.html', {
        'proyecto': proyecto,
        'hitos_pendientes': hitos_pendientes
    })

@login_required
@require_POST
def revisar_avance(request, avance_id):
    if request.user.rol != 'empresa':
        messages.error(request, "Solo las empresas pueden revisar avances.")
        return redirect('inicio')
    
    avance = get_object_or_404(Avance, id=avance_id, proyecto__empresa=request.user)
    
    if request.method == 'POST':
        accion = request.POST.get('accion') 
        comentario = request.POST.get('comentario', '') 
        
        if accion in ['aceptar', 'rechazar']:
            if accion == 'rechazar' and not comentario.strip():
                messages.error(request, "Debes escribir un comentario explicando por qué rechazas el avance.")
                return redirect('ver_avances', proyecto_id=avance.proyecto.id)
            try:
                with transaction.atomic():
                    if accion == 'aceptar':
                        avance.estado = 'aceptado'
                        avance.comentario_revision = comentario
                        avance.save()
                        
                        # Marcar hito como COMPLETADO
                        avance.entregable.estado = 'completado'
                        avance.entregable.save()
                        
                        # Notificar al desarrollador
                        Notificacion.objects.create(
                            usuario=avance.desarrollador,
                            proyecto=avance.proyecto,
                            tipo='aprobacion',
                            mensaje=f"Tu avance en el hito '{avance.entregable.titulo}' ha sido ACEPTADO."
                        )
                        messages.success(request, f"Hito '{avance.entregable.titulo}' aceptado.")
                    else:
                        avance.estado = 'rechazado'
                        avance.comentario_revision = comentario
                        avance.save()

                        # Devolver hito a PENDIENTE
                        # El método save() de Entregable se encargará de devolver el proyecto 
                        # a 'en_desarrollo' si estaba 'en_revision' y registrar la auditoría.
                        avance.entregable.estado = 'pendiente'
                        avance.entregable.save(cambiado_por=request.user)

                        messages.warning(request, f"Hito '{avance.entregable.titulo}' rechazado.")

                        Notificacion.objects.create(
                            usuario=avance.desarrollador,
                            proyecto=avance.proyecto,
                            tipo='alerta',
                            mensaje=f"Tu avance en el hito '{avance.entregable.titulo}' ha sido RECHAZADO. Revisa los comentarios."
                        )
                        messages.warning(request, "Avance rechazado. Se ha notificado al desarrollador y el proyecto ha vuelto a 'En Desarrollo'.")
                
                return redirect('ver_avances', proyecto_id=avance.proyecto.id)
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
                return redirect('ver_avances', proyecto_id=avance.proyecto.id)
    
    return redirect('ver_avances', proyecto_id=avance.proyecto.id)

@login_required
def ver_avances(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    
    # Verificar si el usuario tiene relación con el proyecto (Desarrollador, Empresa, Admin)
    es_admin = request.user.rol == 'administrador'
    es_empresa_duena = (request.user.rol == 'empresa' and proyecto.empresa == request.user)
    es_desarrollador_relacionado = Contratacion.objects.filter(
        proyecto=proyecto, 
        desarrollador=request.user
    ).exists()

    if not (es_admin or es_empresa_duena or es_desarrollador_relacionado):
        messages.error(request, "No tienes permisos para ver los avances de este proyecto.")
        if request.user.rol == 'desarrollador':
            return redirect('dashboard_desarrollador')
        elif request.user.rol == 'empresa':
            return redirect('dashboard_empresa')
        return redirect('inicio')
        
    # Consulta de avances optimizada con select_related
    avances = Avance.objects.filter(proyecto=proyecto).select_related('desarrollador__perfil_desarrollador', 'entregable').order_by('-fecha_hora')
    
    # Obtener el progreso total desde ORM
    progreso = Entregable.objects.filter(proyecto=proyecto).aggregate(
        hitos_completados=Count('id', filter=Q(estado='completado')),
        hitos_totales=Count('id'),
    )
    hitos_completados = progreso['hitos_completados'] or 0
    hitos_totales = progreso['hitos_totales'] or 0

    return render(request, 'avances/ver_lista.html', {
        'proyecto': proyecto, 
        'avances': avances,
        'hitos_completados': hitos_completados,
        'hitos_totales': hitos_totales
    })
