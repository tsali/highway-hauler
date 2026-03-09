"""
Highway Hauler — Random encounter commands and events.

Lot Lizard encounters (truck stops):
  - Random chance when arriving at or idling at a city
  - Accepting services risks robbery, STD (medical bills), or nothing
  - Declining is always safe

Highway Gang encounters (desert stretches - future):
  - Fast & Furious style cargo thieves on long desert highways
  - Fight or flee mechanic with cargo/money stakes
"""

import random
import time
from evennia.commands.command import Command


# Desert highway segments where gang encounters can happen
DESERT_HIGHWAYS = [
    "I-10",   # CA/AZ
    "I-15",   # CA/NV
    "I-40",   # AZ/NM
    "I-8",    # CA/AZ
]

# Cities in desert regions
DESERT_CITIES = [
    "las_vegas", "phoenix", "tucson", "albuquerque", "el_paso",
    "los_angeles", "san_diego", "salt_lake",
]


def trigger_lot_lizard(trucker):
    """
    Called when a trucker arrives at or idles at a truck stop.
    5% chance per arrival at tier 2+ cities.
    """
    if trucker.is_driving:
        return

    city_tier = 1
    if trucker.location and hasattr(trucker.location, 'db'):
        city_data = trucker.location.db.city_data or {}
        city_tier = city_data.get("tier", 1)

    if city_tier < 2:
        return

    # Cooldown: only once per 10 minutes real time
    last = trucker.db.last_lot_lizard or 0
    if time.time() - last < 600:
        return

    if random.random() > 0.05:
        return

    trucker.db.last_lot_lizard = time.time()

    names = [
        "Crystal", "Destiny", "Angel", "Tiffany", "Brandy",
        "Candy", "Diamond", "Jasmine", "Raven", "Starla",
    ]
    name = random.choice(names)

    trucker.msg("")
    trucker.msg(f"|m*** A figure approaches your truck ***|n")
    trucker.msg(f"|mA woman who calls herself {name} knocks on your cab window.|n")
    trucker.msg(f"|m\"Hey driver, looking for some company tonight?\"|n")
    trucker.msg("")
    trucker.msg(f"|wType |ysure|w to accept or |ynah|w to decline.|n")

    trucker.ndb.lot_lizard_active = True
    trucker.ndb.lot_lizard_name = name


