from django.urls import path

from .views import AltaHechaView, SocioCreateView, SocioListView

urlpatterns = [
    # Portada abierta: es la que se enlaza desde el QR.
    path('', SocioCreateView.as_view(), name='socio_nuevo'),
    path('gracias/', AltaHechaView.as_view(), name='alta_hecha'),
    # A partir de aquí, solo el profesorado.
    path('socios/', SocioListView.as_view(), name='socios'),
]
