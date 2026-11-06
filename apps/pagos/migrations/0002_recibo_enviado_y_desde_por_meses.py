from django.db import migrations, models


def desde_al_día_1(apps, schema_editor):
    """Los pagos por meses registrados antes de pagar por meses naturales empezaban el día
    en que se cobraban: pasan al día 1 de ese mismo mes."""
    Pago = apps.get_model('pagos', 'Pago')
    pendientes = Pago.objects.exclude(modalidad='CLASE').exclude(desde__day=1)
    for pago in pendientes:
        pago.desde = pago.desde.replace(day=1)
        pago.save(update_fields=['desde'])


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0001_pagos_de_alumnas'),
    ]

    operations = [
        migrations.AddField(
            model_name='pago',
            name='recibo_enviado',
            field=models.BooleanField(default=False, help_text='Márcalo cuando se le haya enviado el recibo a la alumna.', verbose_name='recibo enviado'),
        ),
        migrations.AlterField(
            model_name='pago',
            name='desde',
            field=models.DateField(help_text='Primer día que cubre el pago: el 1 del mes en que empieza, porque se paga por meses naturales; en una clase suelta, el día de la clase.', verbose_name='desde'),
        ),
        migrations.RunPython(desde_al_día_1, migrations.RunPython.noop),
    ]
