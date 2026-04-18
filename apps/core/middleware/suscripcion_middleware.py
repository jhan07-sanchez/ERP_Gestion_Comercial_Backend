from django.http import JsonResponse
from rest_framework import status

class SuscripcionMiddleware:
    """
    Middleware que verifica el estado de la suscripcion de la empresa del usuario.
    Si el periodo de prueba o la suscripcion ha expirado, bloquea peticiones de mutacion.
    """
    
    SAFE_METHODS = ["GET", "HEAD", "OPTIONS"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        # Skip check for public endpoints or auth logic
        if request.path.startswith('/api/auth/'):
            return self.get_response(request)

        if hasattr(request, 'user') and request.user.is_authenticated:
            # Revisa que el usuario tenga empresa y la empresa tenga suscripcion
            empresa = getattr(request.user, 'empresa', None)
            if empresa and hasattr(empresa, 'suscripcion'):
                suscripcion = empresa.suscripcion
                if request.method not in self.SAFE_METHODS:
                    if not suscripcion.esta_activa():
                        return JsonResponse(
                            {"error": "Tu prueba ha expirado o tu suscripción no está activa."},
                            status=status.HTTP_403_FORBIDDEN
                        )
        
        response = self.get_response(request)
        return response
