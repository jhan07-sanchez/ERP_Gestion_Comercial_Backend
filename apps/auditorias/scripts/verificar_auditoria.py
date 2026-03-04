import os
import django
import sys

# Ajustar el path para que encuentre la configuración
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.auditorias.models import LogAuditoria

def listar_ultimos_logs(limit=10):
    logs = LogAuditoria.objects.all().order_by('-fecha_hora')[:limit]
    print(f"--- ÚLTIMOS {limit} LOGS DE AUDITORÍA ---")
    for log in logs:
        usuario = log.usuario_nombre or "Sistema"
        print(f"[{log.fecha_hora}] {usuario} | {log.accion} | {log.modulo} | {log.descripcion[:70]}...")

if __name__ == "__main__":
    listar_ultimos_logs()
