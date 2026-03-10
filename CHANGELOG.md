# Changelog — Highway Hauler

## v0.2a — 2026-03-09

### Added
- Dynamic weather system with region-appropriate weather (rain, snow, fog, storm)
- Storm weather type: 50% speed reduction, +30% fuel burn, wind/debris/hail events
- Trucker needs system: hunger, bladder, fatigue with gameplay consequences
- Soiling mechanic: bladder at 100 triggers accident with speed -15%, no contracts, $75 cleanup
- DOT hours-of-service tracking: mandatory rest after 16 hours continuous driving
- Fatigue effects: microsleep swerves, missed exits, crash risk at 90+
- 95 rest areas across all major highway segments (expanded from 15)
- Diner system at rest stops with menu choices and lactose intolerance mechanic
- Restroom and bunk/sleep commands at rest stops and cities
- GPS Navigation upgrade (3 levels): auto-routing with reliability chance
- Radar Detector upgrade (4 levels): Cobra, Uniden, Valentine One, Escort MAX 360c
- Speed control: `speed <mph>` command to set driving speed, 65 mph posted limit
- Cop encounters (4% per tick): speeding tickets, fatigue stops, routine patrols, equipment checks
- Radar detector warns of cops and avoids encounters based on detection %
- City message boards: per-city bulletin boards with `board` and `post` commands
- NPC trucker board messages: 35 handles, 50+ templates, posts every ~3 minutes
- Messages reference real highways, cities, and sometimes real player handles
- Weigh station overhaul: detailed weight display, scaled fines, repeat offender tracking
- High score tracking: biggest haul weight, biggest haul income, lifetime earnings
- Live map webpage (bbs.cultofjames.org/hauler.html) with Leaflet + CartoDB dark tiles
- Live trucker positions on map: yellow (driving), green (stopped), grey (offline)
- Scores export pipeline: export_scores.py → scores.json with position data

### Changed
- Weather system separated from random events into dedicated tick
- Weigh stations separated from random events into dedicated tick
- Speed trap replaced by comprehensive cop encounter system
- Upgrade shop compacted: shows current → next per type instead of all levels
- Random events pool rebalanced: road hazards, wildlife, construction
- Engine status shows max speed and current set speed

### Fixed
- `bunks`/`bunk` aliases added to sleep command
- Internal commands hidden from help (`auto_help = False`)
- Upgrade shop fits on BBS terminal screen

## v0.1a — 2026-03-09

### Added
- Core game framework on Evennia 5.0.1
- 50 US cities connected by interstate highway network with real distances
- Cargo contract system: accept, haul, deliver with deadlines and pay
- Truck status: fuel tank, speed, cargo capacity, mileage
- Fuel management: consumption based on distance, refuel at gas stations
- Driving system: real-time travel between connected cities
- Economy: earn money from deliveries, spend on fuel and upgrades
- 4 truck upgrades: engine (speed), fuel tank (range), trailer (capacity), CB radio
- CB radio global chat channel
- Multiplayer: see other drivers at stops and on highways
- ASCII interstate map
- Leaderboard: miles, deliveries, money, on-time %
- Geography trivia at rest stops for bonus cash
- Weather events: rain, snow, fog (affect speed/fuel)
- Weigh station random inspections
- Lot lizard encounters at truck stops (robbery, STD, bonus outcomes)
- Highway gang encounters on desert stretches (I-10, I-15, I-40, I-8)
- Fight or flee mechanics for gang encounters
- Contract bonus modifier from encounters
- BBS rlogin bridge for Mystic BBS integration
- systemd services for auto-start
