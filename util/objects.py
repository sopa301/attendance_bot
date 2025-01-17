from enum import Enum

from util.texts import escape_markdown_characters, generate_status_string, ABSENT

class PollType(Enum):
  WEEKLY = 0
  ADHOC = 1

class EventPoll():
  def __init__(self, start_time, end_time, title, details, type, number_of_distinct_groups, allocations):
    self.start_time = start_time # start time of event
    self.end_time = end_time
    self.regulars = []
    self.non_regulars = []
    self.title = title
    self.details = details
    self.type = type
    self.number_of_distinct_groups = number_of_distinct_groups
    self.allocations = allocations

  def to_dict(self):
    return {
      "start_time": self.start_time,
      "end_time": self.end_time,
      "people": self.people,
      "title": self.title,
      "details": self.details
    }
  
  @staticmethod
  def from_dict(dct):
    poll = EventPoll(dct["start_time"], dct["end_time"], dct["title"], dct["details"])
    poll.people = dct["people"]
    return poll

class PollGroup():
  def __init__(self, id, name, number_of_distinct_groups):
    self.polls = []
    self.id = id
    self.name = name
    self.number_of_distinct_groups = number_of_distinct_groups

  def to_dict(self):
    return {
      "polls": [poll.to_dict() for poll in self.polls],
      "id": self.id,
      "name": self.name
    }
  
  @staticmethod
  def from_dict(dct):
    group = PollGroup(dct["id"], dct["name"])
    group.polls = [EventPoll.from_dict(poll) for poll in dct["polls"]]
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