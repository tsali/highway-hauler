"""
Highway Hauler — Character generation.

New truckers pick a CB handle and a starting city.
"""

from evennia.commands.command import Command
from evennia.utils.evmenu import EvMenu
from world.cities import CITIES


def start_chargen(trucker):
    """Launch the chargen menu for a new trucker."""
    trucker.msg("|w" + "=" * 60 + "|n")
    trucker.msg("|w  HIGHWAY HAULER — New Trucker Setup|n")
    trucker.msg("|w" + "=" * 60 + "|n")
    trucker.msg("")
    EvMenu(
        trucker,
        "commands.chargen",
        startnode="node_handle",
        cmd_on_exit=None,
    )


def node_handle(caller, raw_string, **kwargs):
    """Pick your CB handle."""
    text = (
        "|wEvery trucker needs a handle — your name on the CB radio.\n"
        "|wWhat's your handle, driver?|n\n\n"
        "|y(Type your handle and press Enter)|n"
    )

    def _set_handle(caller, raw_string, **kwargs):
        handle = raw_string.strip()
        if not handle or len(handle) < 2 or len(handle) > 20:
            caller.msg("|rHandle must be 2-20 characters. Try again.|n")
            return "node_handle"
        caller.db.handle = handle
        caller.key = handle
        return "node_city"

    options = {"key": "_default", "goto": _set_handle}
    return text, options


def node_city(caller, raw_string, **kwargs):
    """Pick your starting city."""

    # Show tier 3 cities as starting options (major metros)
    start_cities = {k: v for k, v in CITIES.items() if v["tier"] >= 2}
    sorted_cities = sorted(start_cities.items(), key=lambda x: x[1]["name"])

    lines = [
        f"|wAlright {caller.db.handle}, where are you starting from?|n\n",
        "|wPick your home base:|n\n",
    ]
    for i, (key, data) in enumerate(sorted_cities, 1):
        lines.append(f"  |y{i:2}|n. |w{data['name']}, {data['state']}|n — {data['desc'][:60]}")

    lines.append(f"\n|y(Enter a number 1-{len(sorted_cities)})|n")
    text = "\n".join(lines)

    def _set_city(caller, raw_string, **kwargs):
        try:
            choice = int(raw_string.strip())
        except (ValueError, TypeError):
            caller.msg("|rEnter a number.|n")
            return "node_city"

        if choice < 1 or choice > len(sorted_cities):
            caller.msg("|rInvalid choice.|n")
            return "node_city"

        city_key, city_data = sorted_cities[choice - 1]
        caller.db.home_city = city_key
        caller.ndb._chosen_city = city_key
        caller.ndb._chosen_city_name = city_data["name"]
        return "node_confirm"

    options = {"key": "_default", "goto": _set_city}
    return text, options


def node_confirm(caller, raw_string, **kwargs):
    """Confirm choices."""
    city_name = caller.ndb._chosen_city_name or "Unknown"

    text = (
        f"\n|w=== CONFIRM YOUR TRUCKER ===|n\n\n"
        f"|wHandle:|n {caller.db.handle}\n"
        f"|wHome Base:|n {city_name}\n"
        f"|wStarting Cash:|n |g$500|n\n"
        f"|wTruck:|n Stock rig — 4-Cylinder engine, 50 gal tank, 20ft flatbed\n\n"
        f"|yLook good? (Y/N)|n"
    )

    def _confirm(caller, raw_string, **kwargs):
        answer = raw_string.strip().lower()
        if answer in ("y", "yes"):
            return "node_finish"
        elif answer in ("n", "no"):
            return "node_handle"
        else:
            caller.msg("|rY or N.|n")
            return "node_confirm"

    options = {"key": "_default", "goto": _confirm}
    return text, options


def node_finish(caller, raw_string, **kwargs):
    """Finalize character and move to starting city."""
    caller.db.chargen_complete = True
    city_key = caller.ndb._chosen_city or caller.db.home_city

    # Move to starting city
    from evennia.utils.search import search_tag
    city_rooms = search_tag(city_key, category="city")
    if city_rooms:
        caller.move_to(city_rooms[0], quiet=True)
    else:
        caller.msg("|rWarning: Could not find your starting city room.|n")

    text = (
        f"\n|g{'=' * 60}|n\n"
        f"|g  Welcome to the road, {caller.db.handle}!|n\n"
        f"|g{'=' * 60}|n\n\n"
        f"|wYou climb into your beat-up rig, turn the key, and the engine\n"
        f"coughs to life. The open road awaits.\n\n"
        f"Type |ycontracts|w to find your first haul.\n"
        f"Type |ystatus|w to check your truck.\n"
        f"Type |yhelp|w for all commands.|n\n"
    )

    return text, None
