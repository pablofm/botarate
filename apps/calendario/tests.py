import datetime
import io
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from icalendar import Calendar
from PIL import Image

from .models import Evento


def a_las(año, mes, día, hora, minuto=0):
    return timezone.make_aware(datetime.datetime(año, mes, día, hora, minuto))


def crear(**campos):
    # Basta con el nombre del fichero: salvo al subirlo, nadie lo abre.
    return Evento.objects.create(**{'cartel': 'carteles/2026/cartel.jpg', **campos})


class EventoTests(TestCase):
    def test_no_admite_eventos_sin_duración(self):
        evento = Evento(título='Relámpago', inicio=a_las(2026, 10, 3, 22), duración=0, cartel='carteles/2026/x.jpg')

        with self.assertRaises(ValidationError):
            evento.full_clean()
        with self.assertRaises(IntegrityError):
            evento.save()

    def test_por_defecto_enlaza_a_la_web_de_la_escuela(self):
        self.assertEqual(Evento().enlace, 'https://www.escuelabotarate.com')

    def test_por_defecto_dura_unas_dos_horas(self):
        evento = Evento(inicio=a_las(2026, 10, 3, 21))

        self.assertEqual(evento.duración_aproximada, '2 h')
        self.assertEqual(evento.fin_aproximado, a_las(2026, 10, 3, 23))

    def test_escribe_la_duración_en_horas_y_minutos(self):
        self.assertEqual(Evento(duración=90).duración_aproximada, '1 h 30 min')
        self.assertEqual(Evento(duración=45).duración_aproximada, '45 min')

    def test_sin_cartel_lleva_el_de_por_definir(self):
        evento = Evento(título='Sin cartel', inicio=a_las(2026, 10, 3, 21))

        evento.full_clean()
        self.assertEqual(evento.url_cartel, '/static/img/cartel-por-definir.png')

    def test_con_cartel_lleva_el_suyo(self):
        evento = Evento(cartel='carteles/2026/cartel.jpg')

        self.assertEqual(evento.url_cartel, '/media/carteles/2026/cartel.jpg')

    def test_entre_incluye_los_que_empiezan_antes_y_acaban_dentro(self):
        evento = crear(título='Noche larga', inicio=a_las(2026, 9, 30, 23), duración=180)

        self.assertIn(evento, Evento.objects.entre(a_las(2026, 10, 1, 0), a_las(2026, 11, 1, 0)))
        self.assertNotIn(evento, Evento.objects.entre(a_las(2026, 10, 2, 0), a_las(2026, 11, 1, 0)))


class TemporadaTests(TestCase):
    """La data migration deja cargadas las tres citas fijas de la temporada 2026-2027."""

    def test_carga_todas_las_fechas(self):
        self.assertEqual(Evento.objects.filter(título='Lechugazo').count(), 10)
        self.assertEqual(Evento.objects.filter(título='Micro abierto').count(), 10)
        self.assertEqual(Evento.objects.filter(título='Veladas mágicas').count(), 9)

    def test_cada_espectáculo_a_su_hora_y_con_su_cartel(self):
        lechugazo = Evento.objects.get(título='Lechugazo', inicio__date=datetime.date(2026, 9, 18))
        micro = Evento.objects.get(título='Micro abierto', inicio__date=datetime.date(2026, 9, 25))
        velada = Evento.objects.get(título='Veladas mágicas', inicio__date=datetime.date(2027, 5, 8))

        self.assertEqual(lechugazo.inicio, a_las(2026, 9, 18, 21))
        self.assertEqual(micro.inicio, a_las(2026, 9, 25, 21))
        self.assertEqual(velada.inicio, a_las(2027, 5, 8, 20))
        self.assertEqual({lechugazo.duración, micro.duración, velada.duración}, {90})
        self.assertEqual(lechugazo.cartel.name, 'carteles/lechugazo.png')
        self.assertEqual(micro.cartel.name, 'carteles/micro-abierto.png')
        self.assertEqual(velada.cartel.name, 'carteles/veladas-magicas.jpg')
        self.assertTrue(velada.cartel.storage.exists(velada.cartel.name))

    def test_todas_enlazan_a_la_web_de_la_escuela(self):
        self.assertEqual(set(Evento.objects.values_list('enlace', flat=True)), {'https://www.escuelabotarate.com'})

    def test_todas_las_fechas_de_un_espectáculo_comparten_cartel(self):
        carteles = Evento.objects.filter(título='Lechugazo').order_by().values_list('cartel', flat=True).distinct()

        self.assertEqual(list(carteles), ['carteles/lechugazo.png'])


class CalendarioViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Sin la temporada cargada por la data migration: aquí se cuentan los eventos de octubre.
        Evento.objects.all().delete()
        cls.concierto = crear(
            título='Los Botarates en directo', inicio=a_las(2026, 10, 17, 21), duración=150,
            descripción='Presentación del disco.', enlace='https://entradas.example/botarates')
        cls.borrador = crear(
            título='Por confirmar', inicio=a_las(2026, 10, 24, 21), duración=120, publicado=False)
        cls.noviembre = crear(
            título='Jam de noviembre', inicio=a_las(2026, 11, 7, 20), duración=180)

    def test_se_ve_sin_iniciar_sesión(self):
        respuesta = self.client.get(reverse('calendario_mes', args=[2026, 10]))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Los Botarates en directo')

    def test_solo_muestra_los_publicados_del_mes(self):
        respuesta = self.client.get(reverse('calendario_mes', args=[2026, 10]))

        self.assertEqual(respuesta.context['eventos_mes'], [self.concierto])
        self.assertNotContains(respuesta, 'Por confirmar')

    def test_coloca_cada_evento_en_su_día(self):
        respuesta = self.client.get(reverse('calendario_mes', args=[2026, 10]))

        días = {día: eventos for semana in respuesta.context['semanas'] for día, eventos in semana}
        self.assertEqual(días[datetime.date(2026, 10, 17)], [self.concierto])
        self.assertEqual(días[datetime.date(2026, 10, 24)], [])
        # La rejilla acaba el domingo 1 de noviembre, que no tiene nada.
        self.assertEqual(días[datetime.date(2026, 11, 1)], [])

    def test_un_evento_que_pasa_de_medianoche_sale_en_los_dos_días(self):
        noche = crear(título='Fiesta', inicio=a_las(2026, 10, 30, 23), duración=240)

        respuesta = self.client.get(reverse('calendario_mes', args=[2026, 10]))

        días = {día: eventos for semana in respuesta.context['semanas'] for día, eventos in semana}
        self.assertEqual(días[datetime.date(2026, 10, 30)], [noche])
        self.assertEqual(días[datetime.date(2026, 10, 31)], [noche])

    def test_enlaza_los_meses_vecinos_cruzando_de_año(self):
        respuesta = self.client.get(reverse('calendario_mes', args=[2026, 12]))

        self.assertEqual(respuesta.context['anterior'], datetime.date(2026, 11, 1))
        self.assertEqual(respuesta.context['siguiente'], datetime.date(2027, 1, 1))

    def test_un_mes_inexistente_da_404(self):
        self.assertEqual(self.client.get(reverse('calendario_mes', args=[2026, 13])).status_code, 404)

    def test_muestra_el_cartel(self):
        respuesta = self.client.get(reverse('calendario_mes', args=[2026, 10]))

        self.assertContains(respuesta, 'src="/media/carteles/2026/cartel.jpg"')

    def test_ofrece_los_enlaces_de_suscripción(self):
        respuesta = self.client.get(reverse('calendario'))

        self.assertEqual(respuesta.context['url_ics'], 'http://testserver/calendario/botarate.ics')
        self.assertEqual(respuesta.context['url_webcal'], 'webcal://testserver/calendario/botarate.ics')
        self.assertIn('cid=webcal%3A%2F%2Ftestserver', respuesta.context['url_google'])


class CalendarioIcsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Evento.objects.all().delete()
        cls.concierto = crear(
            título='Los Botarates en directo', inicio=a_las(2026, 10, 17, 21), duración=150,
            enlace='https://entradas.example/botarates')
        crear(
            título='Por confirmar', inicio=a_las(2026, 10, 24, 21), duración=120, publicado=False)

    def leer(self):
        respuesta = self.client.get(reverse('calendario_ics'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta['Content-Type'].startswith('text/calendar'))
        return Calendar.from_ical(respuesta.content)

    def test_se_descarga_sin_iniciar_sesión_y_solo_con_los_publicados(self):
        eventos = self.leer().walk('VEVENT')

        self.assertEqual([str(evento['summary']) for evento in eventos], ['Los Botarates en directo'])

    def test_pide_a_los_clientes_que_lo_refresquen_cada_hora(self):
        cal = self.leer()

        self.assertEqual(cal.decoded('refresh-interval'), datetime.timedelta(hours=1))
        self.assertEqual(str(cal['x-published-ttl']), 'PT1H')

    def test_cada_evento_lleva_sus_datos(self):
        evento = self.leer().walk('VEVENT')[0]

        self.assertEqual(str(evento['uid']), f'{self.concierto.uid}@botarate')
        self.assertEqual(evento.decoded('dtstart'), self.concierto.inicio)
        self.assertEqual(evento.decoded('duration'), datetime.timedelta(minutes=150))
        self.assertNotIn('dtend', evento)
        self.assertIn('Duración aproximada: 2 h 30 min', str(evento['description']))
        self.assertIn('https://entradas.example/botarates', str(evento['description']))
        self.assertEqual(str(evento['location']), 'Botarate')
        self.assertEqual(str(evento['url']), 'https://entradas.example/botarates')

    def test_cada_evento_comparte_su_cartel(self):
        evento = self.leer().walk('VEVENT')[0]
        url = 'http://testserver/media/carteles/2026/cartel.jpg'

        self.assertEqual(str(evento['attach']), url)
        self.assertEqual(evento['attach'].params['FMTTYPE'], 'image/jpeg')
        self.assertEqual(str(evento['image']), url)
        # Para los clientes que no enseñan adjuntos.
        self.assertIn(f'Cartel: {url}', str(evento['description']))

    def test_sin_cartel_comparte_el_de_por_definir(self):
        crear(título='Pendiente', inicio=a_las(2026, 11, 7, 20), duración=180, cartel='')

        evento = next(evento for evento in self.leer().walk('VEVENT') if evento['summary'] == 'Pendiente')
        self.assertEqual(str(evento['attach']), 'http://testserver/static/img/cartel-por-definir.png')
        self.assertEqual(evento['attach'].params['FMTTYPE'], 'image/png')

    def test_el_uid_no_cambia_al_editar_el_evento(self):
        uid = self.concierto.uid
        self.concierto.título = 'Los Botarates (cambio de hora)'
        self.concierto.save()

        self.concierto.refresh_from_db()
        self.assertEqual(self.concierto.uid, uid)


class SubidaCartelTests(TestCase):
    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ajustes = override_settings(MEDIA_ROOT=carpeta.name)
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        self.client.force_login(get_user_model().objects.create_superuser(email='sala@botarate.es', password='x'))

    def subir(self, fichero):
        return self.client.post(reverse('admin:calendario_evento_add'), {
            'título': 'Concierto', 'inicio_0': '17/10/2026', 'inicio_1': '21:00',
            'duración': '120', 'cartel': fichero, 'publicado': 'on'})

    def test_se_sube_desde_el_admin(self):
        imagen = io.BytesIO()
        Image.new('RGB', (30, 40), 'red').save(imagen, 'PNG')

        respuesta = self.subir(SimpleUploadedFile('cartel.png', imagen.getvalue(), content_type='image/png'))

        self.assertRedirects(respuesta, reverse('admin:calendario_evento_changelist'))
        evento = Evento.objects.get(título='Concierto')
        self.assertTrue(evento.cartel.name.startswith('carteles/2026/'))
        self.assertTrue(evento.cartel.storage.exists(evento.cartel.name))

    def test_se_puede_crear_sin_cartel(self):
        respuesta = self.subir('')

        self.assertRedirects(respuesta, reverse('admin:calendario_evento_changelist'))
        self.assertFalse(Evento.objects.get(título='Concierto').cartel)

    def test_rechaza_lo_que_no_es_una_imagen(self):
        respuesta = self.subir(SimpleUploadedFile('cartel.png', b'no soy una imagen', content_type='image/png'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Evento.objects.filter(título='Concierto').exists())


class SuscribirseTests(TestCase):
    """El enlace único: cada dispositivo acaba en su calendario, y si no se sabe cuál, elige."""

    IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148'
    MAC = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15'
    ANDROID = 'Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36'
    WINDOWS = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36'

    def suscribirse(self, navegador):
        return self.client.get(reverse('calendario_suscribirse'), headers={'user-agent': navegador})

    def test_iphone_y_mac_van_a_calendario_de_apple(self):
        for navegador in (self.IPHONE, self.MAC):
            with self.subTest(navegador=navegador):
                respuesta = self.suscribirse(navegador)

                self.assertEqual(respuesta.status_code, 302)
                self.assertEqual(respuesta['Location'], 'webcal://testserver/calendario/botarate.ics')

    def test_android_va_a_google_calendar(self):
        respuesta = self.suscribirse(self.ANDROID)

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta['Location'].startswith('https://calendar.google.com/calendar/render?cid=webcal'))

    def test_en_un_ordenador_se_deja_elegir(self):
        respuesta = self.suscribirse(self.WINDOWS)

        self.assertRedirects(respuesta, reverse('calendario') + '#suscribirse')

    def test_sin_navegador_conocido_también_se_deja_elegir(self):
        self.assertRedirects(self.suscribirse(''), reverse('calendario') + '#suscribirse')

    def test_el_enlace_único_solo_se_le_enseña_a_la_sala(self):
        self.assertNotContains(self.client.get(reverse('calendario')), '/calendario/suscribirse/')

        self.client.force_login(get_user_model().objects.create_user(
            email='sala@botarate.es', password='x', is_staff=True, is_active=True))
        self.assertContains(self.client.get(reverse('calendario')), 'http://testserver/calendario/suscribirse/')
