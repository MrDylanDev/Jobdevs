from django.core.management.base import BaseCommand
from postulaciones.services import expirar_negociaciones_vencidas


class Command(BaseCommand):
    help = "Expira negociaciones inactivas que superaron su fecha límite de 7 días y libera cupos (SCRUM-217)."

    def handle(self, *args, **options):
        total = expirar_negociaciones_vencidas()
        self.stdout.write(
            self.style.SUCCESS(f"Se expiraron {total} negociación(es) vencida(s).")
        )
