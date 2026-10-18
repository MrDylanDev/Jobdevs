from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from usuarios.models import Usuario, PerfilEmpresa, PerfilDesarrollador


class Command(BaseCommand):
    help = "Siembra datos limpios de prueba (sin PII ni credenciales reales) para desarrollo."

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            type=str,
            default='Jobdevs2026*',
            help='Contraseña asignada a las cuentas de prueba (default: Jobdevs2026*)'
        )

    def handle(self, *args, **options):
        password = options['password']
        self.stdout.write("Sembrando datos iniciales limpios...")

        with transaction.atomic():
            # 1. Administrador Demo
            admin, created = Usuario.objects.get_or_create(
                username='admin_demo',
                defaults={
                    'nombre': 'Administrador JobDevs',
                    'email': 'admin@jobdevs.local',
                    'rol': 'administrador',
                    'estado': 'activo',
                    'identificacion': '990001001',
                    'fecha_nacimiento': '1990-01-01',
                }
            )
            if created:
                admin.set_password(password)
                admin.save()
                self.stdout.write(self.style.SUCCESS("✓ Creado admin: admin_demo"))
            else:
                self.stdout.write("  admin_demo ya existe.")

            # 2. Empresa Demo
            empresa_user, created = Usuario.objects.get_or_create(
                username='empresa_demo',
                defaults={
                    'nombre': 'Empresa Demo SAS',
                    'email': 'contacto@empresademo.local',
                    'rol': 'empresa',
                    'estado': 'activo',
                    'identificacion': '900123456',
                    'fecha_nacimiento': '2000-01-01',
                }
            )
            if created:
                empresa_user.set_password(password)
                empresa_user.save()
                PerfilEmpresa.objects.get_or_create(
                    usuario=empresa_user,
                    defaults={
                        'nombre_empresa': 'Empresa Demo SAS',
                        'sector': 'Tecnología e Innovación',
                        'telefono': '3001234567',
                        'ciudad': 'Bogotá',
                        'descripcion': 'Empresa de prueba para evaluación de talento SENA en JobDevs.'
                    }
                )
                self.stdout.write(self.style.SUCCESS("✓ Creada empresa: empresa_demo"))
            else:
                self.stdout.write("  empresa_demo ya existe.")

            # 3. Desarrollador Demo
            dev_user, created = Usuario.objects.get_or_create(
                username='dev_demo',
                defaults={
                    'nombre': 'Aprendiz SENA Demo',
                    'email': 'dev@jobdevs.local',
                    'rol': 'desarrollador',
                    'estado': 'activo',
                    'identificacion': '1001234567',
                    'fecha_nacimiento': '2002-05-15',
                }
            )
            if created:
                dev_user.set_password(password)
                dev_user.save()
                PerfilDesarrollador.objects.get_or_create(
                    usuario=dev_user,
                    defaults={
                        'programa_formacion': 'ADSO - Análisis y Desarrollo de Software',
                        'ficha': '2670123',
                        'habilidades': 'Python, Django, PostgreSQL, Docker, Git',
                        'portafolio_url': 'https://github.com/aprendiz-sena'
                    }
                )
                self.stdout.write(self.style.SUCCESS("✓ Creado desarrollador: dev_demo"))
            else:
                self.stdout.write("  dev_demo ya existe.")

        self.stdout.write(self.style.SUCCESS(f"Datos de prueba listos. Contraseña para todos: {password}"))
