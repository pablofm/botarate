import datetime
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.pagos.models import FORMAS_PAGO_PENDIENTES, FormaPago


# Las de los pagos de clases, más la invitación/merma, que solo se da en la barra.
FormaPagoVenta = models.TextChoices('FormaPagoVenta', [
    *((forma.name, (forma.value, forma.label)) for forma in FormaPago),
    ('INVITACIÓN', ('INVITACION', 'Invitación/Merma')),
])


# Las compras se apuntan desde este día; las ventas de antes salieron de bebida que
# no está registrada, así que no se descuentan del stock.
INICIO_STOCK = datetime.date(2026, 10, 23)


def unidades(queryset, producto):
    """Las unidades de «queryset» (compras o ventas) de cada producto de la consulta de fuera."""
    # Con subconsultas y no con dos Sum sobre joins, que multiplicarían una suma por la otra.
    suma = queryset.filter(**{producto: models.OuterRef('pk')}).values(producto).annotate(
        total=models.Sum('cantidad')).values('total')
    return Coalesce(models.Subquery(suma), 0)


class BebidaQuerySet(models.QuerySet):
    def con_stock(self):
        """Añade a cada bebida «stock_actual»: lo comprado menos lo vendido desde INICIO_STOCK."""
        return self.annotate(stock_actual=(
            unidades(StockBebida.objects.all(), 'bebida')
            - unidades(VentaBebida.objects.filter(fecha__gte=INICIO_STOCK), 'bebida')))


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

    objects = BebidaQuerySet.as_manager()

    @property
    def unidades_compradas(self):
        """Todas las que han entrado, sin descontar ventas: para eso está con_stock()."""
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
    forma_pago = models.CharField('forma de pago', max_length=13, choices=FormaPagoVenta, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ventas_registradas',
        verbose_name='registrado por')

    @property
    def importe(self):
        """El PVP de la bebida no cambia, así que el de ahora es el de la venta."""
        # Una invitación o una merma sale gratis.
        if self.forma_pago == FormaPagoVenta.INVITACIÓN:
            return Decimal('0.00')
        return self.cantidad * self.bebida.precio_venta

    def unidades_disponibles(self):
        """Las que se pueden vender en esta venta: el stock, más lo que ya se llevaba ella."""
        disponibles = Bebida.objects.con_stock().get(pk=self.bebida_id).stock_actual
        if not self._state.adding:
            anterior = VentaBebida.objects.get(pk=self.pk)
            if anterior.bebida_id == self.bebida_id and anterior.fecha >= INICIO_STOCK:
                disponibles += anterior.cantidad
        return disponibles

    def clean(self):
        super().clean()
        errores = {}
        # Las mismas formas de pago pendientes que en los pagos de clases.
        if self._state.adding and self.forma_pago in FORMAS_PAGO_PENDIENTES:
            errores['forma_pago'] = f'{self.get_forma_pago_display()} está pendiente de activar.'
        # Las ventas de antes de INICIO_STOCK no cuentan para el stock, así que no se limitan.
        if self.bebida_id and self.cantidad and self.fecha and self.fecha >= INICIO_STOCK:
            disponibles = max(self.unidades_disponibles(), 0)
            if self.cantidad > disponibles:
                errores['cantidad'] = (
                    f'No se puede vender más de lo comprado: de {self.bebida} '
                    f'se pueden vender {disponibles} como mucho.')
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return f'{self.cantidad} × {self.bebida} ({self.fecha:%d/%m/%Y})'

    class Meta:
        verbose_name = 'Venta de bebida'
        verbose_name_plural = 'Ventas de bebidas'
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='venta_bebida_cantidad_positiva'),
        ]


class Corte(models.TextChoices):
    HOMBRE = 'HOMBRE', 'Hombre'
    MUJER = 'MUJER', 'Mujer'


class Talla(models.TextChoices):
    XS = 'XS'
    S = 'S'
    M = 'M'
    L = 'L'
    XL = 'XL'
    XXL = 'XXL'


class CamisetaQuerySet(models.QuerySet):
    def con_stock(self):
        """Añade a cada camiseta «stock_actual»: lo comprado menos lo vendido."""
        return self.annotate(stock_actual=(
            unidades(StockCamiseta.objects.all(), 'camiseta')
            - unidades(VentaCamiseta.objects.all(), 'camiseta')))


