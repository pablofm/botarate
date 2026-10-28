import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.pagos.models import FormaPago

from .models import INICIO_STOCK, Bebida, CategoríaBebida, FormaPagoVenta, StockBebida, VentaBebida


class StockBebidaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(email='barra@botarate.es', password='x')
        # La data migration ya deja cargada la carta del ambigú.
        cls.cerveza = Bebida.objects.get(nombre='Cerveza con alcohol')
        cls.refresco = Bebida.objects.create(
            categoría=CategoríaBebida.objects.create(nombre='Zumos'),
            nombre='Zumo de piña', precio_venta=Decimal('2'))

    def comprar(self, bebida, cantidad, precio_compra, **cambios):
        return StockBebida.objects.create(
            bebida=bebida, cantidad=cantidad, precio_compra=Decimal(precio_compra),
            registrado_por=self.usuario, **cambios)

    def test_calcula_coste_y_beneficio_de_una_compra(self):
        compra = self.comprar(self.cerveza, 48, '0.45')

        self.assertEqual(compra.coste_total, Decimal('21.60'))
        self.assertEqual(compra.margen_unitario, Decimal('1.05'))
        self.assertEqual(compra.beneficio_previsto, Decimal('50.40'))

    def test_suma_las_unidades_compradas_de_cada_bebida(self):
        self.comprar(self.cerveza, 144, '0.45', fecha=datetime.date(2026, 9, 1))
        self.comprar(self.cerveza, 48, '0.47')
        self.comprar(self.refresco, 6, '0.80')

        self.assertEqual(self.cerveza.unidades_compradas, 192)
        self.assertEqual(self.refresco.unidades_compradas, 6)

    def test_el_stock_resta_las_ventas_desde_el_23_de_octubre(self):
        self.comprar(self.cerveza, 48, '0.45')
        self.comprar(self.cerveza, 24, '0.47')
        VentaBebida.objects.filter(bebida=self.cerveza).delete()
        for fecha, cantidad in ((datetime.date(2026, 10, 22), 100), (INICIO_STOCK, 5), (timezone.localdate(), 3)):
            VentaBebida.objects.create(
                bebida=self.cerveza, fecha=fecha, cantidad=cantidad,
                forma_pago=FormaPago.EFECTIVO, registrado_por=self.usuario)

        stock = dict(Bebida.objects.con_stock().values_list('nombre', 'stock_actual'))

        self.assertEqual(stock['Cerveza con alcohol'], 64)
        self.assertEqual(stock['Zumo de piña'], 0)

    def test_una_bebida_sin_compras_no_tiene_unidades(self):
        self.assertEqual(self.refresco.unidades_compradas, 0)

    def test_no_admite_compras_sin_unidades(self):
        with self.assertRaises(IntegrityError):
            self.comprar(self.cerveza, 0, '0.45')


class VentaBebidaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(email='barra@botarate.es', password='x')
        cls.cerveza = Bebida.objects.get(nombre='Cerveza con alcohol')

    def vender(self, cantidad, forma_pago=FormaPago.EFECTIVO):
        return VentaBebida.objects.create(
            bebida=self.cerveza, cantidad=cantidad, forma_pago=forma_pago, registrado_por=self.usuario)

    def test_registra_una_venta_con_fecha_de_hoy_por_defecto(self):
        venta = self.vender(3)

        self.assertEqual(venta.fecha, timezone.localdate())
        self.assertIn(venta, self.cerveza.ventas.all())

    def test_no_admite_ventas_sin_unidades(self):
        with self.assertRaises(IntegrityError):
            self.vender(0)

    def test_una_invitación_o_merma_no_cuesta_nada(self):
        self.assertEqual(self.vender(3, FormaPagoVenta.INVITACIÓN).importe, Decimal('0.00'))

    def test_no_admite_vender_más_de_lo_comprado(self):
        StockBebida.objects.create(
            bebida=self.cerveza, cantidad=5, precio_compra=Decimal('0.45'), registrado_por=self.usuario)
        venta = self.vender(3)
        venta.full_clean()

        for cantidad in (6, 7):
            with self.subTest(cantidad=cantidad):
                # Al editarla cuentan también las 3 que ya se llevaba: llega hasta 5.
                venta.cantidad = cantidad
                with self.assertRaises(ValidationError) as error:
                    venta.full_clean()
                self.assertIn('se pueden vender 5 como mucho', error.exception.message_dict['cantidad'][0])
        venta.cantidad = 5
        venta.full_clean()

        with self.assertRaises(ValidationError):
            VentaBebida(bebida=self.cerveza, cantidad=3, forma_pago=FormaPago.EFECTIVO,
                        registrado_por=self.usuario).full_clean()

    def test_las_ventas_de_antes_del_stock_no_se_limitan(self):
        VentaBebida(bebida=self.cerveza, cantidad=50, fecha=datetime.date(2026, 10, 22),
                    forma_pago=FormaPago.EFECTIVO, registrado_por=self.usuario).full_clean()

    def test_no_admite_formas_de_pago_pendientes_de_activar(self):
        venta = VentaBebida(
            bebida=self.cerveza, cantidad=1, forma_pago=FormaPago.BIZUM, registrado_por=self.usuario)

        with self.assertRaises(ValidationError) as error:
            venta.full_clean()
        self.assertIn('forma_pago', error.exception.message_dict)


class VentasDeSeptiembreTests(TestCase):
    def test_la_data_migration_carga_las_ventas_de_virginia(self):
        ventas = VentaBebida.objects.filter(registrado_por__email='virmarch@icloud.com')

        self.assertEqual(ventas.count(), 45)
        self.assertEqual(ventas.aggregate(unidades=models.Sum('cantidad'))['unidades'], 83)
        self.assertFalse(ventas.exclude(forma_pago='').exists())


class VistasAmbigúTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.administrativo = User.objects.create_user(
            email='admin@botarate.es', password='x', is_active=True, is_staff=True)
        cls.profesor = User.objects.create_user(email='profe@botarate.es', password='x', is_active=True)
        cls.cerveza = Bebida.objects.get(nombre='Cerveza con alcohol')
        cls.zumos = CategoríaBebida.objects.create(nombre='Zumos')

    def setUp(self):
        self.client.force_login(self.administrativo)

    def test_el_profesorado_no_entra_en_el_ambigú(self):
        self.client.force_login(self.profesor)
        for vista in ('bebidas', 'categorias_bebida', 'stock_bebidas', 'ventas_bebidas',
                      'bebida_nueva', 'venta_bebida_nueva'):
            with self.subTest(vista=vista):
                self.assertEqual(self.client.get(reverse(vista)).status_code, 403)

    def test_la_portada_del_ambigú_abre_las_ventas(self):
        self.assertRedirects(self.client.get('/ambigu/'), reverse('ventas_bebidas'))

    def test_avisa_de_las_bebidas_por_debajo_del_stock_mínimo(self):
        Bebida.objects.update(stock_mínimo=0)
        zumo = Bebida.objects.create(categoría=self.zumos, nombre='Zumo de piña', precio_venta=Decimal('2'),
                                     stock_mínimo=6)
        StockBebida.objects.create(
            bebida=self.cerveza, cantidad=6, precio_compra=Decimal('0.45'), registrado_por=self.administrativo)
        self.cerveza.stock_mínimo = 6
        self.cerveza.save()

        respuesta = self.client.get(reverse('bebidas'))

        # La cerveza está justo en el mínimo, así que solo falta el zumo.
        self.assertQuerySetEqual(respuesta.context['por_reponer'], [zumo])
        self.assertContains(respuesta, 'class="text-end text-danger fw-semibold">0</td>', count=1)
        for vista in ('bebidas', 'categorias_bebida', 'stock_bebidas', 'ventas_bebidas', 'venta_bebida_nueva'):
            with self.subTest(vista=vista):
                html = self.client.get(reverse(vista)).content.decode()
                self.assertIn('Hay que comprar esta bebida', html)
                self.assertRegex(html, r'(?s)<td[^>]*>Zumo de piña</td>\s*<td[^>]*>0</td>\s*<td[^>]*>6</td>')

    def test_los_listados_se_ven(self):
        StockBebida.objects.create(
            bebida=self.cerveza, cantidad=48, precio_compra=Decimal('0.45'), registrado_por=self.administrativo)
        for vista in ('bebidas', 'categorias_bebida', 'stock_bebidas', 'ventas_bebidas'):
            with self.subTest(vista=vista):
                self.assertContains(self.client.get(reverse(vista)), 'Cerveza con alcohol')

    def test_los_formularios_se_ven(self):
        compra = StockBebida.objects.create(
            bebida=self.cerveza, cantidad=48, precio_compra=Decimal('0.45'), registrado_por=self.administrativo)
        venta = VentaBebida.objects.first()
        urls = [reverse(vista) for vista in (
            'bebida_nueva', 'categoria_bebida_nueva', 'stock_bebida_nuevo', 'venta_bebida_nueva')]
        urls += [
            reverse('bebida_editar', args=[self.cerveza.pk]),
            reverse('categoria_bebida_editar', args=[self.zumos.pk]),
            reverse('stock_bebida_editar', args=[compra.pk]),
            reverse('venta_bebida_editar', args=[venta.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_registra_y_edita_una_categoría(self):
        respuesta = self.client.post(reverse('categoria_bebida_nueva'), {'nombre': 'Vinos'})
        self.assertRedirects(respuesta, reverse('categorias_bebida'))

        vinos = CategoríaBebida.objects.get(nombre='Vinos')
        self.client.post(reverse('categoria_bebida_editar', args=[vinos.pk]), {'nombre': 'Vino'})
        vinos.refresh_from_db()
        self.assertEqual(vinos.nombre, 'Vino')

    def test_registra_y_edita_una_bebida(self):
        datos = {'categoría': self.zumos.pk, 'nombre': 'Zumo de piña', 'precio_venta': '2', 'stock_mínimo': 3}
        respuesta = self.client.post(reverse('bebida_nueva'), datos)
        self.assertRedirects(respuesta, reverse('bebidas'))

        zumo = Bebida.objects.get(nombre='Zumo de piña')
        self.client.post(reverse('bebida_editar', args=[zumo.pk]), {**datos, 'stock_mínimo': 6})
        zumo.refresh_from_db()
        self.assertEqual(zumo.stock_mínimo, 6)

    def test_no_borra_una_categoría_con_bebidas(self):
        respuesta = self.client.post(
            reverse('categoria_bebida_eliminar', args=[self.cerveza.categoría.pk]), follow=True)

        self.assertContains(respuesta, 'todavía tiene bebidas')
        self.assertTrue(CategoríaBebida.objects.filter(pk=self.cerveza.categoría.pk).exists())

    def test_borra_una_categoría_vacía(self):
        respuesta = self.client.post(reverse('categoria_bebida_eliminar', args=[self.zumos.pk]))

        self.assertRedirects(respuesta, reverse('categorias_bebida'))
        self.assertFalse(CategoríaBebida.objects.filter(pk=self.zumos.pk).exists())

    def test_no_borra_una_bebida_con_ventas(self):
        respuesta = self.client.post(reverse('bebida_eliminar', args=[self.cerveza.pk]), follow=True)

        self.assertContains(respuesta, 'tiene compras o ventas registradas')
        self.assertTrue(Bebida.objects.filter(pk=self.cerveza.pk).exists())

    def test_registra_una_compra_a_nombre_de_quien_la_apunta(self):
        respuesta = self.client.post(reverse('stock_bebida_nuevo'), {
            'bebida': self.cerveza.pk, 'fecha': '2026-10-01', 'cantidad': 48, 'precio_compra': '0.45'})

        self.assertRedirects(respuesta, reverse('stock_bebidas'))
        compra = StockBebida.objects.get()
        self.assertEqual((compra.cantidad, compra.registrado_por), (48, self.administrativo))

    def datos_venta(self, **cambios):
        return {'bebida': self.cerveza.pk, 'fecha': '2026-10-01', 'cantidad': 2,
                'forma_pago': FormaPago.EFECTIVO, **cambios}

    def test_registra_una_venta_a_nombre_de_quien_la_apunta(self):
        respuesta = self.client.post(reverse('venta_bebida_nueva'), self.datos_venta())

        self.assertRedirects(respuesta, reverse('ventas_bebidas'))
        venta = VentaBebida.objects.get(registrado_por=self.administrativo)
        self.assertEqual((venta.cantidad, venta.importe), (2, Decimal('3.00')))

    def test_una_venta_nueva_necesita_forma_de_pago(self):
        respuesta = self.client.post(reverse('venta_bebida_nueva'), self.datos_venta(forma_pago=''))

        self.assertFormError(respuesta.context['form'], 'forma_pago', 'Este campo es obligatorio.')

    def test_registra_una_invitación_o_merma_gratis(self):
        respuesta = self.client.post(
            reverse('venta_bebida_nueva'), self.datos_venta(forma_pago=FormaPagoVenta.INVITACIÓN))

        self.assertRedirects(respuesta, reverse('ventas_bebidas'))
        venta = VentaBebida.objects.get(registrado_por=self.administrativo)
        self.assertEqual(venta.importe, Decimal('0.00'))

    def test_la_invitación_o_merma_no_es_una_forma_de_pago_de_clases(self):
        self.assertNotIn('INVITACION', FormaPago.values)

    def test_una_venta_nueva_no_admite_bizum(self):
        respuesta = self.client.post(reverse('venta_bebida_nueva'), self.datos_venta(forma_pago=FormaPago.BIZUM))

        self.assertContains(respuesta, 'Bizum está pendiente de activar')

    def test_una_venta_antigua_se_edita_sin_forma_de_pago(self):
        venta = VentaBebida.objects.filter(forma_pago='').first()

        respuesta = self.client.post(
            reverse('venta_bebida_editar', args=[venta.pk]), self.datos_venta(cantidad=5, forma_pago=''))

        self.assertRedirects(respuesta, reverse('ventas_bebidas'))
        venta.refresh_from_db()
        self.assertEqual((venta.cantidad, venta.registrado_por.email), (5, 'virmarch@icloud.com'))

    def test_borra_una_venta(self):
        venta = VentaBebida.objects.first()

        respuesta = self.client.post(reverse('venta_bebida_eliminar', args=[venta.pk]))

        self.assertRedirects(respuesta, reverse('ventas_bebidas'))
        self.assertFalse(VentaBebida.objects.filter(pk=venta.pk).exists())

    def test_el_formulario_de_venta_lleva_el_pvp_para_calcular_el_importe(self):
        respuesta = self.client.get(reverse('venta_bebida_nueva'))

        self.assertContains(respuesta, f'value="{self.cerveza.pk}" data-precio="1.50"')
        self.assertContains(respuesta, 'id="importe-venta"')

    def test_el_formulario_de_venta_pone_todos_los_campos_en_una_fila(self):
        html = self.client.get(reverse('venta_bebida_nueva')).content.decode()

        posiciones = [html.index(f'id="id_{campo}"') for campo in ('fecha', 'bebida', 'cantidad', 'forma_pago_0')]
        self.assertEqual(posiciones, sorted(posiciones))
        self.assertRegex(html, r'(?s)<div class="row">(?:(?!class="row").)*id="id_fecha"'
                               r'(?:(?!class="row").)*id="id_forma_pago_0"')

    def test_el_listado_de_ventas_suma_el_total(self):
        self.assertContains(self.client.get(reverse('ventas_bebidas')), '132,00 €')
