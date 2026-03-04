import os
import django
import sys

# Ajustar el path para que encuentre la configuración
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.auditorias.utils import registrar_log
from django.contrib.auth import get_user_model

def generar_test_seguridad():
    Usuario = get_user_model()
    try:
        admin = Usuario.objects.filter(is_superuser=True).first()
    except:
        admin = None

    # 1. Alerta del Sistema (ERROR)
    registrar_log(
        usuario=admin,
        accion='ERROR',
        modulo='SISTEMA',
        descripcion='Test Backend: Error crítico simulado para verificar KPI de Alertas',
        nivel='ERROR',
        exitoso=False
    )

    # 2. Control de Acceso (LOGIN_FALLIDO)
    registrar_log(
        usuario=None,
        accion='LOGIN_FALLIDO',
        modulo='USUARIOS',
        descripcion='Test Backend: Intento de login fallido simulado para verificar KPI de Seguridad',
        nivel='WARNING',
        exitoso=False
    )

    # 3. Control de Acceso (ACCESO_DENEGADO)
    registrar_log(
        usuario=admin,
        accion='ACCESO_DENEGADO',
        modulo='VENTAS',
        descripcion='Test Backend: Acceso denegado simulado a módulo de ventas',
        nivel='WARNING',
        exitoso=False
    )
    print("Test security logs generated successfully.")

if __name__ == "__main__":
    generar_test_seguridad()
