from django.urls import path

from .views import (
    AltaHechaView,
    CursoDetailView,
    DashboardView,
    IniciarClaseView,
    MatricularAlumnaView,
    SocioCreateView,
    SocioListView,
    TerminarClaseView,
)

urlpatterns = [
    # Portada abierta: es la que se enlaza desde el QR.
    path('', SocioCreateView.as_view(), name='socio_nuevo'),
    path('gracias/', AltaHechaView.as_view(), name='alta_hecha'),
    # A partir de aquí, solo el profesorado.
    path('panel/', DashboardView.as_view(), name='dashboard'),
    path('cursos/<int:pk>/', CursoDetailView.as_view(), name='curso_detalle'),
    path('cursos/<int:pk>/iniciar-clase/', IniciarClaseView.as_view(), name='clase_iniciar'),
    path('clases/<int:pk>/terminar/', TerminarClaseView.as_view(), name='clase_terminar'),
    path('socios/', SocioListView.as_view(), name='socios'),
    path('alumnos/matricular/', MatricularAlumnaView.as_view(), name='alumno_matricular'),
]
