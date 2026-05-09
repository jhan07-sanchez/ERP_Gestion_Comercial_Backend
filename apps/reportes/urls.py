from django.urls import path
from apps.reportes.views.api import (
    BalanceGeneralView,
    EstadoResultadosView,
    FlujoCajaView,
    ProductividadView,
    ProyeccionesView
)

app_name = 'reportes'

urlpatterns = [
    path('financieros/balance-general/', BalanceGeneralView.as_view(), name='balance-general'),
    path('financieros/estado-resultados/', EstadoResultadosView.as_view(), name='estado-resultados'),
    path('financieros/flujo-caja/', FlujoCajaView.as_view(), name='flujo-caja'),
    path('operativos/productividad/', ProductividadView.as_view(), name='productividad'),
    path('analiticos/proyecciones/', ProyeccionesView.as_view(), name='proyecciones'),
]
