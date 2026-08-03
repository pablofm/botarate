from django.contrib import admin

from .forms import ClaseForm, CursoForm
from .models import Alumno, Clase, Curso, DíaSemana


class AlumnoInline(admin.TabularInline):
    model = Alumno
    extra = 1


class DíaSemanaFilter(admin.SimpleListFilter):
    title = 'día de la semana'
    parameter_name = 'día'

    def lookups(self, request, model_admin):
        return DíaSemana.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(días_semana__contains=[int(self.value())])
        return queryset


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    form = CursoForm
    list_display = ('nombre', 'días_semana_display', 'hora_inicio', 'hora_fin',
                    'profesor_principal', 'total_alumnos')
    list_filter = (DíaSemanaFilter, 'profesor_principal', 'profesores_sustitutos')
    search_fields = ('nombre',)
    filter_horizontal = ('profesores_sustitutos',)
    inlines = [AlumnoInline]

    @admin.display(description='Días')
    def días_semana_display(self, curso):
        return curso.días_semana_display

    @admin.display(description='Alumnos')
    def total_alumnos(self, curso):
        return curso.alumnos.count()


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'curso')
    list_filter = ('curso',)
    search_fields = ('nombre',)


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    form = ClaseForm
    list_display = ('curso', 'profesor', 'inicio', 'fin', 'total_asistentes')
    list_filter = ('curso', 'profesor')
    date_hierarchy = 'inicio'
    filter_horizontal = ('asistentes',)

    @admin.display(description='Asistentes')
    def total_asistentes(self, clase):
        return clase.asistentes.count()