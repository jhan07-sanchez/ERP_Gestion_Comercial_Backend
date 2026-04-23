from django.core.management.base import BaseCommand
from apps.usuarios.models import Modulo, Plan

class Command(BaseCommand):
    help = 'Crea los módulos base y los planes (BASIC, PRO, EMPRESARIAL) para el SaaS'

    def handle(self, *args, **kwargs):
        self.stdout.write('Iniciando carga de datos SaaS...')

        # 1. Crear Módulos
        modulos_data = [
            {'nombre': 'Ventas', 'codigo': 'ventas', 'descripcion': 'Gestión de ventas y facturación'},
            {'nombre': 'Inventario', 'codigo': 'inventario', 'descripcion': 'Control de stock y almacenes'},
            {'nombre': 'Compras', 'codigo': 'compras', 'descripcion': 'Gestión de proveedores y compras'},
            {'nombre': 'Reportes', 'codigo': 'reportes', 'descripcion': 'Reportes avanzados y analítica'},
        ]

        modulos_creados = {}
        for mod_data in modulos_data:
            modulo, created = Modulo.objects.get_or_create(
                codigo=mod_data['codigo'],
                defaults={'nombre': mod_data['nombre'], 'descripcion': mod_data['descripcion']}
            )
            modulos_creados[modulo.codigo] = modulo
            estado = "Creado" if created else "Ya existía"
            self.stdout.write(f'  - Módulo {modulo.nombre} ({estado})')

        # 2. Crear Planes y Asignar Módulos
        planes_data = [
            {
                'nombre': 'BASIC',
                'precio': 19.99,
                'descripcion': 'Plan básico para empezar.',
                'modulos': ['ventas']
            },
            {
                'nombre': 'PRO',
                'precio': 49.99,
                'descripcion': 'Plan profesional con control de inventario.',
                'modulos': ['ventas', 'inventario']
            },
            {
                'nombre': 'EMPRESARIAL',
                'precio': 99.99,
                'descripcion': 'Plan completo para empresas grandes.',
                'modulos': ['ventas', 'inventario', 'compras', 'reportes']
            }
        ]

        for plan_data in planes_data:
            plan, created = Plan.objects.get_or_create(
                nombre=plan_data['nombre'],
                defaults={'precio': plan_data['precio'], 'descripcion': plan_data['descripcion']}
            )
            
            # Asignar módulos
            modulos_para_asignar = [modulos_creados[codigo] for codigo in plan_data['modulos']]
            plan.modulos.set(modulos_para_asignar)
            
            estado = "Creado" if created else "Actualizado"
            self.stdout.write(self.style.SUCCESS(f'  - Plan {plan.nombre} ({estado}) con {len(modulos_para_asignar)} módulos.'))

        self.stdout.write(self.style.SUCCESS('¡Datos SaaS cargados exitosamente!'))
