from localflavor.es.models import ESIdentityCardNumberField


class DNIField(ESIdentityCardNumberField):
    """El DNI/NIE de localflavor, que además comprueba la letra.

    A diferencia del campo original, no admite el CIF de las empresas.

    Ya no lo usa ningún modelo: Socio guarda ahora un documento de identidad de
    texto, porque un pasaporte no cabe en los nueve caracteres que fuerza este
    campo. Se queda porque las migraciones antiguas lo importan.
    """

    def formfield(self, **kwargs):
        # localflavor admite escribirlo con un separador («12345678-Z») y lo quita al
        # validarlo, así que el formulario ha de dejar pasar esos caracteres de más.
        kwargs.setdefault('max_length', self.max_length + 2)
        return super().formfield(only_nif=True, **kwargs)
