import datetime

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import migrations
from django.utils import timezone

CARTELES = settings.BASE_DIR / 'static' / 'img'

# Las tres citas fijas de la temporada. En septiembre van al revés que el resto del año
# (Lechugazo el tercer viernes, Micro abierto el cuarto): está confirmado que es así.
# El enlace se queda en el de por defecto: la web de la escuela.
TEMPORADA = [
    {
        'título': 'Lechugazo',
        'descripción': 'Sevilla Open Mic Comedy, versión 2.0.',
        'hora': datetime.time(21, 0),
        'cartel': ('lechugazo.png', 'carteles/lechugazo.png'),
        'fechas': ['18/09/26', '09/10/26', '13/11/26', '11/12/26', '08/01/27',
                   '12/02/27', '12/03/27', '09/04/27', '14/05/27', '11/06/27'],
    },
    {
        'título': 'Micro abierto',
        'descripción': 'Micro abierto de música. Entrada libre.',
        'hora': datetime.time(21, 0),
        'cartel': ('micro-abierto.png', 'carteles/micro-abierto.png'),
        'fechas': ['25/09/26', '16/10/26', '20/11/26', '18/12/26', '15/01/27',
                   '19/02/27', '19/03/27', '16/04/27', '21/05/27', '18/06/27'],
    },
    {
        'título': 'Veladas mágicas',
        'descripción': (
            'El Círculo Mágico y la Escuela Botarate presentan, con Paco Córdoba, Pablo Salas y Falín Galán.\n'
            'La magia cobra vida con un espectáculo único cada mes. Tres prestigiosos magos del «Círculo Mágico» '
            'subirán al escenario para presentar números exclusivos donde la ilusión, el ingenio y el asombro '
            'se unen en una experiencia única e inolvidable.'),
        'hora': datetime.time(20, 0),
        'cartel': ('veladas-magicas.jpg.jpeg', 'carteles/veladas-magicas.jpg'),
        'fechas': ['10/10/26', '14/11/26', '12/12/26', '09/01/27', '13/02/27',
                   '13/03/27', '10/04/27', '08/05/27', '12/06/27'],
    },
]


def guardar_cartel(origen, destino):
    """Un solo fichero por espectáculo, compartido por todas sus fechas; si ya está, no se duplica."""
    if not default_storage.exists(destino):
        with open(CARTELES / origen, 'rb') as fichero:
            destino = default_storage.save(destino, File(fichero))
    return destino


def crear_temporada(apps, schema_editor):
    Evento = apps.get_model('calendario', 'Evento')
    for espectáculo in TEMPORADA:
        cartel = guardar_cartel(*espectáculo['cartel'])
        Evento.objects.bulk_create(
            Evento(
                título=espectáculo['título'],
                descripción=espectáculo['descripción'],
                inicio=timezone.make_aware(datetime.datetime.combine(
                    datetime.datetime.strptime(fecha, '%d/%m/%y').date(), espectáculo['hora'])),
                duración=90,
                cartel=cartel,
            )
            for fecha in espectáculo['fechas']
        )


def borrar_temporada(apps, schema_editor):
    Evento = apps.get_model('calendario', 'Evento')
    Evento.objects.filter(título__in=[espectáculo['título'] for espectáculo in TEMPORADA]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('calendario', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_temporada, borrar_temporada),
    ]
