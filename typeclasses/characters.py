"""
Highway Hauler — Trucker character typeclass.

Players are truckers with a rig, cargo capacity, fuel tank, and money.
Attributes stored via Evennia's db system.
"""

import random
from evennia.objects.objects import DefaultCharacter
from .objects import ObjectParent


# Truck upgrade definitions
TRUCK_UPGRADES = {
    "engine": {
        "name": "Engine",
        "levels": [
            {"name": "Stock 4-Cylinder", "speed": 45, "cost": 0},
            {"name": "V6 Turbo", "speed": 55, "cost": 2000},
            {"name": "V8 Diesel", "speed": 65, "cost": 5000},
            {"name": "Big Block V8", "speed": 75, "cost": 12000},
            {"name": "Supercharged V8", "speed": 85, "cost": 25000},
        ],
    },
    "tank": {
        "name": "Fuel Tank",
        "levels": [
            {"name": "50 Gallon Standard", "capacity": 50, "cost": 0},
            {"name": "80 Gallon Extended", "capacity": 80, "cost": 1500},
            {"name": "120 Gallon Long Haul", "capacity": 120, "cost": 4000},
            {"name": "150 Gallon Cross-Country", "capacity": 150, "cost": 8000},
            {"name": "200 Gallon Transcontinental", "capacity": 200, "cost": 15000},
        ],
    },
    "trailer": {
        "name": "Trailer",
        "levels": [
            {"name": "20ft Flatbed", "capacity": 15000, "cost": 0},
            {"name": "28ft Box", "capacity": 25000, "cost": 3000},
            {"name": "40ft Dry Van", "capacity": 35000, "cost": 7000},
            {"name": "48ft Reefer", "capacity": 45000, "cost": 15000},
            {"name": "53ft Double", "capacity": 60000, "cost": 30000},
        ],
    },
    "cb_radio": {
        "name": "CB Radio",
        "levels": [
            {"name": "None", "range": 0, "cost": 0},
            {"name": "Cobra 29 LTD", "range": 1, "cost": 500},
        ],
    },
    "gps": {
        "name": "GPS Navigation",
        "levels": [
            {"name": "None (Paper Map)", "reliability": 0, "cost": 0},
            {"name": "Garmin DriveSmart", "reliability": 0.70, "cost": 15000},
            {"name": "Rand McNally TND", "reliability": 0.85, "cost": 35000},
            {"name": "Trucker's GPS Pro", "reliability": 0.95, "cost": 60000},
        ],
    },
}


