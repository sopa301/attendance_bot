from enum import Enum

# Symbolic constants for the UI
PRESENT_SYMBOL = "✅"
ABSENT_SYMBOL = "❌"
CANCELLATION_SYMBOL = "🚫"

SIGN_UP_SYMBOL="✅"
DROP_OUT_SYMBOL="❌"

ACTIVE_SYMBOL = "🟢"
INACTIVE_SYMBOL = "🔴"

class Membership(Enum):
  REGULAR = 0
  NON_REGULAR = 1

  @classmethod
  def from_data_string(string):
    return Membership(int(string))
  
  def to_representation(self):
    return "Regular" if self == Membership.REGULAR else "Non-Regulars"
  
  def to_db_representation(self):
    return "regulars" if self == Membership.REGULAR else "non_regulars"

# "Ban"anas constants
ABSENT_POINTS = 3
LAST_MINUTE_CANCELLATION_POINTS = 1
BAN_THRESHOLD = 3
BAN_POINTS_ROLLOVER = True
BAN_DURATION_SESSIONS = 1
PENALISE_REGULARS = False
PENALISE_NON_REGULARS = True
PENALISE_STANDINS = False

# Logistics constants
MAX_PEOPLE_PER_SESSION = 24