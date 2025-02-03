from enum import Enum
from datetime import datetime, timedelta
from typing import List

from util.texts import escape_markdown_characters, generate_status_string, ABSENT, LAST_MINUTE_CANCELLATION
from util.constants import *

class PollType(Enum):
  WEEKLY = 0
  ADHOC = 1

# TODO: figure out how to handle old poll messages when the poll group is deleted
# also handle the updating of all messages when a poll is updated
# also handle the updating of all messages after the week passes
class EventPoll():
  def __init__(self, start_time, end_time, details, allocations):
    self.id = None
    self.start_time = start_time # start time of event
    self.end_time = end_time
    self.regulars = []
    self.non_regulars = []
    self.details = details
    self.type = PollType.WEEKLY
    self.is_active = True
    self.allocations = allocations
    self.poll_group_id = None

  def get_title(self):
    [start_date, start_time] = EventPoll.format_dt_string(self.start_time)
    [_, end_time] = EventPoll.format_dt_string(self.end_time)
    return f"{start_date} {start_time} - {end_time}"

  def to_dict(self):
    return {
      "id": self.id,
      "start_time": self.start_time,
      "end_time": self.end_time,
      "regulars": self.regulars,
      "non_regulars": self.non_regulars,
      "is_active": self.is_active,
      "details": self.details,
      "type": self.type.value,
      "allocations": self.allocations,
      "poll_group_id": self.poll_group_id
    }
  
  @staticmethod
  def format_dt_string(iso_dt: str) -> List[str]:
    dt = datetime.fromisoformat(iso_dt)
    dt_string = dt.strftime("%a, %d/%m/%Y_%#I:%M%p").replace(":00", "")
    date, time, *_ = dt_string.split('_')
    time = time.lstrip('0')
    return date, time

  @staticmethod
  def from_dict(dct):
    poll = EventPoll(dct["start_time"], dct["end_time"], dct["details"], dct["allocations"])
    poll.id = dct["id"]
    poll.regulars = dct["regulars"]
    poll.non_regulars = dct["non_regulars"]
    poll.type = PollType(dct["type"])
    poll.poll_group_id = dct["poll_group_id"]
    poll.is_active = dct["is_active"] if "is_active" in dct else True
    return poll
  
  def get_people_list_by_membership(self, membership: Membership):
    if membership == Membership.REGULAR:
      return self.regulars
    elif membership == Membership.NON_REGULAR:
      return self.non_regulars
    raise ValueError("Invalid membership: " + membership)

  def generate_poll_details_template(self, markdownV2 = True) -> list:
    [start_date, start_time] = EventPoll.format_dt_string(self.start_time)
    [_, end_time] = EventPoll.format_dt_string(self.end_time)
    if markdownV2:
      out = []
      out.append(f"*__Date\: {escape_markdown_characters(start_date)}__*")
      out.append(f"Time\: {escape_markdown_characters(start_time.lower())} \- {escape_markdown_characters(end_time.lower())}")
      out.append(f"{escape_markdown_characters(self.details)}")
      return out
    return list((f"Date: {start_date}", f"Time: {start_time.lower()} - {end_time.lower()}", f"{self.details}"))

  def insert_id(self, id):
    self.id = id

  def is_person_status_changed(self, username, membership: Membership, new_sign_up_status):
    if membership == Membership.REGULAR:
      is_present = username in self.regulars
    elif membership == Membership.NON_REGULAR:
      is_present = username in self.non_regulars
    else:
      raise ValueError("Invalid membership: " + membership)
    return is_present != new_sign_up_status
  
  def get_active_status_representation(self):
    return ACTIVE_SYMBOL if self.is_active else INACTIVE_SYMBOL

