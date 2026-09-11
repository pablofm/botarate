from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Socio, TipoDocumento

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
