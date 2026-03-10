#!/usr/bin/env python3
"""Export Highway Hauler scores as JSON for the BBS website.

Initializes Evennia's Django ORM and reads trucker character data.
Outputs JSON to stdout or writes to a file.

Usage:
    cd /opt/evennia/hauler && source /opt/evennia/venv/bin/activate
    python /home/tsali/projects/highway-hauler/export_scores.py [output_file]

Designed to be called from bbs-scores.py or cron.
"""

import json
import os
import sys

# Initialize Evennia's Django
os.environ["DJANGO_SETTINGS_MODULE"] = "server.conf.settings"
# Must be in the game dir for Evennia to find settings
os.chdir("/opt/evennia/hauler")
sys.path.insert(0, "/opt/evennia/hauler")

import django
django.setup()

from evennia.objects.models import ObjectDB


def get_scores():
    """Read all trucker characters and return scores dict."""
    truckers = []
    live_positions = []

    for obj in ObjectDB.objects.filter(db_typeclass_path__contains="characters.Trucker"):
        if not obj.db.chargen_complete:
            continue

        handle = obj.db.handle or obj.key
        online = bool(obj.sessions.count())

        # Truck upgrade names
        from typeclasses.characters import TRUCK_UPGRADES, ACHIEVEMENTS
        eng_name = TRUCK_UPGRADES["engine"]["levels"][obj.db.engine_level or 0]["name"]
        trailer_name = TRUCK_UPGRADES["trailer"]["levels"][obj.db.trailer_level or 0]["name"]

        truckers.append({
            "handle": handle,
            "miles": obj.db.miles_driven or 0,
            "deliveries": obj.db.deliveries_completed or 0,
            "ontime": obj.db.deliveries_ontime or 0,
            "money": obj.db.money or 0,
            "total_income": obj.db.total_income or 0,
            "biggest_haul_weight": obj.db.biggest_haul_weight or 0,
            "biggest_haul_income": obj.db.biggest_haul_income or 0,
            "reputation": obj.db.reputation or 0,
            "home_city": obj.db.home_city or "",
            "engine": eng_name,
            "trailer": trailer_name,
            "achievements": list(obj.db.achievements or []),
            "truck_health": obj.db.truck_health if obj.db.truck_health is not None else 100,
        })

        # Build live position data
        pos = {"handle": handle, "online": online}
        driving_to = obj.db.driving_to
        driving_from = obj.db.driving_from
        if driving_to and driving_from:
            miles_left = obj.db.driving_miles_left or 0
            miles_total = obj.db.driving_miles_total or miles_left
            progress = max(0, min(1.0, 1.0 - (miles_left / miles_total))) if miles_total > 0 else 0
            pos["status"] = "driving"
            pos["from"] = driving_from
            pos["to"] = driving_to
            pos["highway"] = obj.db.driving_highway or ""
            pos["progress"] = round(progress, 2)
            pos["weather"] = obj.db.current_weather or "clear"
        else:
            # At a city or rest stop
            city_key = ""
            if obj.location and hasattr(obj.location, 'db'):
                city_key = obj.location.db.city_key or ""
            # If at a rest stop, try to figure out which cities it's between
            if not city_key and obj.location and hasattr(obj.location, 'db'):
                # Rest stop rooms store from_city/to_city
                city_key = obj.location.db.from_city or obj.location.db.to_city or ""
            # Check driving_from (last city they departed from, set even after arrival)
            if not city_key:
                city_key = obj.db.last_city or obj.db.home_city or ""
            pos["status"] = "stopped"
            pos["city"] = city_key
        live_positions.append(pos)

    truckers.sort(key=lambda x: x["miles"], reverse=True)

    # Build records
    records = {}
    if truckers:
        by_income = max(truckers, key=lambda x: x["total_income"])
        if by_income["total_income"] > 0:
            records["highest_earnings"] = {"handle": by_income["handle"], "value": by_income["total_income"]}

        by_miles = max(truckers, key=lambda x: x["miles"])
        if by_miles["miles"] > 0:
            records["most_miles"] = {"handle": by_miles["handle"], "value": by_miles["miles"]}

        by_weight = max(truckers, key=lambda x: x["biggest_haul_weight"])
        if by_weight["biggest_haul_weight"] > 0:
            records["heaviest_haul"] = {"handle": by_weight["handle"], "value": by_weight["biggest_haul_weight"]}

        by_haul_pay = max(truckers, key=lambda x: x["biggest_haul_income"])
        if by_haul_pay["biggest_haul_income"] > 0:
            records["highest_payout"] = {"handle": by_haul_pay["handle"], "value": by_haul_pay["biggest_haul_income"]}

    return {
        "truckers": truckers[:20],
        "records": records,
        "positions": live_positions,
    }


def main():
    scores = get_scores()
    output = json.dumps(scores, indent=2)

    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as f:
            f.write(output)
        print(f"Wrote {sys.argv[1]}: {len(scores['truckers'])} truckers")
    else:
        print(output)


if __name__ == "__main__":
    main()
