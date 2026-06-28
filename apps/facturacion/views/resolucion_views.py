from rest_framework import viewsets, serializers
from apps.facturacion.models import ResolucionFacturacion
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions

class ResolucionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResolucionFacturacion
        fields = '__all__'

class ResolucionViewSet(viewsets.ModelViewSet):
    queryset = ResolucionFacturacion.objects.all()
    serializer_class = ResolucionSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    filterset_fields = ['activa']
    search_fields = ['numero_resolucion', 'prefijo']
    ordering_fields = ['fecha_inicio', 'fecha_fin']
    ordering = ['-fecha_inicio']
