from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from notificaciones.models import Notificacion


class Command(BaseCommand):
    help = (
        "Depura notificaciones antiguas para optimizar el rendimiento y espacio en la base de datos (HU-A16).\n"
        "Por defecto elimina notificaciones marcadas como leídas con más de 90 días de antigüedad."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Número de días de antigüedad mínima para depurar (default: 90)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            dest='all',
            default=False,
            help='Elimina todas las notificaciones antiguas sin importar si fueron leídas o no'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Simula la depuración e informa cuántos registros se eliminarían sin aplicar cambios'
        )

    def handle(self, *args, **options):
        days = options['days']
        include_unread = options['all']
        dry_run = options['dry_run']

        if days < 0:
            self.stderr.write(self.style.ERROR("El parámetro --days debe ser un entero positivo o cero."))
            return

        cutoff = timezone.now() - timedelta(days=days)
        qs = Notificacion.objects.filter(fecha__lt=cutoff)

        if not include_unread:
            qs = qs.filter(leida=True)

        total_a_eliminar = qs.count()
        filtro_desc = "todas las notificaciones" if include_unread else "notificaciones leídas"

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY-RUN] Se encontraron {total_a_eliminar} {filtro_desc} con más de {days} días de antigüedad (anteriores a {cutoff:%Y-%m-%d %H:%M:%S}). Ningún registro fue eliminado."
                )
            )
            return

        if total_a_eliminar == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No hay {filtro_desc} con más de {days} días de antigüedad para eliminar."
                )
            )
            return

        with transaction.atomic():
            deleted_count, _ = qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] Se eliminaron exitosamente {deleted_count} {filtro_desc} con más de {days} días de antigüedad (anteriores a {cutoff:%Y-%m-%d %H:%M:%S})."
            )
        )
