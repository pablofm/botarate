import datetime
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.clases.models import Alumno, Curso


class Modalidad(models.TextChoices):
    CLASE = 'CLASE', 'Una clase'
    MENSUAL = 'MENSUAL', 'Mensual'
    TRIMESTRAL = 'TRIMESTRAL', 'Trimestral'
    ANUAL = 'ANUAL', 'Anual'


# Meses que cubre cada modalidad; la clase suelta cubre solo el día de la clase.
MESES_POR_MODALIDAD = {
    Modalidad.CLASE: 0,
    Modalidad.MENSUAL: 1,
    Modalidad.TRIMESTRAL: 3,
    Modalidad.ANUAL: 12,
}


class FormaPago(models.TextChoices):
    TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia bancaria'
    EFECTIVO = 'EFECTIVO', 'Efectivo'
    BIZUM = 'BIZUM', 'Bizum'
    DATÁFONO = 'DATAFONO', 'Datáfono'


# Aún no se aceptan: salen en el formulario, pero sin poder elegirse. Para activar
# una basta con quitarla de aquí.
FORMAS_PAGO_PENDIENTES = {FormaPago.BIZUM}


def sumar_meses(fecha, meses):
    """La misma fecha, tantos meses después; si ese día no existe, el último del mes."""
    año, mes = divmod(fecha.month - 1 + meses, 12)
    año, mes = fecha.year + año, mes + 1
    siguiente = datetime.date(año + mes // 12, mes % 12 + 1, 1)
    último_día = (siguiente - datetime.timedelta(days=1)).day
    return datetime.date(año, mes, min(fecha.day, último_día))


class Pago(models.Model):
    """Lo que paga una alumna por un curso: una clase suelta o un periodo entero."""

    # Alumna y curso por separado, y no la matrícula: si se desmatricula, el pago se queda.
    alumno = models.ForeignKey(
        Alumno, on_delete=models.PROTECT, related_name='pagos', verbose_name='alumna')
    curso = models.ForeignKey(
        Curso, on_delete=models.PROTECT, related_name='pagos', verbose_name='curso')
    modalidad = models.CharField('modalidad', max_length=10, choices=Modalidad)
    desde = models.DateField(
        'desde',
        help_text='Primer día que cubre el pago; en una clase suelta, el día de la clase.')
    importe = models.DecimalField(
        'importe (€)', max_digits=7, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    forma_pago = models.CharField('forma de pago', max_length=13, choices=FormaPago)
    fecha = models.DateField('fecha de pago', default=timezone.localdate)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='pagos_registrados',
        verbose_name='registrado por')

    @property
    def hasta(self):
        """Último día que cubre el pago."""
        meses = MESES_POR_MODALIDAD[self.modalidad]
        if not meses:
            return self.desde
        return sumar_meses(self.desde, meses) - datetime.timedelta(days=1)

    def clean(self):
        super().clean()
        # Solo al registrarlo: si se activa y luego se desactiva, los pagos viejos siguen valiendo.
        if self._state.adding and self.forma_pago in FORMAS_PAGO_PENDIENTES:
            raise ValidationError(
                {'forma_pago': f'{self.get_forma_pago_display()} está pendiente de activar.'})

    def __str__(self):
        return f'{self.alumno} — {self.curso.nombre}: {self.importe} € ({self.get_modalidad_display()})'

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(importe__gt=0), name='pago_importe_positivo'),
        ]
