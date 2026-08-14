import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Alumno, Curso, DíaSemana, Socio

ALTA = {
    'nombre': 'Ana Ruiz',
    'dni': '12345678Z',
    'teléfono': '600 123 456',
    'email': 'ana@example.com',
    'acepta_tratamiento_datos': 'on',
    'acepta_inscripción': 'on',
}


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
            nombre='Ana Ruiz', dni='12345678Z', teléfono='600 123 456', email='ana@example.com')

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
            nombre='Ana Ruiz', dni='12345678Z', teléfono='600 123 456', email='ana@example.com')
        Alumno.objects.create(socio=socia).cursos.add(cls.curso)

    def setUp(self):
        self.client.force_login(self.profesor)

    def test_la_ficha_del_curso_lista_a_las_alumnas_con_sus_datos(self):
        respuesta = self.client.get(reverse('curso_detalle', args=[self.curso.pk]))

        for dato in ('Ana Ruiz', '12345678Z', '600 123 456', 'ana@example.com'):
            self.assertContains(respuesta, dato)

    def test_el_listado_de_socias_indica_a_qué_cursos_van(self):
        Socio.objects.create(
            nombre='Eva Gil', dni='X1234567L', teléfono='600 999 888', email='eva@example.com')

        respuesta = self.client.get(reverse('socios'))

        self.assertContains(respuesta, 'Títeres')
        self.assertContains(respuesta, 'Eva Gil')
        self.assertContains(respuesta, 'No va a clase')

    def test_el_dashboard_cuenta_las_alumnas_del_curso(self):
        respuesta = self.client.get(reverse('dashboard'))

        cursos = {curso.pk: curso for curso in respuesta.context['cursos']}
        self.assertEqual(cursos[self.curso.pk].total_alumnos, 1)


class PortadaPúblicaTests(TestCase):
    """La portada es el alta de socios: se llega por el QR, sin cuenta ninguna."""

    def test_cualquiera_puede_ver_el_formulario_de_alta(self):
        respuesta = self.client.get(reverse('socio_nuevo'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Hazte socia de Botarate')

    def test_el_alta_sin_cuenta_acaba_en_la_página_de_gracias(self):
        respuesta = self.client.post(reverse('socio_nuevo'), ALTA)

        self.assertRedirects(respuesta, reverse('alta_hecha'))
        self.assertEqual(Socio.objects.get().nombre, 'Ana Ruiz')
        self.assertContains(self.client.get(reverse('alta_hecha')), 'Ya eres socia')

    def test_el_resto_de_la_aplicación_sigue_pidiendo_entrar(self):
        for nombre in ('dashboard', 'socios', 'alumno_matricular'):
            with self.subTest(url=nombre):
                respuesta = self.client.get(reverse(nombre))
                self.assertRedirects(
                    respuesta, f'{reverse("login")}?next={reverse(nombre)}')


class SocioTests(TestCase):
    def setUp(self):
        self.profesor = get_user_model().objects.create_user(
            email='profe@botarate.es', password='x', is_active=True)
        self.client.force_login(self.profesor)

    def test_alta_de_socia_con_dni_normalizado(self):
        respuesta = self.client.post(reverse('socio_nuevo'), {**ALTA, 'dni': 'x1234567-l'})

        self.assertRedirects(respuesta, reverse('socios'))
        self.assertEqual(Socio.objects.get().dni, 'X1234567L')

    def test_rechaza_el_dni_con_letra_incorrecta(self):
        respuesta = self.client.post(reverse('socio_nuevo'), {**ALTA, 'dni': '12345678A'})

        self.assertContains(respuesta, 'NIF')
        self.assertFalse(Socio.objects.exists())

    def test_rechaza_un_dni_ya_registrado(self):
        self.client.post(reverse('socio_nuevo'), ALTA)

        respuesta = self.client.post(reverse('socio_nuevo'), {**ALTA, 'nombre': 'Ana R.'})

        self.assertContains(respuesta, 'Ya hay un socio dado de alta con este DNI')
        self.assertEqual(Socio.objects.count(), 1)


class ConsentimientosTests(TestCase):
    def test_no_deja_darse_de_alta_sin_aceptar_los_dos_obligatorios(self):
        for obligatorio in ('acepta_tratamiento_datos', 'acepta_inscripción'):
            with self.subTest(campo=obligatorio):
                respuesta = self.client.post(
                    reverse('socio_nuevo'), {**ALTA, obligatorio: ''})

                self.assertFormError(
                    respuesta.context['form'], obligatorio, 'Este campo es obligatorio.')
                self.assertFalse(Socio.objects.exists())

    def test_guarda_lo_aceptado_y_lo_no_aceptado(self):
        self.client.post(reverse('socio_nuevo'), {**ALTA, 'quiere_whatsapp': 'on'})

        socia = Socio.objects.get()
        self.assertTrue(socia.acepta_tratamiento_datos)
        self.assertTrue(socia.acepta_inscripción)
        self.assertTrue(socia.quiere_whatsapp)
        self.assertFalse(socia.quiere_comunicaciones)

    def test_el_formulario_enseña_los_cuatro_consentimientos(self):
        respuesta = self.client.get(reverse('socio_nuevo'))

        self.assertContains(respuesta, 'Legales')
        self.assertContains(respuesta, 'Comunicaciones')
        for casilla in ('acepta_tratamiento_datos', 'acepta_inscripción',
                        'quiere_comunicaciones', 'quiere_whatsapp'):
            self.assertContains(respuesta, f'name="{casilla}"')
