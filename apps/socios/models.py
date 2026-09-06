from django.db import models
from django.utils import timezone

from .fields import DNIField
from .validators import validar_teléfono


class Socio(models.Model):
    """Toda persona dada de alta en Botarate: es de donde salen los datos personales.

    Solo algunos socios van a clase; esos tienen además su ficha de Alumno.
    """

    # No es auto_now_add para poder fijar la fecha real de los socios antiguos.
    fecha_alta = models.DateField('fecha de alta', default=timezone.localdate)
    nombre = models.CharField('nombre completo', max_length=200)
    dni = DNIField(
        'DNI',
        unique=True,
        help_text='DNI o NIE, con la letra',
        error_messages={'unique': 'Ya hay un socio dado de alta con este DNI.'})
    teléfono = models.CharField('teléfono', max_length=20, validators=[validar_teléfono])
    email = models.EmailField('email')
    # Los dos primeros consentimientos son obligatorios: quien los exige es SocioForm.
    acepta_tratamiento_datos = models.BooleanField(
        'Acepto el tratamiento de mis datos personales',
        default=False,
        help_text='Autorizo a la Asociación Cultural Botarate a tratar mis datos personales '
                  'conforme a la normativa vigente y a almacenarlos mientras exista relación '
                  'entre la asociación y mi participación en sus actividades.')
    acepta_inscripción = models.BooleanField(
        'Acepto mi inscripción como socia/o de la asociación',
        default=False,
        help_text='Comprendo que la inscripción es un requisito administrativo para participar '
                  'en actividades y que no implica cargos de gestión ni responsabilidades internas.')
    quiere_comunicaciones = models.BooleanField(
        'Quiero recibir información sobre cursos, talleres y actividades',
        blank=True,
        default=False,
        help_text='Autorizo a Botarate a enviarme comunicaciones informativas sobre '
                  'actividades culturales.')
    quiere_whatsapp = models.BooleanField(
        'Quiero unirme a la comunidad de WhatsApp de Botarate',
        blank=True,
        default=False,
        help_text='Acepto ser añadida/o al grupo de WhatsApp para recibir avisos y participar '
                  'en la comunidad interna.')

    def clean(self):
        super().clean()
        self.teléfono = ' '.join(self.teléfono.split())

    @property
    def es_alumno(self):
        return hasattr(self, 'alumno')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Socio'
        verbose_name_plural = 'Socios'
        ordering = ['nombre']
