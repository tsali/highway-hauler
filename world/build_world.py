"""
Highway Hauler — World builder.

Creates all city rooms and the chargen room.
Run from Evennia shell: exec open('/path/to/build_world.py').read()
Or: evennia run build_world.py
"""

from evennia.utils.search import search_tag
from evennia.utils import create
from world.cities import CITIES
from typeclasses.rooms import CityRoom, ChargenRoom


def build_world():
    """Create all city rooms and the chargen room."""

    # Create chargen room if it doesn't exist
    chargen_rooms = search_tag("chargen_room", category="chargen")
    if chargen_rooms:
        print(f"Chargen room already exists: {chargen_rooms[0]}")
    else:
        chargen = create.create_object(
            ChargenRoom,
            key="Trucker Registration",
            locks="view:all();edit:perm(Admin)",
        )
        chargen.db.desc = "You're at the trucker registration desk. Time to set up your rig."
        print(f"Created chargen room: {chargen}")

    # Create city rooms
    created = 0
    skipped = 0
    for city_key, city_data in CITIES.items():
        existing = search_tag(city_key, category="city")
        if existing:
            skipped += 1
            continue

        room = create.create_object(
            CityRoom,
            key=f"{city_data['name']}, {city_data['state']}",
            locks="view:all();edit:perm(Admin)",
        )
        room.db.city_key = city_key
        room.db.city_data = city_data
        room.db.desc = city_data.get("desc", "A city along the interstate.")
        room.tags.add(city_key, category="city")
        created += 1

    print(f"World build complete: {created} cities created, {skipped} already existed.")
    print(f"Total cities in data: {len(CITIES)}")


if __name__ == "__main__":
    build_world()
