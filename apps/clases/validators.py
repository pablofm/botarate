from django.core.validators import RegexValidator

# localflavor ya no trae campos de teléfono (los retiró en la versión 4), así que
# nos basta con una comprobación de formato holgada: fijo o móvil, con o sin prefijo.
validar_teléfono = RegexValidator(
    regex=r'^\+?\d[\d\s.-]{7,}$',
    message='Escribe un teléfono válido: 600 123 456, o con prefijo (+34 600 123 456).')