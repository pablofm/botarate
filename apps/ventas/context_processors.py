from django.db.models import F

from apps.accounts.roles import es_staff

from .models import Bebida, Camiseta


def por_reponer(request):
    """El aviso de falta de stock va en el modal de avisos de la barra de navegación, así que se calcula en
    cualquier página: si falta cerveza, se ve también desde socias o el calendario."""
    # Las ventas son cosa del staff: a nadie más le sirve el aviso.
    if not es_staff(request.user):
        return {}
    apartados = []
    for producto in (Bebida, Camiseta):
        # Si están justo en el stock mínimo aún no hace falta comprar.
        artículos = list(producto.objects.con_stock().filter(stock_actual__lt=F('stock_mínimo')))
        if artículos:
            apartados.append({
                'título': producto._meta.verbose_name_plural, 'producto': producto._meta.model_name,
                'artículos': artículos})
    return {'por_reponer': apartados}
