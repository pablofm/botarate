"""Matrícula del curso 26/27, la lista que lleva Virginia a mano.

Lee data/lista-virginia.xlsx: las nueve primeras columnas son los datos del socio y
las nueve últimas los cursos, marcados con una «X».

Quien ya esté dado de alta se queda como está (esa lista no manda sobre lo que ya
hay en la base de datos); de quien no lo esté se crea el socio. Con cualquier curso
marcado se le crea además su ficha de Alumno y se le matricula, sin tocar las
matrículas que ya tuviera.

Igual que socios/0003, el fichero no está en el repositorio: si falta, la migración
avisa y no hace nada. Los ayudantes están repetidos a propósito en las dos
migraciones para que cada una siga funcionando aunque la otra cambie.
"""
import datetime
import re
import unicodedata

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import migrations

EXCEL = 'data/lista-virginia.xlsx'

FECHA = 'Marca temporal'
NOMBRE = 'Nombre'
APELLIDOS = 'Apellidos'
EMAIL = 'Correo electrónico'
DNI = 'DNI'
TELÉFONO = 'Número de teléfono'
DIFUSIÓN_EVENTOS = '¿Quieres recibir la difusión de los eventos de Botarate?'
DIFUSIÓN_CURSOS = '¿Quieres recibir la difusión de Cursos Botarates?'

# Las columnas de curso del Excel no se llaman igual que los cursos de la base de
# datos, así que la correspondencia va escrita a mano.
CURSOS = {
    'Curso Clown Iniciación': 'Clown Iniciación',
    'Curso Clown Avanzado': 'Clown avanzado',
    'Curso Números Clown': 'Números clown',
    'Dramaturgia': 'Laboratorio dramaturgia y escritura teatral',
    'Improvisación a partir del cuerpo': 'Improvisación a partir del cuerpo',
    'Juego y Mimo': 'Mimo y juego dramático',
    'Bufón': 'Bufón',
    'Melodrama': 'Melodrama',
    'Teatro y Comedia': 'Teatro Comedia',
}


def _texto(valor):
    """Un valor de celda como texto, sin espacios de más ni dobles."""
    if valor is None:
        return ''
    return ' '.join(str(valor).split())


def _fecha_alta(valor):
    """La marca temporal como fecha."""
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    return datetime.datetime.strptime(_texto(valor).split()[0], '%m/%d/%Y').date()


def _teléfono(valor):
    """El teléfono como texto.

    Los que solo tienen dígitos llegan como número, y hay algún prefijo escrito
    entre paréntesis —«(+44)7970509769»— que el validador no admite tal cual.
    """
    if isinstance(valor, (int, float)) and float(valor).is_integer():
        return str(int(valor))
    return re.sub(r'[()]', '', _texto(valor))


def _dni(valor):
    """El DNI como lo guarda el modelo: mayúsculas y sin separadores."""
    if isinstance(valor, (int, float)) and float(valor).is_integer():
        return str(int(valor))
    return _texto(valor).upper().replace(' ', '').replace('-', '')


def _es_sí(valor):
    """Si la respuesta es afirmativa: viene como «SI», «Sí», «No», «NO»..."""
    sin_tildes = unicodedata.normalize('NFKD', _texto(valor)).encode('ascii', 'ignore').decode()
    return sin_tildes.lower() == 'si'


def _validar_dni(dni):
    """Comprueba la letra con el campo de localflavor, que es quien sabe de eso."""
    from localflavor.es.forms import ESIdentityCardNumberField

    try:
        ESIdentityCardNumberField(only_nif=True).clean(dni)
    except ValidationError as error:
        raise ValidationError({'dni': error.messages}) from error


