from rest_framework import viewsets, serializers
from apps.facturacion.models import Impuesto
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions

class ImpuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Impuesto
        fields = '__all__'

class ImpuestoViewSet(viewsets.ModelViewSet):
    queryset = Impuesto.objects.all()
    serializer_class = ImpuestoSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    filterset_fields = ['activo']
    search_fields = ['nombre']
    ordering_fields = ['nombre', 'porcentaje']
    ordering = ['nombre']
