from django.contrib import admin

from .models import Bebida, Camiseta, CategoríaBebida, StockBebida, StockCamiseta, VentaBebida, VentaCamiseta


@admin.register(CategoríaBebida)
class CategoríaBebidaAdmin(admin.ModelAdmin):
    search_fields = ('nombre',)


@admin.register(Bebida)
class BebidaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoría', 'precio_venta', 'stock_mínimo')
    list_filter = ('categoría',)
    search_fields = ('nombre',)


@admin.register(StockBebida)
class StockBebidaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'bebida', 'cantidad', 'precio_compra', 'coste_total',
                    'beneficio_previsto', 'registrado_por')
    list_filter = ('bebida__categoría', 'bebida')
    date_hierarchy = 'fecha'
    autocomplete_fields = ('bebida',)
    readonly_fields = ('registrado_por',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('bebida', 'registrado_por')

    @admin.display(description='Coste total (€)')
    def coste_total(self, entrada):
        return entrada.coste_total

    @admin.display(description='Beneficio previsto (€)')
    def beneficio_previsto(self, entrada):
        return entrada.beneficio_previsto

    def save_model(self, request, entrada, form, change):
        if not change:
            entrada.registrado_por = request.user
        super().save_model(request, entrada, form, change)


@admin.register(VentaBebida)
class VentaBebidaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'bebida', 'cantidad', 'forma_pago', 'registrado_por')
    list_filter = ('bebida__categoría', 'bebida', 'forma_pago')
    date_hierarchy = 'fecha'
    autocomplete_fields = ('bebida',)
    readonly_fields = ('registrado_por',)
    list_select_related = ('bebida', 'registrado_por')

    def save_model(self, request, venta, form, change):
        if not change:
            venta.registrado_por = request.user
        super().save_model(request, venta, form, change)


@admin.register(Camiseta)
class CamisetaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'precio_compra', 'precio_venta', 'stock_mínimo')
    list_filter = ('corte', 'talla')
    search_fields = ('corte', 'talla')


@admin.register(StockCamiseta)
class StockCamisetaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'camiseta', 'cantidad', 'coste_total', 'registrado_por')
    list_filter = ('camiseta__corte', 'camiseta__talla')
    date_hierarchy = 'fecha'
    autocomplete_fields = ('camiseta',)
    readonly_fields = ('registrado_por',)
    list_select_related = ('camiseta', 'registrado_por')

    @admin.display(description='Coste total (€)')
    def coste_total(self, entrada):
        return entrada.coste_total

    def save_model(self, request, entrada, form, change):
        if not change:
            entrada.registrado_por = request.user
        super().save_model(request, entrada, form, change)


@admin.register(VentaCamiseta)
class VentaCamisetaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'camiseta', 'cantidad', 'forma_pago', 'registrado_por')
    list_filter = ('camiseta__corte', 'camiseta__talla', 'forma_pago')
    date_hierarchy = 'fecha'
    autocomplete_fields = ('camiseta',)
    readonly_fields = ('registrado_por',)
    list_select_related = ('camiseta', 'registrado_por')

    def save_model(self, request, venta, form, change):
        if not change:
            venta.registrado_por = request.user
        super().save_model(request, venta, form, change)
