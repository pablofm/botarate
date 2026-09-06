"""Da de alta a quien se quedó fuera por no tener DNI ni NIE.

Al cargar data/lista-virginia.xlsx (clases/0006) se descartaron las filas cuyo
documento no pasaba la validación de NIF. Ahora que Socio admite otros documentos,
se recuperan aquí, una a una y con el tipo decidido a mano: el fichero no dice de
qué documento se trata, y no es cosa de adivinarlo.

De momento solo entra Gaia Meloni, con su codice fiscale italiano (fila 31 del
Excel), que además recupera sus tres matrículas. Quedan fuera a propósito:

  - David Engel (fila 4): en la casilla del documento puso literalmente
    «Passport», así que no tenemos número ninguno.
  - Ulises Tomy Castañeda Bazan (fila 20): puso «123281434», pero en el otro
    fichero aparece como «Tomy Castañeda» con «43964698». No se sabe cuál es su
    documento ni de qué tipo.

Cuando lleguen esos números, se añaden a RESCATES en una migración nueva.
"""
import datetime

from django.db import migrations

# Los datos son los de sus filas de data/lista-virginia.xlsx, con el teléfono ya sin
# paréntesis y el tipo de documento puesto a mano.
RESCATES = [
    {
        'fecha_alta': '2026-09-04',
        'nombre': 'Gaia Meloni',
        'tipo_documento': 'OTRO',
        'documento': 'MLNGAI02R55B354L',
        'teléfono': '+3923236222',
        'email': 'meloni.gaia02@mail.com',
        'quiere_comunicaciones': True,
        'cursos': ['Improvisación a partir del cuerpo', 'Mimo y juego dramático', 'Bufón'],
    },
]


def rescatar(apps, schema_editor):
    Socio = apps.get_model('socios', 'Socio')
    Alumno = apps.get_model('clases', 'Alumno')
    Curso = apps.get_model('clases', 'Curso')

    # Los tests nacen sin socios y dan por hecho que siguen así.
    if schema_editor.connection.settings_dict['NAME'].startswith('test_'):
        return

    for datos in RESCATES:
        cursos = datos.get('cursos', [])
        if Socio.objects.filter(documento=datos['documento']).exists():
            continue

        socio = Socio.objects.create(
            **{campo: valor for campo, valor in datos.items()
               if campo not in ('cursos', 'fecha_alta')},
            fecha_alta=datetime.date.fromisoformat(datos['fecha_alta']),
            acepta_tratamiento_datos=True,
            acepta_inscripción=True)
        if cursos:
            alumno, _ = Alumno.objects.get_or_create(socio=socio)
            alumno.cursos.add(*Curso.objects.filter(nombre__in=cursos))
        print(f'\n  Rescatado {socio.nombre} ({socio.documento}) con {len(cursos)} matrículas.')


class Migration(migrations.Migration):

    dependencies = [
        ('clases', '0006_matriculas_del_curso_26_27'),
        ('socios', '0004_documento_de_identidad'),
    ]

    operations = [
        migrations.RunPython(rescatar, migrations.RunPython.noop),
    ]
