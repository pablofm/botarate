import datetime
import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.templatetags.static import static
from django.utils import timezone

CARTEL_POR_DEFINIR = 'img/cartel-por-definir.png'
WEB_BOTARATE = 'https://www.escuelabotarate.com'


class EventoQuerySet(models.QuerySet):
    def publicados(self):
        return self.filter(publicado=True)

    def entre(self, desde, hasta):
        """Los que pisan el intervalo, aunque empiecen antes o, contando la duración, acaben después."""
        fin_aproximado = models.ExpressionWrapper(
            models.F('inicio') + models.F('duración') * datetime.timedelta(minutes=1),
            output_field=models.DateTimeField())
        return self.alias(fin_aproximado=fin_aproximado).filter(inicio__lt=hasta, fin_aproximado__gt=desde)


class Evento(models.Model):
    """Un concierto o cualquier otra cosa que pase en la sala."""

    título = models.CharField('título', max_length=200)
    descripción = models.TextField('descripción', blank=True)
    inicio = models.DateTimeField('empieza')
    # Sin hora de fin: solo una duración orientativa, para no comprometerse a una hora de cierre.
    duración = models.PositiveSmallIntegerField(
        'duración aproximada (minutos)', default=120, validators=[MinValueValidator(1)])
    lugar = models.CharField('lugar', max_length=200, blank=True, help_text='En blanco si es en la propia sala.')
    enlace = models.URLField(
        'enlace', blank=True, default=WEB_BOTARATE, help_text='Venta de entradas o más información.')
    cartel = models.ImageField(
        'cartel', upload_to='carteles/%Y/', blank=True,
        help_text='Mientras no lo haya, sale el de «Cartel por definir».')
    publicado = models.BooleanField(
        'publicado', default=True, help_text='Los que no están publicados no salen en el calendario.')
    # Los calendarios suscritos reconocen cada evento por su UID: no puede cambiar nunca.
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    creado = models.DateTimeField(auto_now_add=True)
    modificado = models.DateTimeField(auto_now=True)

    objects = EventoQuerySet.as_manager()

    @property
    def url_cartel(self):
        """Todo evento se comparte con cartel: si aún no tiene, uno genérico con el logo."""
        return self.cartel.url if self.cartel else static(CARTEL_POR_DEFINIR)

    @property
    def fin_aproximado(self):
        return self.inicio + datetime.timedelta(minutes=self.duración)

    @property
    def duración_aproximada(self):
        """«2 h», «1 h 30 min» o «45 min»."""
        horas, minutos = divmod(self.duración, 60)
        return ' '.join(filter(None, [f'{horas} h' if horas else '', f'{minutos} min' if minutos else '']))

    @property
    def ya_pasó(self):
        return self.fin_aproximado < timezone.now()

    def __str__(self):
        return f'{self.título} ({timezone.localtime(self.inicio):%d/%m/%Y %H:%M})'

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['inicio']
        constraints = [
            models.CheckConstraint(condition=models.Q(duración__gt=0), name='evento_duración_positiva'),
        ]
