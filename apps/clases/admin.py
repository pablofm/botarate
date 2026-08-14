from django.contrib import admin

from .forms import ClaseForm, CursoForm
from .models import Alumno, Clase, Curso, DíaSemana, Socio


class MatrículaInline(admin.TabularInline):
    """Las alumnas del curso, a través de la tabla intermedia de Alumno.cursos."""

    model = Alumno.cursos.through
    verbose_name = 'alumna'
    verbose_name_plural = 'alumnas'
    autocomplete_fields = ('alumno',)
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
    inlines = [MatrículaInline]

    @admin.display(description='Días')
    def días_semana_display(self, curso):
        return curso.días_semana_display

    @admin.display(description='Alumnos')
    def total_alumnos(self, curso):
        return curso.alumnos.count()


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dni', 'teléfono', 'email', 'es_alumno',
                    'quiere_comunicaciones', 'quiere_whatsapp')
    list_filter = ('quiere_comunicaciones', 'quiere_whatsapp')
    search_fields = ('nombre', 'dni', 'teléfono', 'email')

    @admin.display(description='Va a clase', boolean=True)
    def es_alumno(self, socio):
        return socio.es_alumno


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('socio', 'cursos_display')
    list_filter = ('cursos',)
    search_fields = ('socio__nombre', 'socio__dni', 'socio__teléfono', 'socio__email')
    autocomplete_fields = ('socio',)
    filter_horizontal = ('cursos',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('socio').prefetch_related('cursos')

    @admin.display(description='Cursos')
    def cursos_display(self, alumno):
        return ', '.join(curso.nombre for curso in alumno.cursos.all()) or '—'


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