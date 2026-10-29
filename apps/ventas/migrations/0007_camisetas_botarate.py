"""Da de alta las camisetas de Botarate y la primera compra, de 24 camisetas.

Todas cuestan 7,25 € y se venden a 12 €. Se crean los dos cortes en todas las
tallas, aunque de algunas (Mujer XS y XXL, Hombre XS) no haya entrado ninguna,
para que estén listas si se compran. La compra va a nombre de Pablo, con fecha
del 08/09/2026.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import migrations

TALLAS = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
PRECIO_COMPRA = Decimal('7.25')
PRECIO_VENTA = Decimal('12')

PABLO = ('Pablo', 'pablofm@mailbox.org')
FECHA = datetime.date(2026, 9, 8)

# (corte, talla, unidades), del resumen por tallas de la hoja
ENTRADAS = [
    ('MUJER', 'S', 3),
    ('MUJER', 'M', 5),
    ('MUJER', 'L', 3),
    ('MUJER', 'XL', 1),
    ('HOMBRE', 'S', 2),
    ('HOMBRE', 'M', 4),
    ('HOMBRE', 'L', 3),
    ('HOMBRE', 'XL', 2),
    ('HOMBRE', 'XXL', 1),
]


def crear_camisetas(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'BotarateUser')
    Camiseta = apps.get_model('ventas', 'Camiseta')
    StockCamiseta = apps.get_model('ventas', 'StockCamiseta')

    nombre, email = PABLO
    # Si aún no existe, sin contraseña utilizable y sin activar, como los profesores.
    pablo, _ = Usuario.objects.get_or_create(
        email=email,
        defaults={
            'nombre': nombre,
            'password': make_password(None),
            'is_active': False,
            'is_staff': False,
            'is_superuser': False,
        })

    camisetas = {}
    for corte in ('MUJER', 'HOMBRE'):
        for talla in TALLAS:
            camisetas[corte, talla], _ = Camiseta.objects.get_or_create(
                corte=corte, talla=talla,
                defaults={'precio_compra': PRECIO_COMPRA, 'precio_venta': PRECIO_VENTA})

    StockCamiseta.objects.bulk_create(
        StockCamiseta(camiseta=camisetas[corte, talla], fecha=FECHA, cantidad=cantidad, registrado_por=pablo)
        for corte, talla, cantidad in ENTRADAS)


def borrar_camisetas(apps, schema_editor):
    Camiseta = apps.get_model('ventas', 'Camiseta')
    StockCamiseta = apps.get_model('ventas', 'StockCamiseta')

    StockCamiseta.objects.filter(registrado_por__email=PABLO[1], fecha=FECHA).delete()
    # Las camisetas solo si ya no tienen compras ni ventas: alguien puede haberlas usado.
    Camiseta.objects.filter(entradas_stock__isnull=True, ventas__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('ventas', '0006_camisetas'),
    ]

    operations = [
        migrations.RunPython(crear_camisetas, borrar_camisetas),
    ]
