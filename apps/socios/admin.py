from django.contrib import admin

from .models import Nota, Socio


class NotaInline(admin.TabularInline):
    model = Nota
    extra = 0
    fields = ('fecha', 'texto', 'autor')


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    inlines = [NotaInline]
    list_display = ('nombre', 'documento', 'teléfono', 'email', 'fecha_alta', 'es_alumno',
                    'quiere_comunicaciones', 'quiere_whatsapp')
    list_filter = ('tipo_documento', 'fecha_alta', 'quiere_comunicaciones', 'quiere_whatsapp')
    search_fields = ('nombre', 'documento', 'teléfono', 'email')

    @admin.display(description='Va a clase', boolean=True)
    def es_alumno(self, socio):
        return socio.es_alumno


@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ('socio', 'fecha', 'texto', 'autor', 'creada')
    list_filter = ('fecha', 'autor')
    list_select_related = ('socio', 'autor')
    search_fields = ('socio__nombre', 'texto')
    autocomplete_fields = ('socio',)
    date_hierarchy = 'fecha'
