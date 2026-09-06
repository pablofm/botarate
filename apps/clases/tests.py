import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.socios.models import Socio

from .models import Alumno, Curso, DíaSemana


class MatricularAlumnaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profesor = get_user_model().objects.create_user(
            email='profe@botarate.es', password='x', is_active=True)
        cls.curso = Curso.objects.create(
            nombre='Acrobacia',
            días_semana=[DíaSemana.MARTES],
            hora_inicio=datetime.time(18, 0),
            hora_fin=datetime.time(19, 30),
            profesor_principal=cls.profesor)
        cls.otro_curso = Curso.objects.create(
            nombre='Esgrima escénica',
            días_semana=[DíaSemana.VIERNES],
            hora_inicio=datetime.time(18, 0),
            hora_fin=datetime.time(19, 30),
            profesor_principal=cls.profesor)
        cls.socia = Socio.objects.create(
            nombre='Ana Ruiz', documento='12345678Z', teléfono='600 123 456', email='ana@example.com')

    def setUp(self):
        self.client.force_login(self.profesor)

    def test_se_matricula_eligiendo_socia_sin_repetir_sus_datos(self):
        respuesta = self.client.post(
            reverse('alumno_matricular'), {'socio': self.socia.pk, 'curso': self.curso.pk})

        self.assertRedirects(respuesta, reverse('curso_detalle', args=[self.curso.pk]))
        alumna = Alumno.objects.get(socio=self.socia)
        self.assertQuerySetEqual(alumna.cursos.all(), [self.curso])

    def test_la_misma_socia_puede_ir_a_varios_cursos_con_una_sola_ficha(self):
        for curso in (self.curso, self.otro_curso):
            self.client.post(reverse('alumno_matricular'), {'socio': self.socia.pk, 'curso': curso.pk})

        self.assertEqual(Alumno.objects.count(), 1)
        self.assertQuerySetEqual(
            Alumno.objects.get().cursos.order_by('nombre'), [self.curso, self.otro_curso])

    def test_no_se_puede_matricular_dos_veces_en_el_mismo_curso(self):
        datos = {'socio': self.socia.pk, 'curso': self.curso.pk}
        self.client.post(reverse('alumno_matricular'), datos)

        respuesta = self.client.post(reverse('alumno_matricular'), datos)

        self.assertContains(respuesta, 'ya está matriculada en Acrobacia')
        self.assertEqual(Alumno.objects.get().cursos.count(), 1)

    def test_solo_ofrece_los_cursos_que_gestiona_quien_matricula(self):
        otra_profesora = get_user_model().objects.create_user(
            email='otra@botarate.es', password='x', is_active=True)
        self.curso.profesores_sustitutos.add(otra_profesora)
        self.client.force_login(otra_profesora)

        formulario = self.client.get(reverse('alumno_matricular')).context['form']

        self.assertQuerySetEqual(formulario.fields['curso'].queryset, [self.curso])

    def test_no_deja_matricular_a_quien_no_gestiona_ningún_curso(self):
        self.client.force_login(get_user_model().objects.create_user(
            email='nadie@botarate.es', password='x', is_active=True))

        self.assertEqual(self.client.get(reverse('alumno_matricular')).status_code, 403)


class PáginasTests(TestCase):
    """Las plantillas cogen los datos personales del socio, no del alumno."""

    @classmethod
    def setUpTestData(cls):
        cls.profesor = get_user_model().objects.create_user(
            email='profe@botarate.es', password='x', is_active=True)
        cls.curso = Curso.objects.create(
            nombre='Títeres',
            días_semana=[DíaSemana.MIÉRCOLES],
            hora_inicio=datetime.time(19, 45),
            hora_fin=datetime.time(21, 15),
            profesor_principal=cls.profesor)
        socia = Socio.objects.create(
            nombre='Ana Ruiz', documento='12345678Z', teléfono='600 123 456', email='ana@example.com')
        Alumno.objects.create(socio=socia).cursos.add(cls.curso)

    def setUp(self):
        self.client.force_login(self.profesor)

    def test_la_ficha_del_curso_lista_a_las_alumnas_con_sus_datos(self):
        respuesta = self.client.get(reverse('curso_detalle', args=[self.curso.pk]))

        for dato in ('Ana Ruiz', '12345678Z', '600 123 456', 'ana@example.com'):
            self.assertContains(respuesta, dato)

    def test_el_listado_de_socias_indica_a_qué_cursos_van(self):
        Socio.objects.create(
            nombre='Eva Gil', documento='X1234567L', teléfono='600 999 888', email='eva@example.com')

        respuesta = self.client.get(reverse('socios'))

        self.assertContains(respuesta, 'Títeres')
        self.assertContains(respuesta, 'Eva Gil')
        self.assertContains(respuesta, 'No va a clase')

    def test_el_dashboard_cuenta_las_alumnas_del_curso(self):
        respuesta = self.client.get(reverse('dashboard'))

        cursos = {curso.pk: curso for curso in respuesta.context['cursos']}
        self.assertEqual(cursos[self.curso.pk].total_alumnos, 1)