def _leer_filas(ruta):
    """Las filas del Excel como diccionarios {cabecera: valor}, con su número de fila."""
    import openpyxl

    hoja = openpyxl.load_workbook(ruta, data_only=True, read_only=True).active
    filas = hoja.iter_rows(values_only=True)
    cabeceras = [_texto(c) for c in next(filas)]
    for número, valores in enumerate(filas, start=2):
        if not any(_texto(v) for v in valores):
            continue
        yield número, dict(zip(cabeceras, valores))


def _es_base_de_pruebas(schema_editor):
    """Si estamos montando la base de datos de los tests, que nacen sin socios."""
    return schema_editor.connection.settings_dict['NAME'].startswith('test_')


def matricular(apps, schema_editor):
    Socio = apps.get_model('socios', 'Socio')
    Alumno = apps.get_model('clases', 'Alumno')
    Curso = apps.get_model('clases', 'Curso')

    if _es_base_de_pruebas(schema_editor):
        return

    ruta = settings.BASE_DIR / EXCEL
    if not ruta.exists():
        print(f'\n  No está {EXCEL}: no se matricula a nadie.')
        return

    cursos = {columna: Curso.objects.filter(nombre=nombre).first()
              for columna, nombre in CURSOS.items()}
    if sin_curso := [c for c, curso in cursos.items() if curso is None]:
        print(f'\n  Cursos que no están en la base de datos, no se matricula en ellos: {sin_curso}')

    filas = sorted(_leer_filas(ruta), key=lambda fila: _fecha_alta(fila[1][FECHA]))

    creados, ya_estaban, matriculados, matrículas, descartados = 0, 0, 0, 0, []
    for número, fila in filas:
        nombre = f'{_texto(fila[NOMBRE])} {_texto(fila[APELLIDOS])}'.strip()
        dni = _dni(fila[DNI])
        marcados = [columna for columna in CURSOS if fila.get(columna) is not None]

        socio = Socio.objects.filter(dni=dni).first()
        if socio:
            ya_estaban += 1
        else:
            socio = Socio(
                fecha_alta=_fecha_alta(fila[FECHA]),
                nombre=nombre,
                dni=dni,
                teléfono=_teléfono(fila[TELÉFONO]),
                email=_texto(fila[EMAIL]),
                acepta_tratamiento_datos=True,
                acepta_inscripción=True,
                quiere_comunicaciones=_es_sí(fila[DIFUSIÓN_EVENTOS]) and _es_sí(fila[DIFUSIÓN_CURSOS]),
            )
            try:
                _validar_dni(dni)
                socio.full_clean()
            except ValidationError as error:
                motivos = '; '.join(msg for mensajes in error.message_dict.values() for msg in mensajes)
                descartados.append((número, nombre, dni, motivos, marcados))
                continue
            socio.save()
            creados += 1

        if marcados:
            alumno, nuevo = Alumno.objects.get_or_create(socio=socio)
            matriculados += nuevo
            # add() no repite las matrículas que ya tuviera.
            alumno.cursos.add(*(cursos[columna] for columna in marcados if cursos[columna]))
            matrículas += sum(1 for columna in marcados if cursos[columna])

    print(f'\n  {EXCEL}: {len(filas)} filas → {creados} socios nuevos, {ya_estaban} que ya estaban.')
    print(f'  Alumnos nuevos: {matriculados}. Matrículas puestas: {matrículas}.')
    if descartados:
        print(f'  Filas sin cargar ({len(descartados)}), repásalas a mano:')
        for número, nombre, dni, motivos, marcados in descartados:
            perdidas = f' — se quedan sin matricular: {", ".join(marcados)}' if marcados else ''
            print(f'    fila {número}: {nombre} ({dni or "sin DNI"}) → {motivos}{perdidas}')


class Migration(migrations.Migration):

    dependencies = [
        ('clases', '0005_content_type_de_socio'),
        ('socios', '0003_socios_del_formulario_web'),
    ]

    operations = [
        # Sin marcha atrás: al revertir no se sabría qué matrículas venían de aquí.
        migrations.RunPython(matricular, migrations.RunPython.noop),
    ]
