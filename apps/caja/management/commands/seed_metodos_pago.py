from django.core.management.base import BaseCommand
from apps.caja.models import MetodoPago


class Command(BaseCommand):
    help = 'Inicializa los métodos de pago con su tipo (CONTADO/CREDITO)'

    def handle(self, *args, **options):
        metodos = [
            {'nombre': 'EFECTIVO',       'es_efectivo': True,  'tipo': MetodoPago.TIPO_CONTADO},
            {'nombre': 'TARJETA',        'es_efectivo': False, 'tipo': MetodoPago.TIPO_CONTADO},
            {'nombre': 'TRANSFERENCIA',  'es_efectivo': False, 'tipo': MetodoPago.TIPO_CONTADO},
            {'nombre': 'YAPE',           'es_efectivo': False, 'tipo': MetodoPago.TIPO_CONTADO},
            {'nombre': 'PLIN',           'es_efectivo': False, 'tipo': MetodoPago.TIPO_CONTADO},
            {'nombre': 'CRÉDITO',        'es_efectivo': False, 'tipo': MetodoPago.TIPO_CREDITO},
        ]

        for data in metodos:
            obj, created = MetodoPago.objects.update_or_create(
                nombre=data['nombre'],
                defaults={
                    'es_efectivo': data['es_efectivo'],
                    'tipo': data['tipo'],
                },
            )
            status = '✅ Creado' if created else '🔄 Actualizado'
            self.stdout.write(
                self.style.SUCCESS(
                    f"{status}: {data['nombre']} → tipo={data['tipo']}"
                )
            )
