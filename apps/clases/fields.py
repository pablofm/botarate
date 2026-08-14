from localflavor.es.models import ESIdentityCardNumberField


class DNIField(ESIdentityCardNumberField):
    """El DNI/NIE de localflavor, que además comprueba la letra.

    A diferencia del campo original, no admite el CIF de las empresas.
    """

    def formfield(self, **kwargs):
        # localflavor admite escribirlo con un separador («12345678-Z») y lo quita al
        # validarlo, así que el formulario ha de dejar pasar esos caracteres de más.
        kwargs.setdefault('max_length', self.max_length + 2)
        return super().formfield(only_nif=True, **kwargs)
