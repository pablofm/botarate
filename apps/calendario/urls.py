from django.urls import path

from . import views

# Todo abierto: el calendario es la programación pública de la sala.
urlpatterns = [
    path('calendario/', views.CalendarioView.as_view(), name='calendario'),
    path('calendario/<int:año>/<int:mes>/', views.CalendarioView.as_view(), name='calendario_mes'),
    path('calendario/botarate.ics', views.CalendarioIcsView.as_view(), name='calendario_ics'),
    path('calendario/suscribirse/', views.SuscribirseView.as_view(), name='calendario_suscribirse'),
]
