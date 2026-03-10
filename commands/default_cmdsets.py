"""
Highway Hauler — Default command sets.
"""

from evennia.commands.default.cmdset_character import CharacterCmdSet as BaseCharacterCmdSet
from evennia.commands.default.cmdset_account import AccountCmdSet as BaseAccountCmdSet
from evennia.commands.default.cmdset_session import SessionCmdSet as BaseSessionCmdSet
from evennia.commands.default.cmdset_unloggedin import UnloggedinCmdSet as BaseUnloggedinCmdSet

from commands.driving import CmdDrive, CmdRefuel, CmdStop, CmdMap, CmdSpeed
from commands.contracts import CmdContracts, CmdAccept, CmdCargo, CmdDeliver
from commands.trucker import (
    CmdStatus, CmdUpgrade, CmdCB, CmdWho, CmdScores, CmdTrivia, CmdTriviaAnswer,
)
from commands.encounters import CmdLotLizardResponse, CmdGangResponse
from commands.needs import CmdEat, CmdDinerChoice, CmdRestroom, CmdSleep, CmdNoInput, CmdNoMatch
from commands.board import CmdBoard, CmdPost


class CharacterCmdSet(BaseCharacterCmdSet):
    """Command set for in-game characters (truckers)."""

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()

        # Driving
        self.add(CmdDrive())
        self.add(CmdRefuel())
        self.add(CmdStop())
        self.add(CmdMap())
        self.add(CmdSpeed())

        # Contracts
        self.add(CmdContracts())
        self.add(CmdAccept())
        self.add(CmdCargo())
        self.add(CmdDeliver())

        # Trucker utilities
        self.add(CmdStatus())
        self.add(CmdUpgrade())
        self.add(CmdCB())
        self.add(CmdWho())
        self.add(CmdScores())
        self.add(CmdTrivia())
        self.add(CmdTriviaAnswer())

        # Encounters
        self.add(CmdLotLizardResponse())
        self.add(CmdGangResponse())

        # Trucker needs
        self.add(CmdEat())
        self.add(CmdDinerChoice())
        self.add(CmdRestroom())
        self.add(CmdSleep())

        # City message board
        self.add(CmdBoard())
        self.add(CmdPost())

        # System commands
        self.add(CmdNoInput())
        self.add(CmdNoMatch())


class AccountCmdSet(BaseAccountCmdSet):
    key = "DefaultAccount"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()


class UnloggedinCmdSet(BaseUnloggedinCmdSet):
    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()


class SessionCmdSet(BaseSessionCmdSet):
    key = "DefaultSession"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
