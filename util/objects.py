from enum import Enum

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

class AttendanceList():
  def __init__(self):
    self.details = []
    self.non_regulars = []
    self.regulars = []
    self.exco = []
    self.standins = []
  
  def to_dict(self):
    return {
      "details": self.details,
      "non_regulars": self.non_regulars,
      "regulars": self.regulars,
      "standins": self.standins,
      "exco": self.exco
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

    index = 0
    non_regulars = []
    for s in lines[lines.index("Non regulars")+1:lines.index("Regulars")]:
        if s == "":
            continue
        non_regulars.append({"name": s[s.index('.')+1:].strip(), "status": ABSENT, "id": index, "membership": "nr"})
        index += 1
    attendance_list.non_regulars = non_regulars

    regulars = []
    for s in lines[lines.index("Regulars")+1:lines.index("Standins")]:
        if s == "":
            continue
        regulars.append({"name": s[s.index('.')+1:].strip(), "status": ABSENT, "id": index, "membership": "r"})
        index += 1
    attendance_list.regulars = regulars

    standins = []
    for s in lines[lines.index("Standins")+1:lines.index("Exco")]:
        if s == "":
            continue
        standins.append({"name": s[s.index('.')+1:].strip(), "status": ABSENT, "id": index, "membership": "nr"})
        index += 1
    attendance_list.standins = standins

    exco = []
    for s in lines[lines.index("Exco")+1:]:
        if s == "":
            break
        exco.append(s)
    attendance_list.exco = exco

    return attendance_list
  
  @classmethod
  def from_poll(poll):
    attendance_list = AttendanceList()
    attendance_list.details = [poll.title, poll.details]
    attendance_list.non_regulars = [{"name": person, "status": ABSENT, "id": i, "membership": "nr"} for i, person in enumerate(poll.people)]
    return attendance_list