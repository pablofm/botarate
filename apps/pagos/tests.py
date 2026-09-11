import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.clases.models import Alumno, Curso, DíaSemana
from apps.socios.models import Socio

from .models import FormaPago, Modalidad, Pago, sumar_meses


class PagoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.administrativo = User.objects.create_user(
            email='admin@botarate.es', password='x', is_active=True, is_staff=True)
        cls.profesor = User.objects.create_user(email='profe@botarate.es', password='x', is_active=True)
        cls.curso = Curso.objects.create(
            nombre='Bufón',
            días_semana=[DíaSemana.MIÉRCOLES],
            hora_inicio=datetime.time(19, 45),
            hora_fin=datetime.time(21, 15),
            profesor_principal=cls.profesor)
        cls.otro_curso = Curso.objects.create(
            nombre='Melodrama',
            días_semana=[DíaSemana.VIERNES],
            hora_inicio=datetime.time(18, 0),
            hora_fin=datetime.time(19, 30),
            profesor_principal=cls.profesor)
        socia = Socio.objects.create(
            nombre='Ana Ruiz', documento='12345678Z', teléfono='600 123 456', email='ana@example.com')
        cls.alumna = Alumno.objects.create(socio=socia)
        cls.alumna.cursos.add(cls.curso)
        cls.matrícula = Alumno.cursos.through.objects.get(alumno=cls.alumna, curso=cls.curso)

    def setUp(self):
        self.client.force_login(self.administrativo)

    def datos(self, **cambios):
        return {
            'matrícula': self.matrícula.pk,
            'modalidad': Modalidad.MENSUAL,
            'desde': '2026-10-01',
            'importe': '45.00',
            'forma_pago': FormaPago.EFECTIVO,
            'fecha': '2026-09-11',
            **cambios,
        }

    def test_registra_un_pago_mensual_de_una_alumna(self):
        respuesta = self.client.post(reverse('pago_nuevo'), self.datos())

        self.assertRedirects(respuesta, reverse('pagos'))
        pago = Pago.objects.get()
        self.assertEqual((pago.alumno, pago.curso), (self.alumna, self.curso))
        self.assertEqual(pago.importe, Decimal('45.00'))
        self.assertEqual(pago.registrado_por, self.administrativo)
        self.assertEqual(pago.hasta, datetime.date(2026, 10, 31))

    def test_cada_modalidad_cubre_su_periodo(self):
        esperado = {
            Modalidad.CLASE: datetime.date(2026, 10, 1),
            Modalidad.MENSUAL: datetime.date(2026, 10, 31),
            Modalidad.TRIMESTRAL: datetime.date(2026, 12, 31),
            Modalidad.ANUAL: datetime.date(2027, 9, 30),
        }
        for modalidad, hasta in esperado.items():
            with self.subTest(modalidad=modalidad):
                pago = Pago(modalidad=modalidad, desde=datetime.date(2026, 10, 1))
                self.assertEqual(pago.hasta, hasta)

    def test_admite_las_formas_de_pago_activas(self):
        for forma in (FormaPago.TRANSFERENCIA, FormaPago.EFECTIVO, FormaPago.DATÁFONO):
            with self.subTest(forma=forma):
                respuesta = self.client.post(reverse('pago_nuevo'), self.datos(forma_pago=forma))
                self.assertRedirects(respuesta, reverse('pagos'))
        self.assertEqual(Pago.objects.count(), 3)

    def test_bizum_sale_desactivado_y_no_se_puede_usar(self):
        formulario = self.client.get(reverse('pago_nuevo'))
        self.assertContains(formulario, 'Bizum (pendiente de activar)')
        self.assertRegex(formulario.content.decode(), r'value="BIZUM"[^>]*\bdisabled\b')

        respuesta = self.client.post(reverse('pago_nuevo'), self.datos(forma_pago=FormaPago.BIZUM))

        self.assertContains(respuesta, 'Bizum está pendiente de activar')
        self.assertFalse(Pago.objects.exists())

    def test_solo_se_cobra_a_matriculadas_en_ese_curso(self):
        formulario = self.client.get(reverse('pago_nuevo')).context['form']

        self.assertQuerySetEqual(formulario.fields['matrícula'].queryset, [self.matrícula])

    def test_rechaza_un_importe_de_cero(self):
        respuesta = self.client.post(reverse('pago_nuevo'), self.datos(importe='0'))

        self.assertFormError(
            respuesta.context['form'], 'importe', 'Asegúrese de que este valor es mayor o igual a 0.01.')
        self.assertFalse(Pago.objects.exists())

    def test_desde_la_ficha_del_curso_llega_elegida_la_alumna(self):
        ficha = self.client.get(reverse('curso_detalle', args=[self.curso.pk]))
        enlace = f'{reverse("pago_nuevo")}?alumno={self.alumna.pk}&amp;curso={self.curso.pk}'
        self.assertContains(ficha, enlace)

        formulario = self.client.get(
            reverse('pago_nuevo'), {'alumno': self.alumna.pk, 'curso': self.curso.pk}).context['form']

        self.assertEqual(formulario.initial['matrícula'], self.matrícula)

    def test_el_pago_se_conserva_aunque_se_desmatricule(self):
        self.client.post(reverse('pago_nuevo'), self.datos())

        self.client.post(reverse('alumno_desmatricular', args=[self.curso.pk, self.alumna.pk]))

        self.assertContains(self.client.get(reverse('pagos')), 'Ana Ruiz')

    def test_el_profesorado_no_ve_los_pagos(self):
        self.client.force_login(self.profesor)

        for nombre in ('pagos', 'pago_nuevo'):
            with self.subTest(url=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 403)
        self.assertNotContains(self.client.get(reverse('curso_detalle', args=[self.curso.pk])), 'Registrar pago')


class SumarMesesTests(SimpleTestCase):
    def test_si_el_día_no_existe_se_queda_en_el_último_del_mes(self):
        self.assertEqual(sumar_meses(datetime.date(2027, 1, 31), 1), datetime.date(2027, 2, 28))
        self.assertEqual(sumar_meses(datetime.date(2026, 11, 30), 3), datetime.date(2027, 2, 28))
        self.assertEqual(sumar_meses(datetime.date(2026, 12, 15), 12), datetime.date(2027, 12, 15))
