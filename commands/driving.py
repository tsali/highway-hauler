"""
Highway Hauler — Driving and navigation commands.
"""

import heapq
import random
import time
from evennia.commands.command import Command
from world.cities import CITIES, HIGHWAYS


def build_adjacency():
    """Build adjacency dict from HIGHWAYS: {city: [(neighbor, dist, hwy), ...]}."""
    adj = {}
    for a, b, dist, hwy in HIGHWAYS:
        adj.setdefault(a, []).append((b, dist, hwy))
        adj.setdefault(b, []).append((a, dist, hwy))
    return adj


def dijkstra_path(start, end):
    """
    Find shortest-distance path from start to end using Dijkstra's algorithm.
    Returns (total_distance, [(city_key, dist_from_prev, highway), ...]) or None.
    The first entry has dist_from_prev=0 (the start city).
    """
    adj = build_adjacency()
    if start not in adj or end not in adj:
        return None

    # dist_so_far[city] = (total_dist, prev_city, dist_from_prev, highway_from_prev)
    dist_so_far = {start: (0, None, 0, "")}
    heap = [(0, start)]
    visited = set()

    while heap:
        curr_dist, curr = heapq.heappop(heap)
        if curr in visited:
            continue
        visited.add(curr)

        if curr == end:
            # Reconstruct path
            path = []
            node = end
            while node is not None:
                total, prev, seg_dist, hwy = dist_so_far[node]
                path.append((node, seg_dist, hwy))
                node = prev
            path.reverse()
            return (curr_dist, path)

        for neighbor, edge_dist, hwy in adj.get(curr, []):
            if neighbor in visited:
                continue
            new_dist = curr_dist + edge_dist
            if neighbor not in dist_so_far or new_dist < dist_so_far[neighbor][0]:
                dist_so_far[neighbor] = (new_dist, curr, edge_dist, hwy)
                heapq.heappush(heap, (new_dist, neighbor))

    return None


def find_city_by_name(target):
    """Match a target string to a city key. Returns city_key or None."""
    target_lower = target.lower()
    for city_key, city_data in CITIES.items():
        city_name = city_data.get("name", "").lower()
        if target_lower == city_key or target_lower in city_name or city_name.startswith(target_lower):
            return city_key
    return None


def get_direct_connection(city_key, dest_key):
    """
    Check if dest_key is directly connected to city_key.
    Returns (distance, highway) or None.
    """
    best = None
    for a, b, dist, hwy in HIGHWAYS:
        if (a == city_key and b == dest_key) or (b == city_key and a == dest_key):
            if best is None or dist < best[0]:
                best = (dist, hwy)
    return best


def apply_gps_unreliability(trucker, dest_key, dist, hwy, city_key):
    """
    Apply GPS unreliability for one leg of a GPS route.
    Returns (dest_key, dist, hwy, detour_msg) — possibly modified.
    """
    reliability = trucker.gps_reliability
    if random.random() < reliability:
        # GPS works correctly this leg
        return dest_key, dist, hwy, None

    # GPS malfunction — pick one of two failure modes
    if random.random() < 0.5:
        # Mode A: Extra miles on this leg (detour)
        extra = random.randint(10, 30)
        msg = f"|y[GPS] Recalculating... Taking a detour. +{extra} extra miles.|n"
        return dest_key, dist + extra, hwy, msg
    else:
        # Mode B: Route through a random adjacent city instead
        adj = build_adjacency()
        neighbors = adj.get(city_key, [])
        # Filter out the correct destination to pick a wrong one
        wrong_neighbors = [(n, d, h) for n, d, h in neighbors if n != dest_key]
        if wrong_neighbors:
            wrong_dest, wrong_dist, wrong_hwy = random.choice(wrong_neighbors)
            wrong_name = CITIES.get(wrong_dest, {}).get("name", wrong_dest)
            msg = f"|y[GPS] Wrong turn! GPS sent you through {wrong_name} instead!|n"
            return wrong_dest, wrong_dist, wrong_hwy, msg
        else:
            # No wrong neighbors available, fall back to extra miles
            extra = random.randint(10, 30)
            msg = f"|y[GPS] Recalculating... Taking a detour. +{extra} extra miles.|n"
            return dest_key, dist + extra, hwy, msg


