"""Recupera la hora a la que cada socio rellenó el formulario.

Segundo de tres pasos. Cuando fecha_alta era un DateField se tiró la hora de la
«Marca temporal», y las dos cargas de datos solo guardaron el día. Ahora que el campo
lleva hora, se vuelve a leer de los dos Excel y se pone la de verdad, antes de que
socios/0007 cierre el campo con auto_now_add.

De cada socio se coge la marca temporal más antigua de las dos hojas, que es el mismo
criterio con el que se eligió su fila al cargarlo: si alguien rellenó el formulario
dos veces, su alta es la primera.

Las marcas vienen sin zona horaria; son horas de Madrid, que es donde se rellenó el
formulario. Quien no aparezca en ningún fichero —altas hechas por la web o a mano— se
queda con la fecha que ya tuviera.
"""
import datetime

from django.conf import settings
from django.db import migrations
from django.utils import timezone

EXCELES = ('data/respuesta-web.xlsx', 'data/lista-virginia.xlsx')
FECHA = 'Marca temporal'
DOCUMENTO = 'DNI'


def _texto(valor):
    if valor is None:
        return ''
    return ' '.join(str(valor).split())


def _documento(valor):
    if isinstance(valor, (int, float)) and float(valor).is_integer():
        return str(int(valor))
    return _texto(valor).upper().replace(' ', '').replace('-', '')


def _marca_temporal(valor):
    if isinstance(valor, datetime.datetime):
        sin_zona = valor
    elif isinstance(valor, datetime.date):
        sin_zona = datetime.datetime.combine(valor, datetime.time())
    else:
        sin_zona = datetime.datetime.strptime(_texto(valor), '%m/%d/%Y %H:%M:%S')
    return timezone.make_aware(sin_zona)


def _leer_filas(ruta):
    import openpyxl

    hoja = openpyxl.load_workbook(ruta, data_only=True, read_only=True).active
    filas = hoja.iter_rows(values_only=True)
    cabeceras = [_texto(c) for c in next(filas)]
    for valores in filas:
        if not any(_texto(v) for v in valores):
            continue
        yield dict(zip(cabeceras, valores))


def poner_la_hora_real(apps, schema_editor):
    Socio = apps.get_model('socios', 'Socio')

    if schema_editor.connection.settings_dict['NAME'].startswith('test_'):
        return

    altas = {}
    for excel in EXCELES:
        ruta = settings.BASE_DIR / excel
        if not ruta.exists():
            print(f'\n  No está {excel}: sus horas se quedan sin recuperar.')
            continue
        for fila in _leer_filas(ruta):
            documento = _documento(fila[DOCUMENTO])
            marca = _marca_temporal(fila[FECHA])
            if documento not in altas or marca < altas[documento]:
                altas[documento] = marca

    corregidos, sin_fila = [], 0
    for socio in Socio.objects.all():
        marca = altas.get(socio.documento)
        if marca is None:
            sin_fila += 1
            continue
        socio.fecha_alta = marca
        corregidos.append(socio)
    Socio.objects.bulk_update(corregidos, ['fecha_alta'])

    print(f'\n  Hora real recuperada en {len(corregidos)} socios.')
    if sin_fila:
        print(f'  {sin_fila} sin fila en los Excel: se quedan con la fecha que tenían.')


class Migration(migrations.Migration):

    dependencies = [
        ('socios', '0005_fecha_alta_con_hora'),
    ]

    operations = [
        # Sin marcha atrás: la hora que había antes era medianoche inventada.
        migrations.RunPython(poner_la_hora_real, migrations.RunPython.noop),
    ]
