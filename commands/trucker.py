"""
Highway Hauler — Trucker utility commands: status, upgrade, cb, who, scores, trivia.
"""

import random
import time
from evennia.commands.command import Command
from typeclasses.characters import TRUCK_UPGRADES
from world.cities import TRIVIA


class CmdStatus(Command):
    """
    Check your truck status, money, and stats.

    Usage:
        status
    """

    key = "status"
    aliases = ["stats", "rig"]
    locks = "cmd:all()"

    def func(self):
        self.caller.msg(self.caller.get_status_display())


class CmdUpgrade(Command):
    """
    View or buy truck upgrades.

    Usage:
        upgrade          - List available upgrades
        upgrade <type>   - Buy the next level of an upgrade

    Types: engine, tank, trailer, cb, gps, radar
    Must be at a mid-size city or larger.
    """

    key = "upgrade"
    aliases = ["shop"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if caller.is_driving:
            caller.msg("|rYou can't shop while driving!|n")
            return

        # Check city tier
        city_tier = 1
        if caller.location and hasattr(caller.location, 'db'):
            city_data = caller.location.db.city_data or {}
            city_tier = city_data.get("tier", 1)

        if city_tier < 2:
            caller.msg("|rNo upgrade shop in this town. Head to a bigger city.|n")
            return

        if not self.args:
            self._show_upgrades(caller)
            return

        upgrade_type = self.args.strip().lower()
        if upgrade_type == "cb":
            upgrade_type = "cb_radio"

        if upgrade_type not in TRUCK_UPGRADES:
            caller.msg(f"|rUnknown upgrade type. Options: engine, tank, trailer, cb, gps, radar|n")
            return

        self._buy_upgrade(caller, upgrade_type)

    def _show_upgrades(self, caller):
        lines = [
            "|w=== UPGRADE SHOP ===|n",
        ]

        for utype, udata in TRUCK_UPGRADES.items():
            level_attr = f"{utype.replace('cb_radio', 'cb')}_level"
            current = getattr(caller.db, level_attr, 0) or 0
            levels = udata["levels"]
            cur_name = levels[current]["name"]
            cmd = utype.replace("cb_radio", "cb")

            if current >= len(levels) - 1:
                lines.append(f"  |w{udata['name']:12s}|n {cur_name} |g(MAX)|n")
            else:
                nxt = levels[current + 1]
                lines.append(
                    f"  |w{udata['name']:12s}|n {cur_name} -> |y{nxt['name']}|n |y${nxt['cost']:,}|n  |yupgrade {cmd}|n"
                )

        lines.append(f"|wMoney:|n |g${caller.db.money:,}|n")
        caller.msg("\n".join(lines))

    def _buy_upgrade(self, caller, utype):
        level_attr = f"{utype.replace('cb_radio', 'cb')}_level"
        current = getattr(caller.db, level_attr, 0) or 0
        levels = TRUCK_UPGRADES[utype]["levels"]

        if current >= len(levels) - 1:
            caller.msg("|gAlready at max level!|n")
            return

        next_level = levels[current + 1]
        cost = next_level["cost"]

        if (caller.db.money or 0) < cost:
            caller.msg(f"|rNot enough money! Need ${cost:,}, you have ${caller.db.money:,}.|n")
            return

        # Confirmation step
        pending = getattr(caller.ndb, 'pending_upgrade', None)
        if pending and pending.get('utype') == utype:
            # Already confirmed — buy it
            caller.ndb.pending_upgrade = None
            caller.db.money = (caller.db.money or 0) - cost
            setattr(caller.db, level_attr, current + 1)
            caller.msg(f"|g*** UPGRADED: {TRUCK_UPGRADES[utype]['name']} ***|n")
            caller.msg(f"|wNew:|n {next_level['name']}")
            caller.msg(f"|wCost:|n ${cost:,}")
            caller.msg(f"|wMoney remaining:|n |g${caller.db.money:,}|n")
            # Check fully upgraded achievement
            from typeclasses.characters import grant_achievement
            all_maxed = True
            for ut, ud in TRUCK_UPGRADES.items():
                la = f"{ut.replace('cb_radio', 'cb')}_level"
                lv = getattr(caller.db, la, 0) or 0
                if lv < len(ud["levels"]) - 1:
                    all_maxed = False
                    break
            if all_maxed:
                grant_achievement(caller, "fully_upgraded")
        else:
            # Show confirmation prompt
            caller.ndb.pending_upgrade = {'utype': utype}
            current_name = levels[current]['name']
            caller.msg(f"|y--- CONFIRM UPGRADE ---")
            caller.msg(f"|wUpgrade:|n {TRUCK_UPGRADES[utype]['name']}")
            caller.msg(f"|wCurrent:|n {current_name}")
            caller.msg(f"|wNew:|n {next_level['name']}")
            caller.msg(f"|wCost:|n |r${cost:,}|n")
            caller.msg(f"|wYour money:|n |g${caller.db.money:,}|n -> |y${caller.db.money - cost:,}|n after")
            caller.msg(f"|wType |yupgrade {utype}|w again to confirm, or anything else to cancel.|n")


class CmdRelocate(Command):
    """
    Change your home city to where you are now.

    Usage:
        relocate

    Costs $2,500. You must be at a city (not driving or at a rest stop).
    """

    key = "relocate"
    aliases = ["movehome", "sethome"]
    locks = "cmd:all()"

    COST = 2500

    def func(self):
        caller = self.caller

        if caller.is_driving:
            caller.msg("|rCan't relocate while driving!|n")
            return

        from typeclasses.rooms import CityRoom
        if not caller.location or not isinstance(caller.location, CityRoom):
            caller.msg("|rYou need to be at a city to relocate. Can't set a rest stop as home.|n")
            return

        city_key = caller.location.db.city_key
        if not city_key:
            caller.msg("|rCan't determine what city you're in.|n")
            return

        if city_key == caller.db.home_city:
            caller.msg("|yYou're already home!|n")
            return

        from world.cities import CITIES
        city_data = CITIES.get(city_key, {})
        city_name = city_data.get("name", city_key)
        city_state = city_data.get("state", "")

        old_key = caller.db.home_city or ""
        old_data = CITIES.get(old_key, {})
        old_name = old_data.get("name", old_key)

        # Confirmation step
        pending = getattr(caller.ndb, 'pending_relocate', None)
        if pending and pending == city_key:
            caller.ndb.pending_relocate = None
            if (caller.db.money or 0) < self.COST:
                caller.msg(f"|rNot enough money! Need ${self.COST:,}, you have ${caller.db.money:,}.|n")
                return
            caller.db.money = (caller.db.money or 0) - self.COST
            caller.db.home_city = city_key
            caller.msg(f"|g*** HOME RELOCATED ***|n")
            caller.msg(f"|wOld home:|n {old_name}")
            caller.msg(f"|wNew home:|n {city_name}, {city_state}")
            caller.msg(f"|wCost:|n ${self.COST:,}")
            caller.msg(f"|wMoney remaining:|n |g${caller.db.money:,}|n")
        else:
            caller.ndb.pending_relocate = city_key
            caller.msg(f"|y--- RELOCATE HOME ---")
            caller.msg(f"|wCurrent home:|n {old_name}")
            caller.msg(f"|wNew home:|n {city_name}, {city_state}")
            caller.msg(f"|wCost:|n |r${self.COST:,}|n")
            caller.msg(f"|wYour money:|n |g${caller.db.money:,}|n")
            caller.msg(f"|wType |yrelocate|w again to confirm.|n")


class CmdCB(Command):
    """
    CB Radio — broadcast a message to all truckers.

    Usage:
        cb <message>
    """

    key = "cb"
    aliases = ["radio"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if not caller.has_cb:
            caller.msg("|rYou don't have a CB radio! Buy one at an upgrade shop.|n")
            return

        if not self.args:
            caller.msg("|wUsage: cb <message>|n")
            return

        handle = caller.db.handle or caller.key
        msg = self.args.strip()

        # Broadcast to all connected truckers with CB
        from typeclasses.characters import Trucker, grant_achievement
        for t in Trucker.objects.all():
            if (t.db.cb_level or 0) > 0 and t.has_account:
                t.msg(f"|y[CB] {handle}:|n {msg}")

        # CB chatter achievement
        caller.db.cb_messages_sent = (caller.db.cb_messages_sent or 0) + 1
        if (caller.db.cb_messages_sent or 0) >= 50:
            grant_achievement(caller, "cb_chatter")


class CmdWho(Command):
    """
    See all online truckers and their locations.

    Usage:
        who
    """

    key = "who"
    aliases = ["drivers"]
    locks = "cmd:all()"

    def func(self):
        from typeclasses.characters import Trucker
        from world.cities import CITIES

        online = []
        for t in Trucker.objects.all():
            if not t.has_account or not t.sessions.count():
                continue
            handle = t.db.handle or t.key
            if t.is_driving:
                dest_data = CITIES.get(t.db.driving_to or "", {})
                location = f"On {t.db.driving_highway} -> {dest_data.get('name', '???')}"
            elif t.location and hasattr(t.location, 'db') and t.location.db.city_key:
                city_data = t.location.db.city_data or {}
                location = f"{city_data.get('name', '???')}, {city_data.get('state', '')}"
            else:
                location = "Unknown"
            online.append((handle, location, t.db.miles_driven or 0))

        if not online:
            self.caller.msg("|yNo other truckers on the road right now.|n")
            return

        lines = [
            "|w=== TRUCKERS ON THE ROAD ===|n",
            "",
        ]
        for handle, loc, miles in online:
            lines.append(f"  |c{handle:20s}|n |w{loc:30s}|n ({miles:,} mi)")

        lines.append(f"\n|w{len(online)} driver(s) online|n")
        self.caller.msg("\n".join(lines))


class CmdScores(Command):
    """
    View the leaderboard.

    Usage:
        scores
    """

    key = "scores"
    aliases = ["leaderboard", "top"]
    locks = "cmd:all()"

    def func(self):
        from typeclasses.characters import Trucker

        truckers = []
        for t in Trucker.objects.all():
            if not (t.db.chargen_complete):
                continue
            truckers.append({
                "handle": t.db.handle or t.key,
                "miles": t.db.miles_driven or 0,
                "deliveries": t.db.deliveries_completed or 0,
                "money": t.db.money or 0,
                "ontime": t.db.deliveries_ontime or 0,
                "total_income": t.db.total_income or 0,
                "biggest_weight": t.db.biggest_haul_weight or 0,
                "biggest_income": t.db.biggest_haul_income or 0,
            })

        if not truckers:
            self.caller.msg("|yNo truckers registered yet.|n")
            return

        truckers.sort(key=lambda x: x["miles"], reverse=True)

        lines = [
            "|w=== HIGHWAY HAULER LEADERBOARD ===|n",
            "",
            f"  {'#':3s} {'Handle':20s} {'Miles':>10s} {'Deliveries':>12s} {'Money':>10s} {'On-Time':>8s}",
            "  " + "-" * 65,
        ]

        for i, t in enumerate(truckers[:20], 1):
            ontime_pct = (
                f"{t['ontime'] / t['deliveries'] * 100:.0f}%"
                if t['deliveries'] > 0 else "---"
            )
            lines.append(
                f"  {i:3d} |c{t['handle']:20s}|n "
                f"{t['miles']:>10,} "
                f"{t['deliveries']:>12} "
                f"|g${t['money']:>9,}|n "
                f"{ontime_pct:>8s}"
            )

        # High score records
        lines.append("")
        lines.append("|w=== RECORDS ===|n")

        # Most total income
        by_income = sorted(truckers, key=lambda x: x["total_income"], reverse=True)
        if by_income and by_income[0]["total_income"] > 0:
            t = by_income[0]
            lines.append(f"  |wHighest Lifetime Earnings:|n |c{t['handle']}|n |g${t['total_income']:,}|n")

        # Most miles
        by_miles = sorted(truckers, key=lambda x: x["miles"], reverse=True)
        if by_miles and by_miles[0]["miles"] > 0:
            t = by_miles[0]
            lines.append(f"  |wMost Miles Driven:|n       |c{t['handle']}|n {t['miles']:,} mi")

        # Biggest haul by weight
        by_weight = sorted(truckers, key=lambda x: x["biggest_weight"], reverse=True)
        if by_weight and by_weight[0]["biggest_weight"] > 0:
            t = by_weight[0]
            lines.append(f"  |wHeaviest Single Haul:|n    |c{t['handle']}|n {t['biggest_weight']:,} lbs")

        # Biggest haul by income
        by_haul_income = sorted(truckers, key=lambda x: x["biggest_income"], reverse=True)
        if by_haul_income and by_haul_income[0]["biggest_income"] > 0:
            t = by_haul_income[0]
            lines.append(f"  |wHighest Single Payout:|n   |c{t['handle']}|n |g${t['biggest_income']:,}|n")

        self.caller.msg("\n".join(lines))


class CmdTrivia(Command):
    """
    Answer a geography trivia question for bonus cash.
    Only available at rest stops (tier 3 cities).

    Usage:
        trivia
    """

    key = "trivia"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if caller.is_driving:
            caller.msg("|rPull over first! Can't do trivia at 70 mph.|n")
            return

        city_tier = 1
        if caller.location and hasattr(caller.location, 'db'):
            city_data = caller.location.db.city_data or {}
            city_tier = city_data.get("tier", 1)

        if city_tier < 3:
            caller.msg("|rTrivia is only available at rest stops in major cities.|n")
            return

        # Check cooldown (1 trivia per 2 minutes real time)
        last = caller.db.last_trivia or 0
        if time.time() - last < 120:
            wait = int(120 - (time.time() - last))
            caller.msg(f"|yYou just did trivia. Wait {wait} seconds.|n")
            return

        q, a = random.choice(TRIVIA)
        caller.db.pending_trivia_answer = a
        caller.db.last_trivia = time.time()

        caller.msg(f"|w=== GEOGRAPHY TRIVIA ===|n")
        caller.msg(f"|w{q}|n")
        caller.msg(f"|y(Type your answer)|n")

        # Use ndb for the pending state
        caller.ndb.trivia_active = True


class CmdTriviaAnswer(Command):
    """
    Internal command to catch trivia answers.
    Only active when trivia_active is set.
    """

    key = "_trivia_answer"
    locks = "cmd:all()"
    auto_help = False

    def func(self):
        caller = self.caller
        answer = caller.db.pending_trivia_answer

        if not answer:
            return

        guess = self.raw_string.strip().lower()
        if guess in answer or answer in guess:
            reward = random.randint(50, 200)
            caller.msg(f"|g Correct! +${reward}|n")
            caller.db.money = (caller.db.money or 0) + reward
        else:
            caller.msg(f"|rWrong! The answer was: {answer}|n")

        caller.db.pending_trivia_answer = None
        caller.ndb.trivia_active = False
