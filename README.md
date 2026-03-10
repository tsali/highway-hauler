# Highway Hauler

A multiplayer cross-country trucking MUD built on [Evennia 5.0.1](https://www.evennia.com/), designed to run behind a Mystic BBS rlogin bridge. Haul cargo across America, compete for contracts, upgrade your rig, and chat on the CB with other drivers.

Inspired by *Cross Country USA* (1985, Didatech Software).

**Play on BBS PEPSICOLA:**
- Telnet: `bbs.cultofjames.org` port `2023`
- TLS: `bbs.cultofjames.org` port `992`
- From the BBS main menu, press **D** for Doors, then **H** for Highway Hauler
- Live map & scores: [bbs.cultofjames.org/hauler.html](https://bbs.cultofjames.org/hauler.html)

## Overview

Players start as rookie truckers with a beat-up rig and $500. Pick up cargo contracts, plan routes across a network of 50 US cities connected by real interstate highways, manage fuel and time, deal with the realities of life on the road, and earn money to upgrade your truck and unlock longer hauls.

## Game Systems

| System | Description |
|--------|-------------|
| **Contracts** | Pick up cargo at city terminals — each has origin, destination, cargo type, weight, pay, urgency, and deadline |
| **Routing** | Navigate 50 US cities connected by interstate highways with real distances |
| **Driving** | Travel between cities in real-time (accelerated). Speed, fuel, weather, random events |
| **Speed Control** | Set your speed from 10 mph to your engine's max. Posted limit is 65 mph — go faster at your own risk |
| **Fuel** | Manage your tank. Heavier loads and bad weather burn more fuel. Run dry and you're paying for a tow |
| **Truck Upgrades** | 6 upgrade categories with multiple tiers each (see below) |
| **Economy** | Cargo pay scales with distance, weight, and urgency. On-time bonus, late penalty |
| **Trucker Needs** | Hunger, bladder, and fatigue build while driving. Ignore them at your peril |
| **Weather** | Dynamic regional weather: clear, rain, snow, fog, storm. Affects speed and fuel consumption |
| **Cops & Radar** | Speed traps, fatigue stops, routine patrols. Radar detector warns you before they see you |
| **Weigh Stations** | Random inspections with detailed weight checks. Scaled fines for overweight. Repeat offenders flagged |
| **Truck Health** | Truck body, tires, brakes, and oil wear over time. Breakdowns if neglected. Repair at stops |
| **Rest Areas** | 95 truck stops along major highways. Refuel, eat, sleep, repair, bathroom wall graffiti |
| **Encounters** | Lot lizards at truck stops, highway gangs on desert stretches |
| **Message Boards** | City boards for trucker tips; rest stop bathroom walls for shady graffiti and lot lizard reviews |
| **Achievements** | 30 achievements announced by Saint Christopher on CB radio |
| **GPS Navigation** | Auto-route planning with reliability based on upgrade level |
| **DOT Compliance** | Hours-of-service tracking. Drive too long and DOT shuts you down |
| **Multiplayer** | See other drivers at stops and on highways. CB radio chat. Compete on leaderboards |
| **Live Map** | Web page with real-time trucker positions on a Leaflet/CartoDB map |
| **Leaderboard** | Miles driven, deliveries, money earned, on-time %, biggest haul |

## Truck Upgrades

| Category | Levels | Effect |
|----------|--------|--------|
| **Engine** | Stock 4-Cyl (45 mph) through Supercharged V8 (85 mph) | Top speed |
| **Fuel Tank** | 50 gal through 200 gal Transcontinental | Range between fill-ups |
| **Trailer** | 20ft Flatbed (15,000 lbs) through 53ft Double (60,000 lbs) | Cargo capacity |
| **CB Radio** | None or Cobra 29 LTD | Global trucker chat |
| **GPS** | Paper Map through Trucker's GPS Pro (95% reliable) | Auto-routing |
| **Radar Detector** | None through Escort MAX 360c (92% detection) | Cop avoidance |

## Commands

### Navigation & Driving
| Command | Description |
|---------|-------------|
| `drive <city>` | Start driving to a connected city |
| `stop` | Pull over at a rest area or the shoulder |
| `speed` / `speed <mph>` / `speed max` | View or set driving speed (limit: 65 mph) |
| `map` / `map <region>` / `map national` | ASCII interstate map |
| `look` | See current location, services, other drivers |

### Cargo & Money
| Command | Description |
|---------|-------------|
| `contracts` | View available cargo contracts at current terminal |
| `accept <#>` | Accept a contract |
| `cargo` | View your current cargo manifest |
| `deliver` | Deliver cargo at destination city |
| `refuel` | Fill up at a gas station |
| `upgrade` / `upgrade <type>` | View or buy truck upgrades (engine, tank, trailer, cb, gps, radar) |
| `repair` / `repair <part>` / `repair all` | Fix truck body, tires, brakes, or change oil |

### Trucker Life
| Command | Description |
|---------|-------------|
| `eat` | Eat at a diner (reduces hunger) |
| `restroom` | Use the restroom (reduces bladder, cleans up if soiled) |
| `sleep` / `bunks` | Sleep at bunks (reduces fatigue, resets driving hours) |
| `status` | Full truck and trucker status display |
| `board` / `board erase <#>` | Read or manage city message board |
| `post <message>` | Post to the city message board |

### Social
| Command | Description |
|---------|-------------|
| `cb <message>` | CB radio — broadcast to all drivers |
| `who` | See all online drivers and their locations |
| `scores` | Leaderboard |
| `trivia` | Geography trivia for bonus cash (at cities) |

## Roadmap

### Near-Term
- **Convoy system** — Form convoys with other truckers for XP/pay bonuses and shared CB channel
- **Seasonal events** — Holiday cargo (Christmas trees in December, fireworks in July) with bonus pay
- **Truck customization** — Paint jobs, hood ornaments, and vanity items (cosmetic only)
- **Trucker rivalries** — Challenge other drivers to race between cities, winner takes a pot
- **Radio stations** — Tune in to regional music/talk while driving (flavor text variety)
- **Black market cargo** — High-risk, high-pay illegal loads with DOT inspection consequences

### Mid-Term
- **Fuel price fluctuation** — Gas prices vary by region and time, rewarding route planning
- **Company system** — Form trucking companies, shared garage, fleet leaderboard
- **Cargo auctions** — Bid against other truckers for premium contracts at major hubs
- **Truck breakdowns v2** — Tow truck service, roadside repair kits, AAA membership upgrade
- **NPC trucker encounters** — Meet AI truckers on the road with trade/chat/race interactions

### Expansion 1: O Canada
- **30+ Canadian cities** from Vancouver to Halifax connected by the Trans-Canada Highway
- Cross the border at ports of entry (Detroit-Windsor, Buffalo-Niagara, etc.)
- Customs inspections with paperwork delays and contraband checks
- Canadian weather: blizzards, black ice, moose crossings
- New cargo types: lumber, maple syrup, oil sands equipment, hockey gear
- Canadian-specific achievements: "True North", "Ice Road Trucker", "Border Hopper"
- Bilingual road signs in Quebec (flavor text)

### Expansion 2: South of the Border
- **Mexico and Central America** — 20+ cities from Tijuana to Panama City
- Border crossings with cartel encounter risk and bribe mechanics
- New hazards: cartel roadblocks, corrupt checkpoints, jungle washouts
- Cargo types: coffee, bananas, tequila, electronics (maquiladora), exotic animals
- Vehicle restrictions: some roads require smaller trucks
- Achievements: "Border Runner", "Pan-American", "Cartel Survivor", "Coffee Baron"

### Expansion 3: South America
- **15+ major cities** from Bogota to Buenos Aires
- The Pan-American Highway and the Darien Gap (ferry crossing required)
- Andes mountain passes with altitude sickness and rockslide events
- Amazon basin routes with river ferry crossings and monsoon season
- Cargo types: emeralds, cocaine (legal pharmaceutical grade), beef, lithium, copper
- Achievements: "Andes Ascender", "Amazon Explorer", "Gaucho", "Continental Trucker"

## Architecture

```
BBS User -> Mystic BBS (telnet:23) -> rlogin bridge (port 4043) -> Evennia (port 4020)
```

- **Framework**: Evennia 5.0.1 (Python 3.11, Django, Twisted)
- **Data storage**: Evennia AttributeProperty (no custom Django models)
- **Instance**: /opt/evennia/hauler/
- **Live map**: Static HTML + Leaflet.js, served from bbs.cultofjames.org/hauler.html
- **Score pipeline**: export_scores.py (Evennia ORM -> JSON) -> bbs-scores.py -> Synology web server

## Development

```bash
cd /home/tsali/projects/highway-hauler
# Edit typeclasses/, commands/, world/
./deploy.sh   # Rsync to live instance + evennia reload
```

## Tech Stack

- Python 3.11
- Evennia 5.0.1 (Twisted + Django)
- Mystic BBS rlogin bridge
- Leaflet.js + CartoDB dark tiles (live map)
- systemd service management
