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

        # --- Tick trucker needs ---
        self._tick_needs(trucker)

        # Check mandatory rest (DOT hours limit)
        if trucker.db.mandatory_rest:
            trucker.msg("|r*** DOT VIOLATION: You must rest before driving again. ***|n")
            trucker.msg("|rPulling over at the next available stop.|n")
            self._force_stop(trucker)
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
            "storm": 0.5,
        }.get(weather, 1.0)
        miles_this_tick *= weather_speed_mod

        # Needs-based speed penalties
        needs_mod = 1.0
        if trucker.db.soiled:
            needs_mod -= 0.15
        if (trucker.db.hunger or 0) >= 80:
            needs_mod -= 0.05
        if (trucker.db.bladder or 0) >= 80:
            needs_mod -= 0.05
        fatigue = trucker.db.fatigue or 0
        if fatigue >= 80:
            needs_mod -= 0.10
            # Microsleep swerve chance
            if random.random() < 0.15:
                trucker.msg("|r*** Your eyes close for a second — you jerk the wheel! ***|n")
                trucker.msg("|rYou swerve across the rumble strips. That was close!|n")
                trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + random.randint(2, 5)

            # Missed exit chance (fatigue 80+, 8% per tick)
            if random.random() < 0.08:
                extra = random.randint(10, 25)
                trucker.msg("|r*** You missed your exit! ***|n")
                trucker.msg(f"|rYou were zoning out and blew right past the turn. {extra} extra miles to the next one.|n")
                trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + extra

            # Crash risk (fatigue 90+, 5% per tick — serious consequences)
            if fatigue >= 90 and random.random() < 0.05:
                self._fatigue_crash(trucker)

        miles_this_tick *= max(0.5, needs_mod)

        # Consume fuel (storms and snow use more fuel from headwinds/traction)
        fuel_weather_mod = {"storm": 1.3, "snow": 1.2}.get(weather, 1.0)
        fuel_used = miles_this_tick * trucker.fuel_consumption * fuel_weather_mod
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

        # Weather changes dynamically (10% chance per tick, region-appropriate)
        if random.random() < 0.10:
            self._weather_tick(trucker)

        # Weigh station encounters (3% per tick, separate from random events)
        if random.random() < 0.03:
            self._weigh_station(trucker)

        # Cop encounters (4% per tick, more likely when speeding or fatigued)
        if random.random() < 0.04:
            self._cop_encounter(trucker)

        # Random events (5% chance per tick — flat tire, road hazard, etc.)
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

        # Driving HUD — show every tick
        miles_left = trucker.db.driving_miles_left
        total_miles = trucker.db.driving_miles_total or miles_left
        fuel_left = trucker.db.fuel
        dest_key = trucker.db.driving_to
        from_key = trucker.db.driving_from
        from world.cities import CITIES
        dest_name = CITIES.get(dest_key, {}).get("name", dest_key)
        dest_region = CITIES.get(dest_key, {}).get("region", "")
        from_region = CITIES.get(from_key, {}).get("region", "")
        hwy = trucker.db.driving_highway or ""
        cur_speed = speed * weather_speed_mod

        # Progress bar (20 chars wide)
        if total_miles > 0:
            pct = max(0, min(1.0, 1.0 - (miles_left / total_miles)))
        else:
            pct = 0
        filled = int(pct * 20)
        truck_pos = min(19, filled)
        bar = "=" * truck_pos + "|w>|n" + "-" * (19 - truck_pos)

        # Weather icon
        weather_icon = {"clear": "", "rain": " |b~rain~|n", "snow": " |W*snow*|n", "fog": " |xfog|n", "storm": " |r!STORM!|n"}.get(weather, "")

        speed_color = "|r" if speed > 65 else "|w"
        speed_str = f"{speed_color}{cur_speed:.0f}mph|n"
        if speed > 65:
            speed_str += f" |r[!{speed - 65} over]|n"

        trucker.msg(
            f"|y{hwy}|n [{bar}] |c{dest_name}|n "
            f"{miles_left:.0f}mi | {speed_str} | "
            f"F:{fuel_left:.0f}g{weather_icon}"
        )

        # Scenery flavor text (every 3rd tick)
        if random.random() < 0.33:
            region = dest_region or from_region or "midwest"
            from typeclasses.rooms import _get_scenery
            trucker.msg(f"|x{_get_scenery(region, weather, hwy)}|n")

        # Check for rest areas along this highway segment
        self._check_rest_areas(trucker, miles_left, total_miles, hwy, from_key, dest_key)

    def _tick_needs(self, trucker):
        """Increase trucker needs each driving tick (10s = ~15 game minutes)."""
        stomach = trucker.db.stomach_issues or False

        # Hunger: +2-3 per tick
        hunger_inc = random.randint(2, 3)
        trucker.db.hunger = min(100, (trucker.db.hunger or 0) + hunger_inc)

        # Bladder: +3-4 per tick (2x if stomach issues)
        bladder_inc = random.randint(3, 4)
        if stomach:
            bladder_inc *= 2
        trucker.db.bladder = min(100, (trucker.db.bladder or 0) + bladder_inc)

        # Fatigue: +2 per tick (+1 extra if stomach issues)
        fatigue_inc = 2
        if stomach:
            fatigue_inc += 1
        trucker.db.fatigue = min(100, (trucker.db.fatigue or 0) + fatigue_inc)

        # Hours driving: +0.25 per tick (15 game minutes)
        trucker.db.hours_driving = (trucker.db.hours_driving or 0) + 0.25

        # Warnings
        hunger = trucker.db.hunger or 0
        bladder = trucker.db.bladder or 0
        fatigue = trucker.db.fatigue or 0
        hours = trucker.db.hours_driving or 0

        if hunger >= 80 and random.random() < 0.4:
            msgs = [
                "|yYour stomach growls loud enough to hear over the engine.|n",
                "|yYou haven't eaten in hours. The Cracker Barrel billboard is taunting you.|n",
                "|yYou're so hungry you're eyeing the gas station sushi in your mind.|n",
            ]
            trucker.msg(random.choice(msgs))

        if bladder >= 100 and not trucker.db.soiled:
            # You didn't make it
            trucker.db.soiled = True
            trucker.db.reputation = max(0, (trucker.db.reputation or 50) - 5)
            if stomach:
                msgs = [
                    "|r*** OH NO. OH NO NO NO. ***|n",
                    "|rThat chili dog has completed its journey. You did not make it to a restroom.|n",
                    "|rThe cab smells like a war crime. Your eyes are watering.|n",
                ]
            else:
                msgs = [
                    "|r*** IT HAPPENED. ***|n",
                    "|rYou held it as long as you could. The dam has broken.|n",
                    "|rYou stare straight ahead and pretend this isn't happening.|n",
                ]
            for m in msgs:
                trucker.msg(m)
            trucker.msg("|rReputation -5. Everyone at the next truck stop will know.|n")
            trucker.msg("|r  ** SOILED — Speed -15%. Can't accept contracts. Find a restroom! **|n")
            if trucker.has_cb:
                cb_msgs = [
                    "|y[CB] Unknown: \"What's that smell on channel 19? Somebody have an accident?\"|n",
                    "|y[CB] Big Jim: \"We got a code brown on the interstate, boys.\"|n",
                    "|y[CB] Roadhog: \"Somebody call hazmat, I can smell that rig from here.\"|n",
                ]
                trucker.msg(random.choice(cb_msgs))
        elif bladder >= 80 and random.random() < 0.4:
            msgs = [
                "|yYou really need to find a restroom. That last coffee was a mistake.|n",
                "|yEvery pothole is a test of willpower right now.|n",
                "|yYou're considering the Gatorade bottle option.|n",
            ]
            trucker.msg(random.choice(msgs))

        # Ongoing soiled reminders
        if trucker.db.soiled and random.random() < 0.25:
            msgs = [
                "|mYou shift uncomfortably in the driver's seat.|n",
                "|mThe air freshener shaped like a pine tree is losing the battle.|n",
                "|mYou crack the window. It doesn't help.|n",
                "|mA fly has found its way into the cab. It seems happy.|n",
                "|mYou catch a whiff and gag. Find a restroom. Please.|n",
            ]
            trucker.msg(random.choice(msgs))

        if fatigue >= 80 and random.random() < 0.4:
            msgs = [
                "|yYour eyelids are getting heavy. The road lines are blurring together.|n",
                "|yYou catch yourself drifting. Maybe pull over soon.|n",
                "|yThe rumble strips wake you up. That's the third time this mile.|n",
            ]
            trucker.msg(random.choice(msgs))

        # DOT mandatory rest at 16 hours
        if hours >= 16:
            trucker.msg("|r*** DOT HOURS OF SERVICE: 16 hours reached! ***|n")
            trucker.msg("|rFederal regulations require you to stop and rest.|n")
            trucker.msg("|rYou must sleep for 8 hours before driving again.|n")
            trucker.db.mandatory_rest = True

        # Stomach issues: embarrassing messages
        if stomach and random.random() < 0.35:
            msgs = [
                "|m*GRRRRGLE* Your stomach makes a sound like a diesel engine misfiring.|n",
                "|mYou break a cold sweat. That chili dog is staging a revolt.|n",
                "|mYour gut is doing things that violate the Geneva Convention.|n",
                "|mYou clench the steering wheel for reasons unrelated to driving.|n",
                "|mThe cab smells like a crime scene. You crack the window.|n",
            ]
            trucker.msg(random.choice(msgs))

    def _check_rest_areas(self, trucker, miles_left, total_miles, hwy, from_key, dest_key):
        """Check if we're passing a rest area and announce it."""
        from world.cities import REST_AREAS
        miles_driven_on_leg = total_miles - miles_left

        for rest in REST_AREAS:
            # Match highway (strip I-40/I-17 etc)
            rest_hwy = rest["highway"]
            if rest_hwy not in hwy and hwy not in rest_hwy:
                continue
            # Match the segment (either direction)
            a, b = rest["between"]
            if not ((a == from_key and b == dest_key) or (b == from_key and a == dest_key)):
                continue
            # Check if we're at the rest area mile marker (within this tick's range)
            rest_mile = rest["mile"]
            # If driving from b->a, flip the mile marker
            if b == from_key:
                rest_mile = total_miles - rest_mile

            prev_miles = miles_driven_on_leg - (trucker.speed * (GAME_MINUTES_PER_TICK / 60.0))
            if prev_miles <= rest_mile <= miles_driven_on_leg:
                # Just passed it — announce
                trucker.db.nearby_rest_stop = rest["name"]
                trucker.msg(f"\n|y*** {rest['name']} — NEXT EXIT ***|n")
                trucker.msg("|wType |ystop|w to pull in for gas, food, and restrooms.|n")
                return

        # Clear if we've passed it
        trucker.db.nearby_rest_stop = None

    def _force_stop(self, trucker):
        """Force the trucker to pull over (DOT hours violation)."""
        trucker.msg("|rYou pull onto the shoulder and put it in park.|n")
        trucker.msg("|rType |wsleep|r to rest at the roadside.|n")

        # Move to rest stop room if available, otherwise stay on highway
        from typeclasses.rooms import get_or_create_rest_stop_room
        rest_room = get_or_create_rest_stop_room()
        rest_room.db.rest_stop_name = "Roadside Shoulder"
        rest_room.db.highway_name = trucker.db.driving_highway or ""
        trucker.move_to(rest_room, quiet=True)

        # Clear driving state but don't move to a city
        trucker.db.driving_to = None
        trucker.db.driving_from = None
        trucker.db.driving_miles_left = 0
        trucker.db.driving_highway = ""
        self.stop()

    def _fatigue_crash(self, trucker):
        """Trucker falls asleep at the wheel — serious consequences."""
        crash_type = random.choices(
            ["ditch", "guardrail", "jackknife"],
            weights=[40, 35, 25],
            k=1,
        )[0]

        if crash_type == "ditch":
            repair = random.randint(300, 800)
            trucker.msg("|r*** YOU FELL ASLEEP AT THE WHEEL! ***|n")
            trucker.msg("|rYour truck drifts off the road and into a drainage ditch.|n")
            trucker.msg(f"|rTow and repair: |w${repair}|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - repair)
            trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + random.randint(15, 30)
            trucker.msg("|rYou're shaken but back on the road after a long delay.|n")

        elif crash_type == "guardrail":
            repair = random.randint(500, 1200)
            trucker.msg("|r*** YOU FELL ASLEEP AT THE WHEEL! ***|n")
            trucker.msg("|rYou slam into the guardrail doing 60. Metal screams.|n")
            trucker.msg(f"|rRepair bill: |w${repair}|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - repair)
            # Damage a random cargo
            cargo = trucker.db.current_cargo or []
            if cargo:
                damaged = random.choice(cargo)
                damage_pct = random.randint(20, 50)
                old_pay = damaged.get("pay", 0)
                damaged["pay"] = int(old_pay * (1 - damage_pct / 100.0))
                trucker.db.current_cargo = cargo
                trucker.msg(f"|rYour |w{damaged.get('cargo_name', 'cargo')}|r was damaged! Payout reduced {damage_pct}%.|n")
            trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + random.randint(20, 40)

        elif crash_type == "jackknife":
            repair = random.randint(800, 2000)
            trucker.msg("|r*** YOU FELL ASLEEP AND JACKKNIFED! ***|n")
            trucker.msg("|rYour trailer swings out and you skid across three lanes.|n")
            trucker.msg(f"|rMassive repair bill: |w${repair}|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - repair)
            # Lose a random cargo entirely
            cargo = trucker.db.current_cargo or []
            if cargo:
                lost = random.choice(cargo)
                cargo.remove(lost)
                trucker.db.current_cargo = cargo
                trucker.msg(f"|rYour |w{lost.get('cargo_name', 'cargo')}|r spilled across the highway. Contract lost.|n")
            trucker.db.reputation = max(0, (trucker.db.reputation or 50) - 5)
            trucker.msg("|rReputation -5. That made the evening news.|n")
            # Force stop — too damaged to continue
            trucker.msg("|rYour rig needs roadside service. You're stuck here until repairs finish.|n")
            self._force_stop(trucker)

    def _weather_tick(self, trucker):
        """Dynamic weather changes based on region and season."""
        from world.cities import CITIES
        dest_key = trucker.db.driving_to or ""
        from_key = trucker.db.driving_from or ""
        region = CITIES.get(dest_key, {}).get("region", "") or CITIES.get(from_key, {}).get("region", "midwest")
        current = trucker.db.current_weather or "clear"

        # Region-appropriate weather weights: (clear, rain, snow, fog, storm)
        region_weather = {
            "northwest":    [25, 40, 10, 20, 5],
            "pacific":      [35, 30, 5, 25, 5],
            "mountain":     [30, 15, 30, 10, 15],
            "plains":       [30, 20, 15, 10, 25],
            "midwest":      [35, 25, 20, 10, 10],
            "northeast":    [30, 30, 20, 15, 5],
            "southeast":    [40, 35, 5, 15, 5],
            "south_central": [45, 25, 5, 10, 15],
        }
        weights = region_weather.get(region, [35, 25, 15, 15, 10])
        options = ["clear", "rain", "snow", "fog", "storm"]
        new_weather = random.choices(options, weights=weights, k=1)[0]

        if new_weather == current:
            return

        trucker.db.current_weather = new_weather
        weather_msgs = {
            "clear": "|wThe skies clear up. Good driving weather ahead.|n",
            "rain": "|b Rain starts falling. You flip on the wipers.|n",
            "snow": "|W Snow begins to cover the road. Careful now.|n",
            "fog": "|x Dense fog rolls in. Visibility drops to near zero.|n",
            "storm": "|r*** STORM WARNING ***|n|rHeavy winds and rain batter your rig. Slow down!|n",
        }
        trucker.msg(weather_msgs.get(new_weather, ""))

        # Storm can cause extra events
        if new_weather == "storm" and random.random() < 0.20:
            events = [
                ("|rA gust of wind pushes your trailer sideways! You wrestle the wheel.|n", 3),
                ("|rDebris on the road! You swerve to avoid a fallen branch.|n", 5),
                ("|rLightning strikes a transformer ahead. The road goes dark.|n", 0),
                ("|rHail pelts your windshield like a drum solo from hell.|n", 2),
            ]
            msg, extra_miles = random.choice(events)
            trucker.msg(msg)
            if extra_miles:
                trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + extra_miles

    def _weigh_station(self, trucker):
        """Weigh station encounter — more detailed than a simple weight check."""
        cargo = trucker.db.current_cargo or []
        weight = trucker.current_cargo_weight
        capacity = trucker.cargo_capacity

        trucker.msg("")
        trucker.msg("|y*** WEIGH STATION — ALL TRUCKS MUST STOP ***|n")

        # Sometimes they wave you through (30% if clean record)
        violations = trucker.db.weigh_violations or 0
        if violations == 0 and random.random() < 0.30:
            trucker.msg("|gThe officer waves you through. \"Keep it moving, driver.\"|n")
            return

        trucker.msg("|yYou pull onto the scale. The numbers tick up...|n")
        trucker.msg(f"|wTotal weight:|n {weight:,} lbs  |wCapacity:|n {capacity:,} lbs")

        if weight > capacity:
            overage = weight - capacity
            overage_pct = (overage / capacity) * 100
            fine = int(overage_pct * 15) + random.randint(100, 300)
            trucker.msg(f"|r*** OVERWEIGHT by {overage:,} lbs ({overage_pct:.0f}% over)! ***|n")
            trucker.msg(f"|rFine: |w${fine:,}|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - fine)
            trucker.db.weigh_violations = violations + 1

            # Repeat offenders get worse treatment
            if violations >= 2:
                trucker.msg(f"|r\"This is your {violations + 1}th violation. I'm flagging your CDL.\"|n")
                trucker.db.reputation = max(0, (trucker.db.reputation or 50) - 5)
                trucker.msg("|rReputation -5.|n")
            elif violations >= 1:
                trucker.msg(f"|y\"I've seen your name before, driver. Watch it.\"|n")

            trucker.msg(f"|rMoney remaining: |w${trucker.db.money:,}|n")
        else:
            # Within limits but officer might still hassle you
            if random.random() < 0.15:
                trucker.msg("|y\"Weight's fine, but let me see your paperwork...\"|n")
                trucker.msg("|yA 5-minute delay while they check your logbook.|n")
                trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + 2
            else:
                trucker.msg(f"|g\"You're good. {weight:,} lbs, well within limits.\"|n")
                trucker.msg("|gThe officer waves you back on the road.|n")

    def _random_event(self, trucker):
        """Trigger a random highway event (flat tire, speed trap, DOT, road hazard)."""
        hours = trucker.db.hours_driving or 0

        # DOT inspection — higher chance if over 12 hours
        if hours >= 12 and random.random() < 0.15:
            self._dot_inspection(trucker)
            return

        event = random.choices(
            ["flat_tire", "road_hazard", "wildlife", "road_construction", "nothing"],
            weights=[12, 8, 8, 10, 62],
            k=1,
        )[0]

        if event == "flat_tire":
            delay_miles = random.randint(5, 15)
            cost = random.randint(50, 150)
            trucker.msg(f"|r*** FLAT TIRE! ***|n")
            trucker.msg(f"|rRoadside repair: ${cost}. Lost {delay_miles} miles of progress.|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - cost)
            trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + delay_miles

        elif event == "road_hazard":
            hazards = [
                ("A blown tire tread lies across your lane! You swerve hard.", 2, 0),
                ("A mattress fell off someone's truck. You dodge it at the last second.", 1, 0),
                ("Pothole! Your rig slams into a crater. That'll cost you.", 3, random.randint(30, 80)),
                ("An overturned car blocks the right lane. Traffic slows to a crawl.", 8, 0),
                ("A ladder in the road! You brake and weave around it.", 1, 0),
            ]
            msg, delay, cost = random.choice(hazards)
            trucker.msg(f"|y*** ROAD HAZARD ***|n")
            trucker.msg(f"|y{msg}|n")
            if delay:
                trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + delay
            if cost:
                trucker.db.money = max(0, (trucker.db.money or 0) - cost)
                trucker.msg(f"|rRepair cost: ${cost}|n")

        elif event == "wildlife":
            animals = [
                ("A deer leaps across the highway! You stand on the brakes.", 2),
                ("An armadillo waddles across the road. You straddle it.", 0),
                ("A family of turkeys blocks the right lane. You honk and wait.", 3),
                ("Cattle on the highway! A rancher's fence must be down.", 5),
                ("A coyote trots alongside your rig, then disappears into the brush.", 0),
            ]
            msg, delay = random.choice(animals)
            trucker.msg(f"|y{msg}|n")
            if delay:
                trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + delay

        elif event == "road_construction":
            delay = random.randint(5, 15)
            msgs = [
                f"Orange cones funnel you into a single lane. Construction zone. +{delay} miles delay.",
                f"A pilot car leads you through a paving zone at 25 mph. Lost {delay} miles of progress.",
                f"Bridge construction ahead. One lane alternating traffic. {delay} miles of crawling.",
            ]
            trucker.msg(f"|y*** CONSTRUCTION ZONE ***|n")
            trucker.msg(f"|y{random.choice(msgs)}|n")
            trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + delay

    def _cop_encounter(self, trucker):
        """
        Cop encounter — various reasons for getting pulled over.
        Radar detector gives advance warning and chance to avoid.
        """
        speed = trucker.speed
        max_speed = trucker.max_speed
        fatigue = trucker.db.fatigue or 0
        highway = trucker.db.driving_highway or "the highway"

        # Determine reason for the encounter
        # Weight reasons by circumstances
        reasons = []
        if speed > 65:
            over = speed - 65
            # More likely at higher speeds
            reasons.append(("speeding", 30 + over))
        if fatigue >= 70:
            reasons.append(("swerving", 20 + (fatigue - 70)))
        if trucker.db.soiled:
            reasons.append(("erratic", 15))
        # Random patrol — always possible
        reasons.append(("patrol", 20))

        if not reasons:
            return

        # Pick a reason (weighted)
        reason_names, reason_weights = zip(*reasons)
        reason = random.choices(reason_names, weights=reason_weights, k=1)[0]

        # Radar detector check — detect the cop before they see you
        if trucker.has_radar:
            detection = trucker.radar_detection
            if random.random() < detection:
                # Detected! Warn the driver
                detector_msgs = [
                    "|y*** BEEP BEEP BEEP — Radar detector alert! ***|n",
                    "|y*** RADAR ALERT — Ka band detected ahead! ***|n",
                    "|y*** WARNING — Police radar on {highway}! ***|n",
                ]
                trucker.msg(random.choice(detector_msgs).format(highway=highway))

                if speed > 65:
                    trucker.msg(f"|yYou ease off the gas from {speed} mph. Good save.|n")
                else:
                    trucker.msg("|yYou spot the cruiser ahead and keep it cool. He doesn't move.|n")

                if trucker.has_cb:
                    trucker.msg(f"|y[CB] \"Smokey on {highway}, watch your speed.\"|n")
                return  # Avoided!

        # No radar or didn't detect — encounter happens
        cop_names = [
            "A state trooper", "A highway patrol officer", "A county sheriff",
            "A speed enforcement unit", "An unmarked cruiser",
        ]
        cop = random.choice(cop_names)

        trucker.msg("")

        if reason == "speeding":
            over = speed - 65
            trucker.msg(f"|r*** {cop} lights you up on {highway}! ***|n")
            trucker.msg(f"|r\"You were doing {speed} in a 65 zone.\"|n")

            # Fine scales with how far over
            if over <= 10:
                fine = random.randint(75, 150)
                trucker.msg(f"|r\"I'm writing you a ticket. ${fine}.\"|n")
            elif over <= 20:
                fine = random.randint(200, 400)
                trucker.msg(f"|r\"{over} over? That's reckless. ${fine} fine.\"|n")
                trucker.db.reputation = max(0, (trucker.db.reputation or 50) - 2)
                trucker.msg("|rReputation -2.|n")
            else:
                fine = random.randint(500, 1000)
                trucker.msg(f"|r\"{speed} mph in a big rig?! You could've killed someone.\"|n")
                trucker.msg(f"|rMajor speeding violation: ${fine}|n")
                trucker.db.reputation = max(0, (trucker.db.reputation or 50) - 5)
                trucker.msg("|rReputation -5.|n")

            trucker.db.money = max(0, (trucker.db.money or 0) - fine)
            trucker.msg(f"|rMoney remaining: |w${trucker.db.money:,}|n")

            # CB warning to others
            if trucker.has_cb:
                trucker.msg(f"|y[CB] \"Got a bear bite on {highway}. Watch it, drivers.\"|n")

        elif reason == "swerving":
            trucker.msg(f"|r*** {cop} pulls you over on {highway}! ***|n")
            trucker.msg(f"|r\"I saw you drifting across the lane back there.\"|n")

            if fatigue >= 90:
                # Officer can tell you're exhausted
                fine = random.randint(300, 800)
                trucker.msg(f"|r\"You can barely keep your eyes open. You're a danger out here.\"|n")
                trucker.msg(f"|rFatigued driving citation: ${fine}|n")
                trucker.db.money = max(0, (trucker.db.money or 0) - fine)
                trucker.db.reputation = max(0, (trucker.db.reputation or 50) - 3)
                trucker.msg("|rReputation -3.|n")
                # 50% chance of forced rest
                if random.random() < 0.50:
                    trucker.msg(f"|r\"I'm shutting you down, driver. Park it and get some rest.\"|n")
                    trucker.db.mandatory_rest = True
                    self._force_stop(trucker)
            elif fatigue >= 80:
                # Warning
                trucker.msg(f"|y\"You look tired, driver. Maybe pull over and get some coffee.\"|n")
                trucker.msg("|yThe officer lets you go with a warning.|n")
            else:
                trucker.msg(f"|y\"Must have been the wind. Be careful out there.\"|n")

            trucker.msg(f"|rMoney remaining: |w${trucker.db.money:,}|n")

        elif reason == "erratic":
            trucker.msg(f"|r*** {cop} pulls alongside and waves you over! ***|n")
            trucker.msg(f"|r\"Sir, is everything alright? You're driving erratically.\"|n")
            # The soiled trucker gets extra scrutiny
            fine = random.randint(100, 250)
            trucker.msg(f"|r\"I'm gonna need you to step out of the — oh. Oh god.\"|n")
            trucker.msg(f"|rPublic health citation: ${fine}|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - fine)
            trucker.msg(f"|rMoney remaining: |w${trucker.db.money:,}|n")

        elif reason == "patrol":
            trucker.msg(f"|y*** {cop} pulls you over for a routine check on {highway}. ***|n")

            # Various patrol outcomes
            outcome = random.choices(
                ["clean", "logbook", "equipment", "warrant_check"],
                weights=[45, 20, 20, 15],
                k=1,
            )[0]

            if outcome == "clean":
                msgs = [
                    "\"Everything looks good. Drive safe out there.\"",
                    "\"Just a random check. You're free to go.\"",
                    "\"All clear, driver. Keep the shiny side up.\"",
                ]
                trucker.msg(f"|g{random.choice(msgs)}|n")
            elif outcome == "logbook":
                hours = trucker.db.hours_driving or 0
                if hours >= 12:
                    fine = random.randint(200, 600)
                    trucker.msg(f"|r\"Let me see your logbook... {hours:.0f} hours? That's a violation.\"|n")
                    trucker.msg(f"|rHours-of-service fine: ${fine}|n")
                    trucker.db.money = max(0, (trucker.db.money or 0) - fine)
                    trucker.msg(f"|rMoney remaining: |w${trucker.db.money:,}|n")
                else:
                    trucker.msg(f"|g\"Logbook looks good. {hours:.0f} hours — plenty of time.\"|n")
            elif outcome == "equipment":
                if random.random() < 0.3:
                    fine = random.randint(50, 200)
                    issues = [
                        "busted tail light", "cracked mirror", "worn tire tread",
                        "loose mud flap", "faded DOT number",
                    ]
                    issue = random.choice(issues)
                    trucker.msg(f"|r\"You've got a {issue}. I'm writing you up.\"|n")
                    trucker.msg(f"|rEquipment citation: ${fine}|n")
                    trucker.db.money = max(0, (trucker.db.money or 0) - fine)
                    trucker.msg(f"|rMoney remaining: |w${trucker.db.money:,}|n")
                else:
                    trucker.msg(f"|g\"Equipment checks out. On your way.\"|n")
            elif outcome == "warrant_check":
                trucker.msg(f"|y\"Just running your CDL... all clear. Have a good one.\"|n")
                # Small delay
                trucker.db.driving_miles_left = (trucker.db.driving_miles_left or 0) + 2

    def _dot_inspection(self, trucker):
        """DOT officer pulls you over to check your logbook and hours."""
        hours = trucker.db.hours_driving or 0
        trucker.msg("|y*** DOT INSPECTION ***|n")
        trucker.msg("|yA DOT officer waves you over to the shoulder.|n")
        trucker.msg(f"|y\"Let me see your logbook, driver.\"|n")

        violations = []

        # Hours of service violation
        if hours >= 14:
            fine = random.randint(1000, 2500)
            trucker.msg(f"|r\"You've been driving {hours:.0f} hours?! That's a federal violation.\"|n")
            trucker.msg(f"|rHOS violation fine: |w${fine}|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - fine)
            trucker.db.reputation = max(0, (trucker.db.reputation or 50) - 5)
            violations.append("HOS")
        elif hours >= 12:
            fine = random.randint(300, 800)
            trucker.msg(f"|y\"You're pushing it at {hours:.0f} hours. I'm writing you up.\"|n")
            trucker.msg(f"|rLogbook warning fine: |w${fine}|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - fine)
            violations.append("logbook")

        # Check for weigh violations on record
        if (trucker.db.weigh_violations or 0) >= 2:
            extra_fine = random.randint(200, 500)
            trucker.msg(f"|r\"I see you have prior weigh station violations too.\"|n")
            trucker.msg(f"|rAdditional fine: |w${extra_fine}|n")
            trucker.db.money = max(0, (trucker.db.money or 0) - extra_fine)

        if not violations:
            trucker.msg("|g\"Everything checks out. Drive safe out there.\"|n")
        else:
            trucker.msg(f"|rMoney remaining: |w${trucker.db.money:,}|n")
            # Severe violation = forced rest
            if hours >= 14:
                trucker.msg("|r\"I'm shutting you down right here. You're not driving another mile.\"|n")
                trucker.db.mandatory_rest = True
                self._force_stop(trucker)

    def _arrive(self, trucker):
        """Handle arrival at destination city."""
        dest_key = trucker.db.driving_to
        from world.cities import CITIES
        dest_data = CITIES.get(dest_key, {})
        dest_name = dest_data.get("name", dest_key)

        trucker.msg(f"\n|g*** ARRIVED: {dest_name}, {dest_data.get('state', '')} ***|n")
        trucker.db.current_weather = "clear"
        trucker.db.last_city = dest_key

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
        arrived_city = dest_key
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

        # Stop this driving script instance
        self.stop()

        # GPS auto-continue: if there are remaining cities in the GPS route, drive to the next one
        gps_route = trucker.db.gps_route or []
        if gps_route:
            next_city = gps_route[0]
            remaining_after = list(gps_route[1:])

            # Check if mandatory rest triggered during this leg
            if trucker.db.mandatory_rest:
                trucker.msg("|y[GPS] Auto-routing paused -- DOT mandatory rest required.|n")
                trucker.db.gps_route = []
                return

            # Find the direct connection from arrived city to next GPS waypoint
            from commands.driving import (
                get_direct_connection, apply_gps_unreliability,
                start_driving_leg, dijkstra_path,
            )
            conn = get_direct_connection(arrived_city, next_city)
            if not conn:
                # GPS route is stale (e.g. wrong-turn reroute left a gap) — recalculate
                final_dest = gps_route[-1]
                result = dijkstra_path(arrived_city, final_dest)
                if result:
                    _, new_path = result
                    new_legs = new_path[1:]
                    if new_legs:
                        next_city = new_legs[0][0]
                        conn = (new_legs[0][1], new_legs[0][2])
                        remaining_after = [c for c, _, _ in new_legs[1:]]
                    else:
                        trucker.msg("|y[GPS] You've arrived at your final destination.|n")
                        trucker.db.gps_route = []
                        return
                else:
                    trucker.msg("|r[GPS] Cannot find a route to continue. Auto-routing cancelled.|n")
                    trucker.db.gps_route = []
                    return

            dist, hwy = conn

            # Apply GPS unreliability for this leg
            actual_dest, actual_dist, actual_hwy, detour_msg = apply_gps_unreliability(
                trucker, next_city, dist, hwy, arrived_city
            )
            if detour_msg:
                trucker.msg(detour_msg)
                # If GPS routed through wrong city, recalculate remaining
                if actual_dest != next_city:
                    final_dest = gps_route[-1]
                    new_result = dijkstra_path(actual_dest, final_dest)
                    if new_result:
                        _, new_path = new_result
                        remaining_after = [c for c, _, _ in new_path[1:]]
                    else:
                        remaining_after = []

            # Show how many stops remain
            if remaining_after:
                trucker.msg(f"|c[GPS] {len(remaining_after)} more stop(s) after this.|n")

            start_driving_leg(
                trucker, arrived_city, actual_dest, actual_dist, actual_hwy,
                gps_route=remaining_after, gps_leg=True,
            )


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


# --- NPC Trucker handles for board messages ---
NPC_HANDLES = [
    "Big Jim", "Roadhog", "Diesel Dave", "Cornbread", "Hammerdown",
    "Sidewinder", "Mudflap", "Biscuit", "Chrome Charlie", "Rubberband",
    "Smokestack", "Possum", "Gearjammer", "Nighthawk", "Cottonmouth",
    "Tailgate", "Ironhide", "Buster", "Dusty", "Ratchet",
    "Blackjack", "Skidmark", "T-Bone", "Hoss", "Copperhead",
    "Pigpen", "Rooster", "Slingshot", "Bulldog", "Breaker One-Nine",
    "Lady Trucker", "Mama Bear", "Butterfly", "Silver Fox", "Radar Love",
]

# Message templates. {city} = current city name, {highway} = nearby highway,
# {other_city} = random connected city, {handle} = random NPC or real player handle
NPC_BOARD_MESSAGES = [
    # Smokey / bears (cops)
    "Bears thick on {highway} east of {city} tonight. Keep it legal.",
    "Smokey's running radar on {highway} near mile marker {mile}. Heads up.",
    "Full-grown bear in the median on {highway} westbound. 10-4.",
    "County mountie parked under the overpass on {highway}. Watch your speed.",
    "Bear in the air on {highway}! Chopper clocking speeds.",
    "No bears between {city} and {other_city} as of an hour ago.",

    # Road conditions
    "Construction on {highway} about {mile} miles out of {city}. Down to one lane.",
    "Watch for debris on {highway} southbound. Blown tire in the hammer lane.",
    "Road's clear all the way from {city} to {other_city}. Hammer down!",
    "Black ice on {highway} near {other_city}. Saw two rigs in the ditch.",
    "Fog rolling in thick on {highway}. Can barely see the hood.",
    "Pothole the size of a bathtub on {highway} eastbound. Broke my coffee mug.",
    "Bridge out on the back way to {other_city}. Stick to {highway}.",

    # CB chatter / general
    "10-4 good buddy.",
    "Breaker breaker one-nine, anyone got their ears on in {city}?",
    "Hey {handle}, you got your ears on?",
    "What's your 20, {handle}?",
    "Just pulled into {city}. This truck stop coffee could strip paint.",
    "Heading out to {other_city} in the morning. Loaded heavy.",
    "Anyone headed toward {other_city}? Could use a convoy.",
    "Been driving 14 hours. These bunks in {city} aren't bad.",
    "Just dropped a load in {city}. Time to find something heading back east.",
    "Night driving on {highway} is something else. Stars for miles.",
    "If you're in {city}, the diner on the south side has good pie.",
    "Put the hammer down, boys.",

    # Fuel / economy
    "Diesel's cheap in {city} right now. Fill up here.",
    "Fuel prices on {highway} are robbery. Fill up before you leave {city}.",
    "Heard they're hiring out of {other_city}. Good contracts.",
    "Rates out of {city} have been solid this week.",

    # Trucker life
    "Third week on the road. Starting to forget what my couch looks like.",
    "My dispatcher doesn't know the difference between a reefer and a flatbed.",
    "Lot lizard knocked on my door at 3 AM in {city}. That's a negative, ghost rider.",
    "Passed the weigh station outside {other_city}. They're checking everything today.",
    "New tires on the rig. She rides like a dream now.",
    "Somebody tell {handle} they left their load strap on the fuel island.",
    "Just hit 500,000 miles on this old girl. She ain't done yet.",
    "The shower line at this truck stop is 45 minutes deep.",
    "Who keeps writing on the bathroom walls in {city}? We know it's you, {handle}.",
    "Wife says I gotta be home by Friday. I'm in {city}. Gonna be close.",
    "Some four-wheeler cut me off on {highway}. Nearly jackknifed.",
    "Keep the shiny side up and the rubber side down.",
    "Catch you on the flip side, {city}.",
    "This is {handle} signing off. Stay safe out there, drivers.",
    "Somebody left a whole pallet of energy drinks at the {city} truck stop. Finders keepers.",
    "Don't eat the chili dog at the rest stop on {highway}. Trust me.",
    "That sunrise coming into {city} this morning was worth the overnight haul.",
]


class BoardNPCScript(DefaultScript):
    """
    Global script: posts random NPC trucker messages to city boards.
    Ticks every 3 minutes. ~40% chance per tick to post to a random city.
    """

    def at_script_creation(self):
        self.key = "board_npc"
        self.interval = 180  # 3 minutes
        self.persistent = True

    def at_repeat(self):
        """Maybe post an NPC message to a random city board."""
        if random.random() > 0.40:
            return

        from evennia.utils.search import search_tag
        from world.cities import CITIES, HIGHWAYS

        city_keys = list(CITIES.keys())
        city_key = random.choice(city_keys)

        rooms = search_tag(city_key, category="city")
        if not rooms:
            return
        room = rooms[0]

        city_data = CITIES.get(city_key, {})
        city_name = city_data.get("name", city_key)

        # Find highways connected to this city
        connected = []
        for a, b, dist, hwy in HIGHWAYS:
            if a == city_key:
                connected.append((b, dist, hwy))
            elif b == city_key:
                connected.append((a, dist, hwy))

        highway = random.choice(connected)[2] if connected else "I-40"
        other_city_key = random.choice(connected)[0] if connected else random.choice(city_keys)
        other_city_name = CITIES.get(other_city_key, {}).get("name", other_city_key)

        # Pick a handle — sometimes use a real player name
        handle = random.choice(NPC_HANDLES)
        try:
            from typeclasses.characters import Trucker
            real_truckers = [
                t.db.handle for t in Trucker.objects.all()
                if t.db.handle and t.db.chargen_complete
            ]
            if real_truckers and random.random() < 0.3:
                handle = random.choice(real_truckers)
        except Exception:
            pass

        # Build the message
        import time as _time
        template = random.choice(NPC_BOARD_MESSAGES)
        mile = random.randint(5, 180)
        text = template.format(
            city=city_name,
            highway=highway,
            other_city=other_city_name,
            handle=handle,
            mile=mile,
        )

        npc_author = random.choice(NPC_HANDLES)

        board = room.db.message_board or []
        board.append({
            "author": npc_author,
            "text": text,
            "time": _time.time(),
        })
        # Keep boards from growing too large
        if len(board) > 20:
            board = board[-20:]
        room.db.message_board = board
