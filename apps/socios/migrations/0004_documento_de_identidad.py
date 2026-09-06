"""El DNI pasa a ser un documento de identidad con su tipo.

Quien no tiene DNI ni NIE —extranjeros de paso, sobre todo— no podía darse de alta,
porque el campo era obligatorio y se le comprobaba la letra. Ahora el número va en
«documento», con «tipo_documento» diciendo qué es, y la letra solo se comprueba
cuando el tipo es NIF.

Los 65 socios que hay son todos DNI o NIE válidos, así que el valor por defecto del
tipo nuevo ya es el que les toca. El campo deja de ser el DNIField de localflavor
—que fuerza nueve caracteres, y un pasaporte o un codice fiscale no caben— y pasa a
ser texto: quien valida ahora es Socio.clean().
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socios', '0003_socios_del_formulario_web'),
        # clases/0006 carga socios usando «dni», así que tiene que ir antes que el
        # rename. El estado histórico de una migración no es el de su fichero: es el
        # del plan, y sin esta arista el orden entre las dos ramas queda al azar.
        ('clases', '0006_matriculas_del_curso_26_27'),
    ]

    operations = [
        migrations.AddField(
            model_name='socio',
            name='tipo_documento',
            field=models.CharField(
                choices=[('NIF', 'DNI o NIE'), ('PAS', 'Pasaporte'), ('OTRO', 'Otro documento')],
                default='NIF', max_length=4, verbose_name='tipo de documento'),
        ),
        migrations.RenameField(
            model_name='socio',
            old_name='dni',
            new_name='documento',
        ),
        migrations.AlterField(
            model_name='socio',
            name='documento',
            field=models.CharField(
                error_messages={'unique': 'Ya hay un socio dado de alta con este documento.'},
                help_text='El DNI o NIE con la letra; quien no lo tenga, su pasaporte u otro documento.',
                max_length=20, unique=True, verbose_name='documento de identidad'),
        ),
    ]
