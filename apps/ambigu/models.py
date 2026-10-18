from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.pagos.models import FORMAS_PAGO_PENDIENTES, FormaPago


class CategoríaBebida(models.Model):
    nombre = models.CharField('nombre', max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Categoría de bebida'
        verbose_name_plural = 'Categorías de bebida'
        ordering = ['nombre']


class Bebida(models.Model):
    categoría = models.ForeignKey(CategoríaBebida, on_delete=models.PROTECT, related_name='bebidas')
    nombre = models.CharField('nombre', max_length=100, unique=True)
    precio_venta = models.DecimalField(
        'PVP (€)', max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    stock_mínimo = models.PositiveIntegerField(default=0, help_text='Por debajo de estas unidades hay que reponer.')

    @property
    def unidades_compradas(self):
        """Todas las que han entrado; aún no se descuentan ventas ni mermas."""
        return self.entradas_stock.aggregate(total=models.Sum('cantidad'))['total'] or 0

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Bebida'
        verbose_name_plural = 'Bebidas'
        ordering = ['categoría__nombre', 'nombre']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(precio_venta__gt=0), name='bebida_precio_venta_positivo'),
        ]


class StockBebida(models.Model):
    """Una compra de bebida: cuántas unidades entran y a cuánto ha salido cada una."""

    bebida = models.ForeignKey(
        Bebida, on_delete=models.PROTECT, related_name='entradas_stock', verbose_name='bebida')
    fecha = models.DateField('fecha de compra', default=timezone.localdate)
    cantidad = models.PositiveIntegerField('unidades', validators=[MinValueValidator(1)])
    precio_compra = models.DecimalField(
        'precio de compra por unidad (€)', max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Lo que cuesta cada unidad, IVA incluido.')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='entradas_stock_registradas',
        verbose_name='registrado por')

    @property
    def coste_total(self):
        return self.cantidad * self.precio_compra

    @property
    def margen_unitario(self):
        """Lo que se gana con cada unidad al PVP de ahora."""
        return self.bebida.precio_venta - self.precio_compra

    @property
    def beneficio_previsto(self):
        """Lo que se ganaría vendiendo toda la compra al PVP de ahora."""
        return self.cantidad * self.margen_unitario

    def __str__(self):
        return f'{self.cantidad} × {self.bebida} a {self.precio_compra} € ({self.fecha:%d/%m/%Y})'

    class Meta:
        verbose_name = 'Stock de bebida'
        verbose_name_plural = 'Stock de bebidas'
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='stock_bebida_cantidad_positiva'),
            models.CheckConstraint(
                condition=models.Q(precio_compra__gt=0), name='stock_bebida_precio_compra_positivo'),
        ]


class VentaBebida(models.Model):
    """Una venta en barra: cuántas unidades de una bebida han salido ese día."""

    bebida = models.ForeignKey(
        Bebida, on_delete=models.PROTECT, related_name='ventas', verbose_name='bebida')
    fecha = models.DateField('fecha de venta', default=timezone.localdate)
    cantidad = models.PositiveIntegerField('unidades', validators=[MinValueValidator(1)])
    forma_pago = models.CharField('forma de pago', max_length=13, choices=FormaPago, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ventas_registradas',
        verbose_name='registrado por')

    @property
    def importe(self):
        """El PVP de la bebida no cambia, así que el de ahora es el de la venta."""
        return self.cantidad * self.bebida.precio_venta

    def clean(self):
        super().clean()
        # Las mismas formas de pago pendientes que en los pagos de clases.
        if self._state.adding and self.forma_pago in FORMAS_PAGO_PENDIENTES:
            raise ValidationError(
                {'forma_pago': f'{self.get_forma_pago_display()} está pendiente de activar.'})

    def __str__(self):
        return f'{self.cantidad} × {self.bebida} ({self.fecha:%d/%m/%Y})'

    class Meta:
        verbose_name = 'Venta de bebida'
        verbose_name_plural = 'Ventas de bebidas'
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='venta_bebida_cantidad_positiva'),
        ]
