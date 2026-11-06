from django.urls import path

from .views import PagoCreateView, PagoDeleteView, PagoListView, PagoUpdateView

urlpatterns = [
    path('pagos/', PagoListView.as_view(), name='pagos'),
    path('pagos/nuevo/', PagoCreateView.as_view(), name='pago_nuevo'),
    path('pagos/<int:pk>/editar/', PagoUpdateView.as_view(), name='pago_editar'),
    path('pagos/<int:pk>/eliminar/', PagoDeleteView.as_view(), name='pago_eliminar'),
]
