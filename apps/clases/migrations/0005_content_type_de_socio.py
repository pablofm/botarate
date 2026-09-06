"""Lleva a «socios» el ContentType de Socio, con sus permisos.

Al mudar el modelo de app, Django crearía uno nuevo (socios.socio) en el
post_migrate y dejaría el viejo (clases.socio) huérfano, con sus cuatro permisos
colgando de él. Como el post_migrate va después de todas las migraciones, aquí
nos basta con renombrar el que ya hay.
"""
from django.db import migrations


def mover_content_type(apps, schema_editor, de_app, a_app):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')

    viejo = ContentType.objects.filter(app_label=de_app, model='socio').first()
    if viejo is None:
        return

    nuevo = ContentType.objects.filter(app_label=a_app, model='socio').first()
    if nuevo is None:
        # El caso normal: renombrarlo se lleva los permisos y a quien los tenga.
        viejo.app_label = a_app
        viejo.save(update_fields=['app_label'])
        return

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


def a_socios(apps, schema_editor):
    mover_content_type(apps, schema_editor, 'clases', 'socios')


def a_clases(apps, schema_editor):
    mover_content_type(apps, schema_editor, 'socios', 'clases')


class Migration(migrations.Migration):

    dependencies = [
        ('clases', '0004_socio_se_muda_a_su_app'),
        ('auth', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(a_socios, a_clases),
    ]
