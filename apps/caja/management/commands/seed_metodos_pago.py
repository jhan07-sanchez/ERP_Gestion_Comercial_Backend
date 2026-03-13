from django.core.management.base import BaseCommand
from apps.caja.models import MetodoPago

class Command(BaseCommand):
    help = 'Inicializa los métodos de pago básicos en el sistema'

    def handle(self, *args, **options):
        metodos = [
            {'nombre': 'EFECTIVO', 'es_efectivo': True},
            {'nombre': 'TARJETA', 'es_efectivo': False},
            {'nombre': 'TRANSFERENCIA', 'es_efectivo': False},
            {'nombre': 'YAPE', 'es_efectivo': False},
            {'nombre': 'PLIN', 'es_efectivo': False},
            {'nombre': 'CRÉDITO', 'es_efectivo': False},
        ]

        for data in metodos:
            obj, created = MetodoPago.objects.get_or_create(
                nombre=data['nombre'],
                defaults={'es_efectivo': data['es_efectivo']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Método creado: {data["nombre"]}'))
            else:
                self.stdout.write(f'Método ya existe: {data["nombre"]}')
