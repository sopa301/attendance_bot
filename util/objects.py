from enum import Enum
from datetime import datetime

from util.texts import escape_markdown_characters, generate_status_string, ABSENT, LAST_MINUTE_CANCELLATION
from util.constants import *

class PollType(Enum):
  WEEKLY = 0
  ADHOC = 1

# TODO: figure out how to handle old poll messages when the poll group is deleted
# also handle the updating of all messages when a poll is updated
# also handle the updating of all messages after the week passes
class EventPoll():
  def __init__(self, start_time, end_time, title, details, allocations):
    self.id = None
    self.start_time = start_time # start time of event
    self.end_time = end_time
    self.regulars = []
    self.non_regulars = []
    self.title = title
    self.details = details
    self.type = PollType.WEEKLY
    self.allocations = allocations
    self.poll_group_id = None

  def to_dict(self):
    return {
      "id": self.id,
      "start_time": self.start_time,
      "end_time": self.end_time,
      "regulars": self.regulars,
      "non_regulars": self.non_regulars,
      "title": self.title,
      "details": self.details,
      "type": self.type.value,
      "allocations": self.allocations,
      "poll_group_id": self.poll_group_id
    }
  
  @staticmethod
  def format_iso_for_user(iso_dt: str):
    dt = datetime.fromisoformat(iso_dt)
    return dt.strftime("%d %B %y, %I:%M%p").lower().lstrip('0')

  @staticmethod
  def from_dict(dct):
    poll = EventPoll(dct["start_time"], dct["end_time"], dct["title"], dct["details"], dct["allocations"])
    poll.id = dct["id"]
    poll.regulars = dct["regulars"]
    poll.non_regulars = dct["non_regulars"]
    poll.type = PollType(dct["type"])
    poll.poll_group_id = dct["poll_group_id"]
    return poll
  
  def insert_id(self, id):
    self.id = id

# TODO: create the aggregated poll results in the db as well for efficient access.
# remember to use transactions to ensure that the poll results are consistent
class PollGroup():
  def __init__(self, owner_id, name):
    self.polls_ids = []
    self.owner_id = owner_id
    self.id = None
    self.name = name
    self.number_of_distinct_groups = 2

  def to_dict(self):
    return {
      "id": self.id,
      "owner_id": self.owner_id,
      "name": self.name,
      "polls_ids": self.polls_ids
    }
  
  def insert_id(self, id):
    self.id = id

  def insert_poll_ids(self, poll_ids):
    self.polls_ids = poll_ids

  def get_poll_ids(self):
    return self.polls_ids
  
  @staticmethod
  def from_dict(dct):
    group = PollGroup(dct["owner_id"], dct["name"])
    group.id = dct["id"]
    group.polls_ids = dct["polls_ids"]
    group.number_of_distinct_groups = 2
    return group
  
  def generate_overview_text(self, polls: list) -> str:
    return "Non Regulars:\n" + self.generate_poll_group_text(polls, "nr") + "\n\nRegulars\n" + self.generate_poll_group_text(polls, "r")

  def generate_poll_group_text(self, polls: list, membership: str) -> str:
    poll_body = [self.name + "\n"]
    for i, poll in enumerate(polls):
        st = EventPoll.format_iso_for_user(poll.start_time)
        et = EventPoll.format_iso_for_user(poll.end_time)
        # print("st: " + st)
        # print("et: " + et)
        poll_body.append(f"{poll.title}\n{poll.details}\n{st} - {et}\n")
        if membership == "nr":
            lst = poll.non_regulars
        elif membership == "r":
            lst = poll.regulars
        else:
            raise ValueError("Invalid poll type: " + membership)
        for j, person in enumerate(lst):
            poll_body.append(f"{j+1}. {person}")
        if i < len(polls) - 1:
          poll_body.append("\n")
    poll_body = "\n".join(poll_body)
    return poll_body

