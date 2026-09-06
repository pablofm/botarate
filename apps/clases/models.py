from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.socios.models import Socio


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
