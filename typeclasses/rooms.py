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

        # Cargo reminder for looker
        import time as _time
        from typeclasses.characters import Trucker
        if isinstance(looker, Trucker):
            cargo = looker.db.current_cargo or []
            if cargo:
                lines.append("")
                lines.append("|y*** YOUR CARGO ***|n")
                for c in cargo:
                    mins_left = max(0, (c.get("deadline", 0) - _time.time()) / 60)
                    time_str = "|rOVERDUE|n" if mins_left <= 0 else f"{mins_left:.0f}m left"
                    lines.append(
                        f"  |w{c.get('cargo_name', '???')}|n -> "
                        f"|c{c.get('dest_name', '???')}|n | "
                        f"|g${c.get('pay', 0):,}|n | {time_str}"
                    )
                lines.append("|wType |ydrive <city>|n to deliver. |ymap|n to plan route.|n")
            else:
                lines.append("")
                lines.append("|wType |ycontracts|n for cargo. |ymap|n to plan routes. |ydrive <city>|n to go.|n")
        return "\n".join(lines)


class HighwayRoom(Room):
    """
    Virtual highway room. Truckers are moved here while driving.
    Description changes based on the region they're driving through.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.highway_name = ""
        self.locks.add("get:false()")

    def return_appearance(self, looker, **kwargs):
        """Show road scenery + driving status."""
        from typeclasses.characters import Trucker
        if not isinstance(looker, Trucker) or not looker.is_driving:
            return "|wYou're on the highway but not driving. Something went wrong.|n"

        import time as _time
        from world.cities import CITIES

        dest_key = looker.db.driving_to or ""
        from_key = looker.db.driving_from or ""
        dest_name = CITIES.get(dest_key, {}).get("name", dest_key)
        from_name = CITIES.get(from_key, {}).get("name", from_key)
        dest_region = CITIES.get(dest_key, {}).get("region", "")
        from_region = CITIES.get(from_key, {}).get("region", "")
        hwy = looker.db.driving_highway or ""
        miles_left = looker.db.driving_miles_left or 0
        total = looker.db.driving_miles_total or miles_left
        fuel = looker.db.fuel or 0
        weather = looker.db.current_weather or "clear"

        # Progress bar
        pct = max(0, min(1.0, 1.0 - (miles_left / total))) if total > 0 else 0
        filled = int(pct * 30)
        bar = "|g" + "=" * filled + "|w>|n" + "-" * (30 - filled)

        # Scenery based on region
        region = dest_region or from_region
        scenery = _get_scenery(region, weather, hwy)

        lines = [
            f"|y=== {hwy} ===|n",
            f"|w{from_name}|n [{bar}] |c{dest_name}|n",
            "",
            scenery,
            "",
            f"|wMiles left:|n {miles_left:.0f}/{total:.0f}  |wSpeed:|n {looker.speed} mph  |wWeather:|n {weather}",
            f"|wFuel:|n {fuel:.0f}/{looker.fuel_capacity} gal  |wHours:|n {looker.db.hours_driving or 0:.1f}/16",
        ]

        # Cargo
        cargo = looker.db.current_cargo or []
        if cargo:
            lines.append("")
            lines.append("|y*** CARGO ***|n")
            for c in cargo:
                mins_left = max(0, (c.get("deadline", 0) - _time.time()) / 60)
                time_str = "|rOVERDUE|n" if mins_left <= 0 else f"{mins_left:.0f}m"
                dest_marker = " |g<<< DELIVERING HERE|n" if c.get("destination") == dest_key else ""
                lines.append(
                    f"  |w{c.get('cargo_name', '???')}|n -> "
                    f"|c{c.get('dest_name', '???')}|n | "
                    f"|g${c.get('pay', 0):,}|n | {time_str}{dest_marker}"
                )

        # Rest stop nearby?
        rest = looker.db.nearby_rest_stop
        if rest:
            lines.append("")
            lines.append(f"|y*** {rest} — NEXT EXIT ***|n")
            lines.append("|wType |ystop|w to pull in for gas, food, and restrooms.|n")

        return "\n".join(lines)

    def get_display_name(self, looker=None, **kwargs):
        return ""

    def get_display_desc(self, looker, **kwargs):
        return ""

    def get_display_footer(self, looker, **kwargs):
        return ""


class RestStopRoom(Room):
    """
    A truck stop / rest area along the highway.
    Players can refuel, eat, use restroom, sleep here.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.rest_stop_name = ""
        self.db.highway_name = ""
        self.db.from_city = ""
        self.db.to_city = ""

    def return_appearance(self, looker, **kwargs):
        """Show rest stop info."""
        import time as _time
        from typeclasses.characters import Trucker

        name = self.db.rest_stop_name or "Truck Stop"
        hwy = self.db.highway_name or ""

        lines = [
            f"|y=== {name} ===|n",
            f"|wHighway:|n {hwy}",
            "",
            "|wA truck stop along the highway. Diesel fumes and coffee.|n",
            "|wThe parking lot is full of idling rigs.|n",
            "",
            "|wServices:|n |gGas Station|n, |yDiner|n, |cRestrooms|n, |mBunks|n",
            "",
        ]

        if isinstance(looker, Trucker):
            fuel = looker.db.fuel or 0
            lines.append(f"|wFuel:|n {fuel:.0f}/{looker.fuel_capacity} gal")
            lines.append("")
            lines.append("|wType |yrefuel|n, |yeat|n, |yrestroom|n, or |ysleep|n.|n")
            lines.append("|wType |ydrive|n to get back on the road.|n")

            cargo = looker.db.current_cargo or []
            if cargo:
                lines.append("")
                lines.append("|y*** CARGO ***|n")
                for c in cargo:
                    mins_left = max(0, (c.get("deadline", 0) - _time.time()) / 60)
                    time_str = "|rOVERDUE|n" if mins_left <= 0 else f"{mins_left:.0f}m"
                    lines.append(
                        f"  |w{c.get('cargo_name', '???')}|n -> "
                        f"|c{c.get('dest_name', '???')}|n | "
                        f"|g${c.get('pay', 0):,}|n | {time_str}"
                    )

        return "\n".join(lines)


