"""
Highway Hauler — Base object typeclass.
"""

from evennia.objects.objects import DefaultObject


class ObjectParent:
    """Mixin for all Highway Hauler objects."""
    pass


class Object(ObjectParent, DefaultObject):
    """Base object for Highway Hauler."""
    pass
