import datetime
from collections import defaultdict

from django.utils import timezone

from apps.accounts.roles import es_administración
from apps.clases.models import Matrícula

from .models import Pago

# Con cuántos días de antelación se avisa de que a una matrícula se le acaba lo pagado.
DÍAS_DE_AVISO = 5


def matrículas_por_pagar(hoy):
    """Las matrículas sin un pago que cubra hoy («sin_pagar») y aquellas a las que
    se les acaba lo pagado en los próximos DÍAS_DE_AVISO días («por_pagar»).

    Cada curso se paga aparte, así que cuenta la matrícula y no la alumna: si va a
    dos cursos y ha pagado uno, el otro sale. Y se mira el día, no si hay clase:
    con una clase suelta, al día siguiente ya no está cubierta. Las matrículas exentas
    de pago no se miran.
    """
    periodos = defaultdict(list)
    for pago in Pago.objects.only('alumno_id', 'curso_id', 'modalidad', 'desde'):
        periodos[pago.alumno_id, pago.curso_id].append((pago.desde, pago.hasta))

    sin_pagar, por_pagar = [], []
    matrículas = Matrícula.objects.filter(exento_pago=False).select_related(
        'alumno__socio', 'curso').order_by('alumno__socio__nombre', 'curso__nombre')
    for matrícula in matrículas:
        cubiertos = periodos[matrícula.alumno_id, matrícula.curso_id]
        # Se encadenan los pagos que vienen seguidos para saber el primer día sin cubrir.
        día = hoy
        while hasta := max((h for d, h in cubiertos if d <= día <= h), default=None):
            día = hasta + datetime.timedelta(days=1)
        if día == hoy:
            anteriores = [h for d, h in cubiertos if h < hoy]
            sin_pagar.append({'matrícula': matrícula, 'cubierto_hasta': max(anteriores, default=None)})
        elif (día - hoy).days <= DÍAS_DE_AVISO:
            por_pagar.append({'matrícula': matrícula, 'vence': día})
    return sin_pagar, por_pagar


def pagos_pendientes(request):
    """Como el de falta de stock, este aviso va en la barra de navegación de todas las páginas."""
    # Los pagos solo los ve y los registra administración.
    if not es_administración(request.user):
        return {}
    sin_pagar, por_pagar = matrículas_por_pagar(timezone.localdate())
    return {'sin_pagar': sin_pagar, 'por_pagar': por_pagar}