class CmdLotLizardResponse(Command):
    """
    Respond to a lot lizard encounter.
    Only active when lot_lizard_active is set.
    """

    key = "sure"
    aliases = ["nah", "no", "yes", "decline", "accept"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if not caller.ndb.lot_lizard_active:
            return

        caller.ndb.lot_lizard_active = False
        name = caller.ndb.lot_lizard_name or "the stranger"
        response = self.cmdstring.lower()

        if response in ("nah", "no", "decline"):
            caller.msg(f"|wYou wave {name} off. \"Not tonight.\"|n")
            caller.msg(f"|w{name} shrugs and moves on to the next truck.|n")
            return

        # Player accepted — determine outcome
        cost = random.randint(20, 80)
        if (caller.db.money or 0) < cost:
            caller.msg(f"|m{name} takes one look at your wallet and walks away.|n")
            caller.msg(f"|m\"Come back when you got some real money, sugar.\"|n")
            return

        caller.db.money = (caller.db.money or 0) - cost
        caller.msg(f"|m{name} climbs into your cab. Cost: |w${cost}|n")

        # Roll for consequences
        outcome = random.choices(
            ["nothing", "robbed", "std", "good_time"],
            weights=[30, 25, 20, 25],
            k=1,
        )[0]

        if outcome == "nothing":
            caller.msg(f"|mA forgettable evening. {name} leaves before dawn.|n")
            caller.msg(f"|wYou wake up with your wallet ${cost} lighter but otherwise fine.|n")

        elif outcome == "robbed":
            stolen = random.randint(100, 500)
            actual_stolen = min(stolen, caller.db.money or 0)
            caller.db.money = max(0, (caller.db.money or 0) - actual_stolen)
            caller.msg(f"|r*** You wake up alone. ***|n")
            caller.msg(f"|r{name} is gone — and so is ${actual_stolen} from your wallet.|n")
            if random.random() < 0.3:
                caller.msg(f"|rYour CB radio is missing too!|n")
                if (caller.db.cb_level or 0) > 0:
                    caller.db.cb_level = 0
            caller.msg(f"|rMoney remaining: |w${caller.db.money:,}|n")

        elif outcome == "std":
            medical_cost = random.randint(200, 600)
            caller.msg(f"|r*** A few days later you're not feeling so great... ***|n")
            caller.msg(f"|rClinic visit: |w${medical_cost}|n")
            if (caller.db.money or 0) >= medical_cost:
                caller.db.money = (caller.db.money or 0) - medical_cost
                caller.msg(f"|yTreated and back on the road. Lesson learned.|n")
            else:
                # Can't afford treatment — reputation hit
                caller.db.money = 0
                caller.db.reputation = max(0, (caller.db.reputation or 50) - 10)
                caller.msg(f"|rCan't afford treatment. Word gets around. Reputation -10.|n")
            caller.msg(f"|rMoney remaining: |w${caller.db.money:,}|n")

        elif outcome == "good_time":
            caller.msg(f"|mA surprisingly pleasant evening.|n")
            caller.msg(f"|m{name} gives you a tip about a good haul out of town.|n")
            # Small bonus — next contract pays more (store as temp modifier)
            caller.db.contract_bonus = 1.2
            caller.msg(f"|g+20% bonus on your next contract!|n")


def trigger_highway_gang(trucker, highway):
    """
    Check for highway gang encounter on desert stretches.
    Called from DrivingScript during travel on desert highways.
    2% chance per tick on qualifying highways.
    """
    if highway not in DESERT_HIGHWAYS:
        return False

    if random.random() > 0.02:
        return False

    # Don't trigger if no cargo
    cargo = trucker.db.current_cargo or []
    if not cargo:
        return False

    trucker.msg("")
    trucker.msg(f"|r*** VEHICLES APPROACHING FAST ***|n")
    trucker.msg(f"|rA convoy of blacked-out cars is racing up behind you on {highway}!|n")
    trucker.msg(f"|rThey're trying to box you in!|n")
    trucker.msg("")
    trucker.msg(f"|wType |yfloor it|w to try to outrun them or |yfight|w to stand your ground.|n")

    trucker.ndb.gang_encounter_active = True
    return True


class CmdGangResponse(Command):
    """
    Respond to a highway gang encounter.
    """

    key = "floor it"
    aliases = ["fight", "run", "flee"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if not caller.ndb.gang_encounter_active:
            return

        caller.ndb.gang_encounter_active = False
        response = self.cmdstring.lower()

        if response in ("floor it", "run", "flee"):
            # Escape chance based on engine level
            engine_level = caller.db.engine_level or 0
            escape_chance = 0.3 + (engine_level * 0.15)  # 30%-90%

            if random.random() < escape_chance:
                caller.msg(f"|g*** You floor the gas and pull away! ***|n")
                caller.msg(f"|gYour {caller.speed} mph rig leaves them in the dust.|n")
                # Extra fuel used
                caller.db.fuel = max(0, (caller.db.fuel or 0) - 5)
                caller.msg(f"|yBurned extra fuel escaping.|n")
            else:
                caller.msg(f"|r*** They catch up! ***|n")
                self._lose_cargo(caller)

        elif response == "fight":
            # Fight outcome — reputation affects success
            rep = caller.db.reputation or 50
            fight_chance = 0.2 + (rep / 200.0)  # 20%-70%

            if random.random() < fight_chance:
                reward = random.randint(200, 800)
                caller.msg(f"|g*** You fought them off! ***|n")
                caller.msg(f"|gYou find ${reward} they dropped in their retreat.|n")
                caller.db.money = (caller.db.money or 0) + reward
                caller.db.reputation = min(100, (caller.db.reputation or 50) + 5)
                caller.msg(f"|gReputation +5. Word spreads you're not to be messed with.|n")
            else:
                caller.msg(f"|r*** Outnumbered and outgunned. ***|n")
                self._lose_cargo(caller)
                # Extra damage for fighting and losing
                medical = random.randint(100, 300)
                caller.db.money = max(0, (caller.db.money or 0) - medical)
                caller.msg(f"|rMedical bills: ${medical}|n")

    def _lose_cargo(self, caller):
        """Lose some cargo to the gang."""
        cargo = caller.db.current_cargo or []
        if not cargo:
            # Just steal money
            stolen = random.randint(200, 600)
            actual = min(stolen, caller.db.money or 0)
            caller.db.money = max(0, (caller.db.money or 0) - actual)
            caller.msg(f"|rThey grab ${actual} from your cab and speed off.|n")
            return

        # Lose 1 random cargo
        lost = random.choice(cargo)
        cargo.remove(lost)
        caller.db.current_cargo = cargo
        caller.msg(f"|rThey hijacked your |w{lost.get('cargo_name', 'cargo')}|r!|n")
        caller.msg(f"|rLost: {lost.get('cargo_name', '???')} worth ${lost.get('pay', 0):,}|n")
        caller.db.reputation = max(0, (caller.db.reputation or 50) - 3)
