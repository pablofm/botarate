"""Fecha de alta del socio.

Los socios que ya existen se quedan con la fecha en que se aplique esta
migración; las fechas reales las fija después una data migration aparte.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socios', '0001_initial'),
        # El ALTER TABLE es sobre socios_socio, y quien renombra la tabla a ese
        # nombre es clases/0004: sin esto el orden depende de la suerte.
        ('clases', '0004_socio_se_muda_a_su_app'),
    ]

    operations = [
        migrations.AddField(
            model_name='socio',
            name='fecha_alta',
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name='fecha de alta'),
        ),
    ]
