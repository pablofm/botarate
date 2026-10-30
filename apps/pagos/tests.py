import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.clases.models import Alumno, Curso, DíaSemana, Matrícula
from apps.socios.models import Socio

from .context_processors import matrículas_por_pagar
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
        cls.matrícula = Matrícula.objects.get(alumno=cls.alumna, curso=cls.curso)

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

    def test_elimina_un_pago_duplicado_sin_tocar_el_bueno(self):
        self.client.post(reverse('pago_nuevo'), self.datos())
        self.client.post(reverse('pago_nuevo'), self.datos())
        bueno, duplicado = Pago.objects.order_by('pk')

        respuesta = self.client.post(reverse('pago_eliminar', args=[duplicado.pk]))

        self.assertRedirects(respuesta, reverse('pagos'))
        self.assertQuerySetEqual(Pago.objects.all(), [bueno])

    def test_el_listado_ofrece_eliminar_cada_pago(self):
        self.client.post(reverse('pago_nuevo'), self.datos())
        pago = Pago.objects.get()

        self.assertContains(self.client.get(reverse('pagos')), reverse('pago_eliminar', args=[pago.pk]))

    def test_eliminar_un_pago_no_se_hace_por_GET(self):
        self.client.post(reverse('pago_nuevo'), self.datos())
        pago = Pago.objects.get()

        self.assertEqual(self.client.get(reverse('pago_eliminar', args=[pago.pk])).status_code, 405)
        self.assertTrue(Pago.objects.exists())

    def test_el_profesorado_no_ve_los_pagos(self):
        self.client.post(reverse('pago_nuevo'), self.datos())
        pago = Pago.objects.get()
        self.client.force_login(self.profesor)

        for nombre in ('pagos', 'pago_nuevo'):
            with self.subTest(url=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 403)
        self.assertNotContains(self.client.get(reverse('curso_detalle', args=[self.curso.pk])), 'Registrar pago')

        self.assertEqual(
            self.client.post(reverse('pago_eliminar', args=[pago.pk])).status_code, 403)
        self.assertTrue(Pago.objects.exists())


class SumarMesesTests(SimpleTestCase):
    def test_si_el_día_no_existe_se_queda_en_el_último_del_mes(self):
        self.assertEqual(sumar_meses(datetime.date(2027, 1, 31), 1), datetime.date(2027, 2, 28))
        self.assertEqual(sumar_meses(datetime.date(2026, 11, 30), 3), datetime.date(2027, 2, 28))
        self.assertEqual(sumar_meses(datetime.date(2026, 12, 15), 12), datetime.date(2027, 12, 15))