def start_driving_leg(caller, city_key, dest_key, dist, hwy, gps_route=None, gps_leg=False):
    """
    Start driving one leg. Shared by initial drive and GPS auto-continue.
    gps_route: remaining cities after this leg (list of city keys).
    gps_leg: True if this is an auto-continued GPS leg (shorter output).
    """
    dest_data = CITIES.get(dest_key, {})
    dest_name = dest_data.get("name", dest_key)
    dest_state = dest_data.get("state", "")

    # Check fuel
    fuel_needed = dist * caller.fuel_consumption
    if caller.db.fuel < fuel_needed * 0.3:
        caller.msg(f"|rNot enough fuel! You need at least {fuel_needed * 0.3:.0f} gallons for {dest_name}.|n")
        caller.msg("|wType |yrefuel|w to fill up first.|n")
        caller.db.gps_route = []
        return False

    # Set driving state
    caller.db.driving_to = dest_key
    caller.db.driving_from = city_key
    caller.db.driving_miles_left = dist
    caller.db.driving_miles_total = dist
    caller.db.driving_highway = hwy
    caller.db.current_weather = caller.db.current_weather or "clear"
    caller.db.gps_route = gps_route or []

    from typeclasses.scripts import DrivingScript, TICK_INTERVAL, GAME_MINUTES_PER_TICK

    eta_ticks = dist / (caller.speed * (GAME_MINUTES_PER_TICK / 60.0))
    eta_real_seconds = eta_ticks * TICK_INTERVAL

    if gps_leg:
        # Shorter message for GPS auto-continue
        caller.msg(f"|c[GPS] Next stop -- {dest_name}, {dest_state} ({hwy}, {dist} mi, ~{eta_real_seconds:.0f}s)|n")
    else:
        from_data = CITIES.get(city_key, {})
        from_name = from_data.get("name", city_key)
        fuel_needed_display = dist * caller.fuel_consumption

        caller.msg(f"\n|g{'=' * 50}|n")
        caller.msg(f"|g  HITTING THE ROAD|n")
        caller.msg(f"|g{'=' * 50}|n")
        caller.msg(f"|wFrom:|n {from_name}")
        caller.msg(f"|wTo:|n {dest_name}, {dest_state}")
        caller.msg(f"|wHighway:|n {hwy}")
        caller.msg(f"|wDistance:|n {dist} miles")
        caller.msg(f"|wETA:|n ~{eta_real_seconds:.0f} seconds (real time)")
        caller.msg(f"|wFuel needed:|n ~{fuel_needed_display:.0f} gallons")
        caller.msg(f"|g{'=' * 50}|n\n")

    # Announce to room and move to highway
    if caller.location:
        caller.location.msg_contents(
            f"|c{caller.db.handle or caller.key}|n pulls out onto |y{hwy}|n heading for |w{dest_name}|n.",
            exclude=[caller],
        )

    # Save the city room we're leaving from (for rest stop returns)
    caller.db.driving_city_room = caller.location

    # Move to highway room
    from typeclasses.rooms import get_or_create_highway_room
    hwy_room = get_or_create_highway_room()
    caller.move_to(hwy_room, quiet=True, move_type="drive")

    # Clear rest stop state
    caller.db.nearby_rest_stop = None
    caller.db.at_rest_stop = False

    # Start the driving script
    caller.scripts.add(DrivingScript)
    return True


