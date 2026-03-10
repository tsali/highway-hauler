"""
Highway Hauler — Trucker needs commands: eat, restroom, sleep.

Handles hunger, bladder, fatigue, stomach issues, lactose intolerance,
and the diner menu system with numbered choices.
"""

import random
from evennia.commands.command import Command
from evennia import syscmdkeys


# Diner menu items: key -> {name, price, hunger_fill, fatigue_mod, risk, risk_tums, desc}
DINER_MENU = {
    1: {
        "name": "Cheeseburger & Fries",
        "price": 12,
        "hunger_fill": 40,
        "fatigue_mod": 0,
        "risk": 0.0,
        "risk_tums": 0.0,
        "lactose_risk": 0.0,
        "desc": "A solid quarter-pounder with extra pickles.",
    },
    2: {
        "name": "Chili Dog",
        "price": 8,
        "hunger_fill": 30,
        "fatigue_mod": 0,
        "risk": 0.35,
        "risk_tums": 0.10,
        "lactose_risk": 0.0,
        "desc": "Three-alarm chili on a foot-long. Brave choice.",
    },
    3: {
        "name": "Chicken Fried Steak",
        "price": 15,
        "hunger_fill": 50,
        "fatigue_mod": 0,
        "risk": 0.15,
        "risk_tums": 0.05,
        "lactose_risk": 0.0,
        "desc": "Country-fried and smothered in white gravy. God bless America.",
    },
    4: {
        "name": "Trucker's Breakfast",
        "price": 10,
        "hunger_fill": 60,
        "fatigue_mod": 0,
        "risk": 0.0,
        "risk_tums": 0.0,
        "lactose_risk": 0.0,
        "desc": "Three eggs, bacon, sausage, hash browns, toast. The works.",
    },
    5: {
        "name": "Milkshake",
        "price": 6,
        "hunger_fill": 15,
        "fatigue_mod": 0,
        "risk": 0.0,
        "risk_tums": 0.0,
        "lactose_risk": 0.65,
        "desc": "Thick, cold, and chocolatey. What could go wrong?",
    },
    6: {
        "name": "Coffee (just coffee)",
        "price": 3,
        "hunger_fill": 5,
        "fatigue_mod": -20,
        "risk": 0.0,
        "risk_tums": 0.0,
        "lactose_risk": 0.0,
        "desc": "Black as midnight on a moonless night.",
    },
    7: {
        "name": "Salad (yeah right)",
        "price": 9,
        "hunger_fill": 25,
        "fatigue_mod": 0,
        "risk": 0.0,
        "risk_tums": 0.0,
        "lactose_risk": 0.0,
        "desc": "The waitress gives you a look. A trucker ordering salad.",
    },
    8: {
        "name": "Tums (pack of 3)",
        "price": 5,
        "hunger_fill": 0,
        "fatigue_mod": 0,
        "risk": 0.0,
        "risk_tums": 0.0,
        "lactose_risk": 0.0,
        "desc": "For when you know you're about to make a bad decision.",
    },
}