class AvisoDePagosTests(TestCase):
    HOY = datetime.date(2026, 10, 30)

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.administrativo = User.objects.create_user(
            email='admin@botarate.es', password='x', is_active=True, is_staff=True)
        cls.profesor = User.objects.create_user(email='profe@botarate.es', password='x', is_active=True)
        cls.curso = Curso.objects.create(
            nombre='Bufón', días_semana=[DíaSemana.MIÉRCOLES], hora_inicio=datetime.time(19, 45),
            hora_fin=datetime.time(21, 15), profesor_principal=cls.profesor)
        cls.otro_curso = Curso.objects.create(
            nombre='Melodrama', días_semana=[DíaSemana.VIERNES], hora_inicio=datetime.time(18, 0),
            hora_fin=datetime.time(19, 30), profesor_principal=cls.profesor)
        socia = Socio.objects.create(
            nombre='Ana Ruiz', documento='12345678Z', teléfono='600 123 456', email='ana@example.com')
        cls.alumna = Alumno.objects.create(socio=socia)
        cls.alumna.cursos.add(cls.curso)

    def pagar(self, modalidad, desde, curso=None):
        return Pago.objects.create(
            alumno=self.alumna, curso=curso or self.curso, modalidad=modalidad, desde=desde,
            importe=Decimal('45'), forma_pago=FormaPago.EFECTIVO, registrado_por=self.administrativo)

    def avisos(self):
        sin_pagar, por_pagar = matrículas_por_pagar(self.HOY)
        return ([(p['matrícula'].curso.nombre, p['cubierto_hasta']) for p in sin_pagar],
                [(p['matrícula'].curso.nombre, p['vence']) for p in por_pagar])

    def test_sin_ningún_pago_no_está_al_corriente(self):
        self.assertEqual(self.avisos(), ([('Bufón', None)], []))

    def test_con_lo_pagado_vencido_dice_hasta_cuándo_pagó(self):
        self.pagar(Modalidad.MENSUAL, datetime.date(2026, 9, 1))

        self.assertEqual(self.avisos(), ([('Bufón', datetime.date(2026, 9, 30))], []))

    def test_avisa_cinco_días_antes_de_que_se_acabe_lo_pagado(self):
        # Octubre se acaba mañana, así que el 1 de noviembre ya tiene que estar pagado.
        self.pagar(Modalidad.MENSUAL, datetime.date(2026, 10, 1))
        self.assertEqual(self.avisos(), ([], [('Bufón', datetime.date(2026, 11, 1))]))

    def test_no_avisa_si_aún_queda_más_de_cinco_días(self):
        self.pagar(Modalidad.MENSUAL, datetime.date(2026, 10, 4))  # Hay que pagar el 4 de noviembre.
        self.assertEqual(self.avisos(), ([], [('Bufón', datetime.date(2026, 11, 4))]))
        Pago.objects.all().delete()
        self.pagar(Modalidad.MENSUAL, datetime.date(2026, 10, 5))  # El 5, dentro de seis días.
        self.assertEqual(self.avisos(), ([], []))

    def test_el_mes_siguiente_ya_pagado_cuenta(self):
        self.pagar(Modalidad.MENSUAL, datetime.date(2026, 10, 1))
        self.pagar(Modalidad.MENSUAL, datetime.date(2026, 11, 1))

        self.assertEqual(self.avisos(), ([], []))

    def test_una_clase_suelta_solo_cubre_su_día(self):
        self.pagar(Modalidad.CLASE, datetime.date(2026, 10, 28))
        self.assertEqual(self.avisos(), ([('Bufón', datetime.date(2026, 10, 28))], []))
        self.pagar(Modalidad.CLASE, self.HOY)
        self.assertEqual(self.avisos()[1], [('Bufón', datetime.date(2026, 10, 31))])

    def test_cada_curso_se_paga_aparte(self):
        self.alumna.cursos.add(self.otro_curso)
        self.pagar(Modalidad.TRIMESTRAL, datetime.date(2026, 10, 1))
        # Lo pagado de otro curso no cuenta para este.
        self.pagar(Modalidad.ANUAL, datetime.date(2026, 1, 1), curso=self.curso)

        self.assertEqual(self.avisos(), ([('Melodrama', None)], []))

    def test_la_matrícula_exenta_de_pago_no_sale(self):
        self.alumna.cursos.add(self.otro_curso)
        Matrícula.objects.filter(curso=self.curso).update(exento_pago=True)

        # Solo es exenta la de Bufón: la de Melodrama sigue sin pagar.
        self.assertEqual(self.avisos(), ([('Melodrama', None)], []))

    def test_desmatriculada_no_sale(self):
        self.alumna.cursos.clear()
        self.assertEqual(self.avisos(), ([], []))

    def test_sale_en_el_modal_de_avisos_de_cualquier_página(self):
        self.client.force_login(self.administrativo)
        for vista in ('dashboard', 'socios', 'pagos', 'ventas_bebidas'):
            with self.subTest(vista=vista):
                html = self.client.get(reverse(vista)).content.decode()
                self.assertIn('data-bs-target="#avisos"', html)
                self.assertRegex(html, r'(?s)<td[^>]*text-danger[^>]*>Ana Ruiz</td>\s*<td>Bufón</td>')
                self.assertIn('Nunca ha pagado', html)

    def test_el_profesorado_no_ve_los_pagos(self):
        self.client.force_login(self.profesor)
        self.assertNotContains(self.client.get(reverse('dashboard')), 'Ana Ruiz')
