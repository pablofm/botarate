from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'alumno', 'curso', 'modalidad', 'desde', 'hasta', 'importe',
                    'forma_pago', 'registrado_por')
    list_filter = ('curso', 'modalidad', 'forma_pago')
    search_fields = ('alumno__socio__nombre', 'alumno__socio__documento')
    date_hierarchy = 'fecha'
    autocomplete_fields = ('alumno',)
    readonly_fields = ('registrado_por',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('alumno__socio', 'curso', 'registrado_por')

    @admin.display(description='Hasta')
    def hasta(self, pago):
        return pago.hasta

    def save_model(self, request, pago, form, change):
        if not change:
            pago.registrado_por = request.user
        super().save_model(request, pago, form, change)