class CmdEat(Command):
    """
    Visit the diner to eat. Reduces hunger.

    Usage:
        eat
        diner
        food

    Only available when stopped at a city or rest area.
    """

    key = "eat"
    aliases = ["diner", "food", "restaurant"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if caller.is_driving:
            caller.msg("|rYou can't eat while doing 70 on the interstate!|n")
            return

        # Allow eating at cities and rest stops
        from typeclasses.rooms import CityRoom, RestStopRoom
        at_valid = isinstance(caller.location, (CityRoom, RestStopRoom))
        if not at_valid:
            caller.msg("|rNo diner here. Find a city or truck stop.|n")
            return

        # Show the menu
        lines = [
            "|wDINER MENU|n",
            "",
        ]
        for num, item in DINER_MENU.items():
            lines.append(f"  |y{num}|n. {item['name']:30s} |g${item['price']}|n")

        lines.append("")
        lines.append(f"|wYour money:|n |g${caller.db.money:,}|n  |wHunger:|n {caller.db.hunger or 0}/100")
        if caller.db.has_tums and (caller.db.tums_count or 0) > 0:
            lines.append(f"|wTums remaining:|n {caller.db.tums_count}")
        lines.append("")
        lines.append("|wType a number to order.|n")

        caller.msg("\n".join(lines))
        caller.ndb.diner_active = True


class CmdDinerChoice(Command):
    """
    Handle numbered diner menu selection.
    Active only when diner_active is set on caller.ndb.
    """

    key = "1"
    aliases = ["2", "3", "4", "5", "6", "7", "8"]
    locks = "cmd:all()"
    auto_help = False

    def func(self):
        caller = self.caller

        if not caller.ndb.diner_active:
            return

        caller.ndb.diner_active = False

        try:
            choice = int(self.cmdstring.strip())
        except ValueError:
            caller.msg("|rPick a number from the menu.|n")
            return

        item = DINER_MENU.get(choice)
        if not item:
            caller.msg("|rThat's not on the menu.|n")
            return

        price = item["price"]
        if (caller.db.money or 0) < price:
            caller.msg("|rYou can't afford that. Maybe check under the seat cushions.|n")
            return

        # Pay
        caller.db.money = (caller.db.money or 0) - price

        # Tums purchase (item 8)
        if choice == 8:
            caller.db.has_tums = True
            caller.db.tums_count = (caller.db.tums_count or 0) + 3
            caller.msg(f"|gYou buy a pack of Tums. ({caller.db.tums_count} tablets)|n")
            caller.msg(f"|wMoney:|n |g${caller.db.money:,}|n")
            return

        # Eating the food
        caller.msg(f"|wYou order the {item['name']}.|n")
        caller.msg(f"|w\"{item['desc']}\"|n")

        # Apply hunger reduction
        old_hunger = caller.db.hunger or 0
        caller.db.hunger = max(0, old_hunger - item["hunger_fill"])
        caller.msg(f"|gHunger: {old_hunger} -> {caller.db.hunger}|n")

        # Apply fatigue modification (coffee)
        if item["fatigue_mod"] != 0:
            old_fatigue = caller.db.fatigue or 0
            caller.db.fatigue = max(0, min(100, old_fatigue + item["fatigue_mod"]))
            if item["fatigue_mod"] < 0:
                caller.msg(f"|gThe caffeine kicks in. Fatigue: {old_fatigue} -> {caller.db.fatigue}|n")

        # Check stomach risk
        got_stomach_issues = False

        # Lactose intolerance check (milkshake)
        if item["lactose_risk"] > 0 and caller.db.lactose_intolerant:
            risk = item["lactose_risk"]
            # Tums reduce lactose risk too
            if caller.db.has_tums and (caller.db.tums_count or 0) > 0:
                caller.db.tums_count -= 1
                caller.msg("|yYou pop a Tums just in case.|n")
                risk *= 0.3

            if random.random() < risk:
                got_stomach_issues = True
                caller.msg("")
                caller.msg("|r*** Oh no. ***|n")
                caller.msg("|rAbout fifteen minutes after finishing that milkshake, you feel it.|n")
                caller.msg("|rA deep, ominous rumbling. A cold sweat breaks out.|n")
                caller.msg("|rYou are, apparently, |wLACTOSE INTOLERANT|r.|n")
                caller.msg("|rYou did not know this until right now.|n")
                caller.msg("|rThis is going to be a long ride.|n")
                caller.msg("")

        # Regular stomach risk (chili dog, chicken fried steak, etc.)
        if not got_stomach_issues and item["risk"] > 0:
            risk = item["risk"]
            if caller.db.has_tums and (caller.db.tums_count or 0) > 0:
                caller.db.tums_count -= 1
                caller.msg("|yYou pop a Tums just in case.|n")
                risk = item["risk_tums"]

            if random.random() < risk:
                got_stomach_issues = True
                msgs = [
                    "|rThat was a mistake. Your stomach is already protesting.|n",
                    "|rYou feel a disturbance in the force. And in your gut.|n",
                    "|rThe cook comes out to check on you. Even he looks concerned.|n",
                ]
                caller.msg(random.choice(msgs))

        if got_stomach_issues:
            caller.db.stomach_issues = True
            caller.msg("|r  ** Stomach issues active! Find a restroom soon. **|n")

        # Salad flavor text
        if choice == 7:
            caller.msg("|wThe other truckers are staring. You eat quickly.|n")

        caller.msg(f"|wMoney:|n |g${caller.db.money:,}|n")


class CmdRestroom(Command):
    """
    Use the restroom. Reduces bladder. Clears stomach issues.

    Usage:
        restroom
        bathroom
        pee

    Only available at a city or rest area (not while driving).
    """

    key = "restroom"
    aliases = ["bathroom", "pee", "toilet", "john"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if caller.is_driving:
            caller.msg("|rYou're doing 70 mph! There's a Gatorade bottle under the seat...|n")
            caller.msg("|rActually, no. Find a rest stop.|n")
            return

        # Allow restroom at cities, rest stops, or mandatory rest
        from typeclasses.rooms import CityRoom, RestStopRoom
        at_valid = isinstance(caller.location, (CityRoom, RestStopRoom)) or caller.db.mandatory_rest
        if not at_valid:
            caller.msg("|rNo restroom here. Find a city or truck stop.|n")
            return

        bladder = caller.db.bladder or 0
        stomach = caller.db.stomach_issues or False

        if bladder < 10 and not stomach and not caller.db.soiled:
            caller.msg("|wYou don't really need to go right now.|n")
            return

        # Handle soiled cleanup
        if caller.db.soiled:
            cleaning_fee = 75
            caller.msg("|wYou rush to the restroom and... take care of things.|n")
            caller.msg("|w...|n")
            caller.msg("|wA long, long shower later, you emerge.|n")
            if (caller.db.money or 0) >= cleaning_fee:
                caller.db.money = (caller.db.money or 0) - cleaning_fee
                caller.msg(f"|yThe truck stop attendant charges you |w${cleaning_fee}|y to clean the cab.|n")
                caller.msg(f"|y\"We've seen worse,\" they say. You doubt that.|n")
            else:
                caller.msg("|yThe attendant hoses out your cab for free. Out of pity.|n")
                caller.db.reputation = max(0, (caller.db.reputation or 50) - 2)
                caller.msg("|rReputation -2. That story's going to follow you.|n")
            caller.db.soiled = False
            caller.db.bladder = 0
            caller.db.stomach_issues = False
            caller.msg("|gSoiled status cleared. You're a new man.|n")
            caller.msg(f"|wMoney:|n |g${caller.db.money:,}|n")
            return

        # Determine scenario
        if stomach:
            # Stomach issues — extended, uh, visit
            msgs = [
                "|wYou sprint to the restroom with the urgency of a man who has made poor life choices.|n",
                "|w...|n",
                "|wTwenty minutes later, you emerge a changed person.|n",
                "|wThe trucker waiting outside gives you a look of pity and understanding.|n",
                "|gStomach issues cleared. You feel... lighter.|n",
            ]
            for m in msgs:
                caller.msg(m)
            caller.db.stomach_issues = False
        elif bladder >= 90:
            caller.msg("|gJust in time!|n")
            caller.msg("|wYou practically kick down the restroom door.|n")
            relieved_msgs = [
                "|wAaaaahhhhh. Sweet relief.|n",
                "|wYou close your eyes. This is the best part of the whole trip.|n",
            ]
            caller.msg(random.choice(relieved_msgs))
        elif bladder >= 60:
            msgs = [
                "|wYou take care of business. The fluorescent lights hum overhead.|n",
                "|wAnother truck stop bathroom. Another life experience you didn't need.|n",
                "|wSomeone wrote their handle on the wall. You admire their penmanship.|n",
            ]
            caller.msg(random.choice(msgs))
        else:
            msgs = [
                "|wYou make a quick pit stop. In and out.|n",
                "|wA routine visit. The bathroom is... adequate.|n",
            ]
            caller.msg(random.choice(msgs))

        # Graffiti easter egg (10% chance)
        if random.random() < 0.10:
            graffiti = [
                "|x  Scrawled on the wall: \"If you can read this, you're a trucker\"|n",
                "|x  Carved into the stall: \"Lot lizards ain't worth it — Nashville Nick\"|n",
                "|x  Written in Sharpie: \"DOT can kiss my CDL\"|n",
                "|x  Scratched into paint: \"Breaker breaker, someone left a log in stall 2\"|n",
                "|x  On the mirror: \"You are now 30 seconds behind schedule\"|n",
            ]
            caller.msg(random.choice(graffiti))

        caller.db.bladder = 0
        caller.msg(f"|wBladder:|n 0/100")


class CmdSleep(Command):
    """
    Sleep in the sleeper cab. Reduces fatigue and resets driving hours.

    Usage:
        sleep
        rest
        nap

    Only available at cities, rest areas, or when pulled over.
    """

    key = "sleep"
    aliases = ["rest", "nap", "sleeper", "bunks", "bunk"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if caller.is_driving:
            caller.msg("|rYou can't sleep at the wheel! ...Well, you CAN, but you shouldn't.|n")
            return

        # Allow sleep at cities, rest stops, or mandatory rest (roadside)
        from typeclasses.rooms import CityRoom, RestStopRoom
        at_valid = isinstance(caller.location, (CityRoom, RestStopRoom)) or caller.db.mandatory_rest
        if not at_valid:
            caller.msg("|rNowhere safe to park. Find a city or rest area.|n")
            return

        fatigue = caller.db.fatigue or 0
        stomach = caller.db.stomach_issues or False

        if fatigue < 10 and not caller.db.mandatory_rest:
            caller.msg("|wYou're not that tired. Hit the road, driver.|n")
            return

        # Sleep sequence
        caller.msg("|wYou climb into the sleeper cab and pull the curtain shut.|n")

        if stomach:
            caller.msg("|yYour stomach is still acting up. It's a rough night.|n")
            caller.msg("|yYou toss and turn, making several urgent trips to... nevermind.|n")
            caller.msg("|wYou wake up feeling... okay. Not great.|n")
            caller.db.fatigue = 20  # Can't fully rest with stomach issues
            caller.db.stomach_issues = False
            caller.msg("|gStomach issues cleared (eventually).|n")
        else:
            sleep_msgs = [
                "|wThe hum of the interstate is a lullaby tonight.|n",
                "|wYou're out before your head hits the pillow.|n",
                "|wA semi rumbles past. You don't even flinch.|n",
            ]
            caller.msg(random.choice(sleep_msgs))
            caller.msg("|w...|n")

            wake_msgs = [
                "|wYou wake up to sunlight through the cab curtain. Ready to roll.|n",
                "|wThe alarm on your phone goes off. Time to make money.|n",
                "|wA rooster at the rest area wakes you up. Wait, a rooster?|n",
            ]
            caller.msg(random.choice(wake_msgs))
            caller.db.fatigue = 0

        # Reset driving hours and mandatory rest
        caller.db.hours_driving = 0
        was_mandatory = caller.db.mandatory_rest
        caller.db.mandatory_rest = False

        if was_mandatory:
            caller.msg("|gDOT hours reset. You're legal to drive again.|n")

        caller.msg(f"|wFatigue:|n {caller.db.fatigue}/100")
        caller.msg(f"|wDriving hours:|n 0/16")


class CmdNoInput(Command):
    """Re-show the room when player presses Enter with no input."""

    key = syscmdkeys.CMD_NOINPUT
    locks = "cmd:all()"
    auto_help = False

    def func(self):
        self.caller.execute_cmd("look")


class CmdNoMatch(Command):
    """Show help hint when no command matches."""

    key = syscmdkeys.CMD_NOMATCH
    locks = "cmd:all()"
    auto_help = False

    def func(self):
        raw = self.raw_string.strip()
        # Check if this is a diner menu choice while diner is active
        if self.caller.ndb.diner_active:
            try:
                num = int(raw)
                if 1 <= num <= 8:
                    # This shouldn't normally happen since CmdDinerChoice
                    # handles 1-8, but just in case
                    self.caller.msg(f"|rMenu selection failed. Try |yeat|r again.|n")
                    self.caller.ndb.diner_active = False
                    return
            except ValueError:
                pass
        self.caller.msg(f"|rHuh? Type |yhelp|r for commands.|n")
