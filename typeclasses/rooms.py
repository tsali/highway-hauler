"""
Highway Hauler — Room typeclasses.

Room types:
  CityRoom — A city with a freight terminal, gas station, truck stop
  HighwayRoom — On the road between cities (virtual/transient)
  ChargenRoom — Limbo room for character creation
"""

from evennia.objects.objects import DefaultRoom
from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """Base room for Highway Hauler."""

    def get_display_exits(self, looker, **kwargs):
        """Show exits with yellow direction names."""
        exits = self.filter_visible(
            self.contents_get(content_type="exit"), looker, **kwargs
        )
        if not exits:
            return ""
        parts = []
        for exi in exits:
            ename = exi.key
            dest = exi.destination
            if dest:
                parts.append(f"|lc{ename}|lt|y{ename}|n|le to |w{dest.key}|n")
            else:
                parts.append(f"|lc{ename}|lt|y{ename}|n|le")
        return "|wExits:|n " + ", ".join(parts)

    def get_display_characters(self, looker, **kwargs):
        """Show other truckers at this location."""
        from typeclasses.characters import Trucker

        characters = self.filter_visible(
            self.contents_get(content_type="character"), looker, **kwargs
        )
        if not characters:
            return ""

        truckers = []
        for char in characters:
            if char == looker:
                continue
            if isinstance(char, Trucker):
                handle = char.db.handle or char.key
                truckers.append(f"|c{handle}|n")

        if not truckers:
            return ""
        return "|wTruckers here:|n " + ", ".join(truckers)


class CityRoom(Room):
    """
    A city location. Has services: terminal, gas station, truck stop.

    Attributes:
        city_key (str): Key into world.cities.CITIES
        city_data (dict): City data from CITIES dict
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.city_key = ""
        self.db.city_data = {}

    def get_display_desc(self, looker, **kwargs):
        """Show city description with services."""
        data = self.db.city_data or {}
        desc = data.get("desc", "A city.")
        state = data.get("state", "")
        tier = data.get("tier", 1)

        tier_label = {1: "Small Town", 2: "Mid-Size City", 3: "Major Metro"}
        services = ["|gFreight Terminal|n", "|yGas Station|n", "|cTruck Stop|n"]
        if tier >= 2:
            services.append("|mUpgrade Shop|n")
        if tier >= 3:
            services.append("|wRest Stop (Trivia)|n")

        lines = [
            f"|w{desc}|n",
            f"|wState:|n {state}  |wSize:|n {tier_label.get(tier, 'Town')}",
            f"|wServices:|n {', '.join(services)}",
        ]
        return "\n".join(lines)

    def get_display_footer(self, looker, **kwargs):
        """Show connected highways."""
        from world.cities import HIGHWAYS

        city_key = self.db.city_key
        if not city_key:
            return ""

        connections = []
        for a, b, dist, hwy in HIGHWAYS:
            if a == city_key:
                connections.append((b, dist, hwy))
            elif b == city_key:
                connections.append((a, dist, hwy))

        if not connections:
            return ""

        # Deduplicate
        seen = set()
        unique = []
        for dest, dist, hwy in connections:
            if dest not in seen:
                seen.add(dest)
                unique.append((dest, dist, hwy))

        unique.sort(key=lambda x: x[1])

        lines = ["|w--- HIGHWAYS ---|n"]
        for dest_key, dist, hwy in unique:
            from world.cities import CITIES
            dest_data = CITIES.get(dest_key, {})
            dest_name = dest_data.get("name", dest_key)
            dest_state = dest_data.get("state", "")
            lines.append(f"  |y{hwy}|n -> |w{dest_name}, {dest_state}|n ({dist} mi)")

        lines.append("")
        lines.append("|wType |ycontracts|n to see available cargo, |ydrive <city>|n to hit the road.|n")
        return "\n".join(lines)


class ChargenRoom(Room):
    """Room where new truckers set up their character."""

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("chargen_room", category="chargen")
