from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from .fields import DNIField
from .validators import validar_teléfono


class DíaSemana(models.IntegerChoices):
    LUNES = 1, 'Lunes'
    MARTES = 2, 'Martes'
    MIÉRCOLES = 3, 'Miércoles'
    JUEVES = 4, 'Jueves'
    VIERNES = 5, 'Viernes'
    SÁBADO = 6, 'Sábado'
    DOMINGO = 7, 'Domingo'


class CursoQuerySet(models.QuerySet):
    def gestionables_por(self, usuario):
        """Cursos que este usuario puede dar y gestionar.

        Los administradores, todos; el resto, aquellos de los que son profesor
        principal o sustituto.
        """
        if usuario.is_staff or usuario.is_superuser:
            return self
        return self.filter(
            models.Q(profesor_principal=usuario) | models.Q(profesores_sustitutos=usuario)
        ).distinct()


class Curso(models.Model):
    nombre = models.CharField(max_length=200)
    días_semana = ArrayField(
        models.PositiveSmallIntegerField(choices=DíaSemana),
        size=7,
        verbose_name='días de la semana',
        help_text='Días en los que se imparte el curso')
    hora_inicio = models.TimeField('hora de inicio')
    hora_fin = models.TimeField('hora de fin')
    profesor_principal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cursos_impartidos',
        verbose_name='profesor principal')
    profesores_sustitutos = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='cursos_sustituidos',
        verbose_name='profesores sustitutos',
        help_text='Además del principal, quienes pueden dar este curso')

    objects = CursoQuerySet.as_manager()

    def gestionable_por(self, usuario):
        return (usuario.is_staff
                or usuario.is_superuser
                or self.profesor_principal_id == usuario.pk
                or self.profesores_sustitutos.filter(pk=usuario.pk).exists())

    @property
    def profesorado(self):
        """El titular y sus sustitutos, que son quienes pueden dar el curso."""
        return [self.profesor_principal, *self.profesores_sustitutos.all()]

    @property
    def días_semana_display(self):
        return ', '.join(DíaSemana(día).label for día in sorted(self.días_semana))

    def se_imparte_el(self, fecha):
        return fecha.isoweekday() in self.días_semana

    def __str__(self):
        return f'{self.nombre} ({self.días_semana_display} {self.hora_inicio:%H:%M})'

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['días_semana', 'hora_inicio', 'nombre']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hora_fin__gt=models.F('hora_inicio')),
                name='curso_hora_fin_posterior_a_inicio'),
        ]


class Socio(models.Model):
    """Toda persona dada de alta en Botarate: es de donde salen los datos personales.

    Solo algunos socios van a clase; esos tienen además su ficha de Alumno.
    """

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


class Alumno(models.Model):
    """El socio que además va a clase, con los cursos en los que está matriculado."""

    socio = models.OneToOneField(
        Socio,
        on_delete=models.PROTECT,
        related_name='alumno',
        verbose_name='socio')
    cursos = models.ManyToManyField(Curso, related_name='alumnos', verbose_name='cursos')

    def __str__(self):
        return str(self.socio)

    class Meta:
        verbose_name = 'Alumno'
        verbose_name_plural = 'Alumnos'
        ordering = ['socio__nombre']


class Clase(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='clases')
    profesor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='clases_impartidas',
        verbose_name='profesor')
    inicio = models.DateTimeField('hora de inicio')
    fin = models.DateTimeField('Fin de la clase', null=True, blank=True)
    asistentes = models.ManyToManyField(Alumno, blank=True, related_name='clases_asistidas')

    @property
    def está_abierta(self):
        return self.fin is None

    @property
    def duración_display(self):
        if self.está_abierta:
            return ''
        horas, minutos = divmod(int((self.fin - self.inicio).total_seconds() // 60), 60)
        return f'{horas} h {minutos:02d} min' if horas else f'{minutos} min'

    def __str__(self):
        return f'{self.curso.nombre} — {self.inicio}'

    class Meta:
        verbose_name = 'Clase'
        verbose_name_plural = 'Clases'
        ordering = ['-inicio']
        constraints = [
            models.UniqueConstraint(
                fields=['profesor'],
                condition=models.Q(fin__isnull=True),
                name='una_clase_abierta_por_profesor',
                violation_error_message='Este profesor ya tiene una clase empezada sin terminar.'),
        ]
