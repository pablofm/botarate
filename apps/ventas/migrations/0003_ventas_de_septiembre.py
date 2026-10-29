"""Da de alta las ventas del ambigú de septiembre de 2026, todas registradas por Virginia.

De la hoja solo se toman la fecha, el producto y las unidades: el precio unitario y el
importe salen del PVP de cada bebida, que en todas las filas coincide con el de la carta.
La hoja no dice cómo se pagó, así que la forma de pago se queda en blanco. «Refreco
Limón» y «Refreco Maracuyá» son los Nestea, como en la carta, y la fecha «25/092026» se
ha leído como 25/09/2026.
"""
import datetime

from django.contrib.auth.hashers import make_password
from django.db import migrations

VIRGINIA = ('Virginia', 'virmarch@icloud.com')

# (día de septiembre, bebida, unidades), en el orden de la hoja
VENTAS = [
    (9, 'Cerveza con alcohol', 2),
    (9, 'Cerveza con alcohol', 1),
    (9, 'Refresco Cola 00', 1),
    (9, 'Cerveza con alcohol', 3),
    (9, 'Refresco Cola 00', 1),
    (10, 'Cerveza con alcohol', 1),
    (29, 'Cerveza con alcohol', 4),
    (30, 'Cerveza con alcohol', 2),
    (10, 'Cerveza con alcohol', 1),
    (10, 'Refresco Cola 00', 1),
    (10, 'Cerveza con alcohol', 4),
    (10, 'Refresco Cola 00', 2),
    (12, 'Cerveza con alcohol', 1),
    (12, 'Cerveza con alcohol', 3),
    (16, 'Cerveza con alcohol', 2),
    (17, 'Refresco Cola 00', 1),
    (17, 'Cerveza con alcohol', 1),
    (18, 'Refresco Naranja', 3),
    (18, 'Cerveza 0,0', 2),
    (18, 'Cerveza con alcohol', 1),
    (18, 'Cerveza con alcohol', 1),
    (18, 'Nestea Maracuyá', 2),
    (18, 'Cerveza 0,0', 1),
    (19, 'Cerveza con alcohol', 1),
    (22, 'Cerveza con alcohol', 1),
    (22, 'Cerveza con alcohol', 1),
    (23, 'Cerveza con alcohol', 1),
    (23, 'Nestea Maracuyá', 1),
    (25, 'Cerveza con alcohol', 1),
    (25, 'Cerveza 0,0', 1),
    (25, 'Cerveza con alcohol', 4),
    (25, 'Cerveza 0,0', 1),
    (25, 'Cerveza con alcohol', 1),
    (25, 'Cerveza con alcohol', 2),
    (25, 'Cerveza 0,0', 1),
    (25, 'Cerveza con alcohol', 2),
    (26, 'Cerveza con alcohol', 2),
    (26, 'Cerveza con alcohol', 2),
    (26, 'Cerveza con alcohol', 5),
    (26, 'Cerveza con alcohol', 5),
    (29, 'Cerveza con alcohol', 2),
    (29, 'Nestea Maracuyá', 2),
    (29, 'Cerveza con alcohol', 3),
    (29, 'Nestea Limón', 1),
    (30, 'Cerveza con alcohol', 2),
]


def septiembre(día):
    return datetime.date(2026, 9, día)


def crear_ventas(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'BotarateUser')
    Bebida = apps.get_model('ventas', 'Bebida')
    VentaBebida = apps.get_model('ventas', 'VentaBebida')

    nombre, email = VIRGINIA
    # Si aún no existe, sin contraseña utilizable y sin activar, como los profesores.
    virginia, _ = Usuario.objects.get_or_create(
        email=email,
        defaults={
            'nombre': nombre,
            'password': make_password(None),
            'is_active': False,
            'is_staff': False,
            'is_superuser': False,
        })
    bebidas = {bebida.nombre: bebida for bebida in Bebida.objects.filter(
        nombre__in={nombre for _, nombre, _ in VENTAS})}

    VentaBebida.objects.bulk_create(
        VentaBebida(
            fecha=septiembre(día), bebida=bebidas[nombre], cantidad=cantidad, registrado_por=virginia)
        for día, nombre, cantidad in VENTAS)


def borrar_ventas(apps, schema_editor):
    VentaBebida = apps.get_model('ventas', 'VentaBebida')

    VentaBebida.objects.filter(
        registrado_por__email=VIRGINIA[1],
        fecha__in={septiembre(día) for día, *_ in VENTAS}).delete()


class Migration(migrations.Migration):

    # Es la misma migración que se aplicó cuando la app se llamaba «ambigu»: donde ya
    # esté aplicada, Django la da por hecha y no vuelve a crear ni cargar nada.
    replaces = [('ambigu', '0003_ventas_de_septiembre')]

    dependencies = [
        ('accounts', '0001_initial'),
        ('ventas', '0002_bebidas'),
    ]

    operations = [
        migrations.RunPython(crear_ventas, borrar_ventas),
    ]