class Trucker(ObjectParent, DefaultCharacter):
    """
    The Trucker typeclass for player characters.

    Attributes (via self.db):
        chargen_complete (bool): Whether setup is done
        handle (str): CB radio handle / trucker name
        home_city (str): City key where they started
        current_cargo (list): List of active cargo contracts
        money (int): Current funds in dollars
        fuel (float): Current fuel in gallons
        miles_driven (int): Total miles driven
        deliveries_completed (int): Successful deliveries
        deliveries_ontime (int): On-time deliveries
        engine_level (int): Engine upgrade level (0-4)
        tank_level (int): Fuel tank upgrade level (0-4)
        trailer_level (int): Trailer upgrade level (0-4)
        cb_level (int): CB radio level (0-1)
        driving_to (str): City key currently driving to, or None
        driving_from (str): City key driving from
        driving_miles_left (float): Miles remaining to destination
        driving_highway (str): Highway name currently on
        reputation (int): 0-100, affects contract availability
        weigh_violations (int): Number of weigh station violations
    """

    def at_object_creation(self):
        """Called once when the character is first created."""
        super().at_object_creation()
        self.db.chargen_complete = False
        self.db.handle = ""
        self.db.home_city = ""
        self.db.current_cargo = []
        self.db.money = 500
        self.db.fuel = 50.0
        self.db.miles_driven = 0
        self.db.deliveries_completed = 0
        self.db.deliveries_ontime = 0
        self.db.engine_level = 0
        self.db.tank_level = 0
        self.db.trailer_level = 0
        self.db.cb_level = 0
        self.db.gps_level = 0
        self.db.gps_route = []  # remaining cities for GPS auto-routing
        self.db.driving_to = None
        self.db.driving_from = None
        self.db.driving_miles_left = 0
        self.db.driving_highway = ""
        self.db.reputation = 50
        self.db.weigh_violations = 0
        self.db.last_lot_lizard = 0
        self.db.contract_bonus = 1.0
        # Trucker needs
        self.db.hunger = 0        # 0=full, 100=starving
        self.db.bladder = 0       # 0=empty, 100=desperate
        self.db.fatigue = 0       # 0=rested, 100=exhausted
        self.db.hours_driving = 0.0  # continuous driving hours
        self.db.lactose_intolerant = (random.random() < 0.20)
        self.db.has_tums = False
        self.db.tums_count = 0
        self.db.stomach_issues = False
        self.db.mandatory_rest = False  # DOT mandatory rest flag

    @property
    def speed(self):
        """Current truck speed (mph) based on engine level."""
        return TRUCK_UPGRADES["engine"]["levels"][self.db.engine_level or 0]["speed"]

    @property
    def fuel_capacity(self):
        """Max fuel tank capacity (gallons)."""
        return TRUCK_UPGRADES["tank"]["levels"][self.db.tank_level or 0]["capacity"]

    @property
    def cargo_capacity(self):
        """Max cargo weight (lbs)."""
        return TRUCK_UPGRADES["trailer"]["levels"][self.db.trailer_level or 0]["capacity"]

    @property
    def has_cb(self):
        """Whether the trucker has a CB radio."""
        return (self.db.cb_level or 0) > 0

    @property
    def has_gps(self):
        """Whether the trucker has a GPS unit."""
        return (self.db.gps_level or 0) > 0

    @property
    def gps_reliability(self):
        """GPS reliability (0.0-1.0) based on upgrade level."""
        level = self.db.gps_level or 0
        return TRUCK_UPGRADES["gps"]["levels"][level]["reliability"]

    @property
    def current_cargo_weight(self):
        """Total weight of current cargo."""
        return sum(c.get("weight", 0) for c in (self.db.current_cargo or []))

    @property
    def fuel_consumption(self):
        """Gallons per mile. Heavier load = more fuel. Base: 0.15 gal/mi."""
        base = 0.15
        weight_factor = 1.0 + (self.current_cargo_weight / 60000.0) * 0.5
        return base * weight_factor

    @property
    def is_driving(self):
        """Whether currently on the road."""
        return self.db.driving_to is not None

    def get_status_display(self):
        """Return a formatted status string."""
        eng = TRUCK_UPGRADES["engine"]["levels"][self.db.engine_level or 0]
        tank = TRUCK_UPGRADES["tank"]["levels"][self.db.tank_level or 0]
        trailer = TRUCK_UPGRADES["trailer"]["levels"][self.db.trailer_level or 0]
        cb = TRUCK_UPGRADES["cb_radio"]["levels"][self.db.cb_level or 0]
        gps = TRUCK_UPGRADES["gps"]["levels"][self.db.gps_level or 0]

        fuel_pct = (self.db.fuel / self.fuel_capacity) * 100 if self.fuel_capacity else 0
        fuel_bar = self._bar(fuel_pct)

        cargo_pct = (self.current_cargo_weight / self.cargo_capacity) * 100 if self.cargo_capacity else 0

        lines = [
            f"|w=== TRUCKER STATUS: {self.db.handle or self.key} ===|n",
            f"|wMoney:|n |g${self.db.money:,}|n",
            f"|wReputation:|n {self.db.reputation}/100",
            f"|wMiles Driven:|n {self.db.miles_driven:,}",
            f"|wDeliveries:|n {self.db.deliveries_completed} ({self.db.deliveries_ontime} on-time)",
            "",
            f"|w--- TRUCK ---",
            f"|wEngine:|n {eng['name']} ({self.speed} mph)",
            f"|wFuel:|n {self.db.fuel:.0f}/{self.fuel_capacity} gal {fuel_bar}",
            f"|wTrailer:|n {trailer['name']} ({self.current_cargo_weight:,}/{self.cargo_capacity:,} lbs)",
            f"|wCB Radio:|n {cb['name']}",
            f"|wGPS:|n {gps['name']}" + (f" ({gps['reliability']*100:.0f}% reliable)" if gps['reliability'] > 0 else ""),
        ]

        # Trucker needs
        hunger = self.db.hunger or 0
        bladder = self.db.bladder or 0
        fatigue = self.db.fatigue or 0
        lines.append("")
        lines.append(f"|w--- TRUCKER ---")
        lines.append(f"|wHunger:|n  {self._needs_bar(hunger)} {hunger}/100")
        lines.append(f"|wBladder:|n {self._needs_bar(bladder)} {bladder}/100")
        lines.append(f"|wFatigue:|n {self._needs_bar(fatigue)} {fatigue}/100")
        if self.db.hours_driving and self.db.hours_driving > 0:
            lines.append(f"|wDriving hours:|n {self.db.hours_driving:.1f}/16")
        if self.db.stomach_issues:
            lines.append(f"|r  !! Stomach problems !!|n")
        if self.db.mandatory_rest:
            lines.append(f"|r  !! DOT: Mandatory rest required !!|n")

        if self.is_driving:
            lines.append("")
            lines.append(f"|y--- ON THE ROAD ---|n")
            lines.append(f"|wHeading to:|n {self.db.driving_to}")
            lines.append(f"|wMiles left:|n {self.db.driving_miles_left:.0f}")
            lines.append(f"|wHighway:|n {self.db.driving_highway}")
            gps_route = self.db.gps_route or []
            if gps_route:
                from world.cities import CITIES
                route_names = [CITIES.get(k, {}).get("name", k) for k in gps_route]
                lines.append(f"|wGPS Route:|n {' -> '.join(route_names)} ({len(gps_route)} stop(s) remaining)")

        return "\n".join(lines)

    @staticmethod
    def _bar(pct):
        """Simple text progress bar."""
        filled = int(pct / 5)
        empty = 20 - filled
        if pct > 50:
            color = "|g"
        elif pct > 25:
            color = "|y"
        else:
            color = "|r"
        return f"[{color}{'#' * filled}|n{'.' * empty}]"

    @staticmethod
    def _needs_bar(value):
        """Simple needs bar: 0=good (green), 100=bad (red)."""
        filled = int(value / 5)
        empty = 20 - filled
        if value < 40:
            color = "|g"
        elif value < 70:
            color = "|y"
        else:
            color = "|r"
        return f"[{color}{'|' * filled}|n{'.' * empty}]"

    def at_post_puppet(self, **kwargs):
        """Called when a player connects to this character."""
        super().at_post_puppet(**kwargs)

        if not self.db.chargen_complete:
            # Start character setup
            from commands.chargen import start_chargen
            start_chargen(self)
        else:
            self.msg(f"|wWelcome back, {self.db.handle or self.key}!|n")
            self.msg(self.get_status_display())
            if self.location:
                self.msg("")
                self.execute_cmd("look")
