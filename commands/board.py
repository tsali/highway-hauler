"""
Highway Hauler — City message board commands.

Each city has its own message board stored on the CityRoom.
Truckers can read, post, and erase their own messages.
"""

import time
from evennia.commands.command import Command
from typeclasses.rooms import CityRoom

MAX_MESSAGES = 20       # per city
MAX_MSG_LENGTH = 200    # characters per post


class CmdBoard(Command):
    """
    Read the city message board.

    Usage:
        board
        board erase <#>
    """

    key = "board"
    aliases = ["messages", "wall"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if not isinstance(caller.location, CityRoom):
            caller.msg("|rNo message board here. Try a city.|n")
            return

        room = caller.location
        city_data = room.db.city_data or {}
        city_name = city_data.get("name", "Unknown")

        args = self.args.strip()

        # Handle erase
        if args.lower().startswith("erase ") or args.lower().startswith("delete "):
            parts = args.split(None, 1)
            if len(parts) < 2:
                caller.msg("|wUsage: board erase <#>|n")
                return
            try:
                idx = int(parts[1]) - 1
            except ValueError:
                caller.msg("|rEnter a number.|n")
                return

            board = room.db.message_board or []
            if idx < 0 or idx >= len(board):
                caller.msg("|rInvalid message number.|n")
                return

            msg = board[idx]
            handle = caller.db.handle or caller.key
            if msg.get("author") != handle:
                caller.msg("|rYou can only erase your own messages.|n")
                return

            board.pop(idx)
            room.db.message_board = board
            caller.msg(f"|yMessage #{idx + 1} erased.|n")
            return

        # Display board
        board = room.db.message_board or []

        lines = [
            f"|w=== MESSAGE BOARD — {city_name} ===|n",
        ]

        if not board:
            lines.append("")
            lines.append("|xThe board is empty. Be the first to leave a message.|n")
        else:
            lines.append("")
            for i, msg in enumerate(board, 1):
                age = _format_age(msg.get("time", 0))
                lines.append(
                    f"  |y{i}|n. |c{msg.get('author', '???')}|n ({age}): "
                    f"|w{msg.get('text', '')}|n"
                )

        lines.append("")
        lines.append("|wType |ypost <message>|w to leave a message.|n")
        caller.msg("\n".join(lines))


class CmdPost(Command):
    """
    Post a message to the city board.

    Usage:
        post <message>
    """

    key = "post"
    aliases = ["scrawl", "write"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if not isinstance(caller.location, CityRoom):
            caller.msg("|rNo message board here. Try a city.|n")
            return

        if not self.args or not self.args.strip():
            caller.msg("|wUsage: post <message>|n")
            return

        text = self.args.strip()
        if len(text) > MAX_MSG_LENGTH:
            caller.msg(f"|rMessage too long ({len(text)}/{MAX_MSG_LENGTH} chars). Keep it short.|n")
            return

        room = caller.location
        board = room.db.message_board or []
        handle = caller.db.handle or caller.key
        city_data = room.db.city_data or {}
        city_name = city_data.get("name", "Unknown")

        entry = {
            "author": handle,
            "text": text,
            "time": time.time(),
        }

        board.append(entry)

        # Trim old messages if over limit
        if len(board) > MAX_MESSAGES:
            board = board[-MAX_MESSAGES:]

        room.db.message_board = board

        caller.msg(f"|gMessage posted to the {city_name} board.|n")

        # Notify others in the room
        for obj in room.contents:
            if obj != caller and hasattr(obj, 'msg'):
                caller_handle = handle
                obj.msg(f"|y[Board] {caller_handle} posted a new message.|n")


def _format_age(timestamp):
    """Format a timestamp as relative age string."""
    if not timestamp:
        return "unknown"
    elapsed = time.time() - timestamp
    if elapsed < 60:
        return "just now"
    elif elapsed < 3600:
        mins = int(elapsed / 60)
        return f"{mins}m ago"
    elif elapsed < 86400:
        hours = int(elapsed / 3600)
        return f"{hours}h ago"
    else:
        days = int(elapsed / 86400)
        return f"{days}d ago"