class CmdDrive(Command):
    """
    Drive to a connected city, or use GPS to auto-route to distant cities.

    Usage:
        drive <city name>    - Drive to a city (adjacent, or GPS-routed if you have GPS)
        drive stop           - Cancel GPS auto-routing mid-trip
        drive cancel         - Cancel GPS auto-routing mid-trip

    If the destination is directly connected by highway, you drive there normally.
    If it's not directly connected and you have a GPS upgrade, the GPS will plan
    a multi-stop route and auto-drive you through intermediate cities.

    GPS units are unreliable — each leg has a chance of wrong turns or detours
    depending on your GPS quality level.
    """

    key = "drive"
    aliases = ["go", "head"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("|wUsage: drive <city name>|n")
            caller.msg("|wUsage: drive stop|w -- cancel GPS auto-routing|n")
            return

        # Handle drive stop / drive cancel
        arg = self.args.strip().lower()
        if arg in ("stop", "cancel"):
            gps_route = caller.db.gps_route or []
            if gps_route:
                caller.db.gps_route = []
                caller.msg("|y[GPS] Auto-routing cancelled.|n")
                if caller.is_driving:
                    caller.msg("|wYou'll finish this leg, then stop.|n")
                else:
                    caller.msg("|wGPS route cleared.|n")
            elif caller.is_driving:
                caller.msg("|rYou're on the road but have no GPS route to cancel.|n")
            else:
                caller.msg("|wNo GPS route active.|n")
            return

        if caller.is_driving:
            caller.msg("|rYou're already on the road! Type |wdrive stop|r to cancel GPS routing.|n")
            return

        # Resume from rest stop
        if caller.db.at_rest_stop and caller.db.driving_to:
            if caller.db.mandatory_rest:
                caller.msg("|rDOT regulations: You must sleep before driving again.|n")
                caller.msg("|rType |wsleep|r to rest.|n")
                return
            # Resume driving
            caller.db.at_rest_stop = False
            caller.db.nearby_rest_stop = None
            from typeclasses.rooms import get_or_create_highway_room
            hwy_room = get_or_create_highway_room()
            caller.move_to(hwy_room, quiet=True, move_type="drive")
            dest_key = caller.db.driving_to
            dest_name = CITIES.get(dest_key, {}).get("name", dest_key)
            miles_left = caller.db.driving_miles_left or 0
            hwy = caller.db.driving_highway or ""
            caller.msg(f"|gBack on {hwy}. {miles_left:.0f} miles to {dest_name}.|n")
            from typeclasses.scripts import DrivingScript
            caller.scripts.add(DrivingScript)
            return

        if caller.db.mandatory_rest:
            caller.msg("|rDOT regulations: You must sleep before driving again.|n")
            caller.msg("|rType |wsleep|r to rest.|n")
            return

        # Get current city
        city_key = None
        if caller.location and hasattr(caller.location, 'db') and caller.location.db.city_key:
            city_key = caller.location.db.city_key

        if not city_key:
            caller.msg("|rYou need to be at a city to start driving.|n")
            return

        # Find matching destination
        target = self.args.strip().lower()

        # First check direct connections
        connections = []
        for a, b, dist, hwy in HIGHWAYS:
            if a == city_key:
                connections.append((b, dist, hwy))
            elif b == city_key:
                connections.append((a, dist, hwy))

        # Deduplicate (shortest route if multiple highways)
        dest_map = {}
        for dest, dist, hwy in connections:
            if dest not in dest_map or dist < dest_map[dest][0]:
                dest_map[dest] = (dist, hwy)

        # Match target to a direct destination
        matched_direct = None
        for dest_key, (dist, hwy) in dest_map.items():
            dest_data = CITIES.get(dest_key, {})
            dest_name = dest_data.get("name", "").lower()
            if target in dest_name or target == dest_key or dest_name.startswith(target):
                matched_direct = (dest_key, dist, hwy)
                break

        if matched_direct:
            # Direct connection — drive normally (no GPS needed)
            dest_key, dist, hwy = matched_direct
            caller.db.gps_route = []
            start_driving_leg(caller, city_key, dest_key, dist, hwy)
            return

        # Not a direct connection — try to find the city anywhere on the map
        dest_city_key = find_city_by_name(target)

        if not dest_city_key:
            caller.msg(f"|rNo highway to '{self.args.strip()}' from here.|n")
            caller.msg("|wType |ylook|w to see connected cities.|n")
            return

        if dest_city_key == city_key:
            caller.msg("|rYou're already there!|n")
            return

        # Non-adjacent city — need GPS
        if not caller.has_gps:
            dest_name = CITIES.get(dest_city_key, {}).get("name", dest_city_key)
            caller.msg(f"|r{dest_name} isn't directly connected by highway.|n")
            caller.msg("|wUse |ymap|w to plan your route, or buy a GPS upgrade to auto-route.|n")
            return

        # GPS auto-routing via Dijkstra
        result = dijkstra_path(city_key, dest_city_key)
        if not result:
            caller.msg(f"|rNo route found to '{self.args.strip()}'.|n")
            return

        total_dist, path = result
        # path is [(start, 0, ""), (city2, dist, hwy), ..., (dest, dist, hwy)]
        # We need the legs: path[1], path[2], ..., path[-1]
        legs = path[1:]  # each is (city_key, segment_dist, highway)
        if not legs:
            caller.msg("|rYou're already there!|n")
            return

        # Display the GPS planned route
        route_names = []
        for leg_city, leg_dist, leg_hwy in legs:
            route_names.append(CITIES.get(leg_city, {}).get("name", leg_city))
        from_name = CITIES.get(city_key, {}).get("name", city_key)

        caller.msg(f"|c[GPS] Route: {from_name} -> {' -> '.join(route_names)} ({len(legs)} stop(s), {total_dist:,} mi)|n")

        # Store remaining legs (after the first one) as the GPS route
        remaining = [leg_city for leg_city, _, _ in legs[1:]]

        # Start the first leg, applying GPS unreliability
        first_dest, first_dist, first_hwy = legs[0]
        first_dest, first_dist, first_hwy, detour_msg = apply_gps_unreliability(
            caller, first_dest, first_dist, first_hwy, city_key
        )
        if detour_msg:
            caller.msg(detour_msg)
            # If GPS routed through wrong city, we need to recalculate remaining route
            if first_dest != legs[0][0]:
                # Wrong city — recalc remaining from that wrong city to final dest
                new_result = dijkstra_path(first_dest, dest_city_key)
                if new_result:
                    _, new_path = new_result
                    remaining = [c for c, _, _ in new_path[1:]]
                else:
                    remaining = []

        start_driving_leg(caller, city_key, first_dest, first_dist, first_hwy, gps_route=remaining)


class CmdRefuel(Command):
    """
    Fill up your fuel tank at a gas station.

    Usage:
        refuel
        refuel <amount>

    Without an amount, fills the tank completely.
    Gas costs $4.50/gallon.
    """

    key = "refuel"
    aliases = ["fuel", "gas"]
    locks = "cmd:all()"

    GAS_PRICE = 4.50

    def func(self):
        caller = self.caller

        if caller.is_driving:
            caller.msg("|rYou can't refuel while driving! Find a city first.|n")
            return

        current = caller.db.fuel or 0
        capacity = caller.fuel_capacity
        space = capacity - current

        if space <= 0:
            caller.msg("|gTank is already full!|n")
            return

        if self.args:
            try:
                amount = float(self.args.strip())
                amount = min(amount, space)
            except ValueError:
                caller.msg("|wUsage: refuel [amount]|n")
                return
        else:
            amount = space

        cost = amount * self.GAS_PRICE
        if cost > (caller.db.money or 0):
            # Buy what they can afford
            affordable = (caller.db.money or 0) / self.GAS_PRICE
            if affordable < 1:
                caller.msg(f"|rYou can't afford any fuel! Gas is ${self.GAS_PRICE:.2f}/gallon.|n")
                return
            amount = affordable
            cost = amount * self.GAS_PRICE

        caller.db.fuel = current + amount
        caller.db.money = (caller.db.money or 0) - int(cost)

        caller.msg(f"|g*** REFUELED ***|n")
        caller.msg(f"|wAdded:|n {amount:.1f} gallons")
        caller.msg(f"|wCost:|n ${cost:.2f}")
        caller.msg(f"|wTank:|n {caller.db.fuel:.1f}/{capacity} gallons")
        caller.msg(f"|wMoney:|n |g${caller.db.money:,}|n")


class CmdStop(Command):
    """
    Pull over at a rest stop or the roadside.

    Usage:
        stop           - Pull over (at rest stop if nearby, otherwise roadside)
        stop continue  - Get back on the road after stopping

    When near a rest stop, you can refuel, eat, use the restroom, and sleep.
    Type 'stop continue' or 'drive' to resume your trip.
    """

    key = "stop"
    aliases = ["pull over", "pullover"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        arg = self.args.strip().lower() if self.args else ""

        # Resume driving from a rest stop
        if arg in ("continue", "resume", "go"):
            if not caller.db.at_rest_stop:
                caller.msg("|wYou're not at a rest stop.|n")
                return
            if not caller.db.driving_to:
                caller.msg("|wYou don't have a destination. Type |ydrive <city>|w.|n")
                return

            # Move back to highway room and restart driving
            caller.db.at_rest_stop = False
            caller.db.nearby_rest_stop = None

            from typeclasses.rooms import get_or_create_highway_room
            hwy_room = get_or_create_highway_room()
            caller.move_to(hwy_room, quiet=True, move_type="drive")

            dest_key = caller.db.driving_to
            dest_name = CITIES.get(dest_key, {}).get("name", dest_key)
            miles_left = caller.db.driving_miles_left or 0
            hwy = caller.db.driving_highway or ""
            caller.msg(f"|gBack on {hwy}. {miles_left:.0f} miles to {dest_name}.|n")

            from typeclasses.scripts import DrivingScript
            caller.scripts.add(DrivingScript)
            return

        # Pull over
        if not caller.is_driving:
            caller.msg("|wYou're not driving.|n")
            return

        # Stop the driving script but keep driving state
        for script in caller.scripts.all():
            if script.key == "driving_script":
                script.stop()

        # Move to rest stop room
        from typeclasses.rooms import get_or_create_rest_stop_room
        rest_room = get_or_create_rest_stop_room()

        rest_name = caller.db.nearby_rest_stop or "Roadside Shoulder"
        rest_room.db.rest_stop_name = rest_name
        rest_room.db.highway_name = caller.db.driving_highway or ""

        caller.db.at_rest_stop = True
        caller.move_to(rest_room, quiet=True)
        caller.execute_cmd("look")

        # Lot lizard encounter chance at rest stops
        from commands.encounters import trigger_lot_lizard
        trigger_lot_lizard(caller)


class CmdMap(Command):
    """
    Show a regional map of the interstate highway network.

    Usage:
        map             - Show your current region
        map <city>      - Show that city's region
        map national    - Show the full national overview
        map regions     - List all regions

    Like flipping through a Rand McNally road atlas.
    """

    key = "map"
    locks = "cmd:all()"

    # Region maps: hand-drawn ASCII showing cities + highway labels
    # Each map ~12-15 lines, fits on a BBS terminal
    REGION_MAPS = {
        "northeast": (
            "Northeast",
            [
                "|w=== NORTHEAST ===|n",
                "",
                "|w                        BUF --------- BOS|n",
                "|w                       / |y(I-90)|n     / |y(I-90)|n |n",
                "|w                     /          /          |n",
                "|w                   PIT ------- CLE         |n",
                "|w                  / |y(I-76)|n    |           |n",
                "|w               NYC            COL --> |xMidwest|n",
                "|w                |              |            |n",
                "|w              |y(I-95)|n        |y(I-71)|n         |n",
                "|w                |              |            |n",
                "|w               PHL            CIN --> |xSoutheast|n",
                "|w                |                           |n",
                "|w               RIC --> |xSoutheast|n              |n",
                "",
                "|yI-90|w BOS-BUF-CLE  |yI-95|w BOS-NYC-PHL-RIC|n",
                "|yI-80|w NYC-PIT      |yI-71|w CLE-COL-CIN|n",
                "|yI-76|w PIT-CLE      |yI-79|w BUF-PIT|n",
            ],
        ),
        "southeast": (
            "Southeast",
            [
                "|w=== SOUTHEAST ===|n",
                "",
                "|w  |xNE|n<-- RIC               LOU --- CIN <--|xNE|n",
                "|w         |               / |y(I-65)|n \\|y(I-71)|n    |n",
                "|w       |y(I-85)|n       |y(I-64)|n      |            |n",
                "|w         |            STL   NAS --- ATL   |n",
                "|w        CHA          /   |y(I-65)|n |y(I-24)|n  |\\   |n",
                "|w          \\        /       |      / | \\  |n",
                "|w          ATL ---------- BHM     /  JAX |n",
                "|w          / |y(I-20)|n       |y(I-65)|n   /  |y(I-95)|n |n",
                "|w        /              MGM    /     |  |n",
                "|w  NOR ------ MOB --- |y(I-65)|n  TLH   |  |n",
                "|w  |y(I-10)|n      |y(I-10)|n  |     |y(I-10)|n  |  |n",
                "|w                    PNS ------+    MIA|n",
                "",
                "|yI-65|w LOU-NAS-BHM-MGM-MOB  |yI-95|w RIC-JAX-MIA|n",
                "|yI-10|w JAX-TLH-PNS-MOB-NOR  |yI-85|w RIC-CHA-ATL|n",
                "|yI-20|w ATL-BHM-->|xS.Central|n    |yI-75|w CIN-ATL-JAX|n",
            ],
        ),
        "midwest": (
            "Midwest",
            [
                "|w=== MIDWEST ===|n",
                "",
                "|w          MIN --- MIL --- CHI --- DET|n",
                "|w         |y(I-94)|n       |y(I-94)|n  |  |y(I-94)|n|n",
                "|w           |              |     |   |n",
                "|w          |y(I-35)|n          |y(I-65)|n |y(I-75)|n |n",
                "|w           |              |     |   |n",
                "|w  |xPlains|n<--DSM         IND   CIN  |n",
                "|w            \\  |y(I-80)|n   |y(I-70)|n  / |y(I-71)|n|n",
                "|w             OMA      |    /       |n",
                "|w                    STL--LOU -->|xSE|n|n",
                "|w             |y(I-70)|n  |  |y(I-64)|n        |n",
                "|w                   KC --> |xPlains|n    |n",
                "",
                "|yI-94|w MIN-MIL-CHI-DET    |yI-65|w CHI-IND-LOU|n",
                "|yI-70|w PIT-COL-IND-STL-KC |yI-55|w CHI-STL-MEM|n",
                "|yI-80|w OMA-DSM            |yI-71|w CLE-COL-CIN-LOU|n",
            ],
        ),
        "south_central": (
            "South Central",
            [
                "|w=== SOUTH CENTRAL ===|n",
                "",
                "|w      |xMW|n<-- KC           MEM --- NAS -->|xSE|n",
                "|w             |          |y(I-55)|n |  |y(I-40)|n      |n",
                "|w           |y(I-35)|n        |              |n",
                "|w             |          LR --- OKC        |n",
                "|w            WIC       |y(I-40)|n    |  |y(I-40)|n     |n",
                "|w             |                  |           |n",
                "|w           |y(I-35)|n              |y(I-35)|n          |n",
                "|w             |                  |           |n",
                "|w            OKC ------------> ABQ -->|xMtn|n  |n",
                "|w             |y(I-40)|n                        |n",
                "|w            DAL ------- HOU                |n",
                "|w           |y(I-45)|n  |y(I-35)|n  |y(I-10)|n              |n",
                "|w            SAT ------+   NOR -->|xSE|n      |n",
                "",
                "|yI-35|w MIN-DSM-KC-WIC-OKC-DAL-SAT |yI-45|w DAL-HOU|n",
                "|yI-40|w MEM-LR-OKC-ABQ  |yI-10|w NOR-HOU-SAT-ELP|n",
                "|yI-55|w CHI-STL-MEM-NOR  |yI-20|w BHM-DAL|n",
            ],
        ),
        "mountain": (
            "Mountain West",
            [
                "|w=== MOUNTAIN WEST ===|n",
                "",
                "|w  |xNW|n<-- SPO         BIL          |n",
                "|w             |y(I-90)|n      |  |y(I-90)|n       |n",
                "|w                    |              |n",
                "|w          BOI     CHY              |n",
                "|w         |y(I-84)|n   |  |y(I-25)|n |y(I-80)|n          |n",
                "|w           |    DEN ------- OMA -->|xPlains|n|n",
                "|w          SLC  |y(I-25)|n  |y(I-70)|n   KC -->|xMW|n  |n",
                "|w         /  |y(I-80)|n |               |n",
                "|w  |xPac|n<--+      ABQ               |n",
                "|w    |y(I-15)|n    |y(I-25)|n |  |y(I-40)|n            |n",
                "|w   LV       |               |n",
                "|w            ELP -->|xS.Central|n       |n",
                "",
                "|yI-25|w ELP-ABQ-DEN-CHY   |yI-80|w OMA-CHY-SLC-SAC|n",
                "|yI-70|w KC-DEN            |yI-84|w SLC-BOI-POR|n",
                "|yI-90|w BIL-SPO           |yI-15|w LV-SLC|n",
            ],
        ),
        "pacific": (
            "Pacific West",
            [
                "|w=== PACIFIC WEST ===|n",
                "",
                "|w  SEA --- SPO -->|xMountain|n        |n",
                "|w   |  |y(I-90)|n                      |n",
                "|w  |y(I-5)|n                            |n",
                "|w   |                              |n",
                "|w  POR --- BOI -->|xMountain|n        |n",
                "|w   |  |y(I-84)|n                      |n",
                "|w  |y(I-5)|n            SLC -->|xMtn|n    |n",
                "|w   |             /  |y(I-80)|n        |n",
                "|w  SAC --------- +             |n",
                "|w   |  |y(I-80)|n    |y(I-15)|n            |n",
                "|w  SFO          LV              |n",
                "|w              |y(I-15)|n |  |y(US-93)|n       |n",
                "|w   LA -------- + --- PHX        |n",
                "|w   |  |y(I-15)|n      |y(I-10)|n  |          |n",
                "|w  SD          TUC ---- ELP -->|xMtn|n|n",
                "",
                "|yI-5|w SD-LA-SAC-POR-SEA  |yI-15|w SD-LA-LV-SLC|n",
                "|yI-80|w SAC-SLC           |yI-10|w LA-PHX-TUC-ELP|n",
            ],
        ),
        "plains": (
            "Great Plains",
            [
                "|w=== GREAT PLAINS ===|n",
                "",
                "|w          MIN -->|xMidwest|n           |n",
                "|w           |  |y(I-35)|n  |y(I-90)|n         |n",
                "|w           |                       |n",
                "|w          DSM ------ SXF           |n",
                "|w         |y(I-80)|n  |y(I-35)|n    |  |y(I-29)|n      |n",
                "|w           |        |              |n",
                "|w          OMA ----- + --- BIL -->|xMtn|n|n",
                "|w         |y(I-29)|n       |y(I-90)|n           |n",
                "|w           |                       |n",
                "|w          KC --- WIC               |n",
                "|w        |y(I-70)|n   |y(I-35)|n                  |n",
                "|w  |xMtn|n<-- DEN    OKC -->|xS.Central|n       |n",
                "",
                "|yI-35|w MIN-DSM-KC-WIC-OKC  |yI-29|w SXF-OMA-KC|n",
                "|yI-80|w OMA-CHY             |yI-90|w SXF-BIL|n",
                "|yI-70|w KC-DEN              |yI-80|w DSM-OMA|n",
            ],
        ),
        "northwest": (
            "Northwest",
            [
                "|w=== NORTHWEST ===|n",
                "",
                "|w  SEA ---------- SPO               |n",
                "|w   |   |y(I-90)|n       |                |n",
                "|w  |y(I-5)|n              |y(I-90)|n             |n",
                "|w   |               |                |n",
                "|w  POR             BIL -->|xMountain|n   |n",
                "|w   |                                |n",
                "|w  |y(I-84)|n           BOI              |n",
                "|w   |            |y(I-84)|n               |n",
                "|w   +----------- + --> SLC -->|xMountain|n|n",
                "",
                "|yI-90|w SEA-SPO-BIL       |yI-5|w SEA-POR|n",
                "|yI-84|w POR-BOI-SLC       |n",
            ],
        ),
    }

    NATIONAL_MAP = [
        "|w=== NATIONAL OVERVIEW ===|n",
        "",
        "|w SEA-SPO       BIL         MIN-MIL              BUF--BOS|n",
        "|w  |    \\        |            |   \\                |     ||n",
        "|w POR   BOI      |           SXF  CHI--DET       PIT   NYC|n",
        "|w  |     |       |            |    |    |          |     ||n",
        "|w SAC  SLC-----CHY           DSM  IND   \\    COL-CLE   PHL|n",
        "|w  |    |        |            |/   |    |     |    |     ||n",
        "|w SFO   |       DEN          OMA  LOU--CIN   |   RIC    ||n",
        "|w       |        |            | /  |    \\     |    |     ||n",
        "|w      LV       ABQ          KC STL NAS  \\  CHA   |     ||n",
        "|w       |      / |            |  |   |   ATL  |    |     ||n",
        "|w     PHX   TUC  ELP        WIC MEM BHM / \\ JAX  TLH   ||n",
        "|w      |     |    |           |   |  MGM   |   PNS  |    ||n",
        "|w     LA     |    |         OKC  LR  |    |    |    |   MIA|n",
        "|w      |     +----+    SAT-DAL  NOR MOB--+----+    +----+|n",
        "|w     SD               |   |    |                        |n",
        "|w                      +-HOU---+                         |n",
        "",
        "|wRegions:|n |yNE|n |ySE|n |yMW|n |ySC|n |yMtn|n |yPac|n |yPlains|n |yNW|n",
        "|wType |ymap <region>|w or |ymap <city>|w to zoom in.|n",
    ]

    # Aliases for regions
    REGION_ALIASES = {
        "ne": "northeast", "northeast": "northeast",
        "se": "southeast", "southeast": "southeast",
        "mw": "midwest", "midwest": "midwest",
        "sc": "south_central", "south central": "south_central", "south_central": "south_central",
        "mtn": "mountain", "mountain": "mountain",
        "pac": "pacific", "pacific": "pacific",
        "plains": "plains", "great plains": "plains",
        "nw": "northwest", "northwest": "northwest",
        "national": "national", "us": "national", "usa": "national", "all": "national",
    }

    def func(self):
        caller = self.caller

        if not self.args:
            # Show current region
            region = self._get_caller_region(caller)
            if region and region in self.REGION_MAPS:
                name, lines = self.REGION_MAPS[region]
                caller.msg("\n".join(lines))
                caller.msg("")
                caller.msg(f"|wYou are in the |y{name}|w region.|n")
                caller.msg("|wType |ymap <city>|w to see another region. |ymap national|w for full US.|n")
            else:
                # Fallback to national if region unknown
                caller.msg("\n".join(self.NATIONAL_MAP))
            return

        arg = self.args.strip().lower()

        # Check if it's a region name/alias
        region_key = self.REGION_ALIASES.get(arg)
        if region_key == "national":
            caller.msg("\n".join(self.NATIONAL_MAP))
            return
        if region_key and region_key in self.REGION_MAPS:
            name, lines = self.REGION_MAPS[region_key]
            caller.msg("\n".join(lines))
            return

        # Check if it's a city name
        city_key = find_city_by_name(arg)
        if city_key:
            city_data = CITIES.get(city_key, {})
            region = city_data.get("region", "")
            if region in self.REGION_MAPS:
                name, lines = self.REGION_MAPS[region]
                caller.msg("\n".join(lines))
                caller.msg("")
                caller.msg(f"|w{city_data.get('name', city_key)} is in the |y{name}|w region.|n")
                return

        # Check region by partial match
        for alias, rkey in self.REGION_ALIASES.items():
            if arg in alias:
                if rkey == "national":
                    caller.msg("\n".join(self.NATIONAL_MAP))
                    return
                if rkey in self.REGION_MAPS:
                    name, lines = self.REGION_MAPS[rkey]
                    caller.msg("\n".join(lines))
                    return

        caller.msg(f"|rUnknown region or city: '{self.args.strip()}'|n")
        caller.msg("|wRegions: |yne|w |yse|w |ymw|w |ysc|w |ymtn|w |ypac|w |yplains|w |ynw|w |ynational|n")

    def _get_caller_region(self, caller):
        """Get the region the caller is currently in."""
        # Check if at a city
        if caller.location and hasattr(caller.location, 'db'):
            city_key = getattr(caller.location.db, 'city_key', None)
            if city_key:
                return CITIES.get(city_key, {}).get("region", "")

        # Check if driving
        if caller.db.driving_to:
            return CITIES.get(caller.db.driving_to, {}).get("region", "")
        if caller.db.driving_from:
            return CITIES.get(caller.db.driving_from, {}).get("region", "")

        # Check home city
        if caller.db.home_city:
            return CITIES.get(caller.db.home_city, {}).get("region", "")

        return ""


class CmdSpeed(Command):
    """
    Set your driving speed.

    Usage:
        speed           - Show current speed
        speed <mph>     - Set speed (10 to your max)
        speed max       - Reset to max engine speed

    Slower speeds save fuel and avoid speeding tickets.
    The posted speed limit is 65 mph on most interstates.
    """

    key = "speed"
    aliases = ["throttle"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if not self.args:
            top = caller.max_speed
            current = caller.speed
            if current < top:
                caller.msg(f"|wSpeed set to |y{current} mph|w (max {top} mph). Limit: 65 mph.|n")
            else:
                caller.msg(f"|wSpeed at max: |y{top} mph|w. Limit: 65 mph.|n")
            caller.msg("|wType |yspeed <mph>|w to change. |yspeed max|w for full throttle.|n")
            return

        arg = self.args.strip().lower()
        top = caller.max_speed

        if arg == "max":
            caller.db.set_speed = 0
            caller.msg(f"|gSpeed set to max: |y{top} mph|n")
            return

        try:
            mph = int(arg)
        except ValueError:
            caller.msg("|rEnter a number or 'max'.|n")
            return

        if mph < 10:
            caller.msg("|rMinimum speed is 10 mph.|n")
            return
        if mph >= top:
            caller.db.set_speed = 0
            caller.msg(f"|gSpeed set to max: |y{top} mph|n")
            return

        caller.db.set_speed = mph
        if mph <= 65:
            caller.msg(f"|gSpeed set to |y{mph} mph|g. Under the limit — no tickets!|n")
        else:
            caller.msg(f"|ySpeed set to |y{mph} mph|y. Over the 65 mph limit — watch for cops.|n")
