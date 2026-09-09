from django.urls import path

from .views import (
    CursoDetailView,
    DashboardView,
    DesmatricularAlumnaView,
    IniciarClaseView,
    MatricularAlumnaView,
    TerminarClaseView,
)

urlpatterns = [
    path('panel/', DashboardView.as_view(), name='dashboard'),
    path('cursos/<int:pk>/', CursoDetailView.as_view(), name='curso_detalle'),
    path('cursos/<int:pk>/iniciar-clase/', IniciarClaseView.as_view(), name='clase_iniciar'),
    path('clases/<int:pk>/terminar/', TerminarClaseView.as_view(), name='clase_terminar'),
    path('cursos/<int:pk>/alumnos/<int:alumno_pk>/desmatricular/',
         DesmatricularAlumnaView.as_view(), name='alumno_desmatricular'),
    path('alumnos/matricular/', MatricularAlumnaView.as_view(), name='alumno_matricular'),
]
