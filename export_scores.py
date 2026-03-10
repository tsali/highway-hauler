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
    for obj in ObjectDB.objects.filter(db_typeclass_path__contains="characters.Trucker"):
        if not obj.db.chargen_complete:
            continue
        truckers.append({
            "handle": obj.db.handle or obj.key,
            "miles": obj.db.miles_driven or 0,
            "deliveries": obj.db.deliveries_completed or 0,
            "ontime": obj.db.deliveries_ontime or 0,
            "money": obj.db.money or 0,
            "total_income": obj.db.total_income or 0,
            "biggest_haul_weight": obj.db.biggest_haul_weight or 0,
            "biggest_haul_income": obj.db.biggest_haul_income or 0,
        })

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
