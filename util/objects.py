from enum import Enum
from datetime import datetime
from typing import List

from util.texts import escape_markdown_characters, generate_status_string, ABSENT

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
    self.number_of_distinct_groups = 2
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
  def format_dt_string(iso_dt: str) -> List[str]:
    dt = datetime.fromisoformat(iso_dt)
    print(dt)
    dt_string = dt.strftime("%a, %d %B/%#I%p")
    [date, time, *extra] = dt_string.split('/')
    return [date, time]

  @staticmethod
  def from_dict(dct):
    poll = EventPoll(dct["start_time"], dct["end_time"], dct["title"], dct["details"], dct["allocations"])
    poll.id = dct["id"]
    poll.regulars = dct["regulars"]
    poll.non_regulars = dct["non_regulars"]
    poll.number_of_distinct_groups = 2
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
        poll_header = PollGroup.generate_poll_details_template(poll)
        poll_body.append(f"{i+1}. {poll_header}")
        if membership == "nr":
            lst = poll.non_regulars
            poll_body.append("[Non-Regulars]")
        elif membership == "r":
            lst = poll.regulars
            poll_body.append("[Regulars]")
        else:
            raise ValueError("Invalid poll type: " + membership)
        for j, person in enumerate(lst):
            poll_body.append(f"{j+1}. {person}")
        poll_body.append("\n")
    poll_body = "\n".join(poll_body)
    return poll_body
  
  @staticmethod
  def generate_poll_details_template(poll: EventPoll) -> str:
    [start_date, start_time] = EventPoll.format_dt_string(poll.start_time)
    [end_date, end_time] = EventPoll.format_dt_string(poll.end_time)

    return f"{poll.title}\nDate: {start_date}\nTime: {start_time.lower()} - {end_time.lower()}\nDetails: {poll.details}\n"

class AttendanceList():
  def __init__(self):
    self.id = None
    self.owner_id = None
    self.details = []
    self.non_regulars = []
    self.regulars = []
    self.exco = []
    self.standins = []
  
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
      "standins": self.standins
    }
  
  def find_user_by_id(self, id: int):
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
    return attendance_list

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

# Indicate if function has executed - else message to return to user stored
class Status():
  def __init__(self):
    self.status = False 
    self.message = ""

  def set_message(self, message):
    self.message = message
  
  def set_success(self):
    self.status = True
