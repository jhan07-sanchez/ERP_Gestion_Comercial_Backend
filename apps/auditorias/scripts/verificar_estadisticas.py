import os
import django
import sys
import json

# Ajustar el path para que encuentre la configuración
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from apps.auditorias.views.api import EstadisticasAuditoriaView
from django.contrib.auth import get_user_model

def verificar_estadisticas():
    Usuario = get_user_model()
    admin = Usuario.objects.filter(is_superuser=True).first()
    if not admin:
        print("Error: No se encontró un usuario administrador para la prueba.")
        return

    factory = APIRequestFactory()
    request = factory.get('/api/auditorias/estadisticas/')
    force_authenticate(request, user=admin)

    view = EstadisticasAuditoriaView.as_view()
    response = view(request)

    print("--- ESTADÍSTICAS DE AUDITORÍA (JSON) ---")
    print(json.dumps(response.data, indent=2))

if __name__ == "__main__":
    verificar_estadisticas()
