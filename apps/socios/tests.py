import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clases.models import Alumno, Curso, DíaSemana

from .models import Nota, Socio, TipoDocumento

ALTA = {
    'nombre': 'Ana Ruiz',
    'tipo_documento': TipoDocumento.NIF,
    'documento': '12345678Z',
    'teléfono': '600 123 456',
    'email': 'ana@example.com',
    'acepta_tratamiento_datos': 'on',
    'acepta_inscripción': 'on',
}


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
        respuesta = self.client.post(reverse('socio_nuevo'), {**ALTA, 'documento': 'x1234567-l'})

        self.assertRedirects(respuesta, reverse('socios'))
        self.assertEqual(Socio.objects.get().documento, 'X1234567L')

    def test_rechaza_el_dni_con_letra_incorrecta(self):
        respuesta = self.client.post(reverse('socio_nuevo'), {**ALTA, 'documento': '12345678A'})

        self.assertContains(respuesta, 'NIF')
        self.assertFalse(Socio.objects.exists())

    def test_rechaza_un_documento_ya_registrado(self):
        self.client.post(reverse('socio_nuevo'), ALTA)

        respuesta = self.client.post(reverse('socio_nuevo'), {**ALTA, 'nombre': 'Ana R.'})

        self.assertContains(respuesta, 'Ya hay un socio dado de alta con este documento')
        self.assertEqual(Socio.objects.count(), 1)

    def test_alta_de_extranjera_con_pasaporte(self):
        """Quien no tiene DNI ni NIE se da de alta con otro documento, sin letra que valga."""
        respuesta = self.client.post(
            reverse('socio_nuevo'),
            {**ALTA, 'tipo_documento': TipoDocumento.PASAPORTE, 'documento': '547302118'})

        self.assertRedirects(respuesta, reverse('socios'))
        self.assertEqual(Socio.objects.get().documento, '547302118')

    def test_el_documento_repetido_lo_es_aunque_cambie_el_tipo(self):
        self.client.post(reverse('socio_nuevo'), ALTA)

        respuesta = self.client.post(
            reverse('socio_nuevo'),
            {**ALTA, 'nombre': 'Otra Ana', 'tipo_documento': TipoDocumento.OTRO})

        self.assertContains(respuesta, 'Ya hay un socio dado de alta con este documento')
        self.assertEqual(Socio.objects.count(), 1)


class BuscadorSociosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profesor = get_user_model().objects.create_user(
            email='profe@botarate.es', password='x', is_active=True)
        Socio.objects.create(
            nombre='Ana Ruiz', documento='12345678Z', teléfono='600 123 456', email='ana@example.com')
        Socio.objects.create(
            nombre='Eva Gil', documento='X1234567L', teléfono='611 999 888', email='eva@correo.es')

    def setUp(self):
        self.client.force_login(self.profesor)

    def nombres(self, búsqueda):
        respuesta = self.client.get(reverse('socios'), {'q': búsqueda})
        return [socia.nombre for socia in respuesta.context['socios']]

    def test_busca_por_nombre_documento_teléfono_o_email(self):
        for búsqueda in ('ruiz', '12345678z', '600 123', 'ana@example'):
            with self.subTest(búsqueda=búsqueda):
                self.assertEqual(self.nombres(búsqueda), ['Ana Ruiz'])

    def test_no_distingue_tildes_ni_en_la_socia_ni_en_la_búsqueda(self):
        Socio.objects.create(
            nombre='Lucía Martínez', documento='Y1234567X', teléfono='622 333 444', email='lucía@example.com')

        for búsqueda in ('lucia martinez', 'MARTÍNEZ', 'lucia@'):
            with self.subTest(búsqueda=búsqueda):
                self.assertEqual(self.nombres(búsqueda), ['Lucía Martínez'])
        self.assertEqual(self.nombres('Ruíz'), ['Ana Ruiz'])

    def test_el_teléfono_se_encuentra_con_o_sin_separadores(self):
        # Sin pasar por clean(): así queda como lo guardaría quien lo escriba con puntos.
        Socio.objects.create(
            nombre='Eva Luna', documento='Y7654321G', teléfono='+34 622.333.444', email='luna@example.com')

        for búsqueda in ('600123456', '600-123', '600.123.456'):
            with self.subTest(búsqueda=búsqueda):
                self.assertEqual(self.nombres(búsqueda), ['Ana Ruiz'])
        self.assertEqual(self.nombres('622 333 444'), ['Eva Luna'])

    def test_una_búsqueda_de_solo_separadores_no_saca_a_todas(self):
        self.assertEqual(self.nombres('-'), [])

    def test_sin_búsqueda_salen_todas(self):
        self.assertEqual(self.nombres('  '), ['Ana Ruiz', 'Eva Gil'])

    def test_avisa_cuando_no_hay_ninguna_coincidencia(self):
        respuesta = self.client.get(reverse('socios'), {'q': 'Zoe'})

        self.assertContains(respuesta, 'Ninguna socia coincide con «Zoe»')
        self.assertContains(respuesta, 'Ver todas')


class OrdenSociosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profesor = get_user_model().objects.create_user(
            email='profe@botarate.es', password='x', is_active=True)
        cls.ana = Socio.objects.create(
            nombre='Ana Ruiz', documento='12345678Z', teléfono='600 123 456', email='ana@example.com')
        cls.eva = Socio.objects.create(
            nombre='Eva Gil', documento='X1234567L', teléfono='611 999 888', email='eva@correo.es')
        cls.zoe = Socio.objects.create(
            nombre='Zoe Paz', documento='Y1234567X', teléfono='622 333 444', email='zoe@example.com')
        # auto_now_add no deja elegir la fecha al crear: Eva es la más antigua y Ana la más reciente.
        for socia, día in ((cls.eva, 1), (cls.zoe, 2), (cls.ana, 3)):
            Socio.objects.filter(pk=socia.pk).update(
                fecha_alta=datetime.datetime(2026, 9, día, tzinfo=datetime.timezone.utc))

        horario = {'días_semana': [DíaSemana.LUNES], 'hora_inicio': datetime.time(18, 0),
                   'hora_fin': datetime.time(20, 0), 'profesor_principal': cls.profesor}
        acrobacia = Curso.objects.create(nombre='Acrobacia', **horario)
        clown = Curso.objects.create(nombre='Clown', **horario)
        Alumno.objects.create(socio=cls.zoe).cursos.set([acrobacia, clown])
        Alumno.objects.create(socio=cls.ana).cursos.set([clown])

        for _ in range(2):
            Nota.objects.create(socio=cls.eva, texto='Llamó.')
        Nota.objects.create(socio=cls.zoe, texto='Llamó.')

    def setUp(self):
        self.client.force_login(self.profesor)

    def nombres(self, orden, búsqueda=''):
        respuesta = self.client.get(reverse('socios'), {'orden': orden, 'q': búsqueda})
        return [socia.nombre for socia in respuesta.context['socios']]

    def test_ordena_por_cada_columna_en_los_dos_sentidos(self):
        casos = {
            'nombre': ['Ana Ruiz', 'Eva Gil', 'Zoe Paz'],
            '-nombre': ['Zoe Paz', 'Eva Gil', 'Ana Ruiz'],
            'fecha_alta': ['Eva Gil', 'Zoe Paz', 'Ana Ruiz'],
            '-fecha_alta': ['Ana Ruiz', 'Zoe Paz', 'Eva Gil'],
            'notas': ['Ana Ruiz', 'Zoe Paz', 'Eva Gil'],
            '-notas': ['Eva Gil', 'Zoe Paz', 'Ana Ruiz'],
            # Por el primer curso de cada una; quien no va a clase, siempre al final.
            'cursos': ['Zoe Paz', 'Ana Ruiz', 'Eva Gil'],
            '-cursos': ['Ana Ruiz', 'Zoe Paz', 'Eva Gil'],
        }
        for orden, nombres in casos.items():
            with self.subTest(orden=orden):
                self.assertEqual(self.nombres(orden), nombres)

    def test_un_orden_desconocido_ordena_por_nombre(self):
        self.assertEqual(self.nombres('documento'), ['Ana Ruiz', 'Eva Gil', 'Zoe Paz'])

    def test_ordena_también_los_resultados_de_una_búsqueda(self):
        self.assertEqual(self.nombres('-notas', búsqueda='example'), ['Zoe Paz', 'Ana Ruiz'])

    def test_la_cabecera_indica_el_orden_y_le_da_la_vuelta(self):
        respuesta = self.client.get(reverse('socios'), {'orden': 'notas', 'q': 'example'})

        self.assertContains(respuesta, 'aria-sort="ascending"', count=1)
        self.assertEqual(respuesta.context['columnas']['notas']['url'], '?q=example&orden=-notas')
        # Las demás columnas empiezan por su sentido natural.
        self.assertEqual(respuesta.context['columnas']['fecha_alta']['url'], '?q=example&orden=-fecha_alta')
        self.assertEqual(respuesta.context['columnas']['nombre']['url'], '?q=example&orden=nombre')


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


