"""Activa unaccent en Postgres, para que el buscador de socias no distinga tildes.

Crear una extensión exige permisos en la base de datos: si el usuario de la
aplicación no los tiene, hay que ejecutar antes, como administrador,
CREATE EXTENSION unaccent; y entonces esta migración no hace nada.
"""
from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('socios', '0007_fecha_alta_automatica'),
    ]

    operations = [
        UnaccentExtension(),
    ]
