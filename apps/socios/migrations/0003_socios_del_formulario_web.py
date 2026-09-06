"""Carga los socios que se dieron de alta por el formulario web.

Lee data/respuesta-web.xlsx, la exportación de las respuestas del formulario. El
fichero no está en el repositorio: si no aparece, la migración avisa y no hace nada,
para que un despliegue limpio o los tests no se rompan por eso.

Las filas que no se pueden dar de alta (DNI que no pasa la letra, teléfono que no
cuela por el validador, o DNI repetido) no se cargan: se listan al final con su
número de fila del Excel para repasarlas a mano.
"""
import datetime
import unicodedata

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import migrations

EXCEL = 'data/respuesta-web.xlsx'

# Cabeceras del Excel. Se buscan por nombre para que no importe el orden de las columnas.
FECHA = 'Marca temporal'
NOMBRE = 'Nombre'
APELLIDOS = 'Apellidos'
EMAIL = 'Correo electrónico'
DNI = 'DNI'
TELÉFONO = 'Número de teléfono'
DIFUSIÓN_EVENTOS = '¿Quieres recibir la difusión de los eventos de Botarate?'
DIFUSIÓN_CURSOS = '¿Quieres recibir la difusión de Cursos Botarates?'


def _texto(valor):
    """Un valor de celda como texto, sin espacios de más ni dobles."""
    if valor is None:
        return ''
    return ' '.join(str(valor).split())


def _fecha_alta(valor):
    """La marca temporal como fecha.

    Las celdas vienen ya como datetime; si alguna llega como texto es el MM/DD/AAAA
    del formulario.
    """
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    return datetime.datetime.strptime(_texto(valor).split()[0], '%m/%d/%Y').date()


def _teléfono(valor):
    """El teléfono como texto.

    Los que se escribieron solo con dígitos los devuelve openpyxl como float
    (676851871.0), y hay que quitarles el .0 antes de guardarlos.
    """
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return _texto(valor)


def _dni(valor):
    """El DNI en el formato en que lo guarda el modelo: mayúsculas y sin separadores.

    Es lo mismo que hace ESIdentityCardNumberField.to_python, pero los modelos
    históricos de las migraciones no pasan por ahí al asignar el atributo.
    """
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return _texto(valor).upper().replace(' ', '').replace('-', '')


def _es_sí(valor):
    """Si la respuesta del formulario es afirmativa: viene como «SI», «Sí», «No»..."""
    sin_tildes = unicodedata.normalize('NFKD', _texto(valor)).encode('ascii', 'ignore').decode()
    return sin_tildes.lower() == 'si'


def _validar_dni(dni):
    """Comprueba la letra del DNI/NIE con el campo de localflavor.

    El campo de modelo solo normaliza el valor; quien sabe de la letra es el campo de
    formulario, que es el que usa DNIField.formfield y por tanto el alta por la web.
    """
    from localflavor.es.forms import ESIdentityCardNumberField

    try:
        ESIdentityCardNumberField(only_nif=True).clean(dni)
    except ValidationError as error:
        # Como dict, para poder juntarlo con lo que devuelve full_clean.
        raise ValidationError({'dni': error.messages}) from error


def _leer_filas(ruta):
    """Las filas del Excel como diccionarios {cabecera: valor}, con su número de fila."""
    # Se importa aquí y no arriba porque Django carga este módulo en cada «migrate»,
    # también donde no haya Excel que leer.
    import openpyxl

    hoja = openpyxl.load_workbook(ruta, data_only=True, read_only=True).active
    filas = hoja.iter_rows(values_only=True)
    cabeceras = [_texto(c) for c in next(filas)]
    for número, valores in enumerate(filas, start=2):
        if not any(_texto(v) for v in valores):
            continue
        yield número, dict(zip(cabeceras, valores))


def _es_base_de_pruebas(schema_editor):
    """Si estamos montando la base de datos de los tests.

    Django la crea siempre como «test_<nombre>». Los tests dan por hecho que empiezan
    sin socios, así que allí esta migración no carga nada.
    """
    return schema_editor.connection.settings_dict['NAME'].startswith('test_')


def cargar_socios(apps, schema_editor):
    Socio = apps.get_model('socios', 'Socio')

    if _es_base_de_pruebas(schema_editor):
        return

    ruta = settings.BASE_DIR / EXCEL
    if not ruta.exists():
        print(f'\n  No está {EXCEL}: no se cargan socios del formulario web.')
        return

    filas = sorted(_leer_filas(ruta), key=lambda fila: _fecha_alta(fila[1][FECHA]))

    cargados, descartados = 0, []
    for número, fila in filas:
        socio = Socio(
            fecha_alta=_fecha_alta(fila[FECHA]),
            nombre=f'{_texto(fila[NOMBRE])} {_texto(fila[APELLIDOS])}'.strip(),
            dni=_dni(fila[DNI]),
            teléfono=_teléfono(fila[TELÉFONO]),
            email=_texto(fila[EMAIL]),
            # Quien rellenó el formulario aceptó las dos cosas para poder enviarlo.
            acepta_tratamiento_datos=True,
            acepta_inscripción=True,
            quiere_comunicaciones=_es_sí(fila[DIFUSIÓN_EVENTOS]) and _es_sí(fila[DIFUSIÓN_CURSOS]),
        )
        try:
            _validar_dni(socio.dni)
            socio.full_clean()
        except ValidationError as error:
            motivos = '; '.join(msg for mensajes in error.message_dict.values() for msg in mensajes)
            descartados.append((número, socio.nombre, socio.dni, motivos))
            continue

        socio.save()
        cargados += 1

    print(f'\n  Socios cargados desde {EXCEL}: {cargados} de {len(filas)}.')
    if descartados:
        print(f'  Filas sin cargar ({len(descartados)}), repásalas a mano:')
        for número, nombre, dni, motivos in descartados:
            print(f'    fila {número}: {nombre} ({dni or "sin DNI"}) → {motivos}')


class Migration(migrations.Migration):

    dependencies = [
        ('socios', '0002_fecha_de_alta'),
    ]

    operations = [
        # Sin marcha atrás: borrar socios al revertir se llevaría por delante los que
        # se hayan dado de alta después por la web.
        migrations.RunPython(cargar_socios, migrations.RunPython.noop),
    ]
