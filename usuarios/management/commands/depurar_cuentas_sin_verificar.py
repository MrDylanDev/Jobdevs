"""Depura cuentas sin verificar que superaron el plazo en Modo Piloto.

Uso:
    python manage.py depurar_cuentas_sin_verificar
    python manage.py depurar_cuentas_sin_verificar --dias 3
"""

from django.core.management.base import BaseCommand

from usuarios.services_sena import depurar_cuentas_sin_verificar


class Command(BaseCommand):
    help = "Depura cuentas sin verificar tras superar los días límite en Modo Piloto."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=None,
            help='Sobrescribe temporalmente el límite de días sin verificar.',
        )

    def handle(self, *args, **options):
        resultado = depurar_cuentas_sin_verificar(dias_limite=options.get('dias'))
        if not resultado.get('ejecutado'):
            self.stdout.write(
                self.style.WARNING(
                    f"Depuración omitida (motivo: {resultado.get('motivo', 'no_piloto')})."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Depuración completada: {resultado['eliminados']} eliminadas, "
                f"{resultado['desactivados']} desactivadas."
            )
        )
