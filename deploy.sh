#!/bin/bash
# Highway Hauler — deploy to live instance
# Copies typeclasses, commands, world, conf to /opt/evennia/hauler/
# and restarts the Evennia instance.

set -e

LIVE_DIR="/opt/evennia/hauler"
SRC_DIR="/home/tsali/projects/highway-hauler"

echo "=== Highway Hauler Deploy ==="

# Sync game code
for dir in typeclasses commands world bbs_bridge; do
    echo "Syncing $dir..."
    rsync -av --delete "$SRC_DIR/$dir/" "$LIVE_DIR/$dir/"
done

# Sync conf files (don't overwrite secret_settings)
echo "Syncing conf..."
for f in settings.py connection_screens.py at_initial_setup.py at_server_startstop.py __init__.py; do
    if [ -f "$SRC_DIR/conf/$f" ]; then
        cp "$SRC_DIR/conf/$f" "$LIVE_DIR/server/conf/$f"
    fi
done

echo "Reloading Evennia..."
cd "$LIVE_DIR"
source /opt/evennia/venv/bin/activate
evennia reload

echo "=== Deploy complete ==="
