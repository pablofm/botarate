from django.contrib import admin

from .models import Socio


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'documento', 'teléfono', 'email', 'fecha_alta', 'es_alumno',
                    'quiere_comunicaciones', 'quiere_whatsapp')
    list_filter = ('tipo_documento', 'fecha_alta', 'quiere_comunicaciones', 'quiere_whatsapp')
    search_fields = ('nombre', 'documento', 'teléfono', 'email')

    @admin.display(description='Va a clase', boolean=True)
    def es_alumno(self, socio):
        return socio.es_alumno
