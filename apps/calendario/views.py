import calendar
import datetime
import mimetypes
from collections import defaultdict
from urllib.parse import quote

from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from icalendar import Calendar, Event

from .models import Evento

NOMBRE_CALENDARIO = 'Botarate'
DÍAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _medianoche(día):
    return timezone.make_aware(datetime.datetime.combine(día, datetime.time.min))


def enlaces_suscripción(request):
    url = request.build_absolute_uri(reverse('calendario_ics'))
    webcal = 'webcal://' + url.split('://', 1)[1]
    return {
        'url_ics': url,
        'url_webcal': webcal,
        'url_google': f'https://calendar.google.com/calendar/render?cid={quote(webcal, safe="")}',
        'url_outlook': (
            'https://outlook.live.com/calendar/0/addfromweb'
            f'?url={quote(url, safe="")}&name={quote(NOMBRE_CALENDARIO)}'),
        'url_suscribirse': request.build_absolute_uri(reverse('calendario_suscribirse')),
    }


class WebcalRedirect(HttpResponseRedirect):
    # Django solo redirige a http, https y ftp si no se le dice otra cosa.
    allowed_schemes = ['webcal']


@method_decorator(login_not_required, name='dispatch')
class CalendarioView(TemplateView):
    """La programación de un mes, abierta a cualquiera, con los enlaces para suscribirse."""

    template_name = 'calendario/calendario.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        año = kwargs.get('año', hoy.year)
        mes = kwargs.get('mes', hoy.month)
        if not (1 <= mes <= 12 and datetime.MINYEAR < año < datetime.MAXYEAR):
            raise Http404
        primer_día = datetime.date(año, mes, 1)

        # La rejilla empieza en lunes y acaba en domingo, así que asoman días de los meses vecinos.
        semanas = calendar.Calendar().monthdatescalendar(año, mes)
        desde, hasta = semanas[0][0], semanas[-1][-1] + datetime.timedelta(days=1)
        eventos = list(Evento.objects.publicados().entre(_medianoche(desde), _medianoche(hasta)))

        # Un evento que pasa de medianoche sale en todos los días que pisa.
        por_día = defaultdict(list)
        for evento in eventos:
            día = timezone.localdate(evento.inicio)
            último = timezone.localdate(evento.fin_aproximado - datetime.timedelta(microseconds=1))
            while día <= último:
                por_día[día].append(evento)
                día += datetime.timedelta(days=1)

        context['mes'] = primer_día
        context['anterior'] = (primer_día - datetime.timedelta(days=1)).replace(day=1)
        context['siguiente'] = (primer_día + datetime.timedelta(days=31)).replace(day=1)
        context['hoy'] = hoy
        context['días_semana'] = DÍAS_SEMANA
        context['semanas'] = [[(día, por_día[día]) for día in semana] for semana in semanas]
        context['eventos_mes'] = [
            evento for evento in eventos
            if evento.inicio < _medianoche(context['siguiente']) and evento.fin_aproximado > _medianoche(primer_día)]
        context.update(enlaces_suscripción(self.request))
        return context


@method_decorator(login_not_required, name='dispatch')
class SuscribirseView(View):
    """Un único enlace para suscribirse (el de los carteles o un QR): cada dispositivo va a su calendario.

    Por el dispositivo solo se puede adivinar el calendario en Apple y Android. En un ordenador con
    Windows o Linux lo mismo se usa Google que Outlook, así que ahí se deja elegir.
    """

    def get(self, request):
        enlaces = enlaces_suscripción(request)
        navegador = request.headers.get('User-Agent', '')
        # El iPad se presenta como un Mac, pero los dos van a Calendario de Apple igualmente.
        if any(apple in navegador for apple in ('iPhone', 'iPad', 'Macintosh')):
            return WebcalRedirect(enlaces['url_webcal'])
        if 'Android' in navegador:
            return redirect(enlaces['url_google'])
        return redirect(reverse('calendario') + '#suscribirse')


@method_decorator(login_not_required, name='dispatch')
class CalendarioIcsView(View):
    """El fichero iCalendar al que se suscriben los móviles y los clientes de correo."""

    def get(self, request):
        cal = Calendar()
        cal.add('prodid', '-//Botarate//Calendario//ES')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add('x-wr-calname', NOMBRE_CALENDARIO)
        cal.add('x-wr-timezone', 'Europe/Madrid')
        # Cada cuánto vuelven a pedirlo los clientes que hacen caso (Apple, Thunderbird, Outlook).
        cal.add('refresh-interval', datetime.timedelta(hours=1), parameters={'VALUE': 'DURATION'})
        # Las propiedades X- no tienen tipo, así que la duración se escribe ya en formato iCalendar.
        cal.add('x-published-ttl', 'PT1H')

        for evento in Evento.objects.publicados():
            cal.add_component(self.componente(evento, request.build_absolute_uri(evento.url_cartel)))

        respuesta = HttpResponse(cal.to_ical(), content_type='text/calendar; charset=utf-8')
        respuesta['Content-Disposition'] = 'inline; filename="botarate.ics"'
        return respuesta

    def componente(self, evento, url_cartel):
        componente = Event()
        componente.add('uid', f'{evento.uid}@botarate')
        componente.add('summary', evento.título)
        componente.add('dtstart', evento.inicio)
        # La duración es orientativa, pero sin ella los calendarios lo pintan como si durara cero minutos.
        componente.add('duration', datetime.timedelta(minutes=evento.duración))
        componente.add('dtstamp', evento.modificado)
        componente.add('last-modified', evento.modificado)
        componente.add('location', evento.lugar or NOMBRE_CALENDARIO)
        # Google y Outlook no enseñan ni ATTACH ni IMAGE: el enlace en la descripción les llega a todos.
        cartel = f'Cartel: {url_cartel}'
        duración = f'Duración aproximada: {evento.duración_aproximada}'
        componente.add(
            'description', '\n\n'.join(filter(None, [duración, evento.descripción, evento.enlace, cartel])))
        if evento.enlace:
            componente.add('url', evento.enlace)
        tipo = mimetypes.guess_type(url_cartel)[0] or 'application/octet-stream'
        componente.add('attach', url_cartel, parameters={'FMTTYPE': tipo})
        componente.add('image', url_cartel, parameters={'VALUE': 'URI', 'DISPLAY': 'FULLSIZE', 'FMTTYPE': tipo})
        return componente
