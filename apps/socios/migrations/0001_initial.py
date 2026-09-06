"""Socio se muda de la app «clases» a la suya propia.

El modelo se crea solo en el estado de Django: la tabla ya existe (la creó
clases/0001_initial) y es clases/0004 quien la renombra a socios_socio, así que
aquí no se toca la base de datos y no se pierde ningún dato.
"""
import django.core.validators
from django.db import migrations, models

import apps.socios.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clases', '0003_consentimientos_del_socio'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Socio',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('nombre', models.CharField(max_length=200, verbose_name='nombre completo')),
                        ('dni', apps.socios.fields.DNIField(error_messages={'unique': 'Ya hay un socio dado de alta con este DNI.'}, help_text='DNI o NIE, con la letra', max_length=9, unique=True, verbose_name='DNI')),
                        ('teléfono', models.CharField(max_length=20, validators=[django.core.validators.RegexValidator(message='Escribe un teléfono válido: 600 123 456, o con prefijo (+34 600 123 456).', regex='^\\+?\\d[\\d\\s.-]{7,}$')], verbose_name='teléfono')),
                        ('email', models.EmailField(max_length=254, verbose_name='email')),
                        ('acepta_tratamiento_datos', models.BooleanField(default=False, help_text='Autorizo a la Asociación Cultural Botarate a tratar mis datos personales conforme a la normativa vigente y a almacenarlos mientras exista relación entre la asociación y mi participación en sus actividades.', verbose_name='Acepto el tratamiento de mis datos personales')),
                        ('acepta_inscripción', models.BooleanField(default=False, help_text='Comprendo que la inscripción es un requisito administrativo para participar en actividades y que no implica cargos de gestión ni responsabilidades internas.', verbose_name='Acepto mi inscripción como socia/o de la asociación')),
                        ('quiere_comunicaciones', models.BooleanField(blank=True, default=False, help_text='Autorizo a Botarate a enviarme comunicaciones informativas sobre actividades culturales.', verbose_name='Quiero recibir información sobre cursos, talleres y actividades')),
                        ('quiere_whatsapp', models.BooleanField(blank=True, default=False, help_text='Acepto ser añadida/o al grupo de WhatsApp para recibir avisos y participar en la comunidad interna.', verbose_name='Quiero unirme a la comunidad de WhatsApp de Botarate')),
                    ],
                    options={
                        'verbose_name': 'Socio',
                        'verbose_name_plural': 'Socios',
                        'ordering': ['nombre'],
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
