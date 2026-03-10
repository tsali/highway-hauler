"""
Highway Hauler — Truck maintenance and repair commands.
"""

from evennia.commands.command import Command
from typeclasses.rooms import CityRoom, RestStopRoom


# Repair costs per percentage point restored
REPAIR_COSTS = {
    "truck": 15,     # $15 per point (full repair from 0 = $1,500)
    "tires": 8,      # $8 per point (full = $800)
    "brakes": 10,    # $10 per point (full = $1,000)
    "oil": 150,      # flat $150 for oil change
}


class CmdRepair(Command):
    """
    Repair your truck at a gas station or truck stop.

    Usage:
        repair           - Show truck condition and repair costs
        repair truck     - Repair truck body/engine
        repair tires     - Replace worn tires
        repair brakes    - Replace brake pads
        repair oil       - Oil change
        repair all       - Fix everything
    """

    key = "repair"
    aliases = ["fix", "mechanic"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if caller.is_driving:
            caller.msg("|rYou can't repair while driving! Pull over first.|n")
            return

        if not isinstance(caller.location, (CityRoom, RestStopRoom)):
            caller.msg("|rNo mechanic here. Find a city or truck stop.|n")
            return

        if not self.args:
            self._show_condition(caller)
            return

        arg = self.args.strip().lower()

        if arg == "all":
            self._repair_all(caller)
        elif arg in ("truck", "tires", "brakes", "oil"):
            self._repair_one(caller, arg)
        else:
            caller.msg("|rOptions: repair truck, repair tires, repair brakes, repair oil, repair all|n")

    def _show_condition(self, caller):
        health = caller.db.truck_health if caller.db.truck_health is not None else 100
        tires = caller.db.tire_condition if caller.db.tire_condition is not None else 100
        brakes = caller.db.brake_condition if caller.db.brake_condition is not None else 100
        oil_miles = caller.db.oil_miles or 0

        lines = ["|w=== TRUCK CONDITION ===|n", ""]

        # Truck body
        truck_cost = max(0, 100 - health) * REPAIR_COSTS["truck"]
        h_color = "|g" if health >= 70 else ("|y" if health >= 40 else "|r")
        lines.append(f"  |wTruck:|n  {h_color}{health}%|n" + (f"  — repair: |y${truck_cost:,}|n" if health < 100 else "  |g(good)|n"))

        # Tires
        tire_cost = max(0, 100 - tires) * REPAIR_COSTS["tires"]
        t_color = "|g" if tires >= 70 else ("|y" if tires >= 40 else "|r")
        lines.append(f"  |wTires:|n  {t_color}{tires}%|n" + (f"  — replace: |y${tire_cost:,}|n" if tires < 100 else "  |g(good)|n"))

        # Brakes
        brake_cost = max(0, 100 - brakes) * REPAIR_COSTS["brakes"]
        b_color = "|g" if brakes >= 70 else ("|y" if brakes >= 40 else "|r")
        lines.append(f"  |wBrakes:|n {b_color}{brakes}%|n" + (f"  — replace: |y${brake_cost:,}|n" if brakes < 100 else "  |g(good)|n"))

        # Oil
        o_color = "|g" if oil_miles < 2000 else ("|y" if oil_miles < 3000 else "|r")
        oil_status = "OVERDUE" if oil_miles >= 3000 else f"{oil_miles:,} mi"
        lines.append(f"  |wOil:|n    {o_color}{oil_status}|n" + (f"  — change: |y${REPAIR_COSTS['oil']}|n" if oil_miles >= 1500 else "  |g(fresh)|n"))

        total = truck_cost + tire_cost + brake_cost + (REPAIR_COSTS["oil"] if oil_miles >= 1500 else 0)
        lines.append("")
        if total > 0:
            lines.append(f"|wRepair all: |y${total:,}|n  |wYour money: |g${caller.db.money:,}|n")
        else:
            lines.append("|gYour rig is in great shape!|n")
        lines.append("|wType |yrepair <part>|w or |yrepair all|w.|n")
        caller.msg("\n".join(lines))

    def _repair_one(self, caller, part):
        money = caller.db.money or 0

        if part == "truck":
            health = caller.db.truck_health if caller.db.truck_health is not None else 100
            if health >= 100:
                caller.msg("|gTruck body is fine.|n")
                return
            cost = max(0, 100 - health) * REPAIR_COSTS["truck"]
            if money < cost:
                # Partial repair
                affordable = money // REPAIR_COSTS["truck"]
                if affordable <= 0:
                    caller.msg(f"|rCan't afford repairs. Need at least ${REPAIR_COSTS['truck']}.|n")
                    return
                cost = affordable * REPAIR_COSTS["truck"]
                caller.db.truck_health = min(100, health + affordable)
                caller.db.money = money - cost
                caller.msg(f"|yPartial truck repair: +{affordable}% -> {caller.db.truck_health}%. Cost: ${cost:,}|n")
            else:
                caller.db.truck_health = 100
                caller.db.money = money - cost
                caller.msg(f"|gTruck fully repaired! Cost: ${cost:,}|n")

        elif part == "tires":
            tires = caller.db.tire_condition if caller.db.tire_condition is not None else 100
            if tires >= 100:
                caller.msg("|gTires are fine.|n")
                return
            cost = max(0, 100 - tires) * REPAIR_COSTS["tires"]
            if money < cost:
                affordable = money // REPAIR_COSTS["tires"]
                if affordable <= 0:
                    caller.msg(f"|rCan't afford new tires. Need at least ${REPAIR_COSTS['tires']}.|n")
                    return
                cost = affordable * REPAIR_COSTS["tires"]
                caller.db.tire_condition = min(100, tires + affordable)
                caller.db.money = money - cost
                caller.msg(f"|yPartial tire replacement: +{affordable}% -> {caller.db.tire_condition}%. Cost: ${cost:,}|n")
            else:
                caller.db.tire_condition = 100
                caller.db.money = money - cost
                caller.msg(f"|gNew tires installed! Cost: ${cost:,}|n")

        elif part == "brakes":
            brakes = caller.db.brake_condition if caller.db.brake_condition is not None else 100
            if brakes >= 100:
                caller.msg("|gBrakes are fine.|n")
                return
            cost = max(0, 100 - brakes) * REPAIR_COSTS["brakes"]
            if money < cost:
                affordable = money // REPAIR_COSTS["brakes"]
                if affordable <= 0:
                    caller.msg(f"|rCan't afford brake work. Need at least ${REPAIR_COSTS['brakes']}.|n")
                    return
                cost = affordable * REPAIR_COSTS["brakes"]
                caller.db.brake_condition = min(100, brakes + affordable)
                caller.db.money = money - cost
                caller.msg(f"|yPartial brake job: +{affordable}% -> {caller.db.brake_condition}%. Cost: ${cost:,}|n")
            else:
                caller.db.brake_condition = 100
                caller.db.money = money - cost
                caller.msg(f"|gNew brake pads installed! Cost: ${cost:,}|n")

        elif part == "oil":
            oil_miles = caller.db.oil_miles or 0
            if oil_miles < 1500:
                caller.msg(f"|gOil is still fresh ({oil_miles:,} mi). No change needed.|n")
                return
            cost = REPAIR_COSTS["oil"]
            if money < cost:
                caller.msg(f"|rCan't afford oil change. Need ${cost}.|n")
                return
            caller.db.oil_miles = 0
            caller.db.money = money - cost
            caller.msg(f"|gOil changed! Cost: ${cost}. Odometer reset.|n")

        caller.msg(f"|wMoney remaining: |g${caller.db.money:,}|n")

    def _repair_all(self, caller):
        health = caller.db.truck_health if caller.db.truck_health is not None else 100
        tires = caller.db.tire_condition if caller.db.tire_condition is not None else 100
        brakes = caller.db.brake_condition if caller.db.brake_condition is not None else 100
        oil_miles = caller.db.oil_miles or 0
        money = caller.db.money or 0

        truck_cost = max(0, 100 - health) * REPAIR_COSTS["truck"]
        tire_cost = max(0, 100 - tires) * REPAIR_COSTS["tires"]
        brake_cost = max(0, 100 - brakes) * REPAIR_COSTS["brakes"]
        oil_cost = REPAIR_COSTS["oil"] if oil_miles >= 1500 else 0
        total = truck_cost + tire_cost + brake_cost + oil_cost

        if total == 0:
            caller.msg("|gYour rig is in great shape! Nothing to repair.|n")
            return

        if money < total:
            caller.msg(f"|rFull repair costs ${total:,} but you only have ${money:,}.|n")
            caller.msg("|wRepair individual parts with |yrepair truck|w, |yrepair tires|w, etc.|n")
            return

        caller.db.truck_health = 100
        caller.db.tire_condition = 100
        caller.db.brake_condition = 100
        if oil_cost > 0:
            caller.db.oil_miles = 0
        caller.db.money = money - total
        caller.msg(f"|g*** FULL SERVICE COMPLETE ***|n")
        caller.msg(f"|wTruck, tires, brakes" + (", oil" if oil_cost > 0 else "") + f" — all good as new.|n")
        caller.msg(f"|wCost: |y${total:,}|n  |wMoney remaining: |g${caller.db.money:,}|n")
