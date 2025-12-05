from model.event_poll import EventPoll
from model.person import Person
from util.constants import *
from util.texts import ABSENT, LAST_MINUTE_CANCELLATION


class AttendanceList:
    def __init__(self):
        self.id = None
        self.owner_id = None
        self.details = []
        self.non_regulars = []
        self.regulars = []
        self.exco = []
        self.standins = []
        self.reserves = []

    def update_administrative_details(self, old_list):
        self.id = old_list.id
        self.owner_id = old_list.owner_id
        self.reserves = old_list.reserves

    def insert_owner_id(self, owner_id):
        self.owner_id = owner_id

    def to_dict(self):
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

    def find_user_by_id(self, id: str):
        for user in self.non_regulars:
            if user.id == id:
                return user
        for user in self.regulars:
            if user.id == id:
                return user
        for user in self.standins:
            if user.id == id:
                return user
        raise ValueError("User not found with id: " + str(id))

    def get_category_and_index(self, user_id):
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

    def update_user_status(self, id: int, status: int):
        user = self.find_user_by_id(id)
        user.status = status

    def get_title(self):
        return self.details[0]

    @staticmethod
    def from_dict(dct):
        attendance_list = AttendanceList()
        attendance_list.owner_id = dct["owner_id"]
        attendance_list.id = dct["id"]
        attendance_list.details = dct["details"]
        attendance_list.non_regulars = list(
            map(lambda x: Person.from_dict(x), dct["non_regulars"])
        )
        attendance_list.regulars = list(
            map(lambda x: Person.from_dict(x), dct["regulars"])
        )
        attendance_list.exco = dct["exco"]
        attendance_list.standins = list(
            map(lambda x: Person.from_dict(x), dct["standins"])
        )
        attendance_list.reserves = (
            list(map(lambda x: Person.from_dict(x), dct["reserves"]))
            if "reserves" in dct
            else []
        )
        return attendance_list

    def to_parsable_list(self):
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
        lst = []
        for s in lines[lines.index(divider1) + 1 : lines.index(divider2)]:
            if s == "":
                continue
            name = s[s.index(".") + 1 :].strip()
            lst.append(Person(name, name, ABSENT, membership))
        return lst

    def insert_id(self, new_id: str) -> None:
        self.id = new_id

    @staticmethod
    def from_poll(poll: EventPoll, owner_id: str):
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
        if not condition:
            return absent_list, cancelled_list
        for person in lst:
            if person.status == ABSENT:
                absent_list.append(person.id)
            elif person.status == LAST_MINUTE_CANCELLATION:
                cancelled_list.append(person.id)
        return absent_list, cancelled_list

    def get_non_present_penalisable_names(self):
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
        return (
            list(map(lambda x: x.id, self.non_regulars))
            + list(map(lambda x: x.id, self.regulars))
            + list(map(lambda x: x.id, self.standins))
        )

    def remove_banned_people(self, banned_people):
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
        # do only for non regulars for now
        num_total = len(self.non_regulars) + len(self.regulars) + len(self.standins)
        num_to_replace = MAX_PEOPLE_PER_SESSION - num_total
        if num_to_replace <= 0:
            return
        self.non_regulars.extend(self.reserves[:num_to_replace])
        self.reserves = self.reserves[num_to_replace:]
