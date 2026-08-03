import datetime

from django.contrib.auth.hashers import make_password
from django.db import migrations

LUNES, MARTES, MIÉRCOLES, JUEVES, VIERNES, SÁBADO = 1, 2, 3, 4, 5, 6

PROFESORES = [
    ('Falín', 'falinuntipoanormal@gmail.com'),
    ('Rocío', 'rociogalanactress@gmail.com'),
    ('Roberto', 'teransanchezroberto@gmail.com'),
    ('Julia', 'mjuliapardal@gmail.com'),
    ('Sofía', 'sofiacruzarts@gmail.com'),
]

CURSOS = [
    ('Laboratorio dramaturgia y escritura teatral', [LUNES, MIÉRCOLES], (18, 0), (19, 30), 'Roberto'),
    ('Improvisación a partir del cuerpo', [LUNES], (19, 45), (21, 15), 'Sofía'),
    ('Clown Iniciación', [MARTES], (18, 0), (19, 30), 'Falín'),
    ('Números clown', [MARTES], (19, 45), (21, 15), 'Falín'),
    ('Bufón', [MIÉRCOLES], (19, 45), (21, 15), 'Rocío'),
    ('Clown avanzado', [JUEVES], (18, 0), (19, 30), 'Falín'),
    ('Mimo y juego dramático', [JUEVES], (19, 45), (21, 15), 'Sofía'),
    ('Melodrama', [VIERNES], (18, 0), (19, 30), 'Rocío'),
    ('Teatro Comedia', [SÁBADO], (11, 30), (14, 30), 'Julia'),
]


def crear_cursos_y_profesores(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'BotarateUser')
    Curso = apps.get_model('clases', 'Curso')

    profesores = {}
    for nombre, email in PROFESORES:
        # Sin contraseña utilizable y sin activar: cada profesor la establece
        # entrando por /activar/ con su correo.
        profesores[nombre], _ = Usuario.objects.get_or_create(
            email=email,
            defaults={
                'nombre': nombre,
                'password': make_password(None),
                'is_active': False,
                'is_staff': False,
                'is_superuser': False,
            })

    for nombre, días, inicio, fin, profesor in CURSOS:
        Curso.objects.get_or_create(
            nombre=nombre,
            defaults={
                'días_semana': días,
                'hora_inicio': datetime.time(*inicio),
                'hora_fin': datetime.time(*fin),
                'profesor_principal': profesores[profesor],
            })


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('clases', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_cursos_y_profesores),
    ]