class NotasTests(TestCase):
    """La bitácora de cada socia: anotaciones con fecha de las interacciones con ella."""

    @classmethod
    def setUpTestData(cls):
        cls.profesor = get_user_model().objects.create_user(
            email='profe@botarate.es', password='x', is_active=True)
        cls.socia = Socio.objects.create(
            nombre='Ana Ruiz', documento='12345678Z', teléfono='600 123 456', email='ana@example.com')

    def setUp(self):
        self.client.force_login(self.profesor)

    def test_el_listado_y_la_ficha_ofrecen_añadir_nota(self):
        añadir = reverse('nota_nueva', args=[self.socia.pk])

        self.assertContains(self.client.get(reverse('socios')), añadir)
        self.assertContains(self.client.get(reverse('socio_editar', args=[self.socia.pk])), añadir)

    def test_el_listado_muestra_las_notas_previas(self):
        Nota.objects.create(socio=self.socia, autor=self.profesor, texto='Pregunta por el curso de clown.')

        listado = self.client.get(reverse('socios'))

        self.assertContains(listado, f'id="notas-{self.socia.pk}"')
        self.assertContains(listado, 'Pregunta por el curso de clown.')
        self.assertNotContains(listado, 'Sin notas')

    def test_el_listado_indica_que_no_hay_notas(self):
        listado = self.client.get(reverse('socios'))

        self.assertContains(listado, 'Sin notas')
        self.assertNotContains(listado, f'id="notas-{self.socia.pk}"')

    def test_el_teléfono_del_listado_no_es_un_enlace(self):
        listado = self.client.get(reverse('socios'))

        self.assertContains(listado, '600 123 456')
        self.assertNotContains(listado, 'href="tel:')

    def test_el_listado_muestra_la_fecha_de_alta_en_hora_de_madrid(self):
        # A las 23:30 UTC del 31 de diciembre ya es 1 de enero en Madrid.
        Socio.objects.filter(pk=self.socia.pk).update(
            fecha_alta=datetime.datetime(2025, 12, 31, 23, 30, tzinfo=datetime.timezone.utc))

        self.assertContains(self.client.get(reverse('socios')), '01/01/2026')

    def test_añade_una_nota_con_fecha_y_texto(self):
        respuesta = self.client.post(
            reverse('nota_nueva', args=[self.socia.pk]),
            {'fecha': '2026-09-10', 'texto': 'Llamó para preguntar por el curso de clown.'})

        ficha = reverse('socio_editar', args=[self.socia.pk])
        self.assertRedirects(respuesta, ficha)
        nota = Nota.objects.get()
        self.assertEqual((nota.socio, nota.autor), (self.socia, self.profesor))
        self.assertEqual(nota.fecha, datetime.date(2026, 9, 10))
        self.assertContains(self.client.get(ficha), 'Llamó para preguntar por el curso de clown.')

    def test_la_nota_necesita_texto(self):
        respuesta = self.client.post(
            reverse('nota_nueva', args=[self.socia.pk]), {'fecha': '2026-09-10', 'texto': ''})

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Nota.objects.exists())

    def test_la_fecha_propone_hoy_y_usa_el_selector(self):
        respuesta = self.client.get(reverse('nota_nueva', args=[self.socia.pk]))

        self.assertContains(respuesta, 'id="id_fecha" data-dbdp-config')
        self.assertContains(respuesta, timezone.localdate().isoformat())

    def test_la_bitácora_va_de_la_nota_más_reciente_a_la_más_antigua(self):
        Nota.objects.create(socio=self.socia, fecha=datetime.date(2026, 1, 5), texto='Antigua')
        Nota.objects.create(socio=self.socia, fecha=datetime.date(2026, 9, 1), texto='Reciente')

        respuesta = self.client.get(reverse('socio_editar', args=[self.socia.pk]))

        contenido = respuesta.content.decode()
        self.assertLess(contenido.index('Reciente'), contenido.index('Antigua'))
