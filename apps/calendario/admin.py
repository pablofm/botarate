from django.contrib import admin
from django.utils.html import format_html

from .models import Evento


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('título', 'inicio', 'duración_aproximada', 'lugar', 'miniatura', 'publicado')
    list_filter = ('publicado',)
    list_editable = ('publicado',)
    date_hierarchy = 'inicio'
    search_fields = ('título', 'descripción', 'lugar')
    fields = ('título', 'descripción', ('inicio', 'duración'), 'lugar', 'enlace', 'cartel', 'publicado')

    @admin.display(description='Duración aproximada', ordering='duración')
    def duración_aproximada(self, evento):
        return evento.duración_aproximada

    @admin.display(description='Cartel')
    def miniatura(self, evento):
        return format_html('<img src="{}" alt="" style="height: 4rem">', evento.url_cartel)
