import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.socios.models import Socio

from .models import Alumno, Clase, Curso, DíaSemana


class MatricularAlumnaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrativo = get_user_model().objects.create_user(
            email='admin@botarate.es', password='x', is_active=True, is_staff=True)
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
        self.client.force_login(self.administrativo)

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

    def test_el_profesorado_no_matricula_ni_desmatricula_ni_en_sus_cursos(self):
        alumna = Alumno.objects.create(socio=self.socia)
        alumna.cursos.add(self.curso)
        self.client.force_login(self.profesor)

        self.assertEqual(self.client.get(reverse('alumno_matricular')).status_code, 403)
        respuesta = self.client.post(
            reverse('alumno_matricular'), {'socio': self.socia.pk, 'curso': self.otro_curso.pk})
        self.assertEqual(respuesta.status_code, 403)
        respuesta = self.client.post(reverse('alumno_desmatricular', args=[self.curso.pk, alumna.pk]))
        self.assertEqual(respuesta.status_code, 403)
        self.assertQuerySetEqual(alumna.cursos.all(), [self.curso])

        self.assertEqual(self.client.get(reverse('matriculas')).status_code, 403)
        self.assertNotContains(self.client.get(reverse('dashboard')), 'Matrículas')
        ficha = self.client.get(reverse('curso_detalle', args=[self.curso.pk]))
        self.assertNotContains(ficha, 'Matricular alumna')
        self.assertNotContains(ficha, 'Eliminar matrícula')

    def test_el_listado_agrupa_los_cursos_bajo_el_nombre_de_cada_alumna(self):
        alumna = Alumno.objects.create(socio=self.socia)
        alumna.cursos.add(self.curso, self.otro_curso)

        respuesta = self.client.get(reverse('matriculas'))

        self.assertQuerySetEqual(respuesta.context['alumnas'], [alumna])
        # El nombre aparece una sola vez, con sus dos cursos al lado.
        self.assertContains(respuesta, 'Ana Ruiz', count=1)
        self.assertContains(respuesta, 'Acrobacia')
        self.assertContains(respuesta, 'Esgrima escénica')
        # El botón lleva al formulario de siempre.
        self.assertContains(respuesta, reverse('alumno_matricular'))

    def test_el_listado_no_saca_a_quien_se_ha_desmatriculado_de_todo(self):
        alumna = Alumno.objects.create(socio=self.socia)
        alumna.cursos.add(self.curso)
        alumna.cursos.remove(self.curso)

        respuesta = self.client.get(reverse('matriculas'))

        self.assertQuerySetEqual(respuesta.context['alumnas'], [])
        self.assertNotContains(respuesta, 'Ana Ruiz')

    def test_la_navegacion_conoce_el_rol_en_cualquier_pagina(self):
        """El context processor da el rol también donde la vista no lo calcula."""
        socios = reverse('socios')

        self.assertContains(self.client.get(socios), 'Matrículas')

        self.client.force_login(self.profesor)
        self.assertNotContains(self.client.get(socios), 'Matrículas')


class ClaseListTests(TestCase):
    """El listado de clases enseña a cada cual las de los cursos que le tocan."""

    @classmethod
    def setUpTestData(cls):
        cls.administrativo = get_user_model().objects.create_user(
            email='admin@botarate.es', password='x', is_active=True, is_staff=True)
        cls.profesor = get_user_model().objects.create_user(
            email='profe@botarate.es', password='x', is_active=True)
        cls.otro_profesor = get_user_model().objects.create_user(
            email='otro@botarate.es', password='x', is_active=True)
        cls.curso = Curso.objects.create(
            nombre='Acrobacia',
            días_semana=[DíaSemana.MARTES],
            hora_inicio=datetime.time(18, 0),
            hora_fin=datetime.time(19, 30),
            profesor_principal=cls.profesor)
        cls.curso_ajeno = Curso.objects.create(
            nombre='Esgrima escénica',
            días_semana=[DíaSemana.VIERNES],
            hora_inicio=datetime.time(18, 0),
            hora_fin=datetime.time(19, 30),
            profesor_principal=cls.otro_profesor)

        inicio = timezone.now() - datetime.timedelta(days=1)
        cls.clase = Clase.objects.create(
            curso=cls.curso, profesor=cls.profesor,
            inicio=inicio, fin=inicio + datetime.timedelta(hours=1))
        cls.clase_ajena = Clase.objects.create(
            curso=cls.curso_ajeno, profesor=cls.otro_profesor,
            inicio=inicio, fin=inicio + datetime.timedelta(hours=1),
            reporte='Se rompió un florete.')

    def test_el_profesorado_solo_ve_las_clases_de_sus_cursos(self):
        self.client.force_login(self.profesor)

        respuesta = self.client.get(reverse('clases'))

        self.assertQuerySetEqual(respuesta.context['clases'], [self.clase])
        self.assertNotContains(respuesta, 'Se rompió un florete.')

    def test_la_administración_ve_todas_las_clases(self):
        self.client.force_login(self.administrativo)

        respuesta = self.client.get(reverse('clases'))

        self.assertQuerySetEqual(
            respuesta.context['clases'], [self.clase, self.clase_ajena], ordered=False)

    def test_solo_la_administración_ve_y_usa_el_enlace_de_editar(self):
        editar = reverse('clase_editar', args=[self.clase.pk])

        self.client.force_login(self.administrativo)
        self.assertContains(self.client.get(reverse('clases')), editar)
        self.assertEqual(self.client.get(editar).status_code, 200)

        self.client.force_login(self.profesor)
        self.assertNotContains(self.client.get(reverse('clases')), editar)
        self.assertEqual(self.client.get(editar).status_code, 403)

    def test_la_administración_corrige_los_datos_de_una_clase(self):
        self.client.force_login(self.administrativo)

        respuesta = self.client.post(reverse('clase_editar', args=[self.clase.pk]), {
            'curso': self.curso.pk,
            'profesor': self.profesor.pk,
            'inicio': self.clase.inicio.isoformat(),
            'fin': self.clase.fin.isoformat(),
            'reporte': 'Se corrigió la hora.'})

        self.assertRedirects(respuesta, reverse('clases'))
        self.clase.refresh_from_db()
        self.assertEqual(self.clase.reporte, 'Se corrigió la hora.')

    def test_un_sustituto_ve_las_clases_del_curso_que_sustituye(self):
        self.curso_ajeno.profesores_sustitutos.add(self.profesor)
        self.client.force_login(self.profesor)

        respuesta = self.client.get(reverse('clases'))

        self.assertQuerySetEqual(
            respuesta.context['clases'], [self.clase, self.clase_ajena], ordered=False)


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

    def test_la_ficha_del_curso_lista_a_las_alumnas_por_su_nombre(self):
        respuesta = self.client.get(reverse('curso_detalle', args=[self.curso.pk]))

        self.assertContains(respuesta, 'Ana Ruiz')

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
