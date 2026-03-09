"""
Highway Hauler — Scripts.

DrivingScript: Handles real-time travel between cities.
  - Ticks every 10 seconds (represents ~15 minutes of game time)
  - Each tick subtracts miles based on truck speed
  - Consumes fuel proportional to distance
  - Random events: weather, weigh stations, breakdowns
  - When miles_left reaches 0, arrive at destination

ContractExpiryScript: Global script that expires overdue contracts.
EconomyScript: Global script for dynamic cargo pricing.
"""

import random
from evennia.scripts.scripts import DefaultScript
from evennia.utils import logger


# Time scale: 10 real seconds = ~15 game minutes
# At 60 mph, that's 15 miles per tick
TICK_INTERVAL = 10  # seconds
GAME_MINUTES_PER_TICK = 15


class Script(DefaultScript):
    """Base script."""
    pass


class DrivingScript(DefaultScript):
    """
    Attached to a Trucker while they're on the road.
    Ticks every TICK_INTERVAL seconds, moving them closer to destination.
    """

    def at_script_creation(self):
        self.key = "driving_script"
        self.interval = TICK_INTERVAL
        self.persistent = True

    def at_repeat(self):
        """Called every tick while driving."""
        trucker = self.obj
        if not trucker or not trucker.db.driving_to:
            self.stop()
            return

        # Calculate miles this tick
        speed = trucker.speed
        miles_this_tick = speed * (GAME_MINUTES_PER_TICK / 60.0)

        # Weather modifier
        weather = trucker.db.current_weather or "clear"
        weather_speed_mod = {
            "clear": 1.0,
            "rain": 0.8,
            "snow": 0.6,
            "fog": 0.7,
        }.get(weather, 1.0)
        miles_this_tick *= weather_speed_mod

        # Consume fuel
        fuel_used = miles_this_tick * trucker.fuel_consumption
        trucker.db.fuel = max(0, (trucker.db.fuel or 0) - fuel_used)

        # Out of fuel?
        if trucker.db.fuel <= 0:
            trucker.msg("|r*** OUT OF FUEL! ***|n")
            trucker.msg("|rYou're stranded on the highway. A tow truck is on the way...|n")
            trucker.msg(f"|rTow fee: |w$200|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - 200)
            trucker.db.fuel = 10.0  # Tow gives you enough to reach next city
            # Don't stop driving — just penalize and continue

        # Subtract miles
        trucker.db.driving_miles_left = max(0, (trucker.db.driving_miles_left or 0) - miles_this_tick)
        trucker.db.miles_driven = (trucker.db.miles_driven or 0) + int(miles_this_tick)

        # Random events (5% chance per tick)
        if random.random() < 0.05:
            self._random_event(trucker)

        # Highway gang encounter (desert stretches only)
        highway = trucker.db.driving_highway or ""
        from commands.encounters import trigger_highway_gang
        if trigger_highway_gang(trucker, highway):
            return  # Pause driving while encounter resolves

        # Check arrival
        if trucker.db.driving_miles_left <= 0:
            self._arrive(trucker)
            return

        # Periodic update (every 3rd tick roughly)
        if random.random() < 0.33:
            miles_left = trucker.db.driving_miles_left
            fuel_left = trucker.db.fuel
            trucker.msg(
                f"|w[{trucker.db.driving_highway}]|n "
                f"{miles_left:.0f} mi to {trucker.db.driving_to} | "
                f"Fuel: {fuel_left:.0f} gal | "
                f"{speed * weather_speed_mod:.0f} mph"
                f"{f' ({weather})' if weather != 'clear' else ''}"
            )

    def _random_event(self, trucker):
        """Trigger a random highway event."""
        event = random.choices(
            ["weather_change", "weigh_station", "flat_tire", "speed_trap", "nothing"],
            weights=[20, 15, 10, 10, 45],
            k=1,
        )[0]

        if event == "weather_change":
            new_weather = random.choice(["clear", "clear", "rain", "snow", "fog"])
            if new_weather != (trucker.db.current_weather or "clear"):
                trucker.db.current_weather = new_weather
                weather_msgs = {
                    "clear": "|wThe skies clear up. Good driving weather.|n",
                    "rain": "|b Rain starts falling. Slowing down.|n",
                    "snow": "|W Snow begins to cover the road. Careful now.|n",
                    "fog": "|x Dense fog rolls in. Visibility near zero.|n",
                }
                trucker.msg(weather_msgs.get(new_weather, ""))

        elif event == "weigh_station":
            trucker.msg("|y*** WEIGH STATION AHEAD ***|n")
            if trucker.current_cargo_weight > trucker.cargo_capacity:
                fine = random.randint(200, 500)
                trucker.msg(f"|r OVERWEIGHT! Fine: ${fine}|n")
                trucker.db.money = max(0, (trucker.db.money or 0) - fine)
                trucker.db.weigh_violations = (trucker.db.weigh_violations or 0) + 1
            else:
                trucker.msg("|gAll clear. Weight within limits. Roll on, driver.|n")

        elif event == "flat_tire":
            delay_miles = random.randint(5, 15)
            cost = random.randint(50, 150)
            trucker.msg(f"|r*** FLAT TIRE! ***|n")
            trucker.msg(f"|rRoadside repair: ${cost}. Lost {delay_miles} miles of progress.|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - cost)
            trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + delay_miles

        elif event == "speed_trap":
            if trucker.speed > 65:
                fine = random.randint(100, 300)
                trucker.msg(f"|r*** SPEED TRAP! ***|n")
                trucker.msg(f"|rClocked at {trucker.speed} in a 65 zone. Fine: ${fine}|n")
                trucker.db.money = max(0, (trucker.db.money or 0) - fine)

    def _arrive(self, trucker):
        """Handle arrival at destination city."""
        dest_key = trucker.db.driving_to
        from world.cities import CITIES
        dest_data = CITIES.get(dest_key, {})
        dest_name = dest_data.get("name", dest_key)

        trucker.msg(f"\n|g*** ARRIVED: {dest_name}, {dest_data.get('state', '')} ***|n")
        trucker.db.current_weather = "clear"

        # Move to the city room
        from evennia.utils.search import search_tag
        city_rooms = search_tag(dest_key, category="city")
        if city_rooms:
            trucker.move_to(city_rooms[0], quiet=True)
            trucker.msg("")
            trucker.execute_cmd("look")
        else:
            trucker.msg(f"|rError: Could not find room for {dest_name}.|n")

        # Clear driving state
        trucker.db.driving_to = None
        trucker.db.driving_from = None
        trucker.db.driving_miles_left = 0
        trucker.db.driving_highway = ""

        # Check for deliverable cargo
        deliverable = [
            c for c in (trucker.db.current_cargo or [])
            if c.get("destination") == dest_key
        ]
        if deliverable:
            trucker.msg(f"|y You have {len(deliverable)} cargo delivery(ies) for this city! Type |wdeliver|y to drop them off.|n")

        # Lot lizard encounter chance at truck stops
        from commands.encounters import trigger_lot_lizard
        trigger_lot_lizard(trucker)

        self.stop()


class ContractExpiryScript(DefaultScript):
    """
    Global script: runs every 5 minutes, expires overdue contracts from truckers.
    """

    def at_script_creation(self):
        self.key = "contract_expiry"
        self.interval = 300
        self.persistent = True

    def at_repeat(self):
        """Check all truckers for expired contracts."""
        import time
        from typeclasses.characters import Trucker
        now = time.time()

        for trucker in Trucker.objects.all():
            cargo = trucker.db.current_cargo or []
            expired = [c for c in cargo if c.get("deadline", 0) < now]
            if expired:
                remaining = [c for c in cargo if c.get("deadline", 0) >= now]
                trucker.db.current_cargo = remaining
                for c in expired:
                    trucker.msg(f"|r*** CONTRACT EXPIRED: {c.get('cargo_name', 'Unknown')} to {c.get('dest_name', '???')} ***|n")
                    trucker.msg("|rThe cargo has been reclaimed. Your reputation takes a hit.|n")
                    trucker.db.reputation = max(0, (trucker.db.reputation or 50) - 5)
