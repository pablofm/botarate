"""La fecha de alta pasa a llevar hora.

Primero de tres pasos. Aquí solo cambia el tipo, y el campo sigue siendo asignable:
socios/0006 aprovecha para escribir la hora real que traen los Excel, y solo después
socios/0007 le pone el auto_now_add, que impide asignarlo.

Va después de las tres migraciones de datos —clases/0007 arrastra a clases/0006 y a
socios/0003—, que son las que cargan las fechas históricas.

A las filas que ya están, Postgres les añade la hora al cambiar el tipo: se quedan a
medianoche UTC, que en Madrid es la una o las dos de la madrugada de ese mismo día,
así que ningún socio cambia de día. Esa medianoche dura poco: la pisa socios/0006.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socios', '0004_documento_de_identidad'),
        ('clases', '0007_rescate_de_socios_sin_nif'),
    ]

    operations = [
        migrations.AlterField(
            model_name='socio',
            name='fecha_alta',
            field=models.DateTimeField(verbose_name='fecha de alta'),
        ),
    ]
