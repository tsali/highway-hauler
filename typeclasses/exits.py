"""Highway Hauler — Exit typeclass."""

from evennia.objects.objects import DefaultExit
from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """Base exit for Highway Hauler."""
    pass
