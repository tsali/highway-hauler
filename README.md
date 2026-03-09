# Highway Hauler

A multiplayer cross-country trucking MUD built on [Evennia 5.0.1](https://www.evennia.com/), designed to run behind a Mystic BBS rlogin bridge. Haul cargo across America, compete for contracts, upgrade your rig, and chat on the CB with other drivers.

Inspired by *Cross Country USA* (1985, Didatech Software).

**Play on BBS PEPSICOLA:**
- Telnet: `bbs.cultofjames.org` port `2023`
- TLS: `bbs.cultofjames.org` port `992`
- From the BBS main menu, press **D** for Doors, then **H** for Highway Hauler

## Overview

Players start as rookie truckers with a beat-up rig and $500. Pick up cargo contracts, plan routes across a network of US cities connected by real interstate highways, manage fuel and time, and earn money to upgrade your truck and unlock longer hauls.

## Game Systems

| System | Description |
|--------|-------------|
| **Contracts** | Pick up cargo at city terminals — each has origin, destination, cargo type, pay, and deadline |
| **Routing** | Navigate a network of ~50 US cities connected by interstate highways with real distances |
| **Driving** | Travel between cities in real-time (accelerated). Speed, fuel consumption, random events |
| **Fuel** | Manage your tank. Run dry on the highway and you're stuck until a tow |
| **Truck Upgrades** | Better engine (speed), bigger tank (range), larger trailer (cargo capacity), CB radio |
| **Economy** | Dynamic cargo prices. Supply/demand shifts. Bonus pay for on-time delivery |
| **Multiplayer** | See other drivers at stops and on highways. Compete for the same contracts |
| **CB Radio** | Global trucker chat channel. Warn about speed traps, share tips |
| **Weather** | Random weather events affect speed and fuel consumption |
| **Weigh Stations** | Random inspections. Overweight = fines. Keep your paperwork straight |
| **Trivia** | Geography trivia at rest stops for bonus cash |
| **Leaderboard** | Miles driven, deliveries completed, money earned, on-time percentage |

## Architecture

```
BBS User -> Mystic BBS (telnet:23) -> rlogin bridge (port 4043) -> Evennia (port 4020)
```

- **Framework**: Evennia 5.0.1 (Python 3.11, Django, Twisted)
- **Data storage**: Evennia AttributeProperty (no custom Django models)
- **Instance**: /opt/evennia/hauler/

## Commands

| Command | Description |
|---------|-------------|
| `look` | See current location, other drivers, available services |
| `contracts` | View available cargo contracts at current terminal |
| `accept <#>` | Accept a contract |
| `cargo` | View your current cargo manifest |
| `drive <city>` | Start driving to a connected city |
| `stop` | Pull over (if on highway) |
| `refuel` | Fill up at a gas station |
| `status` | Your truck stats, fuel, money, reputation |
| `upgrade` | View/buy truck upgrades at a truck stop |
| `map` | ASCII map of the interstate network |
| `cb <message>` | CB radio — broadcast to all drivers |
| `who` | See all online drivers and their locations |
| `scores` | Leaderboard |
| `trivia` | Answer a geography question for bonus cash (at rest stops) |
| `deliver` | Deliver cargo at destination terminal |
| `help` | Help topics |

## Development

```bash
cd /home/tsali/projects/highway-hauler
# Edit typeclasses/, commands/, world/
./deploy.sh   # Push to live instance
```

## Tech Stack

- Python 3.11
- Evennia 5.0.1 (Twisted + Django)
- Mystic BBS rlogin bridge
- systemd service management
