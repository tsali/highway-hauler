"""
Highway Hauler — Account typeclass.

BBS users connect via the rlogin bridge which auto-logs them in.
Their Evennia account is created on first login.
"""

from evennia.accounts.accounts import DefaultAccount, DefaultGuest
from evennia.utils import logger


class Account(DefaultAccount):
    """
    Account typeclass for BBS-connected truckers.

    On first login, AUTO_CREATE_CHARACTER_WITH_ACCOUNT creates a Trucker.
    The Trucker's at_post_puppet launches chargen if not yet completed.
    """

    def at_post_login(self, session=None, **kwargs):
        """Called after successful login."""
        super().at_post_login(session=session, **kwargs)

        if session and self.get_puppet(session):
            return

        chars = [c for c in self.characters if c.access(self, "puppet")]
        if not chars:
            logger.log_info(f"Account '{self.key}' has no characters; creating one.")
            from evennia.utils.search import search_tag
            start_rooms = search_tag("chargen_room", category="chargen")
            start_loc = start_rooms[0] if start_rooms else None

            char, errs = self.create_character(
                key=self.key,
                typeclass="typeclasses.characters.Trucker",
                location=start_loc,
                home=start_loc,
            )
            if char:
                try:
                    self.puppet_object(session, char)
                except RuntimeError as e:
                    logger.log_err(f"Could not puppet: {e}")
            else:
                logger.log_err(f"Character creation failed: {errs}")
            return

        char = chars[0]
        try:
            self.puppet_object(session, char)
        except RuntimeError as e:
            logger.log_err(f"Could not puppet '{char.key}': {e}")


class Guest(DefaultGuest):
    """Guest accounts — disabled."""
    pass