# Regional scenery for highway driving
SCENERY = {
    "southeast": [
        "Pine trees line both sides of the highway. Spanish moss hangs from the oaks.",
        "You pass a pecan grove. A hand-painted sign advertises boiled peanuts ahead.",
        "Red clay embankments rise on either side. A hawk circles overhead.",
        "Kudzu covers everything — trees, fences, an abandoned barn. The South reclaims.",
        "A white church steeple pokes above the treeline. Cicadas drone in the heat.",
        "You cross a long bridge over a muddy river. Cypress knees poke from the water.",
    ],
    "northeast": [
        "Dense deciduous forest presses close. Road construction narrows you to one lane.",
        "Strip malls and warehouses blur past. Welcome to the BosWash corridor.",
        "You pass through a toll booth. Another $4.50 gone. The turnpike stretches ahead.",
        "Old brick factories line the highway. Rust Belt territory.",
        "Rolling hills and dairy farms. A state trooper sits in the median.",
    ],
    "midwest": [
        "Flat farmland to the horizon. Corn. Soybeans. Corn again. A grain elevator.",
        "Wind turbines spin lazily across the prairie. The sky is enormous out here.",
        "You pass a small town — water tower, grain silo, church, gas station. That's it.",
        "The road is arrow-straight for miles. Nothing but prairie grass and sky.",
        "A John Deere combine crawls through a field. Harvest season.",
    ],
    "south_central": [
        "Oil derricks pump slowly in the distance. The air smells like petroleum.",
        "Cattle ranches stretch to the horizon. A longhorn eyes your truck.",
        "You cross into Texas. Everything gets bigger — the sky, the road, the speed limit.",
        "A mega church and a Whataburger. You must be in Texas.",
        "Cotton fields stretch white to the horizon. A crop duster buzzes overhead.",
    ],
    "mountain": [
        "Red rock mesas rise from the desert floor. The road shimmers with heat.",
        "Sagebrush and tumbleweeds. A roadrunner sprints across the highway.",
        "Snow-capped peaks in the distance. The grade steepens and your engine labors.",
        "High desert. Nothing for miles but rock and sky and the white line ahead.",
        "You pass through a canyon. Sheer rock walls tower on both sides.",
    ],
    "pacific": [
        "Palm trees sway in the breeze. Traffic thickens as you near the coast.",
        "The Pacific glimmers on the horizon. Surfers dot the lineup.",
        "Vineyards cover the hillsides. Wine country. Napa Valley's finest.",
        "Fog rolls through the redwood groves. Your headlights cut through the mist.",
        "Avocado groves and strawberry fields. Welcome to California agriculture.",
    ],
    "plains": [
        "The Great Plains stretch endlessly. The horizon is a ruler-straight line.",
        "Wheat fields ripple in the wind like a golden ocean. Grain elevators rise like castles.",
        "A thunderhead builds to the west. Lightning flickers in the distance.",
        "Antelope graze near the fence line. They watch you pass without concern.",
        "Small-town America. A water tower painted with the high school mascot.",
    ],
    "northwest": [
        "Evergreen forests blanket the mountains. The air smells like pine and rain.",
        "Logging trucks rumble past in the opposite direction. Timber country.",
        "A river gorge opens up below. Whitewater churns between basalt walls.",
        "Rain. Always rain up here. Your wipers beat a steady rhythm.",
    ],
}


def _get_scenery(region, weather, highway):
    """Get a random scenery description for the region."""
    import random
    scenes = SCENERY.get(region, SCENERY["midwest"])
    scene = random.choice(scenes)

    # Weather overlay
    if weather == "rain":
        scene += " |bRain streaks the windshield.|n"
    elif weather == "snow":
        scene += " |WSnow dusts the shoulders.|n"
    elif weather == "fog":
        scene += " |xVisibility is poor. You lean forward.|n"

    return scene


def get_or_create_highway_room():
    """Get or create the shared highway room."""
    from evennia.utils.search import search_tag
    rooms = search_tag("highway_room", category="highway")
    if rooms:
        return rooms[0]
    room = HighwayRoom.create(key="The Highway", locks="get:false()")[0]
    room.tags.add("highway_room", category="highway")
    return room


def get_or_create_rest_stop_room():
    """Get or create the shared rest stop room."""
    from evennia.utils.search import search_tag
    rooms = search_tag("rest_stop_room", category="highway")
    if rooms:
        return rooms[0]
    room = RestStopRoom.create(key="Truck Stop", locks="get:false()")[0]
    room.tags.add("rest_stop_room", category="highway")
    return room


class ChargenRoom(Room):
    """Room where new truckers set up their character."""

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("chargen_room", category="chargen")
