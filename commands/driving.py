"""
Highway Hauler — Driving and navigation commands.
"""

import time
from evennia.commands.command import Command
from world.cities import CITIES, HIGHWAYS


class CmdDrive(Command):
    """
    Drive to a connected city.

    Usage:
        drive <city name>

    Start driving to a city connected by highway from your current location.
    You must be at a city (not already on the road) to start driving.
    You must have enough fuel to make the trip.
    """

    key = "drive"
    aliases = ["go", "head"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if caller.is_driving:
            caller.msg("|rYou're already on the road! Type |wstop|r to pull over (not implemented yet).|n")
            return

        if caller.db.mandatory_rest:
            caller.msg("|rDOT regulations: You must sleep before driving again.|n")
            caller.msg("|rType |wsleep|r to rest.|n")
            return

        if not self.args:
            caller.msg("|wUsage: drive <city name>|n")
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

        # Match target to a destination
        matched = None
        for dest_key, (dist, hwy) in dest_map.items():
            dest_data = CITIES.get(dest_key, {})
            dest_name = dest_data.get("name", "").lower()
            if target in dest_name or target == dest_key or dest_name.startswith(target):
                matched = (dest_key, dist, hwy)
                break

        if not matched:
            caller.msg(f"|rNo highway to '{self.args.strip()}' from here.|n")
            caller.msg("|wType |ylook|w to see connected cities.|n")
            return

        dest_key, dist, hwy = matched
        dest_data = CITIES.get(dest_key, {})
        dest_name = dest_data.get("name", dest_key)
        dest_state = dest_data.get("state", "")

        # Check fuel
        fuel_needed = dist * caller.fuel_consumption
        if caller.db.fuel < fuel_needed * 0.3:  # Need at least 30% of fuel for the trip
            caller.msg(f"|rNot enough fuel! You need at least {fuel_needed * 0.3:.0f} gallons for {dest_name}.|n")
            caller.msg("|wType |yrefuel|w to fill up first.|n")
            return

        # Start driving
        caller.db.driving_to = dest_key
        caller.db.driving_from = city_key
        caller.db.driving_miles_left = dist
        caller.db.driving_highway = hwy
        caller.db.current_weather = "clear"

        from_data = CITIES.get(city_key, {})
        from_name = from_data.get("name", city_key)

        # Estimate travel time
        eta_minutes = (dist / caller.speed) * 60
        eta_ticks = dist / (caller.speed * (GAME_MINUTES_PER_TICK / 60.0))
        eta_real_seconds = eta_ticks * TICK_INTERVAL

        from typeclasses.scripts import DrivingScript, TICK_INTERVAL, GAME_MINUTES_PER_TICK

        caller.msg(f"\n|g{'=' * 50}|n")
        caller.msg(f"|g  HITTING THE ROAD|n")
        caller.msg(f"|g{'=' * 50}|n")
        caller.msg(f"|wFrom:|n {from_name}")
        caller.msg(f"|wTo:|n {dest_name}, {dest_state}")
        caller.msg(f"|wHighway:|n {hwy}")
        caller.msg(f"|wDistance:|n {dist} miles")
        caller.msg(f"|wETA:|n ~{eta_real_seconds:.0f} seconds (real time)")
        caller.msg(f"|wFuel needed:|n ~{fuel_needed:.0f} gallons")
        caller.msg(f"|g{'=' * 50}|n\n")

        # Announce to room
        if caller.location:
            caller.location.msg_contents(
                f"|c{caller.db.handle or caller.key}|n pulls out onto |y{hwy}|n heading for |w{dest_name}|n.",
                exclude=[caller],
            )

        # Move to a "highway" state (stay in room but mark as driving)
        # The driving script handles everything
        caller.scripts.add(DrivingScript)


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


class CmdMap(Command):
    """
    Show an ASCII map of the interstate highway network.

    Usage:
        map
    """

    key = "map"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        # Simple text-based region map
        lines = [
            "|w" + "=" * 65 + "|n",
            "|w  HIGHWAY HAULER — INTERSTATE MAP|n",
            "|w" + "=" * 65 + "|n",
            "",
            "|w  SEA---SPO                              BUF---BOS|n",
            "|w   |        \\          MIN---SXF          |    / |n",
            "|w  POR       BIL---I90---/     |       PIT--CLE  NYC|n",
            "|w   |                   DSM---OMA       |   |    / |n",
            "|w  SAC---SLC---BOI       |     \\      COL--CIN  PHL|n",
            "|w   |    |    CHY---DEN  KC     |      |       RIC|n",
            "|w  SFO   |         |     |    STL---IND--CHI   |  |n",
            "|w        LV       ABQ   WIC    |    |   DET  CHA|n",
            "|w         \\       / \\    |    MEM--NAS       |   |n",
            "|w         PHX--TUC  ELP  OKC   |        ATL--|n",
            "|w          |              |   LR          |  |n",
            "|w         LA---SD   SAT--DAL         JAX----|n",
            "|w                    |    |          |      |n",
            "|w                   HOU---+       MIA      |n",
            "|w                    |                      |n",
            "|w                   NOR                     |n",
            "",
            "|wYour location is shown when you |ylook|w at a city.|n",
            "|wType |ycontracts|w for cargo, |ydrive <city>|w to travel.|n",
        ]
        caller.msg("\n".join(lines))
