"""
Highway Hauler — Contract and delivery commands.
"""

import random
import time
from evennia.commands.command import Command
from world.cities import CITIES, HIGHWAYS, CARGO_TYPES


def find_route_distance(origin, destination):
    """BFS to find shortest highway distance between two cities."""
    if origin == destination:
        return 0

    # Build adjacency
    adj = {}
    for a, b, dist, hwy in HIGHWAYS:
        adj.setdefault(a, []).append((b, dist))
        adj.setdefault(b, []).append((a, dist))

    # Dijkstra-lite
    visited = set()
    dist_map = {origin: 0}
    queue = [(0, origin)]

    while queue:
        queue.sort(key=lambda x: x[0])
        current_dist, current = queue.pop(0)
        if current == destination:
            return current_dist
        if current in visited:
            continue
        visited.add(current)
        for neighbor, d in adj.get(current, []):
            new_dist = current_dist + d
            if neighbor not in dist_map or new_dist < dist_map[neighbor]:
                dist_map[neighbor] = new_dist
                queue.append((new_dist, neighbor))

    return None  # No route


def generate_contracts(city_key, count=5):
    """Generate random cargo contracts from a city."""
    city_data = CITIES.get(city_key, {})
    tier = city_data.get("tier", 1)

    # More contracts at bigger cities
    count = count + (tier - 1) * 2

    # Possible destinations (reachable cities)
    all_cities = [k for k in CITIES if k != city_key]

    contracts = []
    for _ in range(count * 2):  # Generate extra, then filter
        if len(contracts) >= count:
            break

        dest_key = random.choice(all_cities)
        dest_data = CITIES.get(dest_key, {})
        cargo_key = random.choice(list(CARGO_TYPES.keys()))
        cargo_data = CARGO_TYPES[cargo_key]

        distance = find_route_distance(city_key, dest_key)
        if distance is None or distance == 0:
            continue

        # Weight varies 60-100% of base (partial loads, different quantities)
        weight = int(cargo_data["weight"] * random.uniform(0.60, 1.0))
        # Round to nearest 500 for cleaner display
        weight = max(500, (weight // 500) * 500)

        # Calculate pay (scaled to actual weight vs base weight)
        weight_ratio = weight / cargo_data["weight"]
        base_pay = int(distance * cargo_data["base_pay_per_mile"] * weight_ratio)
        # Add urgency bonus (20-60% extra for time-sensitive)
        urgency = random.choice(["standard", "standard", "rush", "urgent"])
        urgency_mult = {"standard": 1.0, "rush": 1.3, "urgent": 1.6}[urgency]
        pay = int(base_pay * urgency_mult)

        # Deadline: based on distance and urgency
        # Standard: generous time, Rush: moderate, Urgent: tight
        base_time = (distance / 55) * 3600  # hours at 55mph, in seconds
        time_mult = {"standard": 3.0, "rush": 2.0, "urgent": 1.5}[urgency]
        # Scale to real-time (game time is accelerated)
        from typeclasses.scripts import TICK_INTERVAL, GAME_MINUTES_PER_TICK
        real_seconds = (base_time / 60) * (TICK_INTERVAL / GAME_MINUTES_PER_TICK) * time_mult
        deadline = time.time() + real_seconds

        contracts.append({
            "cargo_key": cargo_key,
            "cargo_name": cargo_data["name"],
            "weight": weight,
            "desc": cargo_data["desc"],
            "origin": city_key,
            "origin_name": city_data.get("name", city_key),
            "destination": dest_key,
            "dest_name": dest_data.get("name", dest_key),
            "dest_state": dest_data.get("state", ""),
            "distance": distance,
            "pay": pay,
            "urgency": urgency,
            "deadline": deadline,
        })

    return contracts[:5]  # Cap at 5


class CmdContracts(Command):
    """
    View available cargo contracts at the current freight terminal.

    Usage:
        contracts
    """

    key = "contracts"
    aliases = ["jobs", "freight"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if caller.is_driving:
            caller.msg("|rYou need to be at a city to check contracts.|n")
            return

        city_key = None
        if caller.location and hasattr(caller.location, 'db'):
            city_key = caller.location.db.city_key

        if not city_key:
            caller.msg("|rNo freight terminal here.|n")
            return

        contracts = generate_contracts(city_key)
        if not contracts:
            caller.msg("|yNo contracts available right now. Check back later.|n")
            return

        # Store on caller temporarily for accept command
        caller.ndb.available_contracts = contracts

        lines = [
            "|wFREIGHT TERMINAL — Available Contracts|n",
            "",
        ]

        urgency_colors = {"standard": "|w", "rush": "|y", "urgent": "|r"}

        for i, c in enumerate(contracts, 1):
            uc = urgency_colors.get(c["urgency"], "|w")
            mins_left = max(0, (c["deadline"] - time.time()) / 60)
            lines.append(
                f"  |y{i}|n. {uc}[{c['urgency'].upper()}]|n "
                f"|w{c['cargo_name']}|n -> |c{c['dest_name']}, {c['dest_state']}|n"
            )
            lines.append(
                f"     {c['distance']} mi | {c['weight']:,} lbs | "
                f"|g${c['pay']:,}|n | "
                f"Deadline: {mins_left:.0f} min"
            )
            lines.append("")

        lines.append(f"|wType |yaccept <#>|w to take a contract.|n")
        lines.append(f"|wYour trailer capacity: {caller.current_cargo_weight:,}/{caller.cargo_capacity:,} lbs|n")

        caller.msg("\n".join(lines))


class CmdAccept(Command):
    """
    Accept a cargo contract.

    Usage:
        accept <number>
    """

    key = "accept"
    aliases = ["take"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("|wUsage: accept <number>|n")
            return

        contracts = caller.ndb.available_contracts
        if not contracts:
            caller.msg("|rNo contracts listed. Type |wcontracts|r first.|n")
            return

        try:
            idx = int(self.args.strip()) - 1
        except ValueError:
            caller.msg("|rEnter a number.|n")
            return

        if idx < 0 or idx >= len(contracts):
            caller.msg("|rInvalid contract number.|n")
            return

        contract = contracts[idx]

        # Check weight capacity
        current_weight = caller.current_cargo_weight
        new_weight = current_weight + contract["weight"]
        if new_weight > caller.cargo_capacity:
            caller.msg(
                f"|rToo heavy! This cargo weighs {contract['weight']:,} lbs. "
                f"Current load: {current_weight:,}/{caller.cargo_capacity:,} lbs. "
                f"You have {caller.cargo_capacity - current_weight:,} lbs of space left.|n"
            )
            return

        # Apply contract bonus if active
        bonus = caller.db.contract_bonus or 1.0
        if bonus > 1.0:
            old_pay = contract["pay"]
            contract["pay"] = int(old_pay * bonus)
            caller.msg(f"|g+{int((bonus - 1) * 100)}% bonus applied! Pay: ${old_pay:,} -> ${contract['pay']:,}|n")
            caller.db.contract_bonus = 1.0

        # Accept
        cargo_list = caller.db.current_cargo or []
        cargo_list.append(contract)
        caller.db.current_cargo = cargo_list

        caller.msg(f"\n|g*** CONTRACT ACCEPTED ***|n")
        caller.msg(f"|wCargo:|n {contract['cargo_name']}")
        caller.msg(f"|wDestination:|n {contract['dest_name']}, {contract['dest_state']}")
        caller.msg(f"|wPay:|n |g${contract['pay']:,}|n")
        caller.msg(f"|wWeight:|n {contract['weight']:,} lbs")
        caller.msg(f"\n|wHit the road with |ydrive {contract['dest_name'].lower()}|n")


class CmdCargo(Command):
    """
    View your current cargo manifest.

    Usage:
        cargo
    """

    key = "cargo"
    aliases = ["manifest", "haul"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        cargo = caller.db.current_cargo or []

        if not cargo:
            caller.msg("|yTrailer is empty. Check |wcontracts|y at a freight terminal.|n")
            return

        lines = [
            "|w=== CARGO MANIFEST ===|n",
            f"|wTotal weight:|n {caller.current_cargo_weight:,}/{caller.cargo_capacity:,} lbs",
            "",
        ]

        for i, c in enumerate(cargo, 1):
            mins_left = max(0, (c.get("deadline", 0) - time.time()) / 60)
            overdue = mins_left <= 0
            time_str = f"|r OVERDUE|n" if overdue else f"{mins_left:.0f} min left"
            lines.append(
                f"  {i}. |w{c.get('cargo_name', '???')}|n — "
                f"|c{c.get('dest_name', '???')}|n | "
                f"{c.get('weight', 0):,} lbs | "
                f"|g${c.get('pay', 0):,}|n | "
                f"{time_str}"
            )

        caller.msg("\n".join(lines))


class CmdDeliver(Command):
    """
    Deliver cargo at the current city.

    Usage:
        deliver
    """

    key = "deliver"
    aliases = ["dropoff", "unload"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        city_key = None
        if caller.location and hasattr(caller.location, 'db'):
            city_key = caller.location.db.city_key

        if not city_key:
            caller.msg("|rYou need to be at a city to deliver cargo.|n")
            return

        cargo = caller.db.current_cargo or []
        deliverable = [c for c in cargo if c.get("destination") == city_key]

        if not deliverable:
            caller.msg("|yNo cargo to deliver here.|n")
            return

        remaining = [c for c in cargo if c.get("destination") != city_key]
        caller.db.current_cargo = remaining

        total_pay = 0
        for c in deliverable:
            is_ontime = c.get("deadline", 0) >= time.time()
            pay = c.get("pay", 0)
            if is_ontime:
                bonus = int(pay * 0.1)
                total = pay + bonus
                caller.msg(
                    f"|g*** DELIVERED: {c.get('cargo_name', '???')} ***|n "
                    f"— |g${pay:,}|n + |g${bonus:,} on-time bonus|n"
                )
                caller.db.deliveries_ontime = (caller.db.deliveries_ontime or 0) + 1
            else:
                penalty = int(pay * 0.3)
                total = pay - penalty
                caller.msg(
                    f"|y*** DELIVERED (LATE): {c.get('cargo_name', '???')} ***|n "
                    f"— |g${pay:,}|n - |r${penalty:,} late penalty|n"
                )

            total_pay += total
            caller.db.deliveries_completed = (caller.db.deliveries_completed or 0) + 1
            caller.db.reputation = min(100, (caller.db.reputation or 50) + (3 if is_ontime else 1))

        caller.db.money = (caller.db.money or 0) + total_pay
        caller.msg(f"\n|wTotal earned:|n |g${total_pay:,}|n")
        caller.msg(f"|wBank balance:|n |g${caller.db.money:,}|n")
        caller.msg(f"|wReputation:|n {caller.db.reputation}/100")
