"""Constants used across the bot."""

from enum import Enum

# Symbolic constants for the UI
PRESENT_SYMBOL = "✅"
ABSENT_SYMBOL = "❌"
CANCELLATION_SYMBOL = "🚫"

SIGN_UP_SYMBOL = "✅"
DROP_OUT_SYMBOL = "❌"

ACTIVE_SYMBOL = "🟢"
INACTIVE_SYMBOL = "🔴"


class Membership(Enum):
    """Membership types for poll voters."""

    REGULAR = 0
    NON_REGULAR = 1

    @staticmethod
    def from_data_string(string):
        """From callback data from the telegram bot."""
        return Membership(int(string))

    def to_representation(self):
        """Returns a user-friendly string representation of the membership."""
        return "Regulars" if self == Membership.REGULAR else "Non-Regulars"

    def to_db_representation(self):
        """Returns the database representation of the membership."""
        return "regulars" if self == Membership.REGULAR else "non_regulars"


# "Ban"anas constants
PENALISE_REGULARS = False
PENALISE_NON_REGULARS = True

# Logistics constants
MAX_PEOPLE_PER_SESSION = 48
