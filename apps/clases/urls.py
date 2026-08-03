from django.urls import path

from .views import (
    AlumnoCreateView,
    CursoDetailView,
    DashboardView,
    IniciarClaseView,
    TerminarClaseView,
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('cursos/<int:pk>/', CursoDetailView.as_view(), name='curso_detalle'),
    path('cursos/<int:pk>/iniciar-clase/', IniciarClaseView.as_view(), name='clase_iniciar'),
    path('clases/<int:pk>/terminar/', TerminarClaseView.as_view(), name='clase_terminar'),
    path('alumnos/nuevo/', AlumnoCreateView.as_view(), name='alumno_nuevo'),
]
