"""La app «ambigu» pasa a llamarse «ventas»: sus tablas y sus ContentType la siguen.

Las migraciones 0001–0004 reemplazan a las de «ambigu», así que donde ya estaban
aplicadas no se repiten y las tablas siguen llamándose ambigu_*. Aquí se renombran
(se conservan filas, secuencias, índices y claves ajenas); en una base de datos nueva
no existen y no hay nada que hacer. Hacia atrás tampoco: para Django las tablas de
«ventas» siempre se han llamado ventas_*.

Los ContentType se renombran como en clases/0005, para que los permisos y el
historial del admin no se queden colgando del viejo; hacia atrás se quedan en
«ventas» por lo mismo que las tablas.
"""
from django.db import migrations

MODELOS = ['categoríabebida', 'bebida', 'stockbebida', 'ventabebida']


def mover_content_types(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')

    for modelo in MODELOS:
        viejo = ContentType.objects.filter(app_label='ambigu', model=modelo).first()
        if viejo is None:
            continue

        nuevo = ContentType.objects.filter(app_label='ventas', model=modelo).first()
        if nuevo is None:
            # El caso normal: renombrarlo se lleva los permisos y a quien los tenga.
            viejo.app_label = 'ventas'
            viejo.save(update_fields=['app_label'])
            continue

        # En una base de datos donde el destino ya existiera, pasamos los permisos al
        # nuevo (sin duplicar los que ya estén) y tiramos el viejo.
        for permiso in Permission.objects.filter(content_type=viejo):
            gemelo = Permission.objects.filter(content_type=nuevo, codename=permiso.codename).first()
            if gemelo is None:
                permiso.content_type = nuevo
                permiso.save(update_fields=['content_type'])
            else:
                gemelo.group_set.add(*permiso.group_set.all())
                gemelo.user_set.add(*permiso.user_set.all())
                permiso.delete()
        viejo.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0004_venta_forma_pago_invitacion'),
        ('auth', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[f'ALTER TABLE IF EXISTS "ambigu_{modelo}" RENAME TO "ventas_{modelo}";' for modelo in MODELOS],
            reverse_sql=migrations.RunSQL.noop),
        migrations.RunPython(mover_content_types, migrations.RunPython.noop),
    ]