class AttendanceList():
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
      "non_regulars": self.non_regulars,
      "regulars": self.regulars,
      "exco": self.exco,
      "standins": self.standins,
      "reserves": self.reserves
    }
  
  def find_user_by_id(self, id: str):
    for user in self.non_regulars:
      if user["id"] == id:
        return user
    for user in self.regulars:
      if user["id"] == id:
        return user
    for user in self.standins:
      if user["id"] == id:
        return user
    raise ValueError("User not found with id: " + str(id))
  
  def get_category_and_index(self, user_id):
    for user in self.non_regulars:
      if user["id"] == user_id:
        return "non_regulars", self.non_regulars.index(user)
    for user in self.regulars:
      if user["id"] == user_id:
        return "regulars", self.regulars.index(user)
    for user in self.standins:
      if user["id"] == user_id:
        return "standins", self.standins.index(user)
    raise ValueError("User not found with id: " + str(user_id))
  
  def update_user_status(self, id: int, status: int):
    user = self.find_user_by_id(id)
    user["status"] = status

  def generate_summary_text(self):
    output_list = []
    for line in self.details:
        output_list.append(escape_markdown_characters(line))
    output_list.append("")

    output_list.append("Non regulars")
    for i, tp in enumerate(self.non_regulars):
      output_list.append(generate_status_string(tp["status"], tp["name"], i+1))

    output_list.append("")

    output_list.append("Regulars")
    for i, tp in enumerate(self.regulars):
      output_list.append(generate_status_string(tp["status"], tp["name"], i+1))

    if len(self.standins) > 0:
      output_list.append("")

      output_list.append("Standins")
      for i, tp in enumerate(self.standins):
        output_list.append(generate_status_string(tp["status"], tp["name"], i+1))

    return "\n".join(output_list)

  @staticmethod
  def from_dict(dct):
    attendance_list = AttendanceList()
    attendance_list.owner_id = dct["owner_id"]
    attendance_list.id = dct["id"]
    attendance_list.details = dct["details"]
    attendance_list.non_regulars = dct["non_regulars"]
    attendance_list.regulars = dct["regulars"]
    attendance_list.exco = dct["exco"]
    attendance_list.standins = dct["standins"]
    attendance_list.reserves = dct["reserves"] if "reserves" in dct else []
    return attendance_list

  def to_parsable_list(self):
    output_list = []
    for line in self.details:
        output_list.append(line)
    output_list.append("")

    output_list.append("Non regulars")
    for i, tp in enumerate(self.non_regulars):
      output_list.append(f"{i+1}. {tp['name']}")

    output_list.append("")

    output_list.append("Regulars")
    for i, tp in enumerate(self.regulars):
      output_list.append(f"{i+1}. {tp['name']}")

    output_list.append("")

    output_list.append("Standins")
    for i, tp in enumerate(self.standins):
      output_list.append(f"{i+1}. {tp['name']}")

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

    Non regulars
    1. ...
    2. ...

    Regulars
    1. ...
    2. ...

    Exco
    (Name)
    """
    lines = message_text.split("\n")
    attendance_list = AttendanceList()
    session_info = []
    last_non_empty_line = 0
    for i, s in enumerate(lines[:lines.index("Non regulars")]):
        if s != "":
            last_non_empty_line = i
        session_info.append(s)
    session_info = session_info[:last_non_empty_line+1]
    attendance_list.details = session_info
    attendance_list.non_regulars = AttendanceList.parse_section(lines, "Non regulars", "Regulars", "nr")
    attendance_list.regulars = AttendanceList.parse_section(lines, "Regulars", "Standins", "r")
    attendance_list.standins = AttendanceList.parse_section(lines, "Standins", "Exco", "nr")

    exco = []
    for s in lines[lines.index("Exco")+1:]:
        if s == "":
            break
        exco.append(s)
    attendance_list.exco = exco

    return attendance_list
  
  @staticmethod
  def parse_section(lines, divider1, divider2, membership) -> list:
    lst = []
    for s in lines[lines.index(divider1)+1:lines.index(divider2)]:
      if s == "":
        continue
      name = s[s.index('.')+1:].strip()
      lst.append({"name": name, "status": ABSENT, "id": name, "membership": membership})
    return lst

  def insert_id(self, id):
    self.id = id

  @staticmethod
  def from_poll(poll: EventPoll):
    attendance_list = AttendanceList()
    attendance_list.details = [poll.title, poll.details]
    attendance_list.regulars = list(map(lambda x: {"name": x, "status": ABSENT, "id": x, "membership": "r"}, poll.regulars))[:poll.allocations[1]]
    num_regulars = len(attendance_list.regulars)
    temp = list(map(lambda x: {"name": x, "status": ABSENT, "id": x, "membership": "nr"}, poll.non_regulars))
    attendance_list.non_regulars = temp[:max(poll.allocations[0], MAX_PEOPLE_PER_SESSION - num_regulars)]
    attendance_list.reserves = temp[max(poll.allocations[0], MAX_PEOPLE_PER_SESSION - num_regulars):]

    return attendance_list
  
  def get_non_present_penalisable_names(self):
    absent = []
    cancelled = []
    if PENALISE_NON_REGULARS:
      for person in self.non_regulars:
        if person["status"] == ABSENT:
          absent.append(person["id"])
        elif person["status"] == LAST_MINUTE_CANCELLATION:
          cancelled.append(person["id"])
    if PENALISE_REGULARS:
      for person in self.regulars:
        if person["status"] == ABSENT:
          absent.append(person["id"])
        elif person["status"] == LAST_MINUTE_CANCELLATION:
          cancelled.append(person["id"])
    if PENALISE_STANDINS:
      for person in self.standins:
        if person["status"] == ABSENT:
          absent.append(person["id"])
        elif person["status"] == LAST_MINUTE_CANCELLATION:
          cancelled.append(person["id"])
    return absent, cancelled
  
  def get_all_player_names(self):
    return list(map(lambda x: x["id"], self.non_regulars)) \
      + list(map(lambda x: x["id"], self.regulars)) \
      + list(map(lambda x: x["id"], self.standins))

  def remove_banned_people(self, banned_people):
    removed_non_regulars_count = 0
    removed_regulars_count = 0
    removed_standins_count = 0
    for person in banned_people:
      found = False
      for category in [self.non_regulars, self.regulars, self.standins]:
        for i, tp in enumerate(category):
          if tp["id"] == person:
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
    return removed_non_regulars_count, removed_regulars_count, removed_standins_count
  
  def replenish_numbers(self):
    # do only for non regulars for now
    num_total = len(self.non_regulars) + len(self.regulars) + len(self.standins)
    num_to_replace = MAX_PEOPLE_PER_SESSION - num_total
    if num_to_replace <= 0:
      return
    self.standins.extend(self.reserves[:num_to_replace])
    self.reserves = self.reserves[num_to_replace:]

# Indicate if function has executed - else message to return to user stored
class Status():
  def __init__(self):
    self.status = False 
    self.message = ""

  def set_message(self, message):
    self.message = message
  
  def set_success(self):
    self.status = True
