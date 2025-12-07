"""Model for Attendance List."""

from typing import List, Self

from src.util import (
    ABSENT,
    LAST_MINUTE_CANCELLATION,
    MAX_PEOPLE_PER_SESSION,
    PENALISE_NON_REGULARS,
    PENALISE_REGULARS,
    PENALISE_STANDINS,
    Membership,
)

from .event_poll import EventPoll
from .person import Person


class AttendanceList:
    """Class representing an attendance list."""

    def __init__(self):
        self.id: str = None
        self.owner_id: str = None
        self.details: List[str] = []
        self.non_regulars: List[Person] = []
        self.regulars: List[Person] = []
        self.exco: list = []
        self.standins: List[Person] = []
        self.reserves: List[Person] = []

    def update_administrative_details(self, old_list: Self):
        """Updates administrative details from an old attendance list."""
        self.id = old_list.id
        self.owner_id = old_list.owner_id
        self.reserves = old_list.reserves

    def insert_owner_id(self, owner_id: str):
        """Inserts the owner ID for the attendance list."""
        self.owner_id = owner_id

    def to_dict(self):
        """Converts the AttendanceList object to a dictionary."""
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "details": self.details,
            "non_regulars": list(map(lambda x: x.to_dict(), self.non_regulars)),
            "regulars": list(map(lambda x: x.to_dict(), self.regulars)),
            "exco": self.exco,
            "standins": list(map(lambda x: x.to_dict(), self.standins)),
            "reserves": list(map(lambda x: x.to_dict(), self.reserves)),
        }

    def find_user_by_id(self, user_id: str):
        """Finds a user by their ID."""
        for lst in [self.non_regulars, self.regulars, self.standins]:
            for user in lst:
                if user.id == user_id:
                    return user
        raise ValueError("User not found with id: " + str(user_id))

    def get_category_and_index(self, user_id: str):
        """Gets the category and index of a user by their ID."""
        for user in self.non_regulars:
            if user.id == user_id:
                return user.membership.to_db_representation(), self.non_regulars.index(
                    user
                )
        for user in self.regulars:
            if user.id == user_id:
                return user.membership.to_db_representation(), self.regulars.index(user)
        for user in self.standins:
            if user.id == user_id:
                return "standins", self.standins.index(user)
        raise ValueError("User not found with id: " + str(user_id))

    def update_user_status(self, user_id: str, status: int):
        """Updates the status of the user with the given id."""
        user = self.find_user_by_id(user_id)
        user.status = status

    def get_title(self):
        """Gets the title of the attendance list."""
        return self.details[0]

    @staticmethod
    def from_dict(dct):
        """Creates an AttendanceList object from a dictionary."""
        attendance_list = AttendanceList()
        attendance_list.owner_id = dct["owner_id"]
        attendance_list.id = dct["id"]
        attendance_list.details = dct["details"]
        attendance_list.non_regulars = list(map(Person.from_dict, dct["non_regulars"]))
        attendance_list.regulars = list(map(Person.from_dict, dct["regulars"]))
        attendance_list.exco = dct["exco"]
        attendance_list.standins = list(map(Person.from_dict, dct["standins"]))
        attendance_list.reserves = (
            list(map(Person.from_dict, dct["reserves"])) if "reserves" in dct else []
        )
        return attendance_list

    def to_parsable_list(self):
        """Converts the attendance list to a parsable string format.
        Forms a pair with parse_list()."""
        output_list = []
        for line in self.details:
            output_list.append(line)
        output_list.append("")

        output_list.append("Non-Regulars")
        for i, tp in enumerate(self.non_regulars):
            output_list.append(f"{i+1}. {tp.name}")

        output_list.append("")

        output_list.append("Regulars")
        for i, tp in enumerate(self.regulars):
            output_list.append(f"{i+1}. {tp.name}")

        output_list.append("")

        output_list.append("Standins")
        for i, tp in enumerate(self.standins):
            output_list.append(f"{i+1}. {tp.name}")

        output_list.append("")

        output_list.append("Exco")
        for i, tp in enumerate(self.exco):
            output_list.append(tp)

        return "\n".join(output_list)

    @staticmethod
    def parse_list(message_text: str):
        """
        Parses the list in this format:
        Pickleball session (date)

        Non-Regulars
        1. ...
        2. ...

        Regulars
        1. ...
        2. ...

        Standins
        1. ...
        2. ...

        Exco
        (Name)
        """
        lines = message_text.split("\n")
        lines = [l.strip() for l in lines]
        attendance_list = AttendanceList()
        session_info = []
        last_non_empty_line = 0
        for i, s in enumerate(lines[: lines.index("Non-Regulars")]):
            if s != "":
                last_non_empty_line = i
            session_info.append(s)
        session_info = session_info[: last_non_empty_line + 1]
        attendance_list.details = session_info
        attendance_list.non_regulars = AttendanceList.parse_section(
            lines, "Non-Regulars", "Regulars", Membership.NON_REGULAR
        )
        attendance_list.regulars = AttendanceList.parse_section(
            lines, "Regulars", "Standins", Membership.REGULAR
        )
        attendance_list.standins = AttendanceList.parse_section(
            lines, "Standins", "Exco", Membership.NON_REGULAR
        )

        exco = []
        for s in lines[lines.index("Exco") + 1 :]:
            if s == "":
                break
            exco.append(s)
        attendance_list.exco = exco

        return attendance_list

    @staticmethod
    def parse_section(lines, divider1, divider2, membership) -> list:
        """Parses a section of the attendance list between two dividers."""
        lst = []
        for s in lines[lines.index(divider1) + 1 : lines.index(divider2)]:
            if s == "":
                continue
            name = s[s.index(".") + 1 :].strip()
            lst.append(Person(name, name, ABSENT, membership))
        return lst

    def insert_id(self, new_id: str) -> None:
        """Inserts the ID for the attendance list."""
        self.id = new_id

    @staticmethod
    def from_poll(poll: EventPoll, owner_id: str):
        """Creates an AttendanceList object from an EventPoll and owner ID."""
        attendance_list = AttendanceList()
        attendance_list.owner_id = owner_id
        attendance_list.details = [poll.get_title(), poll.details]
        attendance_list.regulars = list(
            map(
                lambda name: Person(name, name, ABSENT, Membership.REGULAR),
                poll.regulars,
            )
        )[: poll.allocations[1]]
        num_regulars = len(attendance_list.regulars)
        temp = list(
            map(
                lambda name: Person(name, name, ABSENT, Membership.NON_REGULAR),
                poll.non_regulars,
            )
        )
        attendance_list.non_regulars = temp[
            : max(poll.allocations[0], MAX_PEOPLE_PER_SESSION - num_regulars)
        ]
        attendance_list.reserves = temp[
            max(poll.allocations[0], MAX_PEOPLE_PER_SESSION - num_regulars) :
        ]

        return attendance_list

    @staticmethod
    def get_non_present_penalisable_names_from_list(
        lst, condition, absent_list, cancelled_list
    ):
        """Gets non-present penalisable names from a list based on a condition."""
        if not condition:
            return absent_list, cancelled_list
        for person in lst:
            if person.status == ABSENT:
                absent_list.append(person.id)
            elif person.status == LAST_MINUTE_CANCELLATION:
                cancelled_list.append(person.id)
        return absent_list, cancelled_list

    def get_non_present_penalisable_names(self):
        """Gets non-present penalisable names from the attendance list."""
        absent = []
        cancelled = []
        absent, cancelled = self.get_non_present_penalisable_names_from_list(
            self.non_regulars, PENALISE_NON_REGULARS, absent, cancelled
        )
        absent, cancelled = self.get_non_present_penalisable_names_from_list(
            self.regulars, PENALISE_REGULARS, absent, cancelled
        )
        absent, cancelled = self.get_non_present_penalisable_names_from_list(
            self.standins, PENALISE_STANDINS, absent, cancelled
        )
        return absent, cancelled

    def get_all_player_names(self):
        """Gets all player names from the attendance list."""
        return (
            list(map(lambda x: x.id, self.non_regulars))
            + list(map(lambda x: x.id, self.regulars))
            + list(map(lambda x: x.id, self.standins))
        )

    def remove_banned_people(self, banned_people):
        """Removes banned people from the attendance list."""
        removed_non_regulars_count = 0
        removed_regulars_count = 0
        removed_standins_count = 0
        for person in banned_people:
            found = False
            for category in [self.non_regulars, self.regulars, self.standins]:
                for i, tp in enumerate(category):
                    if tp.id == person:
                        found = True
                        category.pop(i)
                        if category == self.non_regulars:
                            removed_non_regulars_count += 1
                        elif category == self.regulars:
                            removed_regulars_count += 1
                        elif category == self.standins:
                            removed_standins_count += 1
                        break
                if found:
                    break
            if not found:
                raise ValueError("Person not found in attendance list: " + person)
        return (
            removed_non_regulars_count,
            removed_regulars_count,
            removed_standins_count,
        )

    def replenish_numbers(self):
        """Replenishes the attendance list from reserves if there are vacancies."""
        # do only for non regulars for now
        num_total = len(self.non_regulars) + len(self.regulars) + len(self.standins)
        num_to_replace = MAX_PEOPLE_PER_SESSION - num_total
        if num_to_replace <= 0:
            return
        self.non_regulars.extend(self.reserves[:num_to_replace])
        self.reserves = self.reserves[num_to_replace:]