# TODO: create the aggregated poll results in the db as well for efficient access.
# remember to use transactions to ensure that the poll results are consistent
class PollGroup():
  def __init__(self, owner_id, name):
    self.polls_ids = []
    self.owner_id = owner_id
    self.id = None
    self.name = name

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
  
  def generate_next_group(self, new_poll_name):
    new_group = PollGroup(self.owner_id, new_poll_name)
    return new_group
  
  @staticmethod
  def generate_next_polls(polls: list):
    new_polls = []
    for poll in polls:
      new_start_time = datetime.fromisoformat(poll.start_time) + timedelta(weeks=1)
      new_start_time = new_start_time.isoformat()
      new_end_time = datetime.fromisoformat(poll.end_time) + timedelta(weeks=1)
      new_end_time = new_end_time.isoformat()
      new_poll = EventPoll(new_start_time, new_end_time, poll.details, poll.allocations)
      new_polls.append(new_poll)
    return new_polls
  
  @staticmethod
  def from_dict(dct):
    group = PollGroup(dct["owner_id"], dct["name"])
    group.id = dct["id"]
    group.polls_ids = dct["polls_ids"]
    return group
  
  # To be used with MarkdownV2
  def generate_overview_text(self, polls: list) -> str:
    out = [
      self.generate_poll_group_text(polls, Membership.NON_REGULAR),
      escape_markdown_characters("-------------------------"),
      self.generate_poll_group_text(polls, Membership.REGULAR),
    ]
    return "\n".join(out)

  # To be used with Markdownv2
  def generate_poll_group_text(self, polls: list, membership: Membership) -> str:
    title = escape_markdown_characters(self.name)
    membership_of_poll = membership.to_representation()
    membership_of_poll = escape_markdown_characters(f"({membership_of_poll})")
    poll_body = [f"*{title} {membership_of_poll}*", ""]
    for i, poll in enumerate(polls):
        if not poll.is_active:
          continue
        poll_header = poll.generate_poll_details_template()
        poll_body.extend(poll_header)
        lst = poll.get_people_list_by_membership(membership)
        for j, person in enumerate(lst):
          poll_body.append(f"{j+1}\. {escape_markdown_characters(person)}")
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
      "non_regulars": list(map(lambda x: x.to_dict(), self.non_regulars)),
      "regulars": list(map(lambda x: x.to_dict(), self.regulars)),
      "exco": self.exco,
      "standins": list(map(lambda x: x.to_dict(), self.standins)),
      "reserves": list(map(lambda x: x.to_dict(), self.reserves))
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
        return user.membership.to_db_representation(), self.non_regulars.index(user)
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

  def generate_summary_text(self):
    output_list = []
    for line in self.details:
        output_list.append(escape_markdown_characters(line))
    output_list.append("")

    output_list.append(escape_markdown_characters("Non-Regulars"))
    for i, tp in enumerate(self.non_regulars):
      output_list.append(generate_status_string(tp.status, tp.name, i+1))

    output_list.append("")

    output_list.append("Regulars")
    for i, tp in enumerate(self.regulars):
      output_list.append(generate_status_string(tp.status, tp.name, i+1))

    if len(self.standins) > 0:
      output_list.append("")

      output_list.append("Standins")
      for i, tp in enumerate(self.standins):
        output_list.append(generate_status_string(tp.status, tp.name, i+1))

    return "\n".join(output_list)

  def get_title(self):
    return self.details[0]

  @staticmethod
  def from_dict(dct):
    attendance_list = AttendanceList()
    attendance_list.owner_id = dct["owner_id"]
    attendance_list.id = dct["id"]
    attendance_list.details = dct["details"]
    attendance_list.non_regulars = list(map(lambda x: Person.from_dict(x), dct["non_regulars"]))
    attendance_list.regulars = list(map(lambda x: Person.from_dict(x), dct["regulars"]))
    attendance_list.exco = dct["exco"]
    attendance_list.standins = list(map(lambda x: Person.from_dict(x), dct["standins"]))
    attendance_list.reserves = list(map(lambda x: Person.from_dict(x), dct["reserves"])) if "reserves" in dct else []
    return attendance_list

  def to_parsable_list(self):
    output_list = []
    for line in self.details:
        output_list.append(line)
    output_list.append("")

    output_list.append(escape_markdown_characters("Non-Regulars"))
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
    for i, s in enumerate(lines[:lines.index("Non-Regulars")]):
        if s != "":
            last_non_empty_line = i
        session_info.append(s)
    session_info = session_info[:last_non_empty_line+1]
    attendance_list.details = session_info
    attendance_list.non_regulars = AttendanceList.parse_section(lines, "Non-Regulars", "Regulars", Membership.NON_REGULAR)
    attendance_list.regulars = AttendanceList.parse_section(lines, "Regulars", "Standins", Membership.REGULAR)
    attendance_list.standins = AttendanceList.parse_section(lines, "Standins", "Exco", Membership.NON_REGULAR)

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
      lst.append(Person(name, name, ABSENT, membership))
    return lst

  def insert_id(self, id):
    self.id = id

  @staticmethod
  def from_poll(poll: EventPoll):
    attendance_list = AttendanceList()
    attendance_list.details = [poll.get_title(), poll.details]
    attendance_list.regulars = list(map(lambda name: Person(name, name, ABSENT, Membership.REGULAR), poll.regulars))[:poll.allocations[1]]
    num_regulars = len(attendance_list.regulars)
    temp = list(map(lambda name: Person(name, name, ABSENT, Membership.NON_REGULAR), poll.non_regulars))
    attendance_list.non_regulars = temp[:max(poll.allocations[0], MAX_PEOPLE_PER_SESSION - num_regulars)]
    attendance_list.reserves = temp[max(poll.allocations[0], MAX_PEOPLE_PER_SESSION - num_regulars):]

    return attendance_list
  
  @staticmethod
  def get_non_present_penalisable_names_from_list(lst, condition, absent_list, cancelled_list):
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
    absent, cancelled = self.get_non_present_penalisable_names_from_list(self.non_regulars, PENALISE_NON_REGULARS, absent, cancelled)
    absent, cancelled = self.get_non_present_penalisable_names_from_list(self.regulars, PENALISE_REGULARS, absent, cancelled)
    absent, cancelled = self.get_non_present_penalisable_names_from_list(self.standins, PENALISE_STANDINS, absent, cancelled)
    return absent, cancelled
  
  def get_all_player_names(self):
    return list(map(lambda x: x.id, self.non_regulars)) \
      + list(map(lambda x: x.id, self.regulars)) \
      + list(map(lambda x: x.id, self.standins))

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
    return removed_non_regulars_count, removed_regulars_count, removed_standins_count
  
  def replenish_numbers(self):
    # do only for non regulars for now
    num_total = len(self.non_regulars) + len(self.regulars) + len(self.standins)
    num_to_replace = MAX_PEOPLE_PER_SESSION - num_total
    if num_to_replace <= 0:
      return
    self.non_regulars.extend(self.reserves[:num_to_replace])
    self.reserves = self.reserves[num_to_replace:]

class Person():
  def __init__(self, id=None, name=None, status=None, membership=None):
    self.id = id
    self.name = name
    self.status = status
    self.membership = membership

  def to_dict(self):
    return {
      "id": self.id,
      "name": self.name,
      "status": self.status,
      "membership": self.membership.value
    }
  
  @staticmethod
  def from_dict(dct):
    person = Person()
    person.id = dct["id"]
    person.name = dct["name"]
    person.status = dct["status"]
    person.membership = Membership(dct["membership"])
    return person

# Indicate if function has executed - else message to return to user stored
class Status():
  def __init__(self):
    self.status = False 
    self.message = ""

  def set_message(self, message):
    self.message = message
  
  def set_success(self):
    self.status = True
