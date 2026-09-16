from django.urls import path

from .views import PagoCreateView, PagoDeleteView, PagoListView

urlpatterns = [
    path('pagos/', PagoListView.as_view(), name='pagos'),
    path('pagos/nuevo/', PagoCreateView.as_view(), name='pago_nuevo'),
    path('pagos/<int:pk>/eliminar/', PagoDeleteView.as_view(), name='pago_eliminar'),
]
