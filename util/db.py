from pymongo import MongoClient, UpdateOne
from bson import ObjectId
from util.objects import AttendanceList, EventPoll, PollGroup
from util import import_env
from util.constants import *

env_vars = [
  "MONGO_URL",
  "MONGO_DB_NAME",
  "MONGO_POLLS_COLLECTION_NAME",
  "MONGO_GROUPS_COLLECTION_NAME",
  "MONGO_ATTENANCES_COLLECTION_NAME",
  "MONGO_BANS_COLLECTION_NAME"
]
env_config = import_env(env_vars)

# MongoDB configuration
client = MongoClient(env_config["MONGO_URL"])
db = client[env_config["MONGO_DB_NAME"]]

# Collections
polls_collection = db[env_config["MONGO_POLLS_COLLECTION_NAME"]]
groups_collection = db[env_config["MONGO_GROUPS_COLLECTION_NAME"]]
attendance_collection = db[env_config["MONGO_ATTENANCES_COLLECTION_NAME"]]
bans_collection = db[env_config["MONGO_BANS_COLLECTION_NAME"]]

# Custom error for when objects are not found
class PollNotFoundError(Exception):
  def __init__(self, poll_id):
    self.poll_id = poll_id
    if type(poll_id) is str:
      self.message = "Poll not found with id: " + poll_id
    else:
      self.message = "Polls not found with ids: " + ", ".join(poll_id)
    super().__init__(self.message)

class PollGroupNotFoundError(Exception):
  def __init__(self, group_id):
    self.group_id = group_id
    self.message = "Poll group not found with id: " + group_id
    super().__init__(self.message)

class AttendanceListNotFoundError(Exception):
  def __init__(self, attendance_id):
    self.attendance_id = attendance_id
    self.message = "Attendance list not found with id: " + attendance_id
    super().__init__(self.message)

# Insert functions
def insert_event_poll(poll) -> str:
  return polls_collection.insert_one(poll.to_dict()).inserted_id.__str__()

def insert_event_polls(polls) -> list:
  return insert_event_polls_dicts(list(map(lambda x: x.to_dict(), polls)))

def insert_event_polls_dicts(polls) -> list:
  return list(map(lambda x: x.__str__(), polls_collection.insert_many(polls).inserted_ids))

def insert_poll_group(group):
  return groups_collection.insert_one(group.to_dict()).inserted_id.__str__()

def insert_attendance_list(attendance):
  return attendance_collection.insert_one(attendance.to_dict()).inserted_id.__str__()

# Retrieve functions
def get_event_poll(poll_id):
  event_poll_json = polls_collection.find_one({"_id": ObjectId(poll_id)})
  if event_poll_json is None:
      raise PollNotFoundError(poll_id)
  event_poll = EventPoll.from_dict(event_poll_json)
  event_poll.insert_id(poll_id)
  return event_poll

def get_event_polls(poll_ids):
  event_polls_jsons = list(polls_collection.find({"_id": {"$in": list(map(lambda x: ObjectId(x), poll_ids))}}))
  if len(event_polls_jsons) != len(poll_ids):
      raise PollNotFoundError(poll_ids)
  event_polls = list(map(lambda x: EventPoll.from_dict(x), event_polls_jsons))
  for i, poll in enumerate(event_polls):
      poll.insert_id(poll_ids[i])
  return event_polls

def get_poll_group(group_id):
  poll_group_json = groups_collection.find_one({"_id": ObjectId(group_id)})
  if poll_group_json is None:
      raise PollGroupNotFoundError(group_id)
  poll_group = PollGroup.from_dict(poll_group_json)
  poll_group.insert_id(group_id)
  return poll_group

def get_poll_groups_by_owner_id(owner_id):
  poll_group_jsons = list(groups_collection.find({"owner_id": owner_id}))
  poll_groups = list(map(lambda x: PollGroup.from_dict(x), poll_group_jsons))
  for i, group in enumerate(poll_groups):
      group.insert_id(poll_group_jsons[i]["_id"].__str__())
  return poll_groups

def get_attendance_list(attendance_id):
  attendance_json = attendance_collection.find_one({"_id": ObjectId(attendance_id)})
  if attendance_json is None:
      raise AttendanceListNotFoundError(attendance_id)
  attendance = AttendanceList.from_dict(attendance_json)
  attendance.insert_id(attendance_id)
  return attendance

def get_attendance_lists_by_owner_id(owner_id):
  attendance_jsons = list(attendance_collection.find({"owner_id": owner_id}))
  # print(attendance_jsons)
  attendance_lists = list(map(lambda x: AttendanceList.from_dict(x), attendance_jsons))
  for i, attendance in enumerate(attendance_lists):
      attendance.insert_id(attendance_jsons[i]["_id"].__str__())
  return attendance_lists

