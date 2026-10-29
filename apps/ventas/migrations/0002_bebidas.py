"""Da de alta las bebidas de la hoja de inventario del ambigú.

De la hoja solo se toman el producto, la categoría, el precio de venta y el stock
mínimo; costes, entradas, ventas y stock no tienen todavía dónde guardarse.
«Refreco Limón» y «Refreco Maracuyá» son los Nestea de limón y de maracuyá, y
aquí ya van con ese nombre. «Acuarius» venía mal escrito y aquí ya va corregido. A este la hoja no le daba precio ni stock mínimo: el precio se ha
fijado a mano y el stock mínimo se queda en 0 hasta que se decida.
"""
from decimal import Decimal

from django.db import migrations

# (nombre, categoría, precio de venta, stock mínimo)
BEBIDAS = [
    ('Cerveza con alcohol', 'Cerveza', '1.5', 10),
    ('Cerveza 0,0', 'Cerveza sin alcohol', '1.5', 10),
    ('Refresco Cola', 'Refresco Gas', '2', 10),
    ('Refresco Cola 00', 'Refresco Gas', '2', 10),
    ('Refresco Naranja', 'Refresco Gas', '2', 5),
    ('Nestea Limón', 'Refresco Sin Gas', '2', 5),
    ('Nestea Maracuyá', 'Refresco Sin Gas', '2', 10),
    ('Agua 0,50L', 'Agua', '1', 10),
    ('Aquarius', 'Refresco Sin Gas', '2', 0),
]


def crear_bebidas(apps, schema_editor):
    CategoríaBebida = apps.get_model('ventas', 'CategoríaBebida')
    Bebida = apps.get_model('ventas', 'Bebida')

    for nombre, categoría, precio_venta, stock_mínimo in BEBIDAS:
        categoría, _ = CategoríaBebida.objects.get_or_create(nombre=categoría)
        Bebida.objects.get_or_create(
            nombre=nombre,
            defaults={
                'categoría': categoría,
                'precio_venta': Decimal(precio_venta),
                'stock_mínimo': stock_mínimo,
            })


def borrar_bebidas(apps, schema_editor):
    CategoríaBebida = apps.get_model('ventas', 'CategoríaBebida')
    Bebida = apps.get_model('ventas', 'Bebida')

    Bebida.objects.filter(nombre__in=[nombre for nombre, *_ in BEBIDAS]).delete()
    # Las categorías solo si se han quedado vacías: alguien puede haberles colgado otras bebidas.
    CategoríaBebida.objects.filter(
        nombre__in={categoría for _, categoría, *_ in BEBIDAS}, bebidas__isnull=True).delete()


class Migration(migrations.Migration):

    # Es la misma migración que se aplicó cuando la app se llamaba «ambigu»: donde ya
    # esté aplicada, Django la da por hecha y no vuelve a crear ni cargar nada.
    replaces = [('ambigu', '0002_bebidas')]

    dependencies = [
        ('ventas', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_bebidas, borrar_bebidas),
    ]