class Camiseta(models.Model):
    """Un corte en una talla. Lo que cuesta y a cuánto se vende es fijo para cada una."""

    corte = models.CharField('corte', max_length=6, choices=Corte)
    talla = models.CharField('talla', max_length=3, choices=Talla)
    precio_compra = models.DecimalField(
        'precio de compra (€)', max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Lo que cuesta cada camiseta, IVA incluido.')
    precio_venta = models.DecimalField(
        'PVP (€)', max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    stock_mínimo = models.PositiveIntegerField(default=0, help_text='Por debajo de estas unidades hay que reponer.')

    objects = CamisetaQuerySet.as_manager()

    @property
    def margen_unitario(self):
        return self.precio_venta - self.precio_compra

    def __str__(self):
        return f'Camiseta de {self.get_corte_display().lower()}, talla {self.talla}'

    class Meta:
        verbose_name = 'Camiseta'
        verbose_name_plural = 'Camisetas'
        # Las tallas de menor a mayor, no por orden alfabético.
        ordering = [
            'corte',
            models.Case(*(models.When(talla=talla, then=orden) for orden, talla in enumerate(Talla.values))),
        ]
        constraints = [
            models.UniqueConstraint(fields=['corte', 'talla'], name='camiseta_corte_talla_única'),
            models.CheckConstraint(
                condition=models.Q(precio_compra__gt=0), name='camiseta_precio_compra_positivo'),
            models.CheckConstraint(
                condition=models.Q(precio_venta__gt=0), name='camiseta_precio_venta_positivo'),
        ]


class StockCamiseta(models.Model):
    """Una compra de camisetas: el precio no se apunta, es el de la camiseta."""

    camiseta = models.ForeignKey(
        Camiseta, on_delete=models.PROTECT, related_name='entradas_stock', verbose_name='camiseta')
    fecha = models.DateField('fecha de compra', default=timezone.localdate)
    cantidad = models.PositiveIntegerField('unidades', validators=[MinValueValidator(1)])
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='entradas_camisetas_registradas',
        verbose_name='registrado por')

    @property
    def coste_total(self):
        return self.cantidad * self.camiseta.precio_compra

    def __str__(self):
        return f'{self.cantidad} × {self.camiseta} ({self.fecha:%d/%m/%Y})'

    class Meta:
        verbose_name = 'Stock de camiseta'
        verbose_name_plural = 'Stock de camisetas'
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='stock_camiseta_cantidad_positiva'),
        ]


class VentaCamiseta(models.Model):
    """Una venta de camisetas: cuántas de un corte y una talla han salido ese día."""

    camiseta = models.ForeignKey(
        Camiseta, on_delete=models.PROTECT, related_name='ventas', verbose_name='camiseta')
    fecha = models.DateField('fecha de venta', default=timezone.localdate)
    cantidad = models.PositiveIntegerField('unidades', validators=[MinValueValidator(1)])
    forma_pago = models.CharField('forma de pago', max_length=13, choices=FormaPagoVenta)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ventas_camisetas_registradas',
        verbose_name='registrado por')

    @property
    def importe(self):
        """El PVP de la camiseta no cambia, así que el de ahora es el de la venta."""
        if self.forma_pago == FormaPagoVenta.INVITACIÓN:
            return Decimal('0.00')
        return self.cantidad * self.camiseta.precio_venta

    def unidades_disponibles(self):
        """Las que se pueden vender en esta venta: el stock, más lo que ya se llevaba ella."""
        disponibles = Camiseta.objects.con_stock().get(pk=self.camiseta_id).stock_actual
        if not self._state.adding:
            anterior = VentaCamiseta.objects.get(pk=self.pk)
            if anterior.camiseta_id == self.camiseta_id:
                disponibles += anterior.cantidad
        return disponibles

    def clean(self):
        super().clean()
        errores = {}
        if self._state.adding and self.forma_pago in FORMAS_PAGO_PENDIENTES:
            errores['forma_pago'] = f'{self.get_forma_pago_display()} está pendiente de activar.'
        if self.camiseta_id and self.cantidad:
            disponibles = max(self.unidades_disponibles(), 0)
            if self.cantidad > disponibles:
                errores['cantidad'] = (
                    f'No se puede vender más de lo comprado: de {self.camiseta} '
                    f'se pueden vender {disponibles} como mucho.')
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return f'{self.cantidad} × {self.camiseta} ({self.fecha:%d/%m/%Y})'

    class Meta:
        verbose_name = 'Venta de camiseta'
        verbose_name_plural = 'Ventas de camisetas'
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='venta_camiseta_cantidad_positiva'),
        ]