# Update functions
def update_poll_group_id(poll_ids, group_id):
  return polls_collection.update_many(
    {"_id": {"$in": list(map(lambda x: ObjectId(x), poll_ids))}},
    {"$set": {"poll_group_id": ObjectId(group_id)}}
  )

def add_person_to_event_poll(poll_id, username, field):
  polls_collection.update_one(
    {"_id": ObjectId(poll_id)},
    {"$addToSet": {field: username}}
  )
    
def remove_person_from_event_poll(poll_id, username, field):
  polls_collection.update_one(
    {"_id": ObjectId(poll_id)},
    {"$pull": {field: username}}
  )

def set_active_status(poll_id, membership, is_active):
  return polls_collection.update_one(
    {"_id": ObjectId(poll_id)},
    {"$set": {f"is_active.{membership.value}": is_active}}
  )

def update_attendance_list(attendance_id, attendance_list:AttendanceList, user_id, new_status):
  category, index = attendance_list.get_category_and_index(user_id)
  return attendance_collection.update_one(
    {"_id": ObjectId(attendance_id)},
    {"$set": {f"{category}.{index}.status": new_status}}
  )

def update_attendance_list_full(attendance_id, attendance_list):
  return attendance_collection.update_one(
    {"_id": ObjectId(attendance_id)},
    {"$set": attendance_list.to_dict()}
  )

def log_attendance_list(attendance_list):
  absent_persons, cancelled_persons = attendance_list.get_non_present_penalisable_names()
  all_persons = absent_persons + cancelled_persons
  existing_records = {doc["username"]: doc for doc in bans_collection.find({"username": {"$in": all_persons}})}

  bulk_operations = []
  for person in absent_persons:
    current_record = existing_records.get(person, {"ban_points": 0, "ban_sessions": 0})
    new_points = current_record["ban_points"] + ABSENT_POINTS
    if new_points >= BAN_THRESHOLD:
      new_points = new_points - BAN_THRESHOLD
      new_sessions = current_record["ban_sessions"] + BAN_DURATION_SESSIONS
    else:
      new_sessions = current_record["ban_sessions"]

    bulk_operations.append(
      UpdateOne(
        {"username": person},
        {"$set": {"ban_points": new_points, "ban_sessions": new_sessions}},
        upsert=True
      )
    )
  for person in cancelled_persons:
    current_record = existing_records.get(person, {"ban_points": 0, "ban_sessions": 0})
    new_points = current_record["ban_points"] + LAST_MINUTE_CANCELLATION_POINTS
    if new_points >= BAN_THRESHOLD:
      new_points = new_points - BAN_THRESHOLD
      new_sessions = current_record["ban_sessions"] + BAN_DURATION_SESSIONS
    else:
      new_sessions = current_record["ban_sessions"]

    bulk_operations.append(
      UpdateOne(
        {"username": person},
        {"$set": {"ban_points": new_points, "ban_sessions": new_sessions}},
        upsert=True
      )
    )
  if bulk_operations:
      bans_collection.bulk_write(bulk_operations)

def get_and_update_banned_personnel(attendance_list):
  all_persons = attendance_list.get_all_player_names()
  banned_persons = []
  existing_records = {doc["username"]: doc for doc in bans_collection.find({"username": {"$in": all_persons}})}
  bulk_operations = []
  for person in all_persons:
    current_record = existing_records.get(person, {"ban_points": 0, "ban_sessions": 0})
    if current_record["ban_sessions"] > 0:
      banned_persons.append(person)
      new_sessions = current_record["ban_sessions"] - 1
      bulk_operations.append(
        UpdateOne(
          {"username": person},
          {"$set": {"ban_sessions": new_sessions}}
        )
      )
  if bulk_operations:
      bans_collection.bulk_write(bulk_operations)
  return banned_persons

# Delete functions
def delete_event_poll(poll_id):
  return polls_collection.delete_one({"_id": ObjectId(poll_id)})

def delete_event_polls(poll_ids):
  return polls_collection.delete_many({"_id": {"$in": list(map(lambda x: ObjectId(x), poll_ids))}})

def delete_poll_group(group_id):
  poll_group = get_poll_group(group_id)
  delete_event_polls(poll_group.get_poll_ids())
  return groups_collection.delete_one({"_id": ObjectId(group_id)})

def delete_attendance_list(attendance_id):
  return attendance_collection.delete_one({"_id": ObjectId(attendance_id)})
