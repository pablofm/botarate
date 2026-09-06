from django.core.exceptions import ValidationError
from django.db import models
from localflavor.es.forms import ESIdentityCardNumberField

from .validators import validar_teléfono


class TipoDocumento(models.TextChoices):
    NIF = 'NIF', 'DNI o NIE'
    PASAPORTE = 'PAS', 'Pasaporte'
    OTRO = 'OTRO', 'Otro documento'


class Socio(models.Model):
    """Toda persona dada de alta en Botarate: es de donde salen los datos personales.

    Solo algunos socios van a clase; esos tienen además su ficha de Alumno.
    """

    fecha_alta = models.DateTimeField('fecha de alta', auto_now_add=True)
    nombre = models.CharField('nombre completo', max_length=200)
    tipo_documento = models.CharField(
        'tipo de documento',
        max_length=4,
        choices=TipoDocumento,
        default=TipoDocumento.NIF)
    # Único a secas, no junto al tipo: si no, el mismo número colado como NIF y como
    # pasaporte serían dos socios distintos, que es el duplicado que se quiere evitar.
    documento = models.CharField(
        'documento de identidad',
        max_length=20,
        unique=True,
        help_text='El DNI o NIE con la letra; quien no lo tenga, su pasaporte u otro documento.',
        error_messages={'unique': 'Ya hay un socio dado de alta con este documento.'})
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
        self.documento = self.documento.upper().replace(' ', '').replace('-', '')
        if self.tipo_documento == TipoDocumento.NIF:
            # La letra la comprueba localflavor; el resto de documentos son texto libre.
            try:
                ESIdentityCardNumberField(only_nif=True).clean(self.documento)
            except ValidationError as error:
                raise ValidationError({'documento': error.messages}) from error

    @property
    def es_alumno(self):
        return hasattr(self, 'alumno')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Socio'
        verbose_name_plural = 'Socios'
        ordering = ['nombre']
