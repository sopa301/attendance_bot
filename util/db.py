from pymongo import MongoClient
from bson import ObjectId
from util.objects import AttendanceList, EventPoll, PollGroup
from util import import_env
import certifi

env_vars = ["MONGO_URL", "MONGO_DB_NAME", "MONGO_COLLECTION_NAME"]
env_config = import_env(env_vars)

# MongoDB configuration
client = MongoClient(env_config["MONGO_URL"]+certifi.where())
db = client[env_config["MONGO_DB_NAME"]]

# Collections
polls_collection = db[env_config["MONGO_COLLECTION_NAME"]]
groups_collection = db[env_config["MONGO_COLLECTION_NAME"]]
attendance_collection = db[env_config["MONGO_COLLECTION_NAME"]]

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
    event_poll = EventPoll.from_dict(polls_collection.find_one({"_id": ObjectId(poll_id)}))
    event_poll.insert_id(poll_id)
    return event_poll

def get_event_polls(poll_ids):
    event_polls = list(map(lambda x: EventPoll.from_dict(x), polls_collection.find({"_id": {"$in": list(map(lambda x: ObjectId(x), poll_ids))}})))
    for i, poll in enumerate(event_polls):
        poll.insert_id(poll_ids[i])
    return event_polls

def get_poll_group(group_id):
    poll_group = PollGroup.from_dict(groups_collection.find_one({"_id": ObjectId(group_id)}))
    poll_group.insert_id(group_id)
    return poll_group

def get_poll_groups_by_owner_id(owner_id):
    poll_group_jsons = list(groups_collection.find({"owner_id": owner_id}))
    poll_groups = list(map(lambda x: PollGroup.from_dict(x), poll_group_jsons))
    for i, group in enumerate(poll_groups):
        group.insert_id(poll_group_jsons[i]["_id"].__str__())
    return poll_groups

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

# Delete functions
def delete_event_poll(poll_id):
    return polls_collection.delete_one({"_id": ObjectId(poll_id)})

def delete_event_polls(poll_ids):
    return polls_collection.delete_many({"_id": {"$in": list(map(lambda x: ObjectId(x), poll_ids))}})

def delete_poll_group(group_id):
    poll_group = get_poll_group(group_id)
    delete_event_polls(poll_group.get_poll_ids())
    return groups_collection.delete_one({"_id": ObjectId(group_id)})


if __name__ == "__main__":
    print("Testing db.py")
    poll = EventPoll("2022-01-01T00:00:00", "2022-01-01T01:00:00", "Test", "Test", [])
    poll_ids = insert_event_polls([poll])
    print(poll_ids)
    poll_group = PollGroup("Test", "Test")
    poll_group.insert_poll_ids(poll_ids)
    group_id = insert_poll_group(poll_group)
    print(get_event_polls(poll_ids))
    print(get_poll_group(group_id))
    add_person_to_event_poll(poll_ids[0], "Test", "non_regulars")
    add_person_to_event_poll(poll_ids[0], "Test", "regulars")
    add_person_to_event_poll(poll_ids[0], "Test", "non_regulars")
    remove_person_from_event_poll(poll_ids[0], "Test", "non_regulars")
    delete_poll_group(group_id)
    # print(get_event_polls())
    print("Done testing db.py")