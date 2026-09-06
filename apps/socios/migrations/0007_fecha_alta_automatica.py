"""La fecha de alta la pone Django sola.

Último de tres pasos, y va aquí y no antes a propósito: con auto_now_add el campo
deja de ser asignable —lo que se le pase al crear se ignora sin avisar—, así que
tenía que entrar después de socios/0006, que es quien escribe las horas reales de
los socios que venían de los Excel.

De aquí en adelante, quien se dé de alta por el formulario web queda con la fecha y
la hora exactas en que lo rellenó. Para corregir la de alguien ya guardado hace falta
un queryset.update(), que es lo único que se salta el auto_now_add.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socios', '0006_hora_real_del_alta'),
    ]

    operations = [
        migrations.AlterField(
            model_name='socio',
            name='fecha_alta',
            field=models.DateTimeField(auto_now_add=True, verbose_name='fecha de alta'),
        ),
    ]
