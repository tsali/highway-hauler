"""
Evennia settings file — Highway Hauler.
"""

from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

SERVERNAME = "Highway Hauler"
GAME_VERSION = "v0.1a"

# Ports — distinct from Kayfabe (4000/4001/4006)
TELNET_PORTS = [4020]
WEBSERVER_PORTS = [(4021, 4025)]
WEBSOCKET_CLIENT_PORT = 4022
AMP_PORT = 4026

# Allow new accounts via connect command
NEW_PLAYER_PERMISSIONS = "Player"

# Idle timeout (seconds) — 1 hour
IDLE_TIMEOUT = 3600

# Shared secret password used by the rlogin bridge
BBS_BRIDGE_PASSWORD = "pepsicola_bbs_secret_2026"

# Typeclasses
BASE_ACCOUNT_TYPECLASS = "typeclasses.accounts.Account"
BASE_CHARACTER_TYPECLASS = "typeclasses.characters.Trucker"
BASE_ROOM_TYPECLASS = "typeclasses.rooms.Room"
BASE_OBJECT_TYPECLASS = "typeclasses.objects.Object"
BASE_EXIT_TYPECLASS = "typeclasses.exits.Exit"
BASE_CHANNEL_TYPECLASS = "typeclasses.channels.Channel"
BASE_SCRIPT_TYPECLASS = "typeclasses.scripts.Script"

# Cmdsets
CMDSET_CHARACTER = "commands.default_cmdsets.CharacterCmdSet"
CMDSET_ACCOUNT = "commands.default_cmdsets.AccountCmdSet"
CMDSET_UNLOGGEDIN = "commands.default_cmdsets.UnloggedinCmdSet"
CMDSET_SESSION = "commands.default_cmdsets.SessionCmdSet"

# Don't auto-create character — Account.at_post_login handles it
# so the character starts in the chargen room, not Limbo
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
AUTO_PUPPET_ON_LOGIN = True
MAX_NR_CHARACTERS = 1

# Disable login throttling — local-only behind BBS bridge
LOGIN_THROTTLE_LIMIT = None
LOGIN_THROTTLE_TIMEOUT = None
CREATION_THROTTLE_LIMIT = None
CREATION_THROTTLE_TIMEOUT = None

# Connection screen
CONNECTION_SCREEN_MODULE = "server.conf.connection_screens"

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    pass
